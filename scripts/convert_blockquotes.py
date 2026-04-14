#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_blockquotes.py
将 docs/heroes/*.md 中的 Markdown blockquote 批量转换为 MkDocs Material Admonitions。

转换规则：
  A. `> ⚠️ **描述与实测差异**` + 若干 `> - ` 行
     → `!!! warning "描述与实测差异"` + `    - ` 缩进列表

  B. `> ⚠️ 单行说明文字`（无后续 `> -` 列表）
     → `!!! warning` + `    文字`

  C. `> **注**：...` 或 `> > **注**` 等带"注"前缀的说明
     → `!!! note "注"` + `    内容`

  D. 普通说明性 blockquote（不含 ⚠️，不以列表开头）
     → `!!! note` + `    内容`

  空 `>` 行（段落分隔用）在 blockquote 块内保留为 admonition 内的空行。
"""

import re
from pathlib import Path

HEROES_DIR = Path(__file__).parent.parent / "docs" / "heroes"


def strip_bq(line: str) -> str:
    """去掉行首的 '> ' 或 '>'"""
    if line.startswith("> "):
        return line[2:]
    if line.startswith(">"):
        return line[1:]
    return line


def convert_blockquote_block(bq_lines: list[str]) -> list[str]:
    """
    接受一个连续 blockquote 块（每行以 '>' 开头），
    返回转换后的 admonition 行列表。
    """
    inner = [strip_bq(l) for l in bq_lines]

    # 判断类型
    first = inner[0].rstrip()

    # ── A / B：⚠️ 开头 ──────────────────────────────────────────────
    if first.startswith("⚠️"):
        body = first[len("⚠️"):].strip()

        # A：标题行 = "**描述与实测差异**"（或含该字样），后面有 `- ` 列表
        if re.search(r"\*\*描述与实测差异\*\*", body):
            title = re.sub(r"\*\*(.*?)\*\*", r"\1", body)  # 去掉 ** **
            result = [f'!!! warning "{title}"\n']
            for l in inner[1:]:
                stripped = l.rstrip()
                if stripped == "":
                    result.append("\n")
                else:
                    result.append(f"    {stripped}\n")
            return result

        # B：其他 ⚠️ 单行 / 多行
        has_bullets = any(l.startswith("- ") or l.startswith("  -") for l in inner[1:])
        if has_bullets:
            result = ['!!! warning\n']
            for l in inner:
                stripped = l.rstrip()
                if stripped == "" or stripped == "⚠️":
                    result.append("\n")
                else:
                    # 去掉开头的 ⚠️
                    text = stripped.lstrip("⚠️").strip()
                    if text:
                        result.append(f"    {text}\n")
            return result
        else:
            # 单行警告
            result = ['!!! warning\n']
            # 把所有内容行拼成段落
            for l in inner:
                stripped = l.rstrip()
                text = stripped.lstrip("⚠️").strip()
                if text:
                    result.append(f"    {text}\n")
                elif stripped == "":
                    result.append("\n")
            return result

    # ── C：**注** 开头 ───────────────────────────────────────────────
    if re.match(r"\*\*注\*\*", first) or first.startswith("注：") or first.startswith("注:"):
        body = re.sub(r"^\*\*注\*\*[：:]\s*", "", first)
        body = re.sub(r"^注[：:]\s*", "", body)
        result = ['!!! note "注"\n', f"    {body}\n"]
        for l in inner[1:]:
            stripped = l.rstrip()
            if stripped == "":
                result.append("\n")
            else:
                result.append(f"    {stripped}\n")
        return result

    # ── D：普通说明性 blockquote ──────────────────────────────────────
    result = ['!!! note\n']
    for l in inner:
        stripped = l.rstrip()
        if stripped == "":
            result.append("\n")
        else:
            result.append(f"    {stripped}\n")
    return result


def convert_file(path: Path) -> int:
    """转换单个文件，返回转换的 blockquote 块数量。"""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    result: list[str] = []
    i = 0
    converted = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith(">"):
            # 收集连续的 blockquote 行
            bq_block: list[str] = []
            while i < len(lines) and lines[i].startswith(">"):
                bq_block.append(lines[i].rstrip("\n"))
                i += 1

            # 跳过只有空 `>` 的块（段落间隔符，不转换）
            non_empty = [l for l in bq_block if l.strip() not in (">", "")]
            if not non_empty:
                for l in bq_block:
                    result.append(l + "\n")
                continue

            # 按空 `>` 行拆成子块，分别转换（避免不同语义块被合并）
            sub_blocks: list[list[str]] = []
            current_sub: list[str] = []
            for bl in bq_block:
                if bl.strip() in (">", ""):
                    if current_sub:
                        sub_blocks.append(current_sub)
                        current_sub = []
                else:
                    current_sub.append(bl)
            if current_sub:
                sub_blocks.append(current_sub)

            if result and result[-1].strip() != "":
                result.append("\n")

            for si, sub in enumerate(sub_blocks):
                converted_block = convert_blockquote_block(sub)
                result.extend(converted_block)
                if si < len(sub_blocks) - 1:
                    result.append("\n")
                converted += 1

            if i < len(lines) and lines[i].strip() != "":
                result.append("\n")
        else:
            result.append(line)
            i += 1

    path.write_text("".join(result), encoding="utf-8")
    return converted


def main():
    md_files = sorted(HEROES_DIR.glob("*.md"))
    total = 0
    for f in md_files:
        if f.name == "index.md":
            continue
        n = convert_file(f)
        if n:
            print(f"  [ok] {f.name}  ({n} 块)")
            total += n
    print(f"\n共转换 {total} 个 blockquote 块，覆盖 {len(md_files)-1} 个英雄文件。")


if __name__ == "__main__":
    main()
