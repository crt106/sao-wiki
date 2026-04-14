# -*- coding: utf-8 -*-
"""
将英雄页面从表格格式转换为 ?? 折叠块格式。
规则：
- 基础属性表保留
- 技能表 -> 每个技能一个 ???+ abstract 块
- 描述与实测差异 -> 合并到对应技能块内
- 专属装备 -> 无表格，用文字/列表描述
- 保留标题行信息（头衔、主属性等）
"""

import re
import sys
from pathlib import Path

HEROES_DIR = Path(__file__).parent.parent / "docs" / "heroes"


def parse_md_table(lines: list[str]) -> list[dict]:
    """解析 markdown 表格，返回 list of dict（列名: 值）"""
    rows = []
    headers = None
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if headers is None:
            headers = cells
        elif re.match(r"^[-:| ]+$", line):
            continue  # 分隔行
        else:
            row = dict(zip(headers, cells))
            rows.append(row)
    return rows


def extract_table_block(lines: list[str], start: int) -> tuple[list[str], int]:
    """从 start 行开始提取连续的表格行（遇到空行或非表格行即停止）"""
    table_lines = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        table_lines.append(lines[i])
        i += 1
    return table_lines, i


def is_attr_table(table_lines: list[str]) -> bool:
    return bool(table_lines) and "属性" in table_lines[0] and "初始值" in table_lines[0]


def is_skill_table(table_lines: list[str]) -> bool:
    return bool(table_lines) and "槽位" in table_lines[0]


def is_equip_table(table_lines: list[str]) -> bool:
    return bool(table_lines) and "装备" in table_lines[0] and "效果" in table_lines[0]


def parse_skill_table(table_lines: list[str]) -> list[dict]:
    """解析技能表，合并跨行的单元格内容"""
    rows = parse_md_table(table_lines)
    return rows


def parse_diff_block(lines: list[str], start: int) -> tuple[dict, int]:
    """
    解析 !!! warning "描述与实测差异" 块。
    返回 ({slot: diff_text}, end_index)
    """
    diffs = {}
    i = start + 1  # 跳过 !!! warning 行
    current_lines = []
    while i < len(lines):
        line = lines[i]
        # 结束条件：非缩进且非空行
        if not line.startswith("    ") and line.strip() and not line.strip().startswith("-"):
            break
        if line.strip().startswith("-"):
            # 解析 "- Q：xxx" 形式
            content = line.strip()[2:].strip()
            # 匹配槽位前缀
            m = re.match(r"^([A-Z0-9第]+(?:技)?)\s*[：:]?\s*(.*)", content)
            if m:
                slot = m.group(1).strip()
                text = m.group(2).strip()
                diffs[slot] = text
            else:
                diffs.setdefault("_other", [])
                diffs["_other"].append(content)
        i += 1
    return diffs, i


def parse_note_block(lines: list[str], start: int) -> tuple[str, int]:
    """解析 !!! note 块，返回 (content, end_index)"""
    i = start + 1
    content_lines = []
    while i < len(lines):
        line = lines[i]
        if line.startswith("    ") or line.strip() == "":
            content_lines.append(line[4:] if line.startswith("    ") else "")
            i += 1
        else:
            break
    return "\n".join(content_lines).strip(), i


def slot_to_key(slot: str) -> str:
    """统一槽位键，用于匹配差异"""
    slot = slot.strip()
    # "第5技(F)" -> "第5技", "D" -> "D", "Q" -> "Q"
    slot = re.sub(r"\(.*?\)", "", slot).strip()
    return slot


def build_skill_block(skill: dict, diff_text: str | None) -> str:
    """构建单个技能的 ???+ abstract 折叠块"""
    slot = skill.get("槽位", "").strip()
    name = skill.get("技能名", "").strip()
    cd = skill.get("冷却", "").strip()
    effect = skill.get("效果", "").strip()
    unlock = skill.get("获得方式", skill.get("解锁方式", "")).strip()
    skill_id = skill.get("ID", "").strip()

    # 构建标题
    parts = []
    if slot:
        parts.append(slot)
    if name:
        parts.append(f"· {name}")
    if cd and cd != "—":
        parts.append(f"冷却：{cd}")
    elif cd == "—":
        parts.append("被动")
    if unlock:
        parts.append(unlock)

    title = "　".join(parts)

    lines = [f'???+ abstract "{title}"', ""]
    if skill_id:
        lines.append(f"    *技能ID：{skill_id}*")
        lines.append("")
    if effect:
        lines.append(f"    {effect}")
        lines.append("")
    if diff_text:
        lines.append(f"    !!! warning \"描述与实测差异\"")
        lines.append(f"        {diff_text}")
        lines.append("")

    return "\n".join(lines)


