import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('skill_installer', ROOT / 'scripts/install_skill.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def test_install_only_instruction_files_and_repeat(self):
        with tempfile.TemporaryDirectory(prefix='synthetic-install-', dir=ROOT) as folder:
            target = Path(folder) / 'skill'
            self.assertEqual(installer.install(target)[0], 'installed')
            actual = {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}
            self.assertEqual(actual, set(installer.FILES))
            self.assertEqual(installer.install(target)[0], 'already-installed')

    def test_update_requires_flag_and_preserves_backup_and_extra_files(self):
        with tempfile.TemporaryDirectory(prefix='synthetic-update-', dir=ROOT) as folder:
            target = Path(folder) / 'skill'
            installer.install(target)
            (target / 'SKILL.md').write_text('user-edited instructions', encoding='utf-8')
            (target / 'local-note.txt').write_text('keep', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                installer.install(target)
            self.assertEqual((target / 'SKILL.md').read_text(encoding='utf-8'), 'user-edited instructions')
            self.assertEqual(installer.install(target, update=True)[0], 'updated-with-backup')
            backups = list((target / '.backups').glob('*/SKILL.md'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding='utf-8'), 'user-edited instructions')
            self.assertEqual((target / 'local-note.txt').read_text(encoding='utf-8'), 'keep')
            self.assertEqual((target / 'SKILL.md').read_bytes(), (installer.SOURCE / 'SKILL.md').read_bytes())


if __name__ == '__main__':
    unittest.main()
