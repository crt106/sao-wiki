#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比2.41版本item.ini与wiki/docs/items中已收录物品，统计未收录数量
"""
import re
import json
import os
from pathlib import Path

BASE = Path(__file__).parent.parent
ITEM_INI = BASE / "versions" / "刀剑物语2.41测试版" / "table" / "item.ini"
DOCS_ITEMS = BASE / "docs" / "items"

# 解析item.ini
with open(ITEM_INI, encoding='utf-8') as f:
    content = f.read()

items_241 = {}
parts = re.split(r'(?=^\[[^\]]+\])', content, flags=re.MULTILINE)
for part in parts:
    m = re.match(r'^\[([^\]]+)\]', part)
    if not m:
        continue
    sec_id = m.group(1)
    if not sec_id.startswith('I'):
        continue
    nm = re.search(r'Name\s*=\s*"(.+?)"', part)
    cls = re.search(r'class\s*=\s*"(.+?)"', part)
    items_241[sec_id] = {
        'name': nm.group(1).strip() if nm else '(无名称)',
        'class': cls.group(1).strip() if cls else ''
    }

print(f"2.41版本物品总数: {len(items_241)}")

# 获取wiki中已有的物品ID
wiki_ids = set()
for md_file in DOCS_ITEMS.rglob("*.md"):
    if md_file.name != 'index.md':
        wiki_ids.add(md_file.stem.upper())

print(f"Wiki已收录物品数: {len(wiki_ids)}")

# 未收录
not_in_wiki = {k: v for k, v in items_241.items() if k not in wiki_ids}
print(f"未收录物品数: {len(not_in_wiki)}")

# wiki中有但2.41没有的（可能已删除）
in_wiki_not_241 = wiki_ids - set(items_241.keys())
if in_wiki_not_241:
    print(f"\nWiki中有但2.41没有的（{len(in_wiki_not_241)}个，可能已从游戏删除）:")
    for i in sorted(in_wiki_not_241):
        print(f"  {i}")

# 按class分类统计未收录物品
by_class = {}
for k, v in not_in_wiki.items():
    cls = v['class'] or '(无分类)'
    by_class.setdefault(cls, []).append((k, v['name']))

print(f"\n=== 未收录物品按类型分类 ===")
for cls in sorted(by_class.keys()):
    items_list = sorted(by_class[cls])
    print(f"\n[{cls}] ({len(items_list)}个)")
    for item_id, name in items_list:
        print(f"  {item_id}: {name}")

# 保存结果
result = {
    'total_241': len(items_241),
    'wiki_count': len(wiki_ids),
    'not_in_wiki_count': len(not_in_wiki),
    'not_in_wiki': {k: v for k, v in sorted(not_in_wiki.items())}
}
out_file = BASE / "versions" / "刀剑物语2.41测试版" / "compare_result.json"
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存到: {out_file}")
