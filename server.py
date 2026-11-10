"""Read-only MCP. No Garmin credentials, SQL execution, sync writes, or GPS tools."""
import json
from mcp.server.fastmcp import FastMCP
import assistant as a
mcp=FastMCP('Garmin Running Assistant')
def without_location(v):
    if isinstance(v,dict):return {k:without_location(x) for k,x in v.items() if not any(s in k.lower() for s in ['latitude','longitude','position','coordinate','location','address','displayname','fullname','email','firstname','lastname','polyline','geometry','route','track','waypoint','owner','userprofile'])}
    if isinstance(v,list):return [without_location(x) for x in v]
    return v
@mcp.tool(annotations={'readOnlyHint':True})
def get_sync_status()->dict:
    """同步状态和数据覆盖。首次配置缺失时不会声称已连接。"""
    return a.status()
@mcp.tool(annotations={'readOnlyHint':True})
def get_recent_activities(limit:int=20)->list:
    """最近活动概要，距离米、时间秒，不提供GPS坐标。"""
    return a.recent(limit)
@mcp.tool(annotations={'readOnlyHint':True})
def get_activity_detail(activity_id:int)->dict:
    """本地已同步的活动详情，省略精确位置及身份字段。"""
    with a.connect_db() as c:r=c.execute('SELECT summary,detail FROM activities WHERE id=?',(activity_id,)).fetchone()
    return without_location({'summary':json.loads(r['summary']),'detail':json.loads(r['detail']) if r['detail'] else None}) if r else {'error':'activity_not_synced'}
@mcp.tool(annotations={'readOnlyHint':True})
def get_activity_laps(activity_id:int)->dict:
    """从原始 FIT 解码的分圈数据及单位；无分圈时不捏造。"""
    with a.connect_db() as c:r=c.execute('SELECT laps FROM activities WHERE id=?',(activity_id,)).fetchone()
    return {'activity_id':activity_id,'laps':without_location(json.loads(r[0])) if r and r[0] else [],'source':'original FIT'}
@mcp.tool(annotations={'readOnlyHint':True})
def get_health_trends(kind:str,start_date:str,end_date:str)->dict:
    """查询指定数据集和日期范围；返回原始字段及实际覆盖日期，缺失不表示零。"""
    a.date.fromisoformat(start_date);a.date.fromisoformat(end_date)
    if start_date>end_date:raise ValueError('日期顺序错误')
    if kind not in set(a.RANGE)|set(a.DAILY)|{'heart_rate_zones'}:raise ValueError('不支持此数据集')
    with a.connect_db() as c:
        rows=c.execute('SELECT start,end,payload,updated FROM health WHERE kind=? AND start<=? AND end>=? ORDER BY start LIMIT 366',(kind,end_date,start_date)).fetchall()
    return {'kind':kind,'requested_start':start_date,'requested_end':end_date,'note':'范围型结果保留源批次完整日期，分析时需按 requested 日期过滤，重复批次需去重。',
      'batches':[{'start':r[0],'end':r[1],'data':without_location(json.loads(r[2])),'updated':r[3]} for r in rows]}
@mcp.tool(annotations={'readOnlyHint':True})
def get_training_summary(start_date:str,end_date:str,running_only:bool=True)->dict:
    """指定期间跑量、次数、总时长和加权平均心率。"""
    return a.training_summary(start_date,end_date,running_only)
@mcp.tool(annotations={'readOnlyHint':True})
def compare_periods(first_start:str,first_end:str,second_start:str,second_end:str)->dict:
    """对比两个时间段，不把不同海拔环境下的配速变化判定为体能变化。"""
    return {'first':a.training_summary(first_start,first_end),'second':a.training_summary(second_start,second_end)}
if __name__=='__main__':mcp.run(transport='stdio')
