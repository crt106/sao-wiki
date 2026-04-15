#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比2.3和2.41版本物品差异"""
import re, json

def parse_items(filepath):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    items = {}
    parts = re.split(r'(?=^\[[^\]]+\])', content, flags=re.MULTILINE)
    name_re = re.compile(r'Name\s*=\s*"(.+?)"')
    class_re = re.compile(r'class\s*=\s*"(.+?)"')
    for part in parts:
        m = re.match(r'^\[([^\]]+)\]', part)
        if not m: continue
        sec_id = m.group(1)
        if not sec_id.startswith('I'): continue
        nm = name_re.search(part)
        cls = class_re.search(part)
        items[sec_id] = {
            'name': nm.group(1).strip() if nm else '(无名称)',
            'class': cls.group(1).strip() if cls else ''
        }
    return items

v23 = parse_items('versions/刀剑物语2.3(忘川)测试版/table/item.ini')
v241 = parse_items('versions/刀剑物语2.41测试版/table/item.ini')

added = {k: v for k, v in v241.items() if k not in v23}
removed = {k: v for k, v in v23.items() if k not in v241}
changed = {k: v for k, v in v241.items() if k in v23 and v['name'] != v23[k]['name']}

print(f'2.3版本物品: {len(v23)}')
print(f'2.41版本物品: {len(v241)}')
print(f'新增物品: {len(added)}')
print(f'删除物品: {len(removed)}')
print(f'改名物品: {len(changed)}')

if added:
    print('\n=== 新增物品 ===')
    for k, v in sorted(added.items()):
        print(f'  {k}: {v["name"]} [{v["class"]}]')

if removed:
    print('\n=== 删除物品 ===')
    for k, v in sorted(removed.items()):
        print(f'  {k}: {v["name"]} [{v["class"]}]')

if changed:
    print('\n=== 改名物品 ===')
    for k, v in sorted(changed.items()):
        print(f'  {k}: {v23[k]["name"]} -> {v["name"]}')
