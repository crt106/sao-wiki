#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_heroes.py
将 wiki/hero.md 按 ## 标题拆分为 docs/heroes/<英雄名>.md 独立页面，
并生成 docs/heroes/index.md 总览索引和 docs/heroes/.pages 导航控制文件。

跳过以下非英雄节：目录、技能位获得与扩展位说明、特殊分配英雄
"""

import re
import os
from pathlib import Path

# ──────────────────────────────────────────────
# 路径配置
# ──────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
SRC  = ROOT / "wiki" / "hero.md"
DST  = ROOT / "docs" / "heroes"

# 跳过这些 ## 节（非英雄内容）
SKIP_SECTIONS = {"目录", "技能位获得与扩展位说明（2026-04 复查）", "特殊分配英雄"}

# ──────────────────────────────────────────────
# 文件名清洗：保留中文、字母、数字和常用连字符
# ──────────────────────────────────────────────
def to_filename(title: str) -> str:
    # 去掉括号及其内容中的特殊 markdown 字符，保留内容
    name = title.strip()
    # 替换常见特殊符号为下划线或空串
    name = re.sub(r"[·•·\s]+", "_", name)          # 中点、空格 → _
    name = re.sub(r"[（(]", "_", name)
    name = re.sub(r"[）)]", "", name)
    name = re.sub(r"[：:：/\\|★☆◆♦♥*\"'<>?]", "", name)
    name = re.sub(r"_{2,}", "_", name)              # 多个下划线合并
    name = name.strip("_")
    return name


# ──────────────────────────────────────────────
# 主逻辑
# ──────────────────────────────────────────────
def split():
    DST.mkdir(parents=True, exist_ok=True)

    src_text = SRC.read_text(encoding="utf-8")
    lines = src_text.splitlines(keepends=True)

    # —— 提取全局前导内容（# 一级标题 + 说明段落，直到第一个 ## 出现前）
    preamble_lines = []
    sections: list[tuple[str, list[str]]] = []   # (标题, 行列表)
    current_title = None
    current_lines: list[str] = []

    for line in lines:
        m = re.match(r"^## (.+)", line)
        if m:
            if current_title is not None:
                sections.append((current_title, current_lines))
            elif current_lines:
                preamble_lines = current_lines
            current_title = m.group(1).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    # 最后一节
    if current_title is not None:
        sections.append((current_title, current_lines))

    # —— 拆分写文件
    hero_entries: list[tuple[str, str]] = []  # (标题, 文件名无扩展)

    for title, sec_lines in sections:
        if title in SKIP_SECTIONS:
            print(f"  [skip] {title}")
            continue

        filename = to_filename(title)
        filepath = DST / f"{filename}.md"

        # 将 ## 标题降级为 # 标题（作为页面主标题）
        content_lines = []
        for i, l in enumerate(sec_lines):
            if i == 0 and l.startswith("## "):
                content_lines.append(f"# {title}\n")
            elif l.startswith("### "):
                content_lines.append(l.replace("### ", "## ", 1))
            elif l.startswith("#### "):
                content_lines.append(l.replace("#### ", "### ", 1))
            else:
                content_lines.append(l)

        filepath.write_text("".join(content_lines), encoding="utf-8")
        hero_entries.append((title, filename))
        print(f"  [ok]   {filename}.md ← {title}")

    # —— 生成 index.md（英雄总览表）
    index_lines = [
        "# 英雄图鉴\n\n",
        "游戏开始后，英雄以中立状态站在出生点旁的**选角区**。",
        "**双击**目标英雄可以领取。\n\n",
        "---\n\n",
        "| 英雄 | 页面 |\n",
        "|------|------|\n",
    ]
    for title, filename in hero_entries:
        index_lines.append(f"| {title} | [{title}]({filename}.md) |\n")

    (DST / "index.md").write_text("".join(index_lines), encoding="utf-8")
    print(f"\n[index] docs/heroes/index.md 已生成，共 {len(hero_entries)} 个英雄")

    # —— 生成 .pages（awesome-pages 控制：index 排第一，其余按文件名排序）
    pages_content = "title: 英雄图鉴\narrange:\n  - index.md\n  - ...\n"
    (DST / ".pages").write_text(pages_content, encoding="utf-8")
    print("[pages] docs/heroes/.pages 已生成")


if __name__ == "__main__":
    print(f"源文件: {SRC}")
    print(f"输出目录: {DST}\n")
    split()
