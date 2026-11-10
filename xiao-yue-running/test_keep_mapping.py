from pathlib import Path
from datetime import timezone,timedelta
import sys,unittest
sys.path.insert(0,str(Path(__file__).parent/'scripts'))
from keep_activity_mapping import HEADERS,map_activity

TZ=timezone(timedelta(hours=8))
def fixture():return ['跑步','1800','2025-02-03 18:00:00','2025-02-03 18:32:00','350','6000','150','170','["145","0","153"]','https://example.invalid/private-map.jpg']

class KeepTests(unittest.TestCase):
    def test_units_timezone_and_time_semantics(self):
        a=map_activity(HEADERS,fixture(),TZ)
        self.assertEqual(a['start_time_utc'],'2025-02-03T10:00:00+00:00')
        self.assertEqual(a['distance_m'],6000);self.assertEqual(a['duration_s'],1800)
        self.assertEqual(a['wall_elapsed_s'],1920);self.assertEqual(a['calculated_pace_s_per_km'],300)
        self.assertIsNone(a['reported_pace_s_per_km'])
    def test_sampling_not_assumed_and_route_not_disclosed(self):
        a=map_activity(HEADERS,fixture(),TZ,include_samples=True)
        self.assertEqual(a['heart_rate_samples_bpm'],[145,None,153])
        self.assertIsNone(a['heart_rate_sample_interval_s'])
        self.assertEqual(a['route_representation'],'image_reference');self.assertNotIn('example.invalid',str(a))
    def test_zero_distance_training_not_running(self):
        r=fixture();r[0]='健身';r[5]='0';r[6]='0';r[7]='0';r[8]='[]'
        a=map_activity(HEADERS,r,TZ)
        self.assertEqual(a['sport'],'training');self.assertIsNone(a['calculated_pace_s_per_km'])
        self.assertIsNone(a['avg_hr_bpm']);self.assertEqual(a['heart_rate_sample_count'],0)
    def test_timezone_required_for_naive_time(self):
        with self.assertRaises(ValueError):map_activity(HEADERS,fixture())
    def test_header_and_broken_arrays_rejected(self):
        with self.assertRaises(ValueError):map_activity(HEADERS[::-1],fixture(),TZ)
        r=fixture();r[8]='{"not":"array"}'
        with self.assertRaises(ValueError):map_activity(HEADERS,r,TZ)
    def test_stable_ids_unknown_sports_and_missing_numbers(self):
        r=fixture();r[0]='未识别类型';a=map_activity(HEADERS,r,TZ)
        self.assertIsNone(a['sport']);self.assertEqual(a['id'],map_activity(HEADERS,r,TZ)['id'])
        r[5]='NaN'
        with self.assertRaises(ValueError):map_activity(HEADERS,r,TZ)

if __name__=='__main__':unittest.main()
