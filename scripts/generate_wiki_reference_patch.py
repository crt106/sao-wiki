#!/usr/bin/env python3
"""根据引用审计结果生成可供 ``apply_patch`` 使用的安全链接补丁。

脚本只输出补丁，不直接修改 Wiki。默认仅处理不少于 4 个字符的唯一实体名
和唯一 rawcode，并跳过同一行已经链接到相同页面的重复展示。
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

from audit_wiki_references import ROOT, audit


# 这些名称既是物品名也是场景名。正文绝大多数命中描述的是地点，不能自动
# 指向同名传送物品；需要引用物品时应结合 rawcode 或语境人工链接。
LOCATION_ALIASES = {
    "不安之地",
    "冰晶之地",
    "冰雪世界",
    "凋零之地",
    "动能城",
    "废墟之城",
    "哥布林巢窟",
    "诡域大草原",
    "海与湖",
    "画中世界",
    "辉煌之地",
    "骸骨猎杀者房间",
    "黑暗深处",
    "红魔城宫殿",
    "楼兰后院",
    "楼兰前院",
    "墓地",
    "博丽神社",
    "青眼恶魔领地",
    "琼玉宫殿",
    "深绿之林",
    "深渊回廊",
    "圣灵堂",
    "诗画之乡",
    "霜冻平原",
    "苏醒之地",
    "通天塔",
    "通天塔第1层",
    "王的故乡",
    "伊偌遗迹",
    "遗迹之森",
    "幽静小镇",
}

# 名称确实与实体同名，但该处描述的是当前单位显示名，不是在引用另一英雄。
EXCLUDED_OCCURRENCES = {
    ("docs/changelogs/posts/2.3.md", "罪恶王冠"),
    ("docs/heroes/冬弥_泳装形态.md", "优库里伍德"),
    ("docs/heroes/御坂美琴.md", "超电磁炮"),
    ("docs/heroes/黑猫酱_五更琉璃.md", "魔主之手"),
    ("docs/items/武器/I0NX_诛仙四剑.md", "诛仙四剑"),
}

# 2～3 字名称只在不易与普通叙述、技能名或地点混淆时自动处理。未列出的
# 短名称仍会保留在审计报告中，供结合上下文人工确认。
SHORT_SAFE_ALIASES = {
    # 英雄
    "一皇",
    "爱丽丝",
    "爱弥斯",
    "艾基尔",
    "白雪",
    "克萝伊",
    "初音",
    "草壁操",
    "桐人",
    "狂三",
    "莉法",
    "缇娜",
    "美琴",
    "炮姐",
    "琴里",
    "十香",
    "夏娜",
    "西莉卡",
    "亚丝娜",
    "优纪",
    "琪露诺",
    "穹妹",
    "真白",
    "祸灵梦",
    "芙兰",
    "芽衣",
    "黑猫酱",
    "结衣",
    "克莱因",
    "莉奈娅",
    "莉伊",
    "喵可莉",
    "梦梦",
    "梦幻",
    "杀生丸",
    "数字君",
    "水月",
    # 物品
    "百花环",
    "彼岸",
    "恐惧盾",
    "冰冻天使",
    "沉语",
    "超神钓",
    "超新甲",
    "虫蛋壳",
    "腐蚀物质",
    "鸡肉",
    "祭鬼杖",
    "金将之冠",
    "绝迹",
    "绝仙剑",
    "酒之玉石",
    "奶酪",
    "凝冰",
    "牛奶",
    "啤酒",
    "强盗利刃",
    "桥姬",
    "切割吧!~秋刀鱼",
    "青森の水",
    "轻羽光弓",
    "萝卜",
    "人偶手杖",
    "戮仙剑",
    "生姜",
    "王之冠",
    "死树之矛",
    "蝶恋花",
    "蝴蝶结",
    "偷悦者",
    "武士甲",
    "陷仙剑",
    "邪恶战盔",
    "血蚀",
    "雪兔肉",
    "药材",
    "夜神",
    "影盔",
    "娱乐币",
    "油纸伞",
    "鸭子",
    "鸟之羽",
}


def relative_target(current_file: Path, target_docs_path: str) -> str:
    current = ROOT / current_file
    target = ROOT / "docs" / target_docs_path
    return os.path.relpath(target, current.parent).replace("\\", "/")


def has_same_target_link(line: str, target_docs_path: str) -> bool:
    """同一行已有目标链接时，不再把表格标签或 rawcode 重复包成链接。"""
    return "](" in line and Path(target_docs_path).name in line


def build_changes(min_name_length: int) -> tuple[dict[Path, str], Counter[str]]:
    report = audit(min_name_length)
    by_file: dict[Path, list[dict[str, object]]] = defaultdict(list)
    stats: Counter[str] = Counter()

    for match in report["matches"]:
        if match["status"] != "unique":
            stats["ambiguous"] += 1
            continue
        alias = str(match["alias"])
        file_path = Path(str(match["file"]))
        if (
            match["match_type"] == "name"
            and len(alias) < 4
            and alias not in SHORT_SAFE_ALIASES
        ):
            stats["short_unsafe"] += 1
            continue
        if alias in LOCATION_ALIASES:
            stats["location"] += 1
            continue
        if (file_path.as_posix(), alias) in EXCLUDED_OCCURRENCES:
            stats["context"] += 1
            continue
        by_file[file_path].append(match)

    changed: dict[Path, str] = {}
    for file_path, matches in by_file.items():
        absolute = ROOT / file_path
        original = absolute.read_text(encoding="utf-8-sig")
        lines = original.splitlines(keepends=True)
        per_line: dict[int, list[dict[str, object]]] = defaultdict(list)
        for match in matches:
            per_line[int(match["line"]) - 1].append(match)

        for line_index, line_matches in per_line.items():
            line = lines[line_index]
            replacements: list[tuple[int, int, str]] = []
            for match in line_matches:
                target = match["targets"][0]
                target_path = str(target["path"])
                if has_same_target_link(line, target_path):
                    stats["same_target"] += 1
                    continue
                alias = str(match["alias"])
                start = int(match["column"]) - 1
                end = start + len(alias)
                url = relative_target(file_path, target_path)
                replacements.append((start, end, f"[{alias}]({url})"))

            for start, end, replacement in sorted(replacements, reverse=True):
                line = line[:start] + replacement + line[end:]
                stats["linked"] += 1
            lines[line_index] = line

        updated = "".join(lines)
        if updated != original:
            changed[absolute] = updated
            stats["files"] += 1

    return changed, stats


def emit_patch(changed: dict[Path, str]) -> None:
    print("*** Begin Patch")
    for absolute, updated in sorted(changed.items()):
        original = absolute.read_text(encoding="utf-8-sig")
        diff = list(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile="before",
                tofile="after",
                n=2,
            )
        )
        print(f"*** Update File: {absolute}")
        for line in diff[2:]:
            if line.startswith("@@"):
                print("@@")
            else:
                sys.stdout.write(line)
        if diff and not diff[-1].endswith("\n"):
            print()
    print("*** End Patch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-name-length", type=int, default=4)
    parser.add_argument(
        "--path-prefix",
        type=str,
        help="只输出相对项目根目录位于此前缀下的文件补丁",
    )
    parser.add_argument("--file-start", type=int, default=0, help="排序后的起始文件下标")
    parser.add_argument("--file-count", type=int, help="本批最多输出多少个文件")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="只显示拟处理统计，不输出补丁",
    )
    args = parser.parse_args()
    changed, stats = build_changes(args.min_name_length)
    if args.path_prefix:
        prefix = args.path_prefix.replace("\\", "/").rstrip("/") + "/"
        changed = {
            path: text
            for path, text in changed.items()
            if path.relative_to(ROOT).as_posix().startswith(prefix)
        }
    ordered = sorted(changed.items())
    if args.file_count is not None:
        ordered = ordered[args.file_start : args.file_start + args.file_count]
    elif args.file_start:
        ordered = ordered[args.file_start :]
    changed = dict(ordered)
    if args.summary_only:
        for key in (
            "linked",
            "files",
            "same_target",
            "location",
            "context",
            "short_unsafe",
            "ambiguous",
        ):
            print(f"{key}: {stats[key]}")
    else:
        emit_patch(changed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
