#!/usr/bin/env python3
"""
扫描 docs/heroes/ 下所有英雄 md 文件，将未链接的物品 ID（如 I0H8）
替换为指向 docs/items/ 对应页面的相对链接。

规则：
- 物品 ID 格式：I + 3位大写字母或数字（共4字符，如 I0H8、I06I、I0KY）
- 跳过已在 markdown 链接内的 ID（[...](...)）
- 跳过 index.md
"""

import re
import os
from pathlib import Path

BASE = Path(__file__).parent.parent  # 项目根目录
ITEMS_DIR = BASE / "docs" / "items"
HEROES_DIR = BASE / "docs" / "heroes"

# 物品 ID 正则（4字符：I + 3个[0-9A-Z]）
# 使用 re.ASCII 使 \w 只匹配 ASCII 字母数字，避免中文被当成 word char 导致 \b 失效
ITEM_ID_RE = re.compile(r'(?<!\w)I[0-9A-Z]{3}(?!\w)', re.ASCII)


def build_item_map():
    """构建 item_id -> 相对于 docs/ 的路径 映射"""
    item_map = {}
    for md_file in ITEMS_DIR.rglob("*.md"):
        if md_file.name == "index.md":
            continue
        # 文件名格式：I06H_柔凡剑.md
        name = md_file.stem  # e.g. I06H_柔凡剑
        parts = name.split("_", 1)
        item_id = parts[0]
        if re.match(r'^I[0-9A-Z]{3}$', item_id):
            # 路径相对于 docs/
            rel_path = md_file.relative_to(BASE / "docs")
            item_map[item_id] = rel_path.as_posix()
    return item_map


def make_link(item_id, item_map, hero_file: Path):
    """生成从英雄文件到物品文件的相对链接"""
    if item_id not in item_map:
        return None
    item_rel = item_map[item_id]  # e.g. items/武器/I001_野猪角战刃.md
    # hero 文件相对路径: heroes/XXX.md
    # 从 heroes/ 到 items/ 需要 ../items/...
    return f"../items/{'/'.join(item_rel.split('/')[1:])}"


def process_hero_file(hero_file: Path, item_map: dict, dry_run=False):
    """处理单个英雄文件，返回 (修改数量, 修改后内容)"""
    text = hero_file.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    
    changes = []
    new_lines = []
    
    for lineno, line in enumerate(lines, start=1):
        new_line = replace_item_ids_in_line(line, item_map, hero_file)
        if new_line != line:
            changes.append((lineno, line.rstrip(), new_line.rstrip()))
        new_lines.append(new_line)
    
    return changes, "".join(new_lines)


def replace_item_ids_in_line(line: str, item_map: dict, hero_file: Path) -> str:
    """
    替换行中未链接的物品 ID。
    避免替换已在 markdown 链接 [text](url) 或代码块 `...` 内的 ID。
    """
    # 找出所有已链接区域（[...](...)内的文本范围）以及反引号范围，跳过这些区域
    # 策略：逐字符扫描，记录哪些位置已在链接/代码块内
    
    # 先找出所有 markdown 链接的范围 [显示](url) — 不替换 url 部分里的 ID
    # 也不替换已经是 [显示文字](url) 中 显示文字 是 ID 的情况（已链接）
    
    # 用占位符方法：先把已有的 [xxx](yyy) 整体替换为占位符，防止误替换，最后还原
    
    # 阶段1：提取已有链接，替换为占位符
    placeholders = {}
    placeholder_counter = [0]
    
    def save_link(m):
        key = f"\x00LINK{placeholder_counter[0]}\x00"
        placeholders[key] = m.group(0)
        placeholder_counter[0] += 1
        return key
    
    # 匹配 markdown 链接 [text](url) 包括嵌套括号
    link_re = re.compile(r'\[(?:[^\[\]]|\[[^\[\]]*\])*\]\([^)]*\)')
    # 匹配反引号代码
    code_re = re.compile(r'`[^`]*`')
    
    protected = link_re.sub(save_link, line)
    protected = code_re.sub(save_link, protected)
    
    # 阶段2：替换未链接的 ID
    def replace_id(m):
        item_id = m.group(0)
        link_path = make_link(item_id, item_map, hero_file)
        if link_path is None:
            return item_id  # 没有对应文件，不替换
        # 获取物品名称（从文件名中提取）
        item_rel = item_map[item_id]
        fname = Path(item_rel).stem  # e.g. I06H_柔凡剑
        parts = fname.split("_", 1)
        display_name = parts[1] if len(parts) > 1 else item_id
        return f"[{display_name}（{item_id}）]({link_path})"
    
    result = ITEM_ID_RE.sub(replace_id, protected)
    
    # 阶段3：还原占位符
    for key, val in placeholders.items():
        result = result.replace(key, val)
    
    return result


def main():
    item_map = build_item_map()
    print(f"✓ 已加载 {len(item_map)} 个物品映射")
    
    total_changes = 0
    modified_files = []
    
    for hero_file in sorted(HEROES_DIR.glob("*.md")):
        if hero_file.name == "index.md":
            continue
        
        changes, new_content = process_hero_file(hero_file, item_map)
        
        if changes:
            total_changes += len(changes)
            modified_files.append(hero_file.name)
            print(f"\n【{hero_file.name}】{len(changes)} 处修改：")
            for lineno, old, new in changes:
                print(f"  L{lineno}: {old.strip()[:80]}")
                print(f"       → {new.strip()[:80]}")
            
            hero_file.write_text(new_content, encoding="utf-8")
    
    print(f"\n完成！共修改 {len(modified_files)} 个英雄文件，{total_changes} 处链接。")
    if modified_files:
        print("修改文件：")
        for f in modified_files:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
