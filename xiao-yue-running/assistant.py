"""Local Garmin reader: Windows DPAPI secrets, SQLite history, official API only."""
from __future__ import annotations
import argparse, getpass, io, json, os, sqlite3, sys, time, zipfile
import msvcrt
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from contextlib import contextmanager
import win32crypt
from garmin_personal_api import GarminPersonalApiClient, PersonalApiAuthenticator
from garmin_personal_api.auth import BearerToken
from garmin_personal_api.errors import HttpError

ROOT=Path(__file__).resolve().parent
SECRET=ROOT/'.secrets'; DATA=ROOT/'data'; DB=DATA/'garmin.sqlite3'
TZ=timezone(timedelta(hours=8))
def now():return datetime.now(TZ).isoformat(timespec='seconds')
def today():return datetime.now(TZ).date()
def dump(value):return json.dumps(value,ensure_ascii=False,default=str)
def secure_write(path,content):
    path.parent.mkdir(parents=True,exist_ok=True)
    encrypted=win32crypt.CryptProtectData(content,None,None,None,None,1)
    tmp=path.with_suffix('.tmp');tmp.write_bytes(encrypted);tmp.replace(path)
def secure_read(path):return win32crypt.CryptUnprotectData(path.read_bytes(),None,None,None,1)[1]
class EncryptedAuthenticator(PersonalApiAuthenticator):
    def _read_cached_token(self,fingerprint):
        path=self.bearer_token_cache_file
        if not path.exists():return None
        cache=json.loads(secure_read(path))
        if cache['fingerprint']!=fingerprint:return None
        return BearerToken(cache['access_token'],float(cache['expires_at']))
    def _write_cached_token(self,fingerprint,token):
        secure_write(self.bearer_token_cache_file,dump({'fingerprint':fingerprint,'access_token':token.access_token,'expires_at':token.expires_at}).encode())

@contextmanager
def connect_db():
    DATA.mkdir(exist_ok=True)
    c=sqlite3.connect(DB,timeout=30)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    c.executescript('''
      CREATE TABLE IF NOT EXISTS activities(id INTEGER PRIMARY KEY, day TEXT, summary TEXT NOT NULL, detail TEXT, laps TEXT, updated TEXT);
      CREATE TABLE IF NOT EXISTS health(kind TEXT, start TEXT, end TEXT, payload TEXT, updated TEXT, PRIMARY KEY(kind,start,end));
      CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY, started TEXT, ended TEXT, status TEXT, result TEXT);
    ''')
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:c.close()

def safe_error(e):
    # Never return response bodies, headers, URLs, tokens, or health payloads in logs.
    return {'type':type(e).__name__,'http_status':getattr(e,'status_code',None)}
class Source:
    def __init__(self):
        if os.environ.get('GARMIN_PERSONAL_API_BASE_URL'):
            raise ValueError('自定义 API 地址未启用，避免凭证发送到意外主机')
        self.auth=EncryptedAuthenticator(timeout=25,bearer_token_cache_file=SECRET/'bearer.dpapi')
        region=json.loads((ROOT/'config.json').read_text(encoding='utf-8')).get('region','com')
        hosts={'com':'https://personal.connectapi.garmin.com','cn':'https://personal.connectapi.garmin.cn'}
        self.base_url=hosts[region]
        self.auth.base_url=self.base_url
        self.key=secure_read(SECRET/'key.dpapi').decode().strip()
        token=self.auth.obtain_token(self.key)
        self.client=GarminPersonalApiClient(token.access_token,timeout=25)
        self.client.base_url=self.base_url
    def call(self,method,*args,**kwargs):
        for attempt in range(3):
            time.sleep(0.35)
            try:return getattr(self.client,method)(*args,**kwargs)
            except HttpError as e:
                if e.status_code==401 and attempt==0:
                    t=self.auth.obtain_token(self.key,force_refresh=True)
                    self.client.update_bearer_token(t.access_token);continue
                if e.status_code==429 or 500<=e.status_code<600:
                    if attempt<2:time.sleep(5*(attempt+1));continue
                raise
    def close(self):self.client.close();self.auth.close();self.key=''

RANGE={
 'stress':'get_daily_stress','steps':'get_daily_steps','hydration':'get_daily_hydration',
 'weight':'get_weight_measurements','weight_goals':'get_effective_weight_goals',
 'sleep_summaries':'get_daily_sleep_summaries','body_battery':'get_daily_body_battery',
 'daily_summaries':'get_daily_summaries','hrv_summaries':'get_daily_hrv_summaries',
 'wellness_activities':'get_wellness_activity_summaries'}
