#!/usr/bin/env python3
"""
split_items_to_pages.py
将 docs/items/ 下的分类 .md 文件拆分为每个物品独立的 .md 文件
结构: docs/items/{类别}/{ITEM_ID}.md
"""

import re
import os
from pathlib import Path

# 路径配置
BASE_DIR = Path(__file__).parent.parent
ITEMS_DIR = BASE_DIR / "docs" / "items"

# 分类文件名 → 子目录名
CATEGORY_MAP = {
    "素材.md": "素材",
    "武器.md": "武器",
    "副武器.md": "副武器",
    "装备道具.md": "装备道具",
    "装甲.md": "装甲",
    "头部道具.md": "头部道具",
    "不归类.md": "不归类",
    "消耗物品.md": "消耗物品",
    "特殊.md": "特殊",
}

# 物品ID → 所在类别（用于解析跨类别链接）
item_to_category: dict[str, str] = {}


def parse_category_file(filepath: Path):
    """
    解析分类文件，返回 (intro_text, [(item_id, item_name, item_content), ...])
    item_id 已统一为大写
    """
    content = filepath.read_text(encoding="utf-8")
    item_pattern = re.compile(r"^### ([A-Za-z][0-9A-Za-z]{2,4}) · (.+)$", re.MULTILINE)

    parts = item_pattern.split(content)
    # parts[0]          = 分类引言
    # parts[1,2,3]      = id, name, content (第一个物品)
    # parts[4,5,6]      = id, name, content (第二个物品) ...

    intro = parts[0]
    items = []
    for i in range(1, len(parts), 3):
        if i + 2 <= len(parts):
            raw_id = parts[i]
            item_id = raw_id.upper()
            item_name = parts[i + 1]
            item_content = parts[i + 2]
            # 去除末尾多余的 --- 分隔线和空白
            item_content = re.sub(r"\n---\s*$", "", item_content.rstrip())
            items.append((item_id, item_name, item_content))

    return intro, items


def fix_links(content: str, current_category: str) -> str:
    """
    修复内容中的锚点链接：
    - [text](#iXXX)            → [text](IXXX.md)  或  [text](../其他类/IXXX.md)
    - [text](category.md#iXXX) → [text](IXXX.md)  或  [text](../其他类/IXXX.md)
    """

    def resolve(item_id_lower: str, current_category: str) -> str:
        item_id_upper = item_id_lower.upper()
        target_cat = item_to_category.get(item_id_upper)
        if target_cat and target_cat != current_category:
            return f"../{target_cat}/{item_id_upper}.md"
        else:
            return f"{item_id_upper}.md"

    # 同页锚点: [text](#iXXX)
    def fix_same_page(m):
        text = m.group(1)
        item_id_lower = m.group(2)
        href = resolve(item_id_lower, current_category)
        return f"[{text}]({href})"

    content = re.sub(r"\[([^\]]*)\]\(#(i[0-9a-zA-Z]+)\)", fix_same_page, content)

    # 跨页链接: [text](分类.md#iXXX)
    def fix_cross_page(m):
        text = m.group(1)
        item_id_lower = m.group(3)
        href = resolve(item_id_lower, current_category)
        return f"[{text}]({href})"

    content = re.sub(
        r"\[([^\]]*)\]\(([^)]+\.md)#(i[0-9a-zA-Z]+)\)", fix_cross_page, content
    )

    return content


def build_item_table(items: list, prefix: str = "") -> str:
    """生成物品列表表格（用于分类 index.md）"""
    rows = []
    for item_id, item_name, _ in items:
        rows.append(
            f"| [{item_id}]({prefix}{item_id}.md) | [{item_name}]({prefix}{item_id}.md) |"
        )
    return "| ID | 名称 |\n|---|---|\n" + "\n".join(rows)


def main():
    # ── 第一遍：建立 item_id → category 映射 ──
    for filename, category in CATEGORY_MAP.items():
        filepath = ITEMS_DIR / filename
        if not filepath.exists():
            print(f"  [跳过] {filepath} 不存在")
            continue
        content = filepath.read_text(encoding="utf-8")
        for m in re.finditer(
            r"^### ([A-Za-z][0-9A-Za-z]{2,4}) ·", content, re.MULTILINE
        ):
            item_to_category[m.group(1).upper()] = category

    print(f"物品ID映射完成：{len(item_to_category)} 个物品\n")

    created_total = 0

    # ── 第二遍：拆分各分类文件，生成子目录 ──
    for filename, category in CATEGORY_MAP.items():
        filepath = ITEMS_DIR / filename
        if not filepath.exists():
            continue

        print(f"处理 {filename} → {category}/")
        intro, items = parse_category_file(filepath)

        cat_dir = ITEMS_DIR / category
        cat_dir.mkdir(exist_ok=True)

        # ── 生成分类 index.md ──
        intro_clean = intro.strip().lstrip("\ufeff")
        # 若头部是 "# 武器" 这样的 H1，保留；否则补一个
        if not re.match(r"^#", intro_clean):
            intro_clean = f"# {category}\n\n{intro_clean}"

        item_table = build_item_table(items)
        index_content = (
            intro_clean
            + "\n\n## 物品列表\n\n"
            + item_table
            + "\n\n---\n\n*最后更新：2026-04-15 · 地图版本：2.3 忘川*\n"
        )
        (cat_dir / "index.md").write_text(index_content, encoding="utf-8")

        # ── 生成 .pages（仅设 title，不穷举物品文件，依赖 MkDocs 自动发现） ──
        pages_content = f"title: {category}\n"
        (cat_dir / ".pages").write_text(pages_content, encoding="utf-8")

        # ── 为每个物品生成独立 .md ──
        for item_id, item_name, item_content in items:
            fixed_content = fix_links(item_content, category)
            file_content = f"# {item_id} · {item_name}\n{fixed_content}\n"
            item_filepath = cat_dir / f"{item_id}.md"
            item_filepath.write_text(file_content, encoding="utf-8")

        print(f"  ✓ {len(items)} 个物品文件 + index.md + .pages")
        created_total += len(items)

    print(f"\n共创建 {created_total} 个物品文件")

    # ── 更新顶层 .pages，将分类 .md 替换为子目录 ──
    top_pages = ITEMS_DIR / ".pages"
    nav_items = ["  - index.md"] + [f"  - {d}/" for d in CATEGORY_MAP.values()]
    pages_content = "title: 物品图鉴\nnav:\n" + "\n".join(nav_items) + "\n"
    top_pages.write_text(pages_content, encoding="utf-8")
    print("\n已更新 docs/items/.pages（指向子目录）")

    # ── 更新 index.md 的分类链接 ──
    index_path = ITEMS_DIR / "index.md"
    if index_path.exists():
        index_text = index_path.read_text(encoding="utf-8")
        for filename, category in CATEGORY_MAP.items():
            # 将 [xxx](分类.md) 替换为 [xxx](分类/)
            index_text = index_text.replace(f"]({filename})", f"]({category}/)")
            index_text = index_text.replace(f"]({filename}#", f"]({category}/index.md#")

        index_path.write_text(index_text, encoding="utf-8")
        print("已更新 docs/items/index.md 中的分类链接")

    print("\n完成！请运行 mkdocs build 验证。")
    print("原分类 .md 文件（如武器.md）仍保留，确认无误后可手动删除。")


if __name__ == "__main__":
    main()
