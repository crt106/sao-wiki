#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
item_wiki.md → 飞书多维表格 导入脚本
目标: https://crt10006.feishu.cn/base/YOUR_APP_TOKEN
数据表: YOUR_TABLE_ID
"""

import re
import sys
import time
import json
import requests

# Windows 控制台强制 UTF-8 输出，避免乱码
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────
APP_ID     = "YOUR_APP_ID"
APP_SECRET = "YOUR_APP_SECRET"
APP_TOKEN  = "YOUR_APP_TOKEN"
TABLE_ID   = "YOUR_TABLE_ID"

WIKI_PATH  = r"D:\Program Files\maps\刀剑物语2.3(忘川)测试版\table\wiki\item_wiki.md"

BASE_URL   = "https://open.feishu.cn/open-apis"

# 批量写入每批大小（API上限500，建议100保稳）
BATCH_SIZE = 100
# 写入批次间隔(秒)，避免触发 Write conflict
WRITE_INTERVAL = 1.0


# ──────────────────────────────────────────────
# 1. 获取 tenant_access_token
# ──────────────────────────────────────────────
def get_token() -> str:
    resp = requests.post(
        f"{BASE_URL}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=10,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {data}")
    print(f"[token] 获取成功，有效期 {data['expire']} 秒")
    return data["tenant_access_token"]


# ──────────────────────────────────────────────
# 2. 确保字段存在（先列出已有字段，缺少的再创建）
# ──────────────────────────────────────────────
DESIRED_FIELDS = [
    # (字段名,  type,  ui_type 或 None)
    ("物品ID",   1,  "Text"),
    ("物品名称", 1,  "Text"),
    ("分类",     3,  "SingleSelect"),
    ("品质",     3,  "SingleSelect"),
    ("来源层",   1,  "Text"),
    ("售价（金）", 2, "Number"),
    ("堆叠/使用次数", 1, "Text"),
    ("无法获取", 7,  "Checkbox"),
    ("描述",     1,  "Text"),
    ("用途",     1,  "Text"),
    ("获取方式", 1,  "Text"),
    ("攻击力",   2,  "Number"),
    ("筋力",     2,  "Number"),
    ("敏捷",     2,  "Number"),
    ("体力",     2,  "Number"),
    ("生命值上限", 2, "Number"),
    ("攻击速度", 1,  "Text"),
    ("防御力",   2,  "Number"),
    ("魔法防御", 1,  "Text"),
    ("闪避",     1,  "Text"),
    ("移动速度", 2,  "Number"),
    ("技能效果", 1,  "Text"),
    ("使用效果", 1,  "Text"),
]


def list_fields(token: str) -> dict:
    """返回 {字段名: field_id} 的映射"""
    resp = requests.get(
        f"{BASE_URL}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"列出字段失败: {data}")
    return {f["field_name"]: f["field_id"] for f in data["data"]["items"]}


def ensure_fields(token: str) -> dict:
    """确保 DESIRED_FIELDS 中的每个字段都存在，返回最终的 {字段名: field_id}"""
    existing = list_fields(token)
    print(f"[fields] 已有字段: {list(existing.keys())}")

    # 索引列（第一列）名称可能已是"物品ID"，也可能是默认"文本"——只检查非索引列
    # 飞书索引列不能通过新增字段接口创建，需要手动改名或接受默认
    for name, ftype, ui_type in DESIRED_FIELDS:
        if name in existing:
            continue
        body = {"field_name": name, "type": ftype}
        if ui_type:
            body["ui_type"] = ui_type
        resp = requests.post(
            f"{BASE_URL}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json=body,
            timeout=10,
        )
        result = resp.json()
        if result.get("code") != 0:
            print(f"  [warn] 创建字段「{name}」失败: {result.get('msg')}")
        else:
            fid = result["data"]["field"]["field_id"]
            existing[name] = fid
            print(f"  [fields] 创建「{name}」→ {fid}")
        time.sleep(0.15)  # 字段接口限速 10次/秒

    return existing


# ──────────────────────────────────────────────
# 3. 解析 Markdown
# ──────────────────────────────────────────────

# 章节标题 → 分类名
SECTION_MAP = {
    "一": "素材",
    "二": "武器",
    "三": "副武器",
    "四": "道具",
    "五": "装甲",
    "六": "头部道具",
    "七": "不归类",
    "八": "消耗物品",
    "九": "特殊",
}

# 正则：章节标题
RE_SECTION = re.compile(r"^## ([一二三四五六七八九])、")

# 正则：物品标题   ### I000 · 名称（无法获取）
#                  ### I000 — 名称
RE_ITEM_TITLE = re.compile(
    r"^### ([A-Za-z0-9]+)\s*[·—]\s*(.+?)(?:（无法获取）)?\s*$"
)

# 正则：元数据行  > **来源层**：...  **品质**：...
RE_META_LINE = re.compile(r"^>\s*(.+)$")

# 正则：单个元数据字段  **键**：值
RE_META_KV   = re.compile(r"\*\*([^*]+)\*\*[：:]\s*([^　\t]+)")

# 正则：属性表行  | 攻击力 | +500 |
RE_ATTR_ROW  = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")

# 正则：技能/效果表行（3列）  | 技能名 | 类型 | 效果 |
RE_SKILL_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")

# 需要跳过的表头行关键字
SKIP_ROWS = {"属性", "数值", "技能名", "效果", "类型", "---"}


def parse_price(raw: str) -> int | None:
    """'10,000金' → 10000"""
    m = re.search(r"([\d,]+)", raw.replace(",", ""))
    return int(m.group(1)) if m else None


def parse_percent_or_num(raw: str):
    """'+26%' → '+26%'(str)；'+500' → 500(int)"""
    raw = raw.strip()
    if "%" in raw:
        return raw  # 保留百分比文本
    m = re.search(r"[-+]?([\d,]+)", raw.replace(",", ""))
    return int(m.group()) if m else None


def parse_wiki(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    items = []
    current_section = ""
    current_item: dict | None = None
    in_attr_block   = False   # 基础属性表
    in_skill_block  = False   # 技能/效果表
    in_use_block    = False   # 使用效果表

    def flush():
        nonlocal current_item
        if current_item:
            items.append(current_item)
        current_item = None

    for raw_line in lines:
        line = raw_line.rstrip("\n")

        # ── 章节
        m = RE_SECTION.match(line)
        if m:
            flush()
            current_section = SECTION_MAP.get(m.group(1), "")
            in_attr_block = in_skill_block = in_use_block = False
            continue

        # ── 物品标题
        m = RE_ITEM_TITLE.match(line)
        if m:
            flush()
            item_id   = m.group(1).upper()
            raw_title = line[4:]  # 去掉 "### "
            name_raw  = m.group(2).strip()
            unavail   = "（无法获取）" in raw_title
            current_item = {
                "物品ID":     item_id,
                "物品名称":   name_raw,
                "分类":       current_section,
                "品质":       "",
                "来源层":     "",
                "售价（金）": None,
                "堆叠/使用次数": "",
                "无法获取":   unavail,
                "描述":       "",
                "用途":       [],
                "获取方式":   [],
                "攻击力":     None,
                "筋力":       None,
                "敏捷":       None,
                "体力":       None,
                "生命值上限": None,
                "攻击速度":   "",
                "防御力":     None,
                "魔法防御":   "",
                "闪避":       "",
                "移动速度":   None,
                "技能效果":   [],
                "使用效果":   [],
            }
            in_attr_block = in_skill_block = in_use_block = False
            continue

        if current_item is None:
            continue

        # ── 元数据行（以 > 开头）
        if RE_META_LINE.match(line) and not line.startswith("> ⚠️"):
            meta_text = RE_META_LINE.match(line).group(1)
            for k, v in RE_META_KV.findall(meta_text):
                k, v = k.strip(), v.strip()
                if k == "来源层":
                    current_item["来源层"] = v
                elif k == "品质":
                    current_item["品质"] = v
                elif k == "售价":
                    current_item["售价（金）"] = parse_price(v)
                elif k in ("堆叠上限", "使用次数"):
                    current_item["堆叠/使用次数"] = v
                elif k == "类型":
                    # 副武器/道具的子类型，附加到分类
                    if current_item["分类"] in ("副武器", "道具"):
                        current_item["分类"] = current_item["分类"] + f"/{v}"
            continue

        # ── 块标题
        if line.strip() == "**基础属性**":
            in_attr_block = True
            in_skill_block = in_use_block = False
            continue
        if line.strip() in ("**技能效果**",):
            in_skill_block = True
            in_attr_block = in_use_block = False
            continue
        if line.strip() in ("**使用效果**",):
            in_use_block = True
            in_attr_block = in_skill_block = False
            continue

        # ── 属性表行
        if in_attr_block and line.startswith("|"):
            m2 = RE_ATTR_ROW.match(line)
            if not m2:
                continue
            attr, val = m2.group(1).strip(), m2.group(2).strip()
            if attr in SKIP_ROWS or val in SKIP_ROWS or attr.startswith("-"):
                continue
            parsed = parse_percent_or_num(val)
            if attr == "攻击力":
                current_item["攻击力"] = parsed if isinstance(parsed, int) else None
            elif attr == "筋力":
                current_item["筋力"] = parsed if isinstance(parsed, int) else None
            elif attr == "敏捷":
                current_item["敏捷"] = parsed if isinstance(parsed, int) else None
            elif attr == "体力":
                current_item["体力"] = parsed if isinstance(parsed, int) else None
            elif attr in ("生命值上限", "HP上限"):
                # 可能含括号注释，只取第一个数字
                m3 = re.search(r"\+?([\d,]+)", val.replace(",", ""))
                current_item["生命值上限"] = int(m3.group(1)) if m3 else None
            elif attr == "攻击速度":
                current_item["攻击速度"] = val
            elif attr == "防御力":
                current_item["防御力"] = parsed if isinstance(parsed, int) else None
            elif attr == "魔法防御":
                current_item["魔法防御"] = val
            elif attr == "闪避":
                current_item["闪避"] = val
            elif attr == "移动速度":
                current_item["移动速度"] = parsed if isinstance(parsed, int) else None
            continue

        # ── 技能表行
        if in_skill_block and line.startswith("|"):
            m2 = RE_SKILL_ROW.match(line)
            if not m2:
                # 可能是2列格式
                m2b = RE_ATTR_ROW.match(line)
                if m2b:
                    n, e = m2b.group(1).strip(), m2b.group(2).strip()
                    if n not in SKIP_ROWS and e not in SKIP_ROWS and not n.startswith("-"):
                        current_item["技能效果"].append(f"{n}：{e}")
                continue
            name, typ, eff = m2.group(1).strip(), m2.group(2).strip(), m2.group(3).strip()
            if name in SKIP_ROWS or name.startswith("-"):
                continue
            current_item["技能效果"].append(f"[{typ}] {name}：{eff}")
            continue

        # ── 使用效果表行
        if in_use_block and line.startswith("|"):
            m2 = RE_ATTR_ROW.match(line)
            if m2:
                attr, val = m2.group(1).strip(), m2.group(2).strip()
                if attr not in SKIP_ROWS and val not in SKIP_ROWS and not attr.startswith("-"):
                    current_item["使用效果"].append(f"{attr}：{val}")
            continue

        # ── 列表行（描述/用途/获取）
        if line.startswith("- "):
            content = line[2:].strip()
            if content.startswith("描述：") or content.startswith("描述:"):
                current_item["描述"] = content[3:].strip()
            elif content.startswith("**用途**：") or content.startswith("**用途**:"):
                txt = re.sub(r"\*\*用途\*\*[：:]", "", content).strip()
                if txt:
                    current_item["用途"].append(txt)
            elif content.startswith("**获取**：") or content.startswith("**获取**:"):
                txt = re.sub(r"\*\*获取\*\*[：:]", "", content).strip()
                if txt:
                    current_item["获取方式"].append(txt)
            elif content.startswith("**效果**：") or content.startswith("**效果**:"):
                txt = re.sub(r"\*\*效果\*\*[：:]", "", content).strip()
                if txt:
                    current_item["使用效果"].append(txt)
            elif content.startswith("打造") or content.startswith("用于"):
                current_item["用途"].append(content)
            continue

        # ── 次级列表（用途多条）
        if line.startswith("  - "):
            content = line[4:].strip()
            if content:
                current_item["用途"].append(content)
            continue

        # ── 分隔线：重置块状态（空行不重置，属性块和表格之间有空行）
        if line.strip() == "---":
            in_attr_block = in_skill_block = in_use_block = False

    flush()
    return items


# ──────────────────────────────────────────────
# 4. 将解析结果转为飞书 fields 格式
# ──────────────────────────────────────────────
def item_to_fields(item: dict) -> dict:
    def text(v):
        """文本字段格式"""
        s = str(v).strip() if v else ""
        return s or None

    def num(v):
        return v if isinstance(v, (int, float)) else None

    fields = {}

    def add(key, val):
        if val is not None and val != "" and val != []:
            fields[key] = val

    add("物品ID",     text(item["物品ID"]))
    add("物品名称",   text(item["物品名称"]))
    add("分类",       text(item["分类"]))
    add("品质",       text(item["品质"]) or None)
    add("来源层",     text(item["来源层"]) or None)
    add("售价（金）", num(item["售价（金）"]))
    add("堆叠/使用次数", text(item["堆叠/使用次数"]) or None)
    # 复选框
    fields["无法获取"] = bool(item["无法获取"])
    add("描述",       text(item["描述"]) or None)
    add("用途",       "\n".join(item["用途"]) if item["用途"] else None)
    add("获取方式",   "\n".join(item["获取方式"]) if item["获取方式"] else None)
    add("攻击力",     num(item["攻击力"]))
    add("筋力",       num(item["筋力"]))
    add("敏捷",       num(item["敏捷"]))
    add("体力",       num(item["体力"]))
    add("生命值上限", num(item["生命值上限"]))
    add("攻击速度",   text(item["攻击速度"]) or None)
    add("防御力",     num(item["防御力"]))
    add("魔法防御",   text(item["魔法防御"]) or None)
    add("闪避",       text(item["闪避"]) or None)
    add("移动速度",   num(item["移动速度"]))
    add("技能效果",   "\n".join(item["技能效果"]) if item["技能效果"] else None)
    add("使用效果",   "\n".join(item["使用效果"]) if item["使用效果"] else None)

    return fields


# ──────────────────────────────────────────────
# 5. 拉取表中已有记录（用于去重）
# ──────────────────────────────────────────────
def fetch_existing_records(token: str) -> dict[str, str]:
    """
    分页拉取表中所有记录，返回 {物品ID: record_id} 映射。
    物品ID 字段名为「物品ID」，内容是纯文本。
    """
    url = f"{BASE_URL}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
    headers = {"Authorization": f"Bearer {token}"}
    existing: dict[str, str] = {}
    page_token = None

    print("[去重] 拉取表中已有记录...")
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token

        resp = requests.get(url, headers=headers, params=params, timeout=30)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"拉取记录失败: {data}")

        items = data["data"].get("items", [])
        for rec in items:
            rid = rec["record_id"]
            fields = rec.get("fields", {})
            # 物品ID 字段在飞书返回时是文本段落列表，需展平
            raw_id = fields.get("物品ID", "")
            if isinstance(raw_id, list):
                # 多行文本格式：[{"text": "I000", "type": "text"}, ...]
                item_id = "".join(seg.get("text", "") for seg in raw_id).strip()
            else:
                item_id = str(raw_id).strip()
            if item_id:
                existing[item_id] = rid

        has_more = data["data"].get("has_more", False)
        page_token = data["data"].get("page_token")
        print(f"  已拉取 {len(existing)} 条...")
        if not has_more:
            break
        time.sleep(0.3)

    print(f"[去重] 表中现有 {len(existing)} 条记录")
    return existing


# ──────────────────────────────────────────────
# 6. 批量操作（通用重试包装）
# ──────────────────────────────────────────────
def _batch_request(token: str, url: str, payload: dict, label: str) -> tuple[int, int]:
    """单批次 POST，失败重试3次。返回 (success_count, fail_count)"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    for attempt in range(3):
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        data = resp.json()
        if data.get("code") == 0:
            return len(payload.get("records", [])), 0
        elif data.get("code") in (1254291, 1254607):
            wait = (attempt + 1) * 2
            print(f"  [重试] {label} code={data['code']} 等待{wait}s...")
            time.sleep(wait)
        else:
            print(f"  [失败] {label} code={data['code']} msg={data.get('msg')}")
            return 0, len(payload.get("records", []))
    return 0, len(payload.get("records", []))


