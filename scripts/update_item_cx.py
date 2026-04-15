"""
解析 item_cx_init 中所有 item_cx_add 调用
提取物品技能描述并更新 wiki 文档
"""
import os
import re
import json

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
ITEMS_DIR = os.path.join(BASE_DIR, 'docs', 'items')
J_PATH = os.path.join(BASE_DIR, 'versions', '刀剑物语2.41测试版', 'map', 'war3map.j')

# ─────────────────────────────────────────────
# Step 1: 读取并解析 item_cx_init
# ─────────────────────────────────────────────
def parse_cx_init():
    with open(J_PATH, encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # 找 item_cx_init 函数范围
    start = end = None
    for i, line in enumerate(lines):
        if 'function item_cx_init takes nothing returns nothing' in line:
            start = i
        if start and i > start and line.strip() == 'endfunction':
            end = i
            break

    print(f'item_cx_init: lines {start+1} to {end+1}')
    cx_lines = lines[start:end]
    text = ''.join(cx_lines)

    # 解析 call item_cx_add(itemValue , abilityValue , num , n1,c1, n2,c2, n3,c3, n4,c4)
    pattern = re.compile(
        r"call item_cx_add\s*\(\s*'?([^',\)\s]+)'?\s*,\s*'?([^',\)\s]*)'?\s*,\s*(\d+)\s*,"
        r'\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,'
        r'\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"'
    )

    ability_descs = {}   # ability_id -> (name, content)
    item_skills = {}     # item_id -> [{'name':..,'content':..}, ...]

    calls = pattern.findall(text)
    print(f'Parsed calls: {len(calls)}')

    for c in calls:
        item_val, abil_val, num_str, n1, c1, n2, c2, n3, c3, n4, c4 = c
        item_val = item_val.strip().strip("'")
        abil_val = abil_val.strip().strip("'")
        num = int(num_str)

        # num 表示技能数量索引（最大3），实际槽位：0=1条，1=2条，2=3条，3=4条
        all_entries = [(n1, c1), (n2, c2), (n3, c3), (n4, c4)]
        # 取前 num+1 个非空项（num=0时只有1项）
        skills = []
        for name, content in all_entries[:num + 1]:
            clean_name = strip_wc3_colors(name)
            clean_content = strip_wc3_colors(content)
            if clean_name:
                skills.append({'name': clean_name, 'content': clean_content})

        if item_val == '0':
            if abil_val and abil_val != '0':
                ability_descs[abil_val] = (strip_wc3_colors(n1), strip_wc3_colors(c1))
        else:
            item_skills[item_val] = skills

    print(f'  Ability descs (shared): {len(ability_descs)}')
    print(f'  Direct item skills: {len(item_skills)}')
    return ability_descs, item_skills


# ─────────────────────────────────────────────
# Step 2: 建立物品ID→文件路径映射
# ─────────────────────────────────────────────
def strip_wc3_colors(s):
    """去除 WC3 颜色代码，如 |cffRRGGBB...text...|r"""
    s = re.sub(r'\|c(?:ff)?[0-9a-fA-F]{6,8}', '', s)
    s = s.replace('|r', '')
    return s.strip()

PLACEHOLDER_KEYWORDS = {'待考证', '待查验', '暂不明确', '待补全', '待确认', '效果未知', '暂时未知', '...', '—', '?', '？'}

def build_item_map():
    item_map = {}  # item_id -> filepath
    for root, dirs, files in os.walk(ITEMS_DIR):
        dirs.sort()
        for fname in sorted(files):
            if not fname.endswith('.md') or fname == 'index.md':
                continue
            m = re.match(r'^([A-Z][0-9A-Z]{3})[_\.]', fname)
            if m:
                item_map[m.group(1)] = os.path.join(root, fname)
    return item_map


# ─────────────────────────────────────────────
# Step 3: 更新 wiki 文件的技能表格
# ─────────────────────────────────────────────
PLACEHOLDER_KEYWORDS = {'待考证', '待查验', '暂不明确', '待补全', '待确认', '效果未知', '暂时未知', '...', '—', '?', '？'}

def table_has_placeholder(lines):
    """检查技能效果表格中是否含有占位符内容"""
    in_table = False
    for line in lines:
        if '**技能效果**' in line or ('技能名' in line and '|' in line):
            in_table = True
        if in_table and '|' in line and not line.strip().startswith('|---'):
            for kw in PLACEHOLDER_KEYWORDS:
                if kw in line:
                    return True
    return False

def count_table_skills(lines):
    """统计技能效果表中的技能行数"""
    in_table = False
    count = 0
    for line in lines:
        if '**技能效果**' in line or ('技能名' in line and '效果' in line and '|' in line):
            in_table = True
            continue
        if in_table and '|' in line and not line.strip().startswith('|---') and '技能名' not in line:
            if line.strip().startswith('|') and len(line.strip()) > 3:
                count += 1
        if in_table and line.strip() == '' and count > 0:
            # 空行表示表格结束
            pass
    return count

def update_item_wiki(fpath, skills):
    """
    将 skills 列表更新到物品文档中。
    skills: [{'name': '技能名', 'content': '效果描述'}, ...]

    策略：
    1. 如果已有完整表格且无占位符，且技能数 >= cx_add 提供数 → SKIP
    2. 如果有占位符或技能数不足 → 替换技能表格
    3. 如果有 "- 能力：" 行但无表格 → 替换为规范技能表格
    4. 如果什么都没有 → 在描述行前新增
    """
    with open(fpath, encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    has_skill_table = any('技能名' in l and '效果' in l and '|' in l for l in lines)

    if has_skill_table:
        # 检查 war3map.j 中每条技能的效果文本是否都已出现在文档中
        all_present = all(
            s['content'] and s['content'].strip() and s['content'].strip() in content
            for s in skills
        )
        if all_present:
            return 'SKIP_COMPLETE'

        reason = 'CONTENT_MISMATCH'

        # 替换现有技能表格
        new_table = ['**技能效果**', '', '| 技能名 | 效果 |', '|---|---|']
        for s in skills:
            name = s['name'].replace('|', '\\|')
            content_str = s['content'].replace('|', '\\|') if s['content'] else '—'
            new_table.append(f'| {name} | {content_str} |')

        # 找技能效果区域并替换
        new_lines = []
        i = 0
        replaced = False
        while i < len(lines):
            line = lines[i]
            # 找到技能效果开始
            if not replaced and ('**技能效果**' in line or ('技能名' in line and '效果' in line and '|' in line)):
                # 如果是直接的表格行（没有 **技能效果** 标题），不替换标题
                if '**技能效果**' in line:
                    # 跳过直到表格结束（连续的 | 行和空行）
                    new_lines.extend(new_table)
                    new_lines.append('')
                    i += 1
                    # 跳过旧的表格内容
                    while i < len(lines) and (lines[i].strip().startswith('|') or lines[i].strip() == '' or '技能名' in lines[i]):
                        if lines[i].strip() == '' and i+1 < len(lines) and not lines[i+1].strip().startswith('|'):
                            i += 1
                            break
                        i += 1
                    replaced = True
                    continue
                else:
                    # 表格行直接在内容里（没有标题）
                    new_lines.extend([''] + new_table + [''])
                    i += 1
                    while i < len(lines) and (lines[i].strip().startswith('|') or '技能名' in lines[i]):
                        i += 1
                    replaced = True
                    continue
            new_lines.append(line)
            i += 1

        new_content = '\n'.join(new_lines)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return f'UPDATED({reason})'

    # 构建新的技能表格
    new_table = ['**技能效果**', '', '| 技能名 | 效果 |', '|---|---|']
    for s in skills:
        name = s['name'].replace('|', '\\|')
        content_str = s['content'].replace('|', '\\|') if s['content'] else '—'
        new_table.append(f'| {name} | {content_str} |')

    # 找现有 "- 能力：" 行的位置
    ability_line_indices = [i for i, l in enumerate(lines) if re.match(r'^[-\*]\s*能力\s*[：:]', l)]

    if ability_line_indices:
        first = ability_line_indices[0]
        new_lines = [l for i, l in enumerate(lines) if i not in ability_line_indices]
        new_lines[first:first] = new_table + ['']
        new_content = '\n'.join(new_lines)
    else:
        desc_idx = next((i for i, l in enumerate(lines) if l.startswith('- 描述：') or l.startswith('- **描述**') or l.startswith('- 描述:')), None)
        if desc_idx is not None:
            new_lines = lines[:desc_idx] + new_table + [''] + lines[desc_idx:]
        else:
            new_lines = lines + [''] + new_table
        new_content = '\n'.join(new_lines)

    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return 'CREATED'


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == '__main__':
    ability_descs, item_skills = parse_cx_init()
    item_map = build_item_map()

    print(f'\nItem wiki files found: {len(item_map)}')

    # 统计可匹配的物品
    matched = [(iid, item_map[iid], skills) for iid, skills in item_skills.items() if iid in item_map]
    unmatched = [iid for iid in item_skills if iid not in item_map]

    print(f'Direct item matches: {len(matched)} / {len(item_skills)}')
    if unmatched:
        print(f'Unmatched item IDs: {unmatched}')

    updated = []
    skipped = []

    for iid, fpath, skills in matched:
        if not skills:
            skipped.append((iid, 'NO_SKILLS'))
            continue
        result = update_item_wiki(fpath, skills)
        if result.startswith('UPDATED') or result == 'CREATED':
            updated.append((iid, os.path.basename(fpath), skills, result))
        else:
            skipped.append((iid, result))

    print(f'\nUpdated: {len(updated)}')
    print(f'Skipped: {len(skipped)}')
    print()
    print('Updated items:')
    for iid, fname, skills, result in updated:
        skill_names = ' / '.join(s['name'] for s in skills)
        print(f'  [{result}] {iid} {fname}: {skill_names}')

    skip_placeholder = [(i, r) for i, r in skipped if r == 'SKIP_COMPLETE']
    skip_other = [(i, r) for i, r in skipped if r != 'SKIP_COMPLETE']
    print(f'\nSkipped COMPLETE (already has content): {len(skip_placeholder)}')
    if skip_other:
        print(f'Skipped OTHER:')
        for iid, reason in skip_other:
            print(f'  {iid}: {reason}')

    # 保存 ability_descs 以备参考
    with open('dev/item_cx_ability_descs.json', 'w', encoding='utf-8') as f:
        json.dump({k: {'name': v[0], 'content': v[1]} for k, v in ability_descs.items()}, f, ensure_ascii=False, indent=2)
    print(f'\nAbility descs saved to dev/item_cx_ability_descs.json')
