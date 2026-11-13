"""Install only the reviewed instruction files; never copies accounts or health data."""
from pathlib import Path
import argparse
import uuid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'skills' / 'open-running-coach'
FILES = ['SKILL.md', 'agents/openai.yaml', 'references/analysis.md',
         'references/platforms.md', 'references/training-plans.md',
         'references/screenshots.md', 'references/integration-status.md',
         'references/recovery.md', 'references/hiking.md', 'references/nutrition.md',
         'references/intake.md', 'LICENSE']


def install(target, update=False):
    if Path(target).is_symlink():
        raise ValueError('目标不能为符号链接')
    target = Path(target).resolve()
    inputs = {name: (SOURCE / name).read_bytes() for name in FILES}
    for name in inputs:
        if not (target / name).resolve().is_relative_to(target):
            raise ValueError('安装路径越界')
        if (target / name).is_symlink() or ((target / name).exists() and not (target / name).is_file()):
            raise ValueError('指令目标必须是普通文件')
    existed = target.exists()
    if existed:
        if all((target / name).is_file() and (target / name).read_bytes() == value for name, value in inputs.items()):
            return 'already-installed', len(inputs)
        if not update:
            raise FileExistsError('目标已有不同内容，未覆盖。审阅后可使用 --update，旧指令会备份。')
        backup = target / '.backups' / uuid.uuid4().hex
        if not backup.resolve().is_relative_to(target):
            raise ValueError('备份路径越界')
        for name in inputs:
            old = target / name
            if old.is_file():
                destination = backup / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(old.read_bytes())
    else:
        target.mkdir(parents=True, exist_ok=False)
    for name, value in inputs.items():
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(value)
    return 'updated-with-backup' if existed else 'installed', len(inputs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=Path, default=Path.home() / '.codex/skills/open-running-coach')
    parser.add_argument('--update', action='store_true', help='审阅后更新白名单指令；备份旧文件，保留其他文件')
    args = parser.parse_args()
    status, count = install(args.target, args.update)
    print(f'{status}: {count} instruction/reference files; no credentials, health records or MCP configuration copied')