def batch_create(token: str, records: list[dict]):
    """records: [{"fields": {...}}, ...]"""
    if not records:
        print("[新增] 无新记录需要写入")
        return
    url = f"{BASE_URL}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_create"
    total = len(records)
    success = fail = 0
    for i in range(0, total, BATCH_SIZE):
        batch = records[i: i + BATCH_SIZE]
        s, f = _batch_request(token, url, {"records": batch},
                              f"新增 {i+1}~{min(i+BATCH_SIZE, total)}/{total}")
        success += s
        fail += f
        if s:
            print(f"  [新增] {i+1}~{min(i+BATCH_SIZE, total)} / {total} ✓")
        time.sleep(WRITE_INTERVAL)
    print(f"[新增完成] 成功 {success} 条，失败 {fail} 条")


def batch_update(token: str, records: list[dict]):
    """records: [{"record_id": "...", "fields": {...}}, ...]"""
    if not records:
        print("[更新] 无已有记录需要更新")
        return
    url = f"{BASE_URL}/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_update"
    total = len(records)
    success = fail = 0
    for i in range(0, total, BATCH_SIZE):
        batch = records[i: i + BATCH_SIZE]
        s, f = _batch_request(token, url, {"records": batch},
                              f"更新 {i+1}~{min(i+BATCH_SIZE, total)}/{total}")
        success += s
        fail += f
        if s:
            print(f"  [更新] {i+1}~{min(i+BATCH_SIZE, total)} / {total} ✓")
        time.sleep(WRITE_INTERVAL)
    print(f"[更新完成] 成功 {success} 条，失败 {fail} 条")


