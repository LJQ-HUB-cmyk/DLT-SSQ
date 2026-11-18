"""
Skill 打包器
============
把 skill/<name>/ 打成可上传的 zip (WorkBuddy 开放平台要求 zip)。

★ zip 内部结构: 顶层就是 skill 目录本身 (SKILL.md 在根),
  不要多套一层 —— 否则平台解析会失败。

用法:
  python scripts/pack_skill.py                  # 打包全部 skill/
  python scripts/pack_skill.py --name lottery-lab
  python scripts/pack_skill.py --out dist
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

SKILL_DIR = PROJECT_ROOT / 'skill'
DEFAULT_OUT = PROJECT_ROOT / 'dist'

REQUIRED = ['SKILL.md']
OPTIONAL_DIRS = ['references', 'scripts', 'templates', 'assets']


def validate(skill_dir: Path) -> list:
    """检查 SKILL.md frontmatter 必填字段"""
    problems = []
    md = skill_dir / 'SKILL.md'
    if not md.exists():
        return ['缺少 SKILL.md']
    text = md.read_text(encoding='utf-8')
    if not text.startswith('---'):
        return ['SKILL.md 没有 YAML frontmatter']
    end = text.find('\n---', 3)
    if end < 0:
        return ['SKILL.md frontmatter 未闭合']
    fm = text[3:end]
    required = ['name', 'display_name', 'display_name_en', 'description',
                'description_zh', 'description_en', 'version', 'author']
    for field in required:
        if f'{field}:' not in fm:
            problems.append(f'frontmatter 缺必填字段: {field}')
    for opt in ('examples_zh', 'examples_en', 'allowed-tools'):
        if opt not in fm:
            print(f'  ℹ️ 建议补上可选字段: {opt}')
    return problems


def pack(skill_dir: Path, out_dir: Path) -> Path:
    name = skill_dir.name
    out = out_dir / f'{name}.zip'
    out_dir.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    n = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(skill_dir.rglob('*')):
            if f.is_dir():
                continue
            # zip 内路径: skill-name/相对路径
            arc = f'{name}/{f.relative_to(skill_dir).as_posix()}'
            z.write(f, arc)
            n += 1
    return out, n


def main():
    ap = argparse.ArgumentParser(description='Skill 打包器')
    ap.add_argument('--name', default=None)
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    args = ap.parse_args()

    out_dir = Path(args.out)
    if not SKILL_DIR.exists():
        print(f'❌ 没有 skill 目录: {SKILL_DIR}')
        return 1

    dirs = [SKILL_DIR / args.name] if args.name else \
        [d for d in sorted(SKILL_DIR.iterdir()) if d.is_dir()]
    if not dirs:
        print('❌ 没有可打包的 skill')
        return 1

    all_ok = True
    for sd in dirs:
        print()
        print('=' * 66)
        print(f'  打包 Skill: {sd.name}')
        print('=' * 66)
        problems = validate(sd)
        if problems:
            all_ok = False
            for p in problems:
                print(f'  ❌ {p}')
            continue
        print('  ✅ frontmatter 校验通过')
        out, n = pack(sd, out_dir)
        print(f'  ✅ 已打包: {out}  ({n} 个文件, {out.stat().st_size / 1024:.1f} KB)')
        with zipfile.ZipFile(out) as z:
            for i in z.infolist():
                print(f'       {i.filename}  ({i.file_size} B)')

    print()
    if all_ok:
        print('  ✅ 全部打包完成, 可上传到 WorkBuddy 开放平台')
        return 0
    print('  ❌ 有 skill 未通过校验')
    return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