DAILY={'sleep':'get_daily_sleep','heart_rate':'get_daily_heart_rate','hrv':'get_daily_hrv',
       'spo2':'get_daily_spo2','fitness_age':'get_fitness_age','food_logs':'get_daily_food_logs'}
def sync(*args,**kwargs):
    DATA.mkdir(exist_ok=True)
    with (DATA/'sync.lock').open('a+b') as lock:
        lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:raise RuntimeError('已有同步进程，请稍后重试')
        try:return _sync(*args,**kwargs)
        finally:
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
def _sync(days=7,activity_limit=100,health=True,source=None,start_date=None,end_date=None):
    if not 1<=days<=31 or not 1<=activity_limit<=2000:raise ValueError('days 1..31; limit 1..2000')
    end=date.fromisoformat(end_date) if end_date else today()
    start=date.fromisoformat(start_date) if start_date else end-timedelta(days=days-1)
    if start>end or (end-start).days>30:raise ValueError('每批日期范围不超过31天')
    with connect_db() as c:
        run=c.execute('INSERT INTO runs(started,status) VALUES(?,?)',(now(),'running')).lastrowid;c.commit()
        result={'activities':0,'health_sets':0,'errors':[],'start':str(start),'end':str(end)}
        own=source is None
        try:
            source=source or Source()
            def attempt(kind,fn):
                try:return True,fn()
                except Exception as e:
                    result['errors'].append({'dataset':kind,**safe_error(e)})
                    if getattr(e,'status_code',None) in (401,429):raise
                    return False,None
            offset=0
            while offset<activity_limit:
                batch=source.call('search_activities',start=offset,limit=min(100,activity_limit-offset),start_date=str(start),end_date=str(end))
                if not isinstance(batch,list):raise ValueError('活动列表格式不符合官方接口预期')
                if not batch:break
                for a in batch:
                    aid=int(a['activityId']);day=str(a.get('startTimeLocal') or a.get('startTimeGMT') or '')[:10]
                    old=c.execute('SELECT detail,laps FROM activities WHERE id=?',(aid,)).fetchone()
                    detail=old['detail'] if old else None; laps=old['laps'] if old else None
                    ok,value=attempt(f'activity:{aid}',lambda:source.call('get_activity',aid))
                    if ok:detail=dump(value)
                    archive=DATA/'fit'/f'{aid}.zip';archive.parent.mkdir(exist_ok=True)
                    if not archive.exists():
                        ok,value=attempt(f'fit:{aid}',lambda:source.call('download_activity',aid))
                        if ok:
                            with zipfile.ZipFile(io.BytesIO(value)) as z:
                                if z.testzip():raise ValueError('无效活动压缩包')
                            tmp=archive.with_suffix('.tmp');tmp.write_bytes(value);tmp.replace(archive)
                    if archive.exists():
                        ok,value=attempt(f'laps:{aid}',lambda:parse_laps(archive))
                        if ok:laps=dump(value)
                    c.execute('''INSERT INTO activities VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                      day=excluded.day,summary=excluded.summary,detail=excluded.detail,laps=excluded.laps,updated=excluded.updated''',
                      (aid,day,dump(a),detail,laps,now()));c.commit();result['activities']+=1
                offset+=len(batch)
                if len(batch)<min(100,activity_limit-(offset-len(batch))):break
            result['activity_limit_reached']=offset>=activity_limit
            if health:
                jobs=[(k,str(start),str(end),m,(str(start),str(end))) for k,m in RANGE.items()]
                for n in range((end-start).days+1):
                    day=str(start+timedelta(days=n));jobs += [(k,day,day,m,(day,)) for k,m in DAILY.items()]
                jobs += [('profile',str(end),str(end),'get_user_profile_settings',()),('heart_rate_zones',str(end),str(end),'get_heart_rate_zones',())]
                for kind,s,e,method,args in jobs:
                    ok,value=attempt(kind,lambda:source.call(method,*args))
                    if ok:
                        c.execute('INSERT OR REPLACE INTO health VALUES(?,?,?,?,?)',(kind,s,e,dump(value),now()));c.commit();result['health_sets']+=1
            status='partial' if result['errors'] or result['activity_limit_reached'] else 'success'
        except Exception as e:
            status='failed';result['errors'].append({'dataset':'sync',**safe_error(e)})
        finally:
            if own and source:source.close()
            c.execute('UPDATE runs SET ended=?,status=?,result=? WHERE id=?',(now(),status,dump(result),run));c.commit()
        return {'status':status,**result}

