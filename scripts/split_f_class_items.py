#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_f_class_items.py

从各聚合文档中提取 F 类未独立物品（### IXXX — 格式），
为每个条目在对应分类目录下创建独立的 md 文件。

用法：
    python scripts/split_f_class_items.py [--dry-run]
"""

import os
import re
import sys

BASE = r"D:\Program Files\maps\刀剑物语wiki建设"

# 源文件 → 目标目录 的映射
SOURCE_TO_TARGET = {
    os.path.join(BASE, r"docs\items\武器\I086.md"):      os.path.join(BASE, r"docs\items\武器"),
    os.path.join(BASE, r"docs\items\副武器\I07W.md"):     os.path.join(BASE, r"docs\items\副武器"),
    os.path.join(BASE, r"docs\items\装甲\I07H.md"):       os.path.join(BASE, r"docs\items\装甲"),
    os.path.join(BASE, r"docs\items\头部道具\I06L.md"):   os.path.join(BASE, r"docs\items\头部道具"),
    os.path.join(BASE, r"docs\items\装备道具\I082.md"):   os.path.join(BASE, r"docs\items\装备道具"),
    os.path.join(BASE, r"docs\items\消耗物品\I07Y.md"):   os.path.join(BASE, r"docs\items\消耗物品"),
    os.path.join(BASE, r"docs\items\不归类\I05N.md"):     os.path.join(BASE, r"docs\items\不归类"),
    os.path.join(BASE, r"docs\items\特殊\I085.md"):       os.path.join(BASE, r"docs\items\特殊"),
    os.path.join(BASE, r"docs\items\素材\I07S.md"):       os.path.join(BASE, r"docs\items\素材"),
}

# 页脚
FOOTER = "\n---\n\n*最后更新：2026-04-15 · 地图版本：2.3 忘川*\n"


def parse_subsections(content):
    """
    解析文件中的 '### IXXX — 名称' 子节。
    返回 dict: {item_id: (item_name, section_markdown)}
    其中 section_markdown 是从 ### 行开始到下一个 ### 行（或文件页脚）之间的完整内容。
    """
    sections = {}
    # 找到所有 ### 子节的起始位置
    pattern = re.compile(r'^### (I[0-9A-Z]+) [—·] (.+)$', re.MULTILINE)
    matches = list(pattern.finditer(content))

    for i, match in enumerate(matches):
        item_id = match.group(1)
        item_name = match.group(2).strip()

        start = match.start()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            # 末尾：去掉文件页脚（--- *最后更新...）
            end = content.find('\n\n---\n\n*最后更新', start)
            if end == -1:
                end = len(content)

        section_raw = content[start:end]
        sections[item_id] = (item_name, section_raw)

    return sections


def build_standalone_content(item_id, item_name, section_raw):
    """
    将子节格式转换为独立文件格式：
    - ### IXXX — 名称  →  # IXXX · 名称
    - 去掉开头 '---' 分隔线（如有）
    - 追加页脚
    """
    # 去掉第一行（### 标题行）
    lines = section_raw.splitlines()
    body_lines = lines[1:] if lines else []  # 跳过 ### 行

    # 去掉 body 开头的空行和 --- 分隔线
    while body_lines and body_lines[0].strip() in ('', '---'):
        body_lines.pop(0)

    body = '\n'.join(body_lines).strip()

    return f"# {item_id} · {item_name}\n\n{body}{FOOTER}"


def process_source(source_file, target_dir, dry_run=False):
    created = []
    skipped = []

    if not os.path.exists(source_file):
        print(f"  [WARN] 源文件不存在：{source_file}")
        return created, skipped

    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = parse_subsections(content)
    if not sections:
        print(f"  [INFO] 无子节：{os.path.basename(source_file)}")
        return created, skipped

    for item_id, (item_name, section_raw) in sections.items():
        target_path = os.path.join(target_dir, f"{item_id}.md")
        if os.path.exists(target_path):
            skipped.append(item_id)
            continue

        new_content = build_standalone_content(item_id, item_name, section_raw)

        if not dry_run:
            os.makedirs(target_dir, exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

        created.append(item_id)

    return created, skipped


def main():
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("=== DRY RUN 模式（不写入文件）===\n")

    total_created = 0
    total_skipped = 0
    all_created = {}

    for source_file, target_dir in SOURCE_TO_TARGET.items():
        src_name = os.path.basename(source_file)
        tgt_name = os.path.basename(target_dir)
        print(f"处理：{src_name} → {tgt_name}/")

        created, skipped = process_source(source_file, target_dir, dry_run)
        for item_id in created:
            all_created[item_id] = tgt_name
            status = "[DRY]" if dry_run else "[OK ]"
            print(f"  {status} 创建 {item_id}.md")
        for item_id in skipped:
            print(f"  [SKIP] {item_id}.md 已存在")

        total_created += len(created)
        total_skipped += len(skipped)
        print()

    print(f"=== 完成 ===")
    print(f"新建文件：{total_created}")
    print(f"跳过（已存在）：{total_skipped}")

    if all_created:
        print("\n新建物品列表：")
        for item_id, category in sorted(all_created.items()):
            print(f"  {item_id}  →  {category}/")


if __name__ == '__main__':
    main()
