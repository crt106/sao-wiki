"""
修复E类标题格式错误：
- 删除文件开头的 # ---\n# hide: true\n# ---\n 伪frontmatter注释
- 将第一个 ### 标题改为 # 标题
"""

import os
import re

ITEMS_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs', 'items')

def fix_e_class():
    fixed = 0
    skipped = 0
    errors = []

    for root, dirs, files in os.walk(ITEMS_DIR):
        dirs.sort()
        for fname in sorted(files):
            if not fname.endswith('.md') or fname == 'index.md':
                continue
            fpath = os.path.join(root, fname)
            try:
                content = open(fpath, encoding='utf-8').read()
            except Exception as ex:
                errors.append(f'READ_ERROR: {fpath}: {ex}')
                continue

            lines = content.split('\n')

            # 检查是否是E类文件
            is_e = False
            for line in lines[:10]:
                stripped = line.strip()
                if stripped == '# ---' or stripped == '# hide: true':
                    is_e = True
                    break

            if not is_e:
                continue

            new_content = content

            # 删除开头的 # ---\n# hide: true\n# ---\n（后接可选空行）
            new_content = re.sub(r'^# ---\s*\n# hide: true\s*\n# ---\s*\n\n?', '', new_content)

            if new_content == content:
                # 尝试不带尾部空行的变体
                new_content = re.sub(r'^# ---\s*\n# hide: true\s*\n# ---\s*\n', '', new_content)

            if new_content == content:
                errors.append(f'NO_MATCH: {fpath}')
                skipped += 1
                continue

            # 将文件开头的第一个 ### 标题改为 #
            new_content = re.sub(r'^### ', '# ', new_content, count=1)

            open(fpath, 'w', encoding='utf-8').write(new_content)
            fixed += 1

    print(f'Fixed: {fixed}, Skipped: {skipped}')
    if errors:
        print(f'\nErrors ({len(errors)}):')
        for e in errors[:20]:
            print(' ', e)

if __name__ == '__main__':
    fix_e_class()