# ──────────────────────────────────────────────
# main
# ──────────────────────────────────────────────
def main():
    # 1. token
    token = get_token()

    # 2. 确保字段
    print("\n[step 2] 检查并补全字段...")
    ensure_fields(token)

    # 3. 解析 markdown
    print(f"\n[step 3] 解析 {WIKI_PATH} ...")
    items = parse_wiki(WIKI_PATH)
    print(f"  共解析出 {len(items)} 条物品")

    # 调试：输出前3条看看
    for itm in items[:3]:
        print(json.dumps({k: v for k, v in itm.items() if v is not None and v != [] and v != ""},
                         ensure_ascii=False, indent=2))

    # 4. 拉取已有记录，建立 物品ID → record_id 映射
    print("\n[step 4] 检查已有记录...")
    existing_map = fetch_existing_records(token)   # {物品ID: record_id}

    # 5. 按物品ID分流：新增 vs 更新
    to_create: list[dict] = []   # [{"fields": {...}}]
    to_update: list[dict] = []   # [{"record_id": "...", "fields": {...}}]

    for itm in items:
        fields = item_to_fields(itm)
        item_id = itm["物品ID"]
        if item_id in existing_map:
            to_update.append({"record_id": existing_map[item_id], "fields": fields})
        else:
            to_create.append({"fields": fields})

    print(f"\n[step 5] 分流结果：新增 {len(to_create)} 条 / 更新 {len(to_update)} 条")

    # 6. 执行写入
    print("\n── 新增 ──")
    batch_create(token, to_create)

    print("\n── 更新 ──")
    batch_update(token, to_update)

    print("\n[全部完成]")


if __name__ == "__main__":
    main()