def convert_equip_table_to_text(table_lines: list[str]) -> str:
    """将装备表转换为列表形式"""
    rows = parse_md_table(table_lines)
    result = []
    for row in rows:
        equip = row.get("装备", "").strip()
        effect = row.get("效果", "").strip()
        if equip and effect:
            result.append(f"- **{equip}**：{effect}")
        elif equip:
            result.append(f"- {equip}")
    return "\n".join(result)


def convert_hero_file(filepath: Path) -> str:
    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines()

    output = []
    i = 0
    n = len(lines)

    attr_table_done = False
    skill_table_done = False
    equip_table_done = False

    # 收集技能差异，稍后合并
    skill_diffs = {}
    other_diffs = []

    # ----- 第一遍扫描：收集所有差异块 -----
    for j, line in enumerate(lines):
        if re.match(r'^!!! warning.*描述与实测差异', line):
            diffs, _ = parse_diff_block(lines, j)
            for k, v in diffs.items():
                if k == "_other":
                    other_diffs.extend(v)
                else:
                    skill_diffs[k] = v

    # ----- 第二遍：逐行重建 -----
    while i < n:
        line = lines[i]

        # 跳过原有的差异块（已合并到技能中）
        if re.match(r'^!!! warning.*描述与实测差异', line):
            _, i = parse_diff_block(lines, i)
            continue

        # 检测表格开始
        if line.strip().startswith("|"):
            table_lines, end = extract_table_block(lines, i)

            if is_attr_table(table_lines) and not attr_table_done:
                output.append("## 基础属性")
                output.append("")
                output.extend(table_lines)
                output.append("")
                attr_table_done = True
                i = end
                continue

            elif is_skill_table(table_lines) and not skill_table_done:
                skills = parse_skill_table(table_lines)
                output.append("## 技能")
                output.append("")
                for skill in skills:
                    slot_key = slot_to_key(skill.get("槽位", ""))
                    diff = skill_diffs.get(slot_key)
                    block = build_skill_block(skill, diff)
                    output.append(block)
                skill_table_done = True
                i = end
                continue

            elif is_equip_table(table_lines) and not equip_table_done:
                # 专属装备表 -> 列表形式
                # 找是否已有 ## 专属装备 标题，没有就插入
                if output and not any("专属装备" in l for l in output[-5:]):
                    output.append("## 专属装备")
                    output.append("")
                text = convert_equip_table_to_text(table_lines)
                output.append(text)
                output.append("")
                equip_table_done = True
                i = end
                continue
            else:
                # 其他表格原样保留
                output.extend(table_lines)
                output.append("")
                i = end
                continue

        # 处理 !!! warning（非差异块）和 !!! note
        if re.match(r'^!!! (note|warning|tip|info)', line) and "描述与实测差异" not in line:
            output.append(line)
            i += 1
            continue

        # "## 装备专属武器后的变化" 这类标题 -> 保留为 ## 专属装备 子节
        if re.match(r'^## 装备.+变化', line):
            if not any("专属装备" in l for l in output[-10:]):
                output.append("## 专属装备")
                output.append("")
            i += 1
            continue

        # 过滤掉旧的 "**专属武器**：xxx" 独立行（会合并进专属装备节）
        # 但先保留，稍后在专属装备节处理
        output.append(line)
        i += 1

    result = "\n".join(output)
    # 清理多余空行（超过2个连续空行 -> 2个）
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def main():
    files = sorted(HEROES_DIR.glob("*.md"))
    # 跳过 index.md 和 .pages
    skip = {"index.md"}
    converted = 0
    errors = []

    for fp in files:
        if fp.name in skip:
            continue
        # 跳过时崎狂三（已手动处理）
        if fp.stem == "时崎狂三":
            print(f"  跳过（已手动处理）: {fp.name}")
            continue
        try:
            new_content = convert_hero_file(fp)
            fp.write_text(new_content, encoding="utf-8")
            print(f"  ✓ {fp.name}")
            converted += 1
        except Exception as e:
            errors.append((fp.name, str(e)))
            print(f"  ✗ {fp.name}: {e}")

    print(f"\n完成：{converted} 个文件转换，{len(errors)} 个错误")
    for name, err in errors:
        print(f"  错误 [{name}]: {err}")


if __name__ == "__main__":
    main()
