import io,tempfile,unittest,zipfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'scripts'))
import probe_vivo_export as p
import pyzipper

class ProbeTests(unittest.TestCase):
    def test_actual_signature_beats_extension(self):
        self.assertEqual(p.detect_format(p.OLE_MAGIC+b'fictional'), 'ole')
        self.assertEqual(p.detect_format(b'not an excel workbook'),'unsupported')
    def test_ooxml_structure_in_memory(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Synthetic" sheetId="1"/></sheets></workbook>')
        self.assertEqual(p.probe_workbook(b.getvalue())['sheets'],[{'name':'Synthetic'}])
    def test_bad_workbook_is_not_password_error(self):
        with self.assertRaises(p.ExportError) as r:p.probe_workbook(b'invalid')
        self.assertEqual(r.exception.stage,'workbook')
    def test_aes_password_separate_from_workbook_parsing(self):
        # Only fictional bytes/password are used; no real workbook enters tests.
        base=(Path(__file__).parent/'private').resolve();base.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='synthetic-probe-',dir=base) as tmp:
            self.assertTrue(Path(tmp).resolve().is_relative_to(base))
            f=Path(tmp)/'fixture.zip'
            with pyzipper.AESZipFile(f,'w',encryption=pyzipper.WZ_AES) as z:
                z.setpassword(b'fictional-test-password');z.writestr('fictional.xlsx',b'not a real workbook')
            with self.assertRaises(p.ExportError) as missing:p.read_export(f)
            self.assertEqual((missing.exception.stage,missing.exception.code),('password','required'))
            with self.assertRaises(p.ExportError) as wrong:p.read_export(f,'wrong-fixture-password')
            self.assertEqual((wrong.exception.stage,wrong.exception.code),('password','incorrect'))
            raw=p.read_export(f,'fictional-test-password')
            with self.assertRaises(p.ExportError) as broken:p.probe_workbook(raw)
            self.assertEqual(broken.exception.stage,'workbook')

if __name__=='__main__':unittest.main()
