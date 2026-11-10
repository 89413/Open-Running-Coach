"""Read-only export structure probe. Does not print passwords, record values or member names."""
from pathlib import Path
import argparse, getpass, io, json, zipfile

OLE_MAGIC = bytes.fromhex('d0cf11e0a1b11ae1')


class ExportError(ValueError):
    def __init__(self, stage, code):
        self.stage, self.code = stage, code
        super().__init__(f'{stage}: {code}')


def detect_format(raw):
    if raw.startswith(OLE_MAGIC): return 'ole'
    if zipfile.is_zipfile(io.BytesIO(raw)): return 'ooxml_zip'
    return 'unsupported'


def read_export(path, password=None):
    path = Path(path)
    if path.stat().st_size > 100_000_000: raise ExportError('archive', 'file_too_large')
    raw = path.read_bytes()
    if raw.startswith(OLE_MAGIC): return raw
    if not zipfile.is_zipfile(io.BytesIO(raw)): raise ExportError('archive', 'unsupported_format')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if 'xl/workbook.xml' in z.namelist(): return raw
        members = [i for i in z.infolist() if not i.is_dir() and Path(i.filename).suffix.lower() in ('.xls', '.xlsx')]
        if len(members) != 1: raise ExportError('archive', 'expected_single_workbook')
        if members[0].file_size > 50_000_000: raise ExportError('archive', 'workbook_too_large')
        name, encrypted = members[0].filename, bool(members[0].flag_bits & 1)
        if encrypted and password is None: raise ExportError('password', 'required')
    import pyzipper
    try:
        with pyzipper.AESZipFile(io.BytesIO(raw)) as z:
            return z.read(name, pwd=password.encode('utf-8') if password is not None else None)
    except RuntimeError as e:
        if 'bad password' in str(e).lower(): raise ExportError('password', 'incorrect') from None
        raise ExportError('archive', 'read_failed') from None
    except (zipfile.BadZipFile, pyzipper.BadZipFile, NotImplementedError):
        raise ExportError('archive', 'integrity_or_compression_error') from None


def probe_workbook(raw):
    # OLE can contain either BIFF or an encrypted Office package. xlrd verifies BIFF;
    # the magic bytes alone are not enough to assert either case.
    kind = detect_format(raw)
    if kind == 'ole':
        import xlrd
        try: book = xlrd.open_workbook(file_contents=raw, on_demand=True)
        except Exception: raise ExportError('workbook', 'ole_not_readable_as_biff') from None
        try:
            return {'actual_format': 'xls/BIFF', 'sheets': [
                {'name': sh.name, 'row_count_including_header': sh.nrows, 'column_count': sh.ncols,
                 'headers': [str(v) for v in sh.row_values(0)] if sh.nrows else []}
                for sh in book.sheets()]}
        finally: book.release_resources()
    if kind == 'ooxml_zip':
        import xml.etree.ElementTree as ET
        ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                wb = ET.fromstring(z.read('xl/workbook.xml'))
                return {'actual_format': 'xlsx/OOXML', 'sheets': [
                    {'name': n.attrib['name']} for n in wb.findall('s:sheets/s:sheet', ns)]}
        except Exception: raise ExportError('workbook', 'invalid_ooxml') from None
    raise ExportError('workbook', 'unsupported_signature')


def main():
    p = argparse.ArgumentParser(description='只读检查导出包结构，不导出原始健康记录。')
    p.add_argument('file', type=Path); args = p.parse_args()
    try:
        try: raw = read_export(args.file)
        except ExportError as e:
            if e.stage != 'password' or e.code != 'required': raise
            password = getpass.getpass('解压密码（不回显，不保存）: ')
            try: raw = read_export(args.file, password)
            finally: password = ''
        result = probe_workbook(raw)
        print(json.dumps(result, ensure_ascii=False))
    except ExportError as e:
        print(json.dumps({'ok': False, 'stage': e.stage, 'code': e.code}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__': raise SystemExit(main())
