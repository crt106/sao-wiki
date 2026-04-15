#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析任务文件E区与当前wiki状态的差异"""
import json, re
from pathlib import Path

BASE = Path(__file__).parent.parent

with open(BASE / 'versions/刀剑物语2.41测试版/compare_result.json', encoding='utf-8') as f:
    result = json.load(f)

not_in_wiki = set(result['not_in_wiki'].keys())  # 644个未收录ID
all_241 = result['not_in_wiki']  # 含名称

with open(BASE / 'dev/item_wiki_task.md', encoding='utf-8') as f:
    content = f.read()

# 找出E区所有item ID
e_section_match = re.search(r'## E\. 未收录物品.*', content, re.DOTALL)
e_items = []
if e_section_match:
    e_section = e_section_match.group(0)
    e_items = re.findall(r'-\s*\[.\]\s*(I[0-9A-Za-z]+)', e_section)

print(f'E区记录的物品数: {len(e_items)}')

# 哪些E区物品现在已经在wiki了
now_in_wiki = [i for i in e_items if i not in not_in_wiki]
print(f'E区物品中已迁移到wiki的: {len(now_in_wiki)}')

# E区物品中仍未收录的
still_missing_e = [i for i in e_items if i in not_in_wiki]
print(f'E区物品中仍未收录的: {len(still_missing_e)}')

# not_in_wiki中不在E区的（之前在旧wiki中有记录但现在未迁移为独立文件的）
e_set = set(e_items)
not_in_e = {k: v for k, v in result['not_in_wiki'].items() if k not in e_set}
print(f'不在E区但也未收录（旧wiki有记录但未迁移）: {len(not_in_e)}')

if not_in_e:
    print('\n前20个未迁移示例:')
    for k, v in list(sorted(not_in_e.items()))[:20]:
        name = v['name'] if isinstance(v, dict) else str(v)
        print(f'  {k}: {name}')
