#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rename_items_with_name.py

将 docs/items/*/ 下所有物品独立 md 文件从 IXXX.md 重命名为 IXXX_物品名.md，
同时更新 docs/ 目录下所有 md 文件中的引用链接。

用法：
    python scripts/rename_items_with_name.py [--dry-run]
"""

import os
import re
import sys

BASE       = r"D:\Program Files\maps\刀剑物语wiki建设"
ITEMS_ROOT = os.path.join(BASE, r"docs\items")
DOCS_ROOT  = os.path.join(BASE, r"docs")

# Windows 文件名禁止字符（去掉空格，单独处理）
WIN_FORBIDDEN = re.compile(r'[\\/:*?"<>|]')


def sanitize_name(name: str) -> str:
    """将物品名称处理为合法文件名片段。"""
    # 去两端空白
    name = name.strip()
    # 去掉 Windows 禁止字符
    name = WIN_FORBIDDEN.sub('', name)
    # 空格 → 下划线
    name = name.replace(' ', '_')
    # 不允许以点或空格开头/结尾（Windows规则）
    name = name.strip('._')
    return name


def read_item_name(filepath: str):
    """
    从文件第一行 '# IXXX · 物品名' 中解析出 (item_id, item_name)。
    若格式不符则返回 (None, None)。
    """
    try:
        # utf-8-sig 自动去除 UTF-8 BOM（PowerShell Set-Content 会加 BOM）
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            first_line = f.readline().strip()
    except Exception:
        return None, None

    m = re.match(r'^#\s+(I[0-9A-Z]+)\s+[··]\s+(.+)$', first_line)
    if not m:
        return None, None
    return m.group(1), m.group(2).strip()


def collect_item_dirs():
    """返回所有物品分类目录路径。"""
    dirs = []
    for entry in os.listdir(ITEMS_ROOT):
        full = os.path.join(ITEMS_ROOT, entry)
        if os.path.isdir(full):
            dirs.append(full)
    return dirs


def build_rename_map(dry_run=False):
    """
    扫描所有物品文件，构建重命名映射。
    返回 dict: { (dir_path, old_basename): new_basename }
    只重命名符合格式且当前文件名是纯 ID 格式（没有下划线）的文件。
    """
    rename_map = {}          # (dir, old_base) -> new_base
    skip_count = 0

    for cat_dir in collect_item_dirs():
        for fname in sorted(os.listdir(cat_dir)):
            if fname in ('index.md', '.pages') or not fname.endswith('.md'):
                continue

            # 只处理 纯ID格式 "IXXXX.md"（尚未改过的）
            stem = fname[:-3]  # 去掉 .md
            if not re.match(r'^I[0-9A-Z]{3,4}$', stem):
                # 已含下划线或其他，说明已经改过了或者特殊文件
                if '_' in stem:
                    skip_count += 1
                continue

            filepath = os.path.join(cat_dir, fname)
            item_id, item_name = read_item_name(filepath)

            if item_id is None or item_name is None:
                print(f"  [WARN] 无法解析标题，跳过：{os.path.join(os.path.basename(cat_dir), fname)}")
                continue

            if item_id != stem:
                print(f"  [WARN] ID 不匹配（文件名={stem}，标题ID={item_id}），跳过：{fname}")
                continue

            safe_name = sanitize_name(item_name)
            if not safe_name:
                print(f"  [WARN] 物品名清理后为空，跳过：{fname}")
                continue

            new_base = f"{item_id}_{safe_name}.md"

            if new_base == fname:
                skip_count += 1
                continue

            rename_map[(cat_dir, fname)] = new_base

    if skip_count:
        print(f"  [INFO] 跳过 {skip_count} 个（已重命名或无需更改）")

    return rename_map


def apply_renames(rename_map: dict, dry_run=False):
    """执行文件重命名。"""
    for (cat_dir, old_base), new_base in rename_map.items():
        old_path = os.path.join(cat_dir, old_base)
        new_path = os.path.join(cat_dir, new_base)
        cat_name = os.path.basename(cat_dir)
        if dry_run:
            print(f"  [DRY] {cat_name}/{old_base}  →  {new_base}")
        else:
            os.rename(old_path, new_path)
            print(f"  [REN] {cat_name}/{old_base}  →  {new_base}")


def update_references(rename_map: dict, dry_run=False):
    """
    在 docs/ 下所有 .md 文件中将旧文件名引用替换为新文件名。
    构建纯文件名的映射：{ old_base: new_base }（忽略目录，因为链接都是相对同目录）
    """
    if not rename_map:
        return

    # 扁平化：旧basename → 新basename
    flat = {}
    for (_, old_base), new_base in rename_map.items():
        flat[old_base] = new_base

    # 按文件名长度降序排序，防止短名称误替换长名称的子串
    sorted_old = sorted(flat.keys(), key=len, reverse=True)

    # 编译单个大正则：匹配 (IXXX.md) 或 (IXXX.md#xxx)
    # 使用逐个替换
    updated_files = 0

    for root, dirs, files in os.walk(DOCS_ROOT):
        # 跳过 site/ 等非 docs/ 目录
        for fname in files:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue

            new_content = content
            for old_base in sorted_old:
                new_base = flat[old_base]
                # 匹配 markdown 链接里的 (IXXX.md) 或 (IXXX.md#anchor)
                # 以及纯文件名形式
                new_content = new_content.replace(f'({old_base})', f'({new_base})')
                new_content = new_content.replace(f'({old_base}#', f'({new_base}#')

            if new_content != content:
                updated_files += 1
                if dry_run:
                    print(f"  [DRY] 更新引用：{os.path.relpath(fpath, BASE)}")
                else:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"  [UPD] 更新引用：{os.path.relpath(fpath, BASE)}")

    print(f"\n  共更新引用文件数：{updated_files}")


def main():
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("=== DRY RUN 模式（不写入文件）===\n")

    print("=== 第一步：构建重命名映射 ===")
    rename_map = build_rename_map(dry_run)
    print(f"待重命名文件数：{len(rename_map)}\n")

    if not rename_map:
        print("无需操作。")
        return

    print("=== 第二步：重命名文件 ===")
    apply_renames(rename_map, dry_run)

    print("\n=== 第三步：更新引用链接 ===")
    update_references(rename_map, dry_run)

    print("\n=== 完成 ===")


if __name__ == '__main__':
    main()
