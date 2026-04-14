# CLAUDE.md

## 项目环境说明

- 操作系统：Windows 11
- Python 环境建议：3.10+，推荐使用虚拟环境（.venv）
- 推荐编辑器：VS Code
- 本项目为 MkDocs + Material 主题构建的 War3 刀剑物语地图 Wiki 站点

## 主要依赖

- mkdocs-material
- mkdocs-awesome-pages-plugin

## 目录结构

```
docs/            主文档目录（wiki 页面）
  heroes/        英雄图鉴页面
  items/         物品图鉴页面
  changelogs/    版本更新日志
docs_template/   页面模板（英雄/各类物品）
dev/             调研工作区（不发布到 wiki）
  hero.md        英雄图鉴详细数据（调研成果）
  hero_task.md   英雄调研任务清单与方法论
  item_wiki.md   物品图鉴详细数据
  item_wiki_task.md  物品待补全清单
  探索笔记.md    合成公式、专属武器、Boss掉落等探索记录
scripts/         批量处理与格式转换脚本
versions/        地图历史版本资源（已在 .gitignore 中排除）
  刀剑物语2.3(忘川)测试版/
    map/war3map.j     主脚本（43万行，15MB）
    table/unit.ini    单位数据
    table/ability.ini 技能数据
    table/item.ini    物品数据
    table/buff.ini    状态数据
  刀剑物语2.41测试版/  （同上结构）
site/            MkDocs 构建产物（已在 .gitignore 中排除）
```

## 维护者

- 地图作者：忘川
- Wiki 维护：crt106

---

## Wiki 编写工作流（核心方法论）

> **当前版本基准**：刀剑物语 2.3（忘川）测试版
> 所有调研数据基于 `versions/刀剑物语2.3(忘川)测试版/` 下的文件。

---

### 一、核心数据文件与用途

| 文件 | 用途 | 查找方式 |
|------|------|---------|
| `table/unit.ini` | 英雄/单位 ID、名称、属性成长、技能列表(abilList) | grep 单位ID或中文名 |
| `table/ability.ini` | 技能冷却(Cool)、消耗(Cost)、数值系数(DataA-F)、提示文字(Ubertip) | grep `^\[技能ID\]` |
| `table/item.ini` | 物品名称、品质、属性加成、ID 对应关系 | grep `^\[物品ID\]` |
| `map/war3map.j` | **所有触发逻辑、真实伤害计算、专属装备判断、合成/掉落** | **先 grep 定位行号，再 Read 片段** |

> ⚠️ **war3map.j 严禁整文件读取**（43万行/15MB）。始终先 grep 定位，再按行号 Read 片段（每次 limit≤150）。

---

### 二、英雄调研标准流程

#### 步骤 1：定位英雄单位 ID

```bash
# 优先：在 unit.ini 中 grep 中文名
grep -n "Name.*英雄名" versions/刀剑物语2.3\(忘川\)测试版/table/unit.ini

# 失败（编码问题）则改用已知ID或 hero_ability_add 批量扫描
grep -n "hero_ability_add" versions/刀剑物语2.3\(忘川\)测试版/map/war3map.j | head -80
```

找到段落头 `[XXXX]`，`XXXX` 即单位类型 ID（如 `Hamg` = 桐人）。

**特殊情况**：部分英雄技能不走 `hero_ability_add`，而用 `UnitAddAbility(gg_unit_XXXX_NNNN, ...)` 单独注册（如时崎狂三 `Nsjs`）：
```bash
grep -n "UnitAddAbility.*Nsjs" versions/刀剑物语2.3\(忘川\)测试版/map/war3map.j
```

#### 步骤 2：找技能 ID

**方法 A（优先）**：读 `hero_ability_init` 中的 `hero_ability_add` 行（war3map.j 第 **365197** 行附近）：
```
hero_ability_add('单位ID', 'Q技能ID', "Q名", 'W技能ID', "W名", ...)
```

**方法 B**：读 unit.ini 中该单位的 `abilList` 字段（含基础能力，需过滤）。

#### 步骤 3：查技能数值（ability.ini）

```bash
grep -n "^\[A0TB\]" versions/刀剑物语2.3\(忘川\)测试版/table/ability.ini
# 得到行号后：Read offset=行号 limit=30
```

关键字段：
- `Cool` = 冷却时间（秒）
- `Cost` = 魔法消耗
- `DataA` ~ `DataF` = 各等级系数（取第1个逗号前 = Lv1 数值）
- `Ubertip` = 工具提示文字（**不可盲信，策划文字可能与实际不符**）

#### 步骤 4：找触发器实现（war3map.j）

**方法 A：通过技能 ID 找施法事件入口**
```bash
grep -n "GetSpellAbilityId() == 'A0TB'" versions/刀剑物语2.3\(忘川\)测试版/map/war3map.j
# 返回行号 → 向上找 function Trig_XXX → Read 该函数
```