def parse_laps(archive):
    import fitdecode
    laps=[]
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if name.lower().endswith('.fit'):
                info=z.getinfo(name)
                if info.file_size>100_000_000:raise ValueError('FIT 文件过大')
                with fitdecode.FitReader(io.BytesIO(z.read(name))) as reader:
                    for frame in reader:
                        if frame.frame_type==fitdecode.FIT_FRAME_DATA and frame.name=='lap':
                            laps.append({f.name:{'value':str(f.value) if isinstance(f.value,datetime) else f.value,'units':f.units} for f in frame.fields})
    return laps

def recent(limit=20):
    if not 1<=limit<=100:raise ValueError('limit 1..100')
    with connect_db() as c:
        values=[json.loads(r[0]) for r in c.execute('SELECT summary FROM activities ORDER BY day DESC,id DESC LIMIT ?',(limit,))]
    fields=['activityId','activityType','startTimeLocal','startTimeGMT','distance','duration','movingDuration','averageHR','maxHR','averageSpeed','elevationGain','elevationLoss','averageRunningCadenceInStepsPerMinute','vo2MaxValue','minElevation','maxElevation']
    return [{k:a[k] for k in fields if k in a} for a in values]

def training_summary(start,end,running_only=True):
    s=date.fromisoformat(start);e=date.fromisoformat(end)
    if s>e or (e-s).days>366:raise ValueError('查询范围为0..366天')
    with connect_db() as c:items=[json.loads(r[0]) for r in c.execute('SELECT summary FROM activities WHERE day BETWEEN ? AND ?',(start,end))]
    if running_only:items=[a for a in items if 'running' in str(a.get('activityType',{})).lower()]
    dist=sum(a.get('distance') or 0 for a in items);seconds=sum(a.get('duration') or 0 for a in items)
    weighted=[(a.get('averageHR'),a.get('duration') or 0) for a in items if a.get('averageHR') is not None and (a.get('duration') or 0)>0]
    return {'start':start,'end':end,'activity_count':len(items),'distance_km':round(dist/1000,3),'duration_hours':round(seconds/3600,3),
            'aggregate_pace_seconds_per_km':round(seconds/(dist/1000),1) if dist else None,
            'duration_weighted_average_hr':round(sum(h*t for h,t in weighted)/sum(t for _,t in weighted),1) if weighted else None,
            'running_only':running_only,'interpretation':'汇总配速混合不同训练及海拔，不能直接等同于能力变化。'}

def status():
    with connect_db() as c:
        last=c.execute('SELECT * FROM runs ORDER BY id DESC LIMIT 1').fetchone()
        return {'credential_configured':(SECRET/'key.dpapi').exists(),'activities':c.execute('SELECT count(*) FROM activities').fetchone()[0],
          'health_sets':c.execute('SELECT count(*) FROM health').fetchone()[0],
          'last_sync':dict(last) if last else None,'timezone':'Asia/Shanghai','data_path':str(DATA)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['configure','status','sync','check'])
    parser.add_argument('--key-file');parser.add_argument('--days',type=int,default=7);parser.add_argument('--limit',type=int,default=100)
    parser.add_argument('--activities-only',action='store_true');parser.add_argument('--start');parser.add_argument('--end')
    args=parser.parse_args()
    try:
        if args.command=='configure':
            key=Path(args.key_file).read_text(encoding='utf-8-sig').strip() if args.key_file else getpass.getpass('Garmin Personal API Key（输入不回显）: ').strip()
            if not key or any(x.isspace() for x in key):raise ValueError('请提供只含 API Key 的文本文件')
            secure_write(SECRET/'key.dpapi',key.encode());key='';print('密钥已通过当前 Windows 用户的 DPAPI 加密保存。')
        elif args.command=='status':print(dump(status()))
        elif args.command=='check':
            s=Source()
            try:
                values=s.call('search_activities',start=0,limit=1)
                print(dump({'status':'connected','activity_list_received':isinstance(values,list),'returned_count':len(values) if isinstance(values,list) else None}))
            finally:s.close()
        else:
            result=sync(args.days,args.limit,not args.activities_only,start_date=args.start,end_date=args.end)
            print(dump(result));sys.exit(0 if result['status']=='success' else 2)
    except Exception as e:
        print(dump({'status':'error',**safe_error(e)}));sys.exit(1)
if __name__=='__main__':main()
