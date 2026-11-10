"""Normalize the observed Keep privacy-export table; no account or route URL output."""
from datetime import datetime, timezone
from urllib.parse import urlparse
import hashlib,json,math

HEADERS=['运动类型','运动时长(秒)','开始时间','结束时间','卡路里','运动距离(米)','平均心率','最大心率','心率记录','运动轨迹']
SPORTS={'跑步':'running','骑行':'cycling','健身':'training'}

def number(value):
    if value is None or value=='' or isinstance(value,bool):return None
    try:
        n=float(value);return n if math.isfinite(n) else None
    except (ValueError,TypeError):return None

def parse_time(value,source_timezone):
    if isinstance(value,datetime):parsed=value
    else:
        try:parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        except ValueError:raise ValueError('无法识别日期格式，请核对来源') from None
    if parsed.tzinfo is None:
        if source_timezone is None:raise ValueError('无时区时间必须显式指定来源时区')
        parsed=parsed.replace(tzinfo=source_timezone)
    return parsed.astimezone(timezone.utc)

def parse_heart_rate(value):
    if value in ('',None):return [],[]
    try:data=json.loads(value) if isinstance(value,str) else value
    except (ValueError,TypeError):raise ValueError('心率记录不是有效JSON数组') from None
    if not isinstance(data,list) or len(data)>200_000:raise ValueError('不支持的心率记录结构或长度')
    samples=[];flags=[]
    for raw in data:
        n=number(raw)
        samples.append(n if n is not None and 25<=n<=250 else None)
    if any(v is None for v in samples):flags.append('heart_rate_sequence_has_missing_or_invalid_values')
    return samples,flags

def map_activity(headers,row,source_timezone=None,include_samples=False):
    if list(headers)!=HEADERS or len(row)!=len(HEADERS):raise ValueError('Keep表头或列数变化，停止自动映射')
    r=dict(zip(headers,row));start=parse_time(r['开始时间'],source_timezone);end=parse_time(r['结束时间'],source_timezone)
    duration=number(r['运动时长(秒)']);distance=number(r['运动距离(米)'])
    if duration is None or duration<=0:raise ValueError('运动时长缺失或无效')
    if distance is None or distance<0:raise ValueError('运动距离缺失或无效')
    elapsed=(end-start).total_seconds()
    if elapsed<0:raise ValueError('结束时间早于开始时间')
    samples,flags=parse_heart_rate(r['心率记录'])
    if abs(elapsed-duration)>1:flags.append('wall_elapsed_differs_from_reported_duration')
    avg,max_hr=number(r['平均心率']),number(r['最大心率'])
    avg=avg if avg is not None and 25<=avg<=250 else None
    max_hr=max_hr if max_hr is not None and 25<=max_hr<=250 else None
    if avg is not None and max_hr is not None and max_hr<avg:flags.append('maximum_hr_below_average_hr')
    route=str(r['运动轨迹'] or '');parsed=urlparse(route)
    image=parsed.scheme in ('http','https') and parsed.path.lower().endswith(('.jpg','.jpeg','.png','.webp'))
    sport_label=str(r['运动类型']);fingerprint='|'.join(map(str,[start.isoformat(),end.isoformat(),duration,distance,sport_label]))
    result={'id':'keep:'+hashlib.sha256(fingerprint.encode()).hexdigest()[:24],
            'source':'keep_privacy_export','mapping_version':1,'sport':SPORTS.get(sport_label),
            'source_sport_label':sport_label,'start_time_utc':start.isoformat(),'end_time_utc':end.isoformat(),
            'duration_s':duration,'wall_elapsed_s':elapsed,'distance_m':distance,
            'calculated_pace_s_per_km':duration/(distance/1000) if distance>0 else None,
            'reported_pace_s_per_km':None,'avg_hr_bpm':avg,'max_hr_bpm':max_hr,
            'calories_kcal':number(r['卡路里']),'heart_rate_sample_count':len(samples),
            'heart_rate_sample_interval_s':None,'heart_rate_samples_have_timestamps':False,
            'route_representation':'image_reference' if image else 'unverified_reference' if route else None,
            'flags':flags}
    if include_samples:result['heart_rate_samples_bpm']=samples
    return result
