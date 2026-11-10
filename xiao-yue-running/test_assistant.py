import io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import assistant as a
import server
from garmin_personal_api.auth import BearerToken

def archive():
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:z.writestr('readme.txt','No FIT records in this fixture')
    return b.getvalue()
class FixtureSource:
    def call(self,method,*args,**kwargs):
        if method=='search_activities':return [
          {'activityId':1,'startTimeLocal':'2026-11-01 10:00:00','activityType':{'typeKey':'running'},'distance':5000,'duration':1500,'averageHR':None},
          {'activityId':2,'startTimeLocal':'2026-11-01 11:00:00','activityType':{'typeKey':'running'},'distance':2000,'duration':600,'averageHR':140}]
        if method=='download_activity':return archive()
        return {'fixture':True}
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='synthetic-garmin-',dir=Path(__file__).resolve().parent);self.path=Path(self.tmp.name)
        self.p=patch.multiple(a,DATA=self.path,DB=self.path/'db.sqlite',SECRET=self.path/'secret');self.p.start()
    def tearDown(self):self.p.stop();self.tmp.cleanup()
    def test_encrypted_credentials_and_token_cache(self):
        path=a.SECRET/'key.dpapi';a.secure_write(path,b'fake-key-never-real')
        self.assertNotIn(b'fake-key-never-real',path.read_bytes());self.assertEqual(a.secure_read(path),b'fake-key-never-real')
        auth=a.EncryptedAuthenticator(bearer_token_cache_file=a.SECRET/'token.dpapi')
        auth._write_cached_token('fingerprint',BearerToken('fake-token',9999999999))
        self.assertEqual(auth._read_cached_token('fingerprint').access_token,'fake-token')
        self.assertIsNone(auth._read_cached_token('different'));auth.close()
    def test_idempotent_sync_and_missing_hr(self):
        for _ in range(2):self.assertEqual(a.sync(1,100,False,FixtureSource(),end_date='2026-11-01')['status'],'success')
        self.assertEqual(a.status()['activities'],2)
        summary=a.training_summary('2026-11-01','2026-11-01')
        self.assertEqual(summary['distance_km'],7)
        self.assertEqual(summary['duration_weighted_average_hr'],140)
    def test_partial_failure_retains_valid_activity(self):
        class Partial(FixtureSource):
            def call(self,method,*args,**kwargs):
                if method=='get_activity':raise TimeoutError('must not expose sensitive text')
                return super().call(method,*args,**kwargs)
        result=a.sync(1,100,False,Partial(),end_date='2026-11-01')
        self.assertEqual(result['status'],'partial');self.assertEqual(a.status()['activities'],2)
        self.assertNotIn('sensitive text',json.dumps(result))
    def test_location_and_identity_not_returned(self):
        cleaned=server.without_location({'startLatitude':30,'startLongitude':90,'email':'hidden','nested':{'avgHR':140,'position_lat':1}})
        self.assertEqual(cleaned,{'nested':{'avgHR':140}})
    def test_invalid_date_and_boundaries(self):
        with self.assertRaises(ValueError):a.training_summary('2026-11-02','2026-11-01')
        with self.assertRaises(ValueError):a.recent(101)
if __name__=='__main__':unittest.main()
