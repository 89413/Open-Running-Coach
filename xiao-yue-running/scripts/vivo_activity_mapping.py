"""Explicit mapping for the observed 45-column vivo privacy export layout.

Basic fields have one screenshot cross-check. Type codes beyond that observation,
sleep semantics and remaining generic columns are intentionally not inferred.
"""
from datetime import datetime, timezone
import hashlib
import math

FIELDS = {
    'start_ms': (1, '运动时长'), 'end_ms': (2, '运动时长1'),
    'distance_m': (4, '运动距离'), 'duration_ms': (5, '运动时长2'),
    'computed_export_pace': (6, '运动速率'), 'fastest_pace': (7, '运动速率1'),
    'slowest_pace': (8, '运动速率2'), 'calories': (9, '消耗热量'),
    'type_code': (11, '运动类型'), 'avg_hr': (12, '运动心率'),
    'cadence_spm': (13, '运动频率'), 'stride_cm': (14, '运动速率3'),
    'steps': (15, '步数'), 'display_pace': (25, '运动速率6'),
}


def numeric(value):
    if value is None or value == '' or isinstance(value, bool): return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError): return None


def validate_headers(headers):
    if len(headers) != 45: raise ValueError('未匹配已核对的45列导出结构，请先检查新版本布局')
    for field, (index, label) in FIELDS.items():
        if headers[index] != label: raise ValueError(f'字段位置变化：{field}；停止自动映射')


def map_activity(headers, row):
    validate_headers(headers)
    if len(row) != len(headers): raise ValueError('记录列数与表头不一致')
    v = {field: numeric(row[index]) for field, (index, _) in FIELDS.items()}
    for field in ['start_ms', 'end_ms', 'distance_m', 'duration_ms']:
        if v[field] is None: raise ValueError(f'必要字段缺失或无效：{field}')
    if v['distance_m'] <= 0 or v['duration_ms'] <= 0: raise ValueError('距离与计时时长须大于零')
    start = datetime.fromtimestamp(v['start_ms'] / 1000, timezone.utc)
    end = datetime.fromtimestamp(v['end_ms'] / 1000, timezone.utc)
    elapsed = (end - start).total_seconds()
    if elapsed < 0: raise ValueError('结束时间早于开始时间')
    duration = v['duration_ms'] / 1000
    calculated_pace = duration / (v['distance_m'] / 1000)
    flags = []
    if abs(elapsed - duration) > 1: flags.append('elapsed_differs_from_reported_duration')
    reported_pace = v['display_pace'] if v['display_pace'] is not None and v['display_pace'] > 0 else None
    if reported_pace is not None and abs(reported_pace - calculated_pace) > 1:
        flags.append('reported_pace_differs_from_duration_distance_ratio')
    if duration > elapsed + 1: flags.append('reported_duration_exceeds_elapsed')
    fingerprint = '|'.join(str(v[k]) for k in ['start_ms','end_ms','distance_m','duration_ms','type_code'])
    avg_hr = v['avg_hr'] if v['avg_hr'] is not None and 25 <= v['avg_hr'] <= 250 else None
    return {
        'id': 'vivo:' + hashlib.sha256(fingerprint.encode()).hexdigest()[:24],
        'source': 'vivo_health_privacy_export', 'mapping_version': 1,
        'start_time_utc': start.isoformat(), 'end_time_utc': end.isoformat(),
        'distance_m': v['distance_m'], 'duration_s': duration, 'elapsed_s': elapsed,
        'reported_pace_s_per_km': reported_pace,
        'calculated_pace_s_per_km': calculated_pace,
        'export_ratio_pace_s_per_km': v['computed_export_pace'],
        'fastest_reported_pace_s_per_km': v['fastest_pace'],
        'slowest_reported_pace_s_per_km': v['slowest_pace'],
        'avg_hr_bpm': avg_hr, 'cadence_spm': v['cadence_spm'],
        'stride_m': v['stride_cm'] / 100 if v['stride_cm'] is not None else None,
        'steps': v['steps'], 'calories_kcal': v['calories'],
        'source_sport_type_code': v['type_code'],
        'sport': None,
        'sport_mapping_note': '仅一条App截图确认源类型2为户外跑步；跨记录/版本枚举尚未验证，保留原始代码供核对',
        'flags': flags,
    }
