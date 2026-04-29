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
| `item_cx_add` 函数定义 | **364002** | 物品查询添加函数签名 |
| `item_cx_init` | **364524** | 物品被动技能注册总表（约200条 `item_cx_add` 调用） |
| `item_hc_init` | **365138** | 普通物品合成公式（`item_hc_add` 调用） |
| `item_xynum_init` | **365154** | 带数量合成（食物系统，`item_xynum_add` 调用） |
| `item_ability_xx_init` | **365165** | 吸血/生命恢复类技能注册（`item_ability_xx_add` 调用） |
| Boss 掉落集中区 | ~420000 | Boss 死亡掉落逻辑（`boss_item_dl` / `CreateItem`） |
| 扭蛋机触发器 ND_a | **370487** | 扭蛋机A（使用 `ChooseRandomItemExBJ(level)` 按物品等级出货） |
| 扭蛋机触发器 nd_b | **370530** | 扭蛋机B（同上机制） |
| 物品升级链触发区 | ~387860 | 提升系列武器升级逻辑（`UnitAddItemTisheng` / `RemoveItem+AddItem`） |
| 特殊赠送触发区 | ~369500-370700 | 特殊物品赠送（`UnitAddItemByIdSwapped`） |
| 特殊掉落触发区 | ~423690 | 高阶特殊物品掉落 |
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

### 六-B、物品调研标准流程

> 以下方法论来自武器类物品全量核查（150个）的实战经验，适用于所有物品类别。

#### 总体原则

1. **先建索引，再逐项核查**：不要逐个 grep 物品ID，而是先批量读取关键初始化函数（`item_cx_init`、`item_hc_init`、`item_ability_xx_init`），建立全局索引表，再按索引逐项核查。
2. **获取途径必须有触发器证据**：仅凭 item.ini 的 `goldcost` 或 `Level` 字段不能确定获取途径，必须在 war3map.j 中找到 `CreateItem`、`UnitAddItemByIdSwapped`、`boss_item_dl`、`AddItemToStock` 或 `ChooseRandomItemExBJ` 等实际创建/发放调用。
3. **无触发器引用 = 疑似无法获取**：如果一个物品ID在 war3map.j 中完全没有引用（除了 `item_cx_add` 技能注册外），应标记为"触发器无关联逻辑，当前版本无法获取"。

#### 步骤 1：建立物品ID清单

```powershell
# 从文件名提取物品ID（以武器为例）
Get-ChildItem "docs\items\武器\*.md" | Where-Object { $_.Name -ne "index.md" } |
  ForEach-Object { ($_.BaseName -split '_')[0] } | Sort-Object
```

#### 步骤 2：批量索引关键初始化函数

**2a. 技能效果索引（item_cx_init，约364524行）**

读取 `item_cx_init` 函数（每次 limit≤150），提取所有 `item_cx_add` 调用。参数格式：
```jass
call item_cx_add('物品ID', 0, 技能数量, "技能1名", "技能1效果", "技能2名", "技能2效果", ...)
// 第1参数：物品ID（4字符）或 0（通用技能定义）
// 第3参数：技能数量（1-4）
// 后续参数：成对的 技能名+效果描述
```

> ⚠️ 当第1参数为 `0` 时，该行定义的是通用技能（如"生命恢复Lv1"），不绑定特定物品。当第1参数为物品ID时，该行定义的是该物品的专属被动效果。

**2b. 吸血/生命恢复索引（item_ability_xx_init，约365165行）**

```jass
call item_ability_xx_add('物品ID', 吸血比例, 特效路径, 绑定点)
// 吸血比例：0.1=10%, 0.25=25%, 0.35=35%, 0.44=44%
```

**2c. 合成公式索引（item_hc_init，约365138行）**

```jass
call item_hc_add('结果ID', 材料数量, '材料1ID', '材料2ID', ...)
```

**2d. 带数量合成索引（item_xynum_init，约365154行）**

```jass
call item_xynum_add('结果ID', 材料种类数, '材料1ID', 数量1, '材料2ID', 数量2, ...)
```

#### 步骤 3：索引获取途径

按以下优先级逐一排查：

| 获取途径 | 搜索方法 | 关键特征 |
|---------|---------|---------|
| **扭蛋机** | 查 item.ini 中 `Level=201-205`（扭蛋机A）或 `211-215`（扭蛋机B） | `ChooseRandomItemExBJ(level)` 按等级随机出货 |
| **Boss掉落** | grep `'物品ID'` 在 420000+ 行区域 | `CreateItem` 或 `boss_item_dl` 调用 |
| **商店售卖** | 查 item.ini 中 `goldcost>0` 且 `Level` 为商店层级 | `AddItemToStockBJ` 或直接商店配置 |
| **合成产物** | 查 `item_hc_init` / `item_xynum_init` | `item_hc_add` / `item_xynum_add` |
| **升级链** | grep `'物品ID'` 在 387xxx 行区域 | `RemoveItem` + `UnitAddItemByIdSwapped` 模式 |
| **特殊赠送** | grep `'物品ID'` 在 369xxx-375xxx 行区域 | `UnitAddItemByIdSwapped` 调用 |
| **随机掉落池** | grep `RandomDistAddItem.*'物品ID'` | `RandomDistAddItem('物品ID', 权重)` |
| **地图放置** | grep `CreateItem.*'物品ID'` 在非Boss区域 | 固定坐标的 `CreateItem` |

#### 步骤 4：批量状态检查

用脚本批量检查 md 文件的当前状态，识别需要更新的文件：

