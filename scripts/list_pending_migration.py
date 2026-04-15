#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成209个待迁移物品的分类列表"""
import json, re
from pathlib import Path

BASE = Path(__file__).parent.parent

# 加载比较结果
with open(BASE / 'versions/刀剑物语2.41测试版/compare_result.json', encoding='utf-8') as f:
    result = json.load(f)

not_in_wiki = result['not_in_wiki']  # 644个

# 读取task文件E区的435个ID
with open(BASE / 'dev/item_wiki_task.md', encoding='utf-8') as f:
    content = f.read()

e_section_match = re.search(r'## E\. 未收录物品.*', content, re.DOTALL)
e_items = set()
if e_section_match:
    e_items = set(re.findall(r'-\s*\[.\]\s*(I[0-9A-Za-z]+)', e_section_match.group(0)))

# 209个：在not_in_wiki但不在E区（旧wiki中有记录但未迁移为独立文件）
pending_migration = {k: v for k, v in not_in_wiki.items() if k not in e_items}

print(f'待迁移物品总数: {len(pending_migration)}')
print()

# 按class分类
by_class = {}
for k, v in pending_migration.items():
    cls = v['class'] or '(无分类)'
    # 清除颜色代码得到干净名称
    clean_name = re.sub(r'\|[Cc][Ff][Ff][0-9A-Fa-f]{6}', '', v['name'])
    clean_name = re.sub(r'\|[Rr]', '', clean_name).strip()
    by_class.setdefault(cls, []).append((k, clean_name))

for cls in sorted(by_class.keys()):
    items = sorted(by_class[cls])
    print(f'### {cls} ({len(items)}个)')
    for item_id, name in items:
        print(f'- [ ] {item_id} {name}')
    print()
