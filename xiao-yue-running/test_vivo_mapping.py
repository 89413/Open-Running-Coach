import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'scripts'))
from vivo_activity_mapping import FIELDS,map_activity


def fixture():
    headers=['未映射']*45;row=['']*45
    values={'start_ms':1738584000000,'end_ms':1738585920000,'distance_m':6000,
            'duration_ms':1800000,'computed_export_pace':300,'display_pace':300,
            'fastest_pace':260,'slowest_pace':600,'avg_hr':150,'cadence_spm':176,
            'stride_cm':110,'steps':5500,'calories':400,'type_code':2}
    for key,(index,label) in FIELDS.items():headers[index]=label;row[index]=str(values[key])
    row[0]='fictional-owner-must-not-leak';row[3]='fictional-location-must-not-leak'
    row[10]='fictional-route-must-not-leak'
    return headers,row


class MappingTests(unittest.TestCase):
    def test_units_and_distinct_time_semantics(self):
        h,r=fixture();a=map_activity(h,r)
        self.assertEqual(a['distance_m'],6000);self.assertEqual(a['duration_s'],1800)
        self.assertEqual(a['elapsed_s'],1920);self.assertEqual(a['stride_m'],1.1)
        self.assertIn('elapsed_differs_from_reported_duration',a['flags'])
    def test_reported_pace_not_silently_overwritten(self):
        h,r=fixture();r[25]='297';a=map_activity(h,r)
        self.assertEqual(a['reported_pace_s_per_km'],297)
        self.assertEqual(a['calculated_pace_s_per_km'],300)
        self.assertIn('reported_pace_differs_from_duration_distance_ratio',a['flags'])
    def test_identity_and_route_not_exported(self):
        h,r=fixture();a=map_activity(h,r)
        self.assertNotIn('fictional',str(a));self.assertIsNone(a['sport'])
        self.assertEqual(a['id'],map_activity(h,r)['id'])
    def test_unknown_header_layout_rejected(self):
        h,r=fixture();h[5]='单位已变化'
        with self.assertRaises(ValueError):map_activity(h,r)
    def test_missing_hr_not_zero_and_required_values_validated(self):
        h,r=fixture();r[12]='';self.assertIsNone(map_activity(h,r)['avg_hr_bpm'])
        r[12]='0';self.assertIsNone(map_activity(h,r)['avg_hr_bpm'])
        r[4]='NaN'
        with self.assertRaises(ValueError):map_activity(h,r)
    def test_timestamps_kept_as_utc_not_host_timezone(self):
        h,r=fixture();a=map_activity(h,r)
        self.assertTrue(a['start_time_utc'].endswith('+00:00'))


if __name__=='__main__':unittest.main()
