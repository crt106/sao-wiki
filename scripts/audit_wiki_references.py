#!/usr/bin/env python3
"""审计 Wiki 正文中未链接的英雄、物品名称与 rawcode。

默认只输出汇总，不修改文档。使用 ``--report`` 可写出 JSON 明细；
后续批量链接必须基于人工复核后的唯一命中清单执行。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
HEROES = DOCS / "heroes"
ITEMS = DOCS / "items"
HERO_INVENTORY = ROOT / "dev" / "2.5_refresh" / "hero_inventory.csv"
ITEM_INVENTORY = ROOT / "dev" / "2.5_refresh" / "item_inventory.csv"

RAWCODE_RE = re.compile(r"^[A-Za-z0-9]{4}$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^\s*#{1,6}\s")
INLINE_CODE_RE = re.compile(r"`+[^`]*`+")
MARKDOWN_LINK_RE = re.compile(r"!?\[(?:[^\[\]]|\[[^\[\]]*\])*\]\([^\n]*?\)")
REFERENCE_LINK_RE = re.compile(r"!?\[[^\]\n]+\]\[[^\]\n]*\]")
HTML_RE = re.compile(r"<!--.*?-->|<[^>]+>")

# 文件名中的这些括注主要是分类或品质，不是玩家通常使用的物品名。
ITEM_SUFFIX_RE = re.compile(
    r"[（(](?:普通|优秀|精良|稀有|传说|史诗|礼物|专属[^）)]*|"
    r"不归类[^）)]*|融合|灵魂|稀有材料|道具|消耗品|任务物品)[）)]$"
)

# 页面标题往往使用称号或全名，而正文和更新日志更常用玩家熟悉的简称。
# 这里只登记能明确落到单一英雄页的别名；“黄泉”“冬弥”等对应多个页面的
# 名称继续保持歧义状态，不能自动链接。
HERO_MANUAL_ALIASES = {
    "⑨_琪露诺": ("琪露诺",),
    "五河琴里": ("琴里",),
    "兄控万岁_莉法": ("莉法",),
    "克萝伊_莉莉丝忒拉": ("克萝伊",),
    "冬_夜刀神十香": ("十香", "夜刀神十香"),
    "加速世界_黑雪姬": ("黑雪姬",),
    "娃娃_Saber": ("Saber",),
    "孤独轮回观测者_祸灵梦": ("祸灵梦",),
    "封弊者_桐谷和人_桐人": ("桐人", "桐谷和人"),
    "御坂美琴": ("美琴", "炮姐"),
    "斯托蕾亚_魔方": ("斯托蕾亚",),
    "时崎狂三": ("狂三",),
    "未来初音": ("初音",),
    "灼眼的夏娜": ("夏娜",),
    "白雪公主_White_Trailer": ("白雪", "White"),
    "穹_冬弥": ("穹妹",),
    "穿越时空的少女_椎名真白": ("真白", "椎名真白"),
    "绝剑_优纪": ("优纪",),
    "芙兰朵露_斯卡雷特": ("芙兰", "芙兰朵露"),
    "蕾米莉亚_斯卡雷特": ("蕾米莉亚",),
    "闪光_亚丝娜": ("亚丝娜",),
    "雷电_忘川守_芽衣_刺客": ("芽衣",),
    "驯兽师_西莉卡": ("西莉卡",),
}


@dataclass(frozen=True)
class Entity:
    kind: str
    entity_id: str
    name: str
    path: Path

    @property
    def docs_path(self) -> str:
        return self.path.relative_to(DOCS).as_posix()


def read_front_matter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.match(r"([A-Za-z0-9_]+):\s*[\"']?(.*?)[\"']?\s*$", line)
        if match:
            result[match.group(1)] = match.group(2)
    return result


def first_h1(text: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    if not match:
        return ""
    return re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", match.group(1)).strip()


def add_alias(alias_map: dict[str, set[Entity]], alias: str, entity: Entity) -> None:
    alias = alias.strip().strip("`*_ ")
    if len(alias) < 2:
        return
    alias_map[alias].add(entity)


def load_item_inventory() -> dict[str, str]:
    if not ITEM_INVENTORY.exists():
        return {}
    with ITEM_INVENTORY.open(encoding="utf-8-sig", newline="") as handle:
        return {
            row["item_id"].strip(): row["name_25"].strip()
            for row in csv.DictReader(handle)
            if row.get("item_id") and row.get("name_25")
        }


def load_hero_inventory() -> dict[str, str]:
    if not HERO_INVENTORY.exists():
        return {}
    with HERO_INVENTORY.open(encoding="utf-8-sig", newline="") as handle:
        return {
            Path(row["wiki_page"]).as_posix(): row["hero_name"].strip()
            for row in csv.DictReader(handle)
            if row.get("wiki_page") and row.get("hero_name")
        }


def build_index() -> tuple[list[Entity], dict[str, set[Entity]]]:
    entities: list[Entity] = []
    aliases: dict[str, set[Entity]] = defaultdict(set)
    item_names = load_item_inventory()
    hero_names = load_hero_inventory()

    for path in sorted(ITEMS.rglob("*.md")):
        if path.name == "index.md":
            continue
        stem_parts = path.stem.split("_", 1)
        if len(stem_parts) != 2 or not RAWCODE_RE.fullmatch(stem_parts[0]):
            continue
        item_id, filename_name = stem_parts
        canonical_name = item_names.get(item_id, filename_name)
        entity = Entity("item", item_id, canonical_name, path)
        entities.append(entity)
        add_alias(aliases, item_id, entity)
        add_alias(aliases, canonical_name, entity)
        add_alias(aliases, filename_name, entity)
        shortened = ITEM_SUFFIX_RE.sub("", filename_name).strip()
        if shortened != filename_name:
            add_alias(aliases, shortened, entity)

    for path in sorted(HEROES.glob("*.md")):
        if path.name == "index.md":
            continue
        text = path.read_text(encoding="utf-8-sig")
        rel = path.relative_to(ROOT).as_posix()
        front_matter = read_front_matter(text)
        canonical_name = hero_names.get(rel, front_matter.get("hero_title", first_h1(text)))
        entity = Entity("hero", path.stem, canonical_name, path)
        entities.append(entity)
        add_alias(aliases, canonical_name, entity)
        add_alias(aliases, front_matter.get("hero_title", ""), entity)
        add_alias(aliases, first_h1(text), entity)
        add_alias(aliases, path.stem.replace("_", "·"), entity)
        for alias in HERO_MANUAL_ALIASES.get(path.stem, ()):
            add_alias(aliases, alias, entity)

    return entities, aliases


def protected_line(line: str) -> str:
    """以空格覆盖不应扫描的 Markdown 区域，同时保留字符下标。"""
    chars = list(line)
    for pattern in (MARKDOWN_LINK_RE, REFERENCE_LINK_RE, INLINE_CODE_RE, HTML_RE):
        current = "".join(chars)
        for match in pattern.finditer(current):
            chars[match.start() : match.end()] = " " * (match.end() - match.start())
    return "".join(chars)


def find_matches(
    text: str,
    current_path: Path,
    alias_map: dict[str, set[Entity]],
    alias_pattern: re.Pattern[str],
) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    in_front_matter = text.startswith("---\n")
    in_fence = False

    for line_number, original_line in enumerate(text.splitlines(), start=1):
        stripped = original_line.strip()
        if in_front_matter:
            if line_number > 1 and stripped == "---":
                in_front_matter = False
            continue
        if FENCE_RE.match(original_line):
            in_fence = not in_fence
            continue
        if in_fence or HEADING_RE.match(original_line):
            continue

        searchable = protected_line(original_line)
        for found in alias_pattern.finditer(searchable):
            alias = found.group(0)
            is_rawcode = bool(RAWCODE_RE.fullmatch(alias))
            start, _ = found.span()
            candidates = sorted(
                alias_map[alias], key=lambda entity: (entity.kind, entity.docs_path)
            )
            # 本页自己的名称不是交叉引用。若有同名实体，也不能据此把本页正文
            # 自动链接到另一个页面，应由人工结合 rawcode 判断。
            if any(entity.path == current_path for entity in candidates):
                continue

            status = "unique" if len(candidates) == 1 else "ambiguous"
            matches.append(
                {
                    "file": current_path.relative_to(ROOT).as_posix(),
                    "line": line_number,
                    "column": start + 1,
                    "alias": alias,
                    "match_type": "rawcode" if is_rawcode else "name",
                    "status": status,
                    "targets": [
                        {
                            "kind": entity.kind,
                            "id": entity.entity_id,
                            "name": entity.name,
                            "path": entity.docs_path,
                        }
                        for entity in candidates
                    ],
                    "text": stripped,
                }
            )
    return matches


def audit(min_name_length: int) -> dict[str, object]:
    entities, alias_map = build_index()
    eligible_aliases = sorted(
        (
            alias
            for alias in alias_map
            if RAWCODE_RE.fullmatch(alias) or len(alias) >= min_name_length
        ),
        key=lambda value: (-len(value), value),
    )
    alias_pattern = re.compile("|".join(re.escape(alias) for alias in eligible_aliases))
    all_matches: list[dict[str, object]] = []
    for path in sorted(DOCS.rglob("*.md")):
        all_matches.extend(
            find_matches(
                path.read_text(encoding="utf-8-sig"),
                path,
                alias_map,
                alias_pattern,
            )
        )

    status_counts = Counter(match["status"] for match in all_matches)
    kind_counts = Counter(
        target["kind"]
        for match in all_matches
        if match["status"] == "unique"
        for target in match["targets"]
    )
    return {
        "summary": {
            "entity_count": len(entities),
            "item_count": sum(entity.kind == "item" for entity in entities),
            "hero_count": sum(entity.kind == "hero" for entity in entities),
            "alias_count": len(alias_map),
            "markdown_count": sum(1 for _ in DOCS.rglob("*.md")),
            "match_count": len(all_matches),
            "unique_count": status_counts["unique"],
            "ambiguous_count": status_counts["ambiguous"],
            "unique_item_count": kind_counts["item"],
            "unique_hero_count": kind_counts["hero"],
            "min_name_length": min_name_length,
        },
        "matches": all_matches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-name-length",
        type=int,
        default=4,
        help="扫描自然语言名称的最短字符数；rawcode 不受影响（默认：4）",
    )
    parser.add_argument("--report", type=Path, help="可选 JSON 报告路径")
    parser.add_argument(
        "--show",
        type=int,
        default=30,
        help="在控制台展示的前 N 条候选（默认：30）",
    )
    args = parser.parse_args()

    report = audit(args.min_name_length)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    for match in report["matches"][: args.show]:
        targets = "；".join(target["path"] for target in match["targets"])
        print(
            f"{match['status']:9} {match['file']}:{match['line']} "
            f"{match['alias']!r} -> {targets}"
        )

    if args.report:
        output = args.report
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"报告已写入：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