**方法 B：新式命名英雄（直接函数名）**

| 英雄 | 函数前缀 |
|------|---------|
| 五河琴里 | `hero_qingli_` |
| 蕾米莉亚 | `hero_leimi_` |
| 暗杀者（H06C） | `tina_` |

```bash
grep -n "^function hero_qingli_" versions/刀剑物语2.3\(忘川\)测试版/map/war3map.j
```

**方法 C：专属物品效果**
```bash
# 拾取事件（类型检查）
grep -n "GetItemTypeId.*'I0DK'" versions/刀剑物语2.3\(忘川\)测试版/map/war3map.j
# 背包检测（软专属）
grep -n "YDWEUnitHasItemOfTypeBJNull.*'I0DK'" versions/刀剑物语2.3\(忘川\)测试版/map/war3map.j
```

#### 步骤 5：读触发代码

```bash
grep -n "^function Trig_XXX" versions/刀剑物语2.3\(忘川\)测试版/map/war3map.j
# Read offset=行号 limit=80~150
# 大函数分段读取，每次 limit≤150
```

---

### 三、常见 JASS 伤害公式速查

| JASS 代码 | 含义 |
|-----------|------|
| `GetHeroStr(un, true)` | 当前力量（含加成） |
| `GetHeroAgi(un, true)` | 当前敏捷 |
| `GetHeroInt(un, true)` | 当前智力 |
| `GetHeroSAI(un, true)` | 全属性之和（STR+AGI+INT） |
| `ATTACK_TYPE_CHAOS` | 混乱攻击（无视护甲） |
| `DAMAGE_TYPE_DEMOLITION` | 毁灭伤害 |
| `GetRandomInt(a, b)` | 随机整数 a~b（用于浮动系数） |

**专属物品检测模式**：
```jass
// 硬专属（实例绑定）
YDWEGetItemOfTypeFromUnitBJNull(gg_unit_XXXX_NNNN, 'IYYY') != null

// 软专属（背包运行时检测）
YDWEUnitHasItemOfTypeBJNull(GetTriggerUnit(), 'IYYY') == true
```

---

### 四、war3map.j 关键行号速查（2.3版本）

| 位置 | 行号 | 说明 |
|------|------|------|
| `hero_ability_init` | **365197** | 英雄技能绑定总表（最常用） |
| `item_cx_add` 批量 | ~364xxx | 物品自定义被动效果注册 |
| `item_hc_init` | **365138** | 普通物品合成公式 |
| `item_xynum_init` | **365154** | 带数量合成（食物系统） |
| Boss 掉落集中区 | ~420000 | Boss 死亡掉落逻辑 |
| 时崎狂三技能注册 | ~395818 | `UnitAddAbility` 方式（非标准链）|
| 王珏实例掉落 | 420569 | `gg_unit_n02B_0589` 死亡触发 |
| 王珏类型掉落 | 420851 | 所有 `n02B` 类型触发 |

---

### 五、技能位解锁等级规则

| 技能位 | 解锁等级 | 说明 |
|--------|---------|------|
| Q | 3级 | |
| W | 10级 | |
| E | 15级 | |
| R | 20级 | |
| F | 35级 | 仅部分英雄有 |
| G | 120级 | 目前无英雄有此位 |
| D | 初始自带 | 由 `abilList` 或初始化触发器控制 |

---

### 六、重要注意事项

1. **Ubertip ≠ 真实数值**：技能描述文字是策划手写，实际触发器才是真值。凡「描述与实测差异」均来自触发器验证。
2. **中文 grep 可能因编码失败**：改用 4 字符 ID 搜索（如 `'Hamg'`、`'A0TB'`），不要依赖中文 grep。
3. **实例 vs 类型**：`gg_unit_Nsjs_0707` 是地图上特定实例，其**类型 ID** 是 `Nsjs`。两者用途不同。
4. **同名技能复用**：不同英雄可能共享同一 ability ID（如「疯狂幻想」），需交叉比对确认。
5. **触发器有多个入口**：同一技能的即时效果和 timer 延迟效果在不同函数里（如 `tina_R` 和 `tina_R_time`）。

---

### 七、调研进度追踪

- 英雄调研进度详见 `dev/hero_task.md`（含已完成/待完成清单）
- 物品调研进度详见 `dev/item_wiki_task.md`（A/B/C/D 四类待补全）
- 探索笔记（合成公式、专属武器、Boss掉落）见 `dev/探索笔记.md`

---

## 贡献说明

- 英雄/物品页面请参考 `docs_template/` 下对应模板
- 统一使用 UTF-8 编码
- 站点导航结构在 `mkdocs.yml` 中维护
- 数值须经触发器验证，不得仅凭工具提示文字填写