```powershell
# 检查哪些文件的获取途径写"未知"
foreach ($id in $ids) {
  $files = Get-ChildItem "docs\items\武器\$id*.md"
  $content = Get-Content $files[0].FullName -Raw -Encoding UTF8
  if ($content -match "未知") { Write-Output "$id NEEDS_UPDATE" }
}
```

#### 步骤 5：更新 md 文件

- **有 BOM 的文件**（字节头 `EF BB BF`）：使用 `create` 命令重写整个文件（`strReplace` 可能因 BOM 匹配失败）
- **技能效果**：优先使用 `item_cx_add` 中的描述文字，它是游戏内 `-cxitem` 命令显示的内容
- **吸血类技能**：同时标注 `item_cx_add` 描述和 `item_ability_xx_init` 的实际比例值
- **获取途径链接化**：合成材料和升级产物应使用相对路径 markdown 链接

#### 关键经验教训

1. **扭蛋机判定靠 Level 字段，不靠 stockStart**：item.ini 中 `Level=201-205` 的物品在扭蛋机A出货池中。`stockStart=9999999` 只表示不在商店上架，不代表无法获取。
2. **Level=0 且无触发器引用 ≠ 扭蛋机**：之前有物品被错标为"扭蛋机2★出货"，实际 Level=0 不在任何出货池中。
3. **item_cx_add 第1参数为 0 vs 物品ID 的区别**：参数为 0 的行定义通用技能字典（如"生命恢复Lv1"对应能力ID `A0XL`）；参数为物品ID的行定义该物品的专属被动效果。
4. **升级链武器的获取途径**：提升系列武器（如"食刃·提升◆"）的获取途径是"由前一阶升级获得"，不需要独立的掉落/购买来源。
5. **批量处理优于逐个处理**：先用脚本批量扫描所有文件状态，识别出需要更新的子集，再集中处理，效率远高于逐个打开检查。

---

### 七、调研进度追踪

- 英雄调研进度详见 `dev/hero_task.md`（含已完成/待完成清单）
- 物品调研进度详见 `dev/item_wiki_task.md`
  - 武器类：150/150 全量核查完毕（2026-04-29）
  - 其他类别（装甲、副武器、头部道具、装备道具、素材、消耗物品、特殊、不归类）：待发起
- 探索笔记（合成公式、专属武器、Boss掉落）见 `dev/探索笔记.md`

---

## 页脚地图版本管理

站点使用 `mkdocs-git-revision-date-localized-plugin` 自动显示最后更新日期，地图版本通过以下机制维护：

## MkDocs 构建性能原则

本站文档数量较多，当前约 1000+ 个 Markdown 页面。`mkdocs-git-revision-date-localized-plugin` 会逐页读取 Git 最后修订时间，`mkdocs-git-authors-plugin` 会逐页统计作者信息；完整构建会明显变慢，这是 Git 元信息的正常成本。

### 本地开发默认快模式

本地编辑、预览和热更新时，优先关闭 Git 元信息插件，并使用 dirty reload：

```powershell
$env:MKDOCS_ENABLE_GIT_META="false"
$env:WATCHFILES_FORCE_POLLING="true"
.\.venv\Scripts\python.exe -m mkdocs serve --dirtyreload -a 127.0.0.1:8000
```

该模式不生成页脚 Git 修订日期和贡献者信息，但启动与热更新更快，适合日常写文档。

### 发布前完整构建

发布前或 CI 中保持默认完整构建，生成页脚 Git 修订日期和贡献者信息：

```powershell
Remove-Item Env:\MKDOCS_ENABLE_GIT_META -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m mkdocs build --strict
```

`mkdocs.yml` 中 Git 元信息插件通过环境变量控制：

```yaml
enabled: !ENV [MKDOCS_ENABLE_GIT_META, true]
```

默认值为 `true`，因此 GitHub Actions 和正式发布会保留完整页面元信息；只有本地显式设置 `MKDOCS_ENABLE_GIT_META=false` 时才关闭。

### 全局默认版本

在 `mkdocs.yml` 的 `extra.map_version` 中设置当前基准版本：

```yaml
extra:
  map_version: "2.3 忘川"
```

所有页面默认继承此值，显示于页脚右侧（地图图钉图标旁）。

### 单文件版本覆盖

若某页面内容对应更新的地图版本，在文件开头添加 YAML front matter：

```yaml
---
map_version: "2.41 测试版"
---
```

**当前已标注非默认版本的文件**（内容基于 2.41 测试版）：

| 文件 | map_version |
|------|-------------|
| `docs/heroes/克萝伊_莉莉丝忒拉.md` | `2.41 测试版` |
| `docs/heroes/雷电_忘川守_芽衣_刺客.md` | `2.41 测试版` |
| `docs/heroes/魅影十字军.md` | `2.41 测试版` |
| `docs/info/楼层信息.md` | `2.41 测试版` |

### 地图版本升级时的操作清单

当 Wiki 整体升级到新版本（如 2.5）时：

1. 修改 `mkdocs.yml` 中的 `extra.map_version` 为新版本字符串
2. 对**尚未更新内容**的页面，无需操作（会显示旧的全局默认值直到内容更新）
3. 对**已按新版本更新内容**的页面，添加对应 `map_version` front matter
4. 若所有页面内容已全部升级完毕，可删除各文件中的 front matter（统一由全局默认值覆盖）

---

## 贡献说明

- 英雄/物品页面请参考 `docs_template/` 下对应模板
- 统一使用 UTF-8 编码
- 站点导航结构在 `mkdocs.yml` 中维护
- 数值须经触发器验证，不得仅凭工具提示文字填写
