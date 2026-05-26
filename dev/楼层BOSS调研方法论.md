# 楼层 Boss 调研方法论

> 本文档总结如何通过分析 war3map.j 定位楼层 Boss 单位 ID，以及如何进一步分析 Boss 技能。
> 适用版本：刀剑物语 2.41 测试版

---

## 一、核心原理

### 1.1 传送道具与 Boss 死亡判断

游戏内的「传送迷宫X层」道具使用逻辑：

```jass
if ( GetItemTypeId(GetManipulatedItem()) == '物品ID' ) then
    if ( IsUnitAliveBJ(gg_unit_XXX_YYYY) == true ) then
        call DisplayTimedTextToForce(..., "|cffff0000系统:请先挑战前一关卡的BOSS|r")
    else
        // 执行传送逻辑
    endif
endif
```

**关键规律**：
- 传送道具的物品 ID（如 `I018`）→ 判断其目标层是否可以进入
- `IsUnitAliveBJ(gg_unit_XXX_YYYY)` 中的单位实例 → **上一层的守门 Boss**
- 如果 Boss 存活，则禁止传送；只有击杀 Boss 后才能使用该传送道具

### 1.2 dj_boss 注册表（更可靠的定位方式）

war3map.j 中存在一个 `BossUnitInitChoose` 函数（约 365100 行），以 `dj_boss` 为 key 将每层的 Boss 实例注册到 `BossTable` 哈希表中：

```jass
// 本层 Boss（key=0）
call SaveUnitHandle(BossTable, StringHash("dj_boss" + I2S(itemType)), 0, gg_unit_n03R_0066)

// 守门 Boss / 上一层 Boss（key=100）
call SaveUnitHandle(BossTable, StringHash("dj_boss" + I2S(itemType)), 100, gg_unit_nwiz_0643)

// 多体 Boss 的额外单位（key=1, 2, ...）
call SaveUnitHandle(BossTable, StringHash("dj_boss" + I2S('I0EB')), 1, gg_unit_n012_0067) // 魔人
call SaveUnitHandle(BossTable, StringHash("dj_boss" + I2S('I0EB')), 2, gg_unit_n014_0068) // 死亡
```

**key 含义**：

| key | 含义 | 说明 |
|-----|------|------|
| 0 | 本层 Boss | 该层需要击杀的目标 |
| 1, 2, ... | 多体 Boss 的额外单位 | 如 54 层魔人+死亡执行者 |
| 100 | 守门 Boss（上一层） | 击杀后才可进入本层 |

**优势**：比传送道具触发器更完整——部分层（如 57-60 层）没有独立的 chuansong 触发器函数，但 dj_boss 注册表一定存在。

---

## 二、搜索定位方法

### 2.1 方法一：传送道具触发器

**适用**：1-56 层（大部分层有独立的 chuansong 函数）

```bash
# 搜索传送触发器
grep -n "chuansong" war3map.j

# 搜索物品 ID 判断（以 I018 为例）
grep -n "'I018'" war3map.j
```

**关键触发器区域**：

| 触发器函数 | 行号区间 | 说明 |
|-----------|----------|------|
| `Trig_chuansong4Actions` | ~378760 | 1-10层传送 + 51-54层传送 |
| `Trig_chuansong11_______________uActions` | ~378920 | 11-20层传送（部分） |
| `Trig_chuansong16_____________________uActions` | ~379130 | 21-30层传送 |
| `Trig_chuansong31Actions` | ~379290 | 31-40层传送 |
| `Trig_chuansong40Actions` | ~379405 | 41-50层传送 |
| `Trig_chuansong46Actions` | ~379496 | 46-50层传送 |
| `Trig_chuansong54Actions` | ~379567 | 54层（地底） |
| `Trig_chuansong55Actions` | ~379584 | 55层（琼玉宫殿） |
| `Trig_chuansong55_______uActions` | ~379599 | 56层（废墟之城/冰冻死原） |
| `Trig_chuansong55_______________2Actions` | ~379635 | 57层（遗迹之森） |

**局限**：57-60 层没有独立的 chuansong 触发器，传送逻辑可能通过 `Unit_GD` 系统或其他方式实现。

### 2.2 方法二：dj_boss 注册表（推荐，全层通用）

**适用**：所有层（1-71+）

```bash
# 搜索 BossUnitInitChoose 函数
grep -n "BossUnitInitChoose" war3map.j

# 搜索特定层的 dj_boss 注册
grep -n "dj_boss.*I0EA" war3map.j
```

**读取方式**：从 `BossUnitInitChoose` 函数入口（约 365102 行）开始，每次 Read 150 行。

**注册表结构**（以 51-60 层为例）：

```
itemType='I0EC' (52层) → key=0: nwiz(腾蛇), key=100: n02Z(黑死病之源)
itemType='I0E9' (53层) → key=0: n03R(暗杀者), key=100: nwiz(腾蛇)
itemType='I0EB' (54层) → key=1: n012(魔人), key=2: n014(死亡), key=100: n03R(暗杀者)
itemType='I0CT' (55层) → key=0: n03Q(女帝), key=100: 54层Boss
itemType='I09Z' (56层) → key=100: n03Q(女帝)
itemType='I0GM' (57层) → key=100: e068(虫群)
itemType='I0GN' (58层) → key=100: n04Q(元素人)
itemType='I0GO' (59层) → key=100: n04R(史莱姆高级)
itemType='I0GP' (60层) → key=100: n04S(怪异法师)
```

### 2.3 方法三：item.ini 传送道具描述

**适用**：快速获取楼层场景名和掉落信息

```bash
# 搜索传送道具
grep -B5 "传送迷宫51层" table/item.ini
```

每个传送道具的 `Description` 字段包含场景名、掉落物品和难度评级：

```
Description = "迷宫51层(黑死病之森)|n|n|cff7fffd4掉落物品:剧毒牙齿(5%),致病根源(10%)|r|n|n|n|cffff0000特殊物品:边界魔石,剧毒呼吸|r|n|n|cff00ff7f难度:★★★★☆|r"
```

### 2.4 推荐的定位流程

```
1. item.ini → 获取传送物品ID + 场景名 + 掉落描述
2. BossUnitInitChoose → 获取 Boss 实例映射（key=0本层, key=100守门, key=1+多体）
3. chuansong 触发器 → 交叉验证守门 Boss（仅 1-56 层可用）
```

---

## 三、楼层 Boss 映射表（2.41 测试版）

### 3.1 初环起步（1-10 层）

| 目标层 | 传送物品ID | 守门 Boss 实例 | Boss 名称 |
|--------|------------|----------------|-----------|
| 2层 | I018 | `gg_unit_nanw_0140` | 狼人领主 |
| 3层 | I019 | `gg_unit_nscb_0567` | 森林之主 |
| 4层 | I01A | `gg_unit_nbrg_0558` | 蜘蛛领主 |
| 5层 | I02B | `gg_unit_nass_0427` | 早期三头蛇 |
| 6层 | I02A | `gg_unit_nenf_0560` | 狡猾食人鱼 |
| 7层 | I00V | `gg_unit_nbdm_0562` | 占领者 |
| 8层 | I02C | `gg_unit_nrog_0559` | 主棺者 |
| 9层 | I02E | `gg_unit_ncea_0565` | 棺林守护者 |
| 10层 | I01Q | `gg_unit_ncim_0566` | 夺魂者（?）|

### 3.2 骷髅环（11-20 层）

| 目标层 | 传送物品ID | 守门 Boss 实例 | Boss 名称 |
|--------|------------|----------------|-----------|
| 12层 | I029 | `gg_unit_ndrh_0576` | 残忍野兽 |
| 13层 | I02D | `gg_unit_ndrm_0575` | 森林守护者 |
| 14层 | I02F | `gg_unit_nfor_0580` | 骷髅司令和 |
| 15层 | I01S | `gg_unit_nenc_0577` | 骷髅将军 |
| 16层 | I05S | `gg_unit_nepl_0579` | 骷髅皇帝 |
| 17层 | I02F | `gg_unit_nfor_0580` | 夺魂者（?）|
| 18层 | I066 | `gg_unit_nfod_0578` | 巨龟 |
| 19层 | I01B | `gg_unit_nfod_0578` | 同上 |

### 3.3 兽境环（21-30 层）

| 目标层 | 传送物品ID | 守门 Boss 实例 | Boss 名称 |
|--------|------------|----------------|-----------|
| 22层 | I065 | `gg_unit_npfm_0582` | 食人魔 |
| 23层 | I067 | `gg_unit_nftb_0583` | 鹰身女妖 |
| 24层 | I06V | `gg_unit_nftb_0583` | 同上 |
| 25层 | I06W | `gg_unit_nftb_0583` | 同上 |
| 26层 | I06X | `gg_unit_nfre_0592` | 石巨人 |
| 27层 | I06Y | `gg_unit_nsgh_0598` | 强力树人 |
| 28层 | I06Z | `gg_unit_nggr_0600` | 天空龙 |
| 29层 | I071 | `gg_unit_njgb_0561` | 狂暴雪走兽 |
| 30层 | I072 | `gg_unit_njgb_0561` | 同上 |

### 3.4 极寒环（31-40 层）

| 目标层 | 传送物品ID | 守门 Boss 实例 | Boss 名称 |
|--------|------------|----------------|-----------|
| 31层 | I09J | `gg_unit_ngna_0595` | 点灯使者 |
| 32层 | I085 | `gg_unit_nmgd_0616` | 鱼龙兽 |
| 33层 | I0AA | `gg_unit_nmgw_0608` | 同上 |
| 34层 | I0AB | `gg_unit_nmgw_0608` | 同上 |
| 35层 | I0AC | `gg_unit_nenp_0642` | 前奏曲·狼神 |
| 36层 | I0B6 | `gg_unit_nmam_0618` | 雪地双头巨魔领主 |
| 37层 | - | - | 同上（合并层） |
| 38层 | I0BT | `gg_unit_nmpg_0622` | Pearl's Monster |
| 39层 | - | - | 同上（合并层） |
| 40层 | I0CL | `gg_unit_nfrs_0557` | 阿修罗 |

### 3.5 灼热环（41-50 层）

| 目标层 | 传送物品ID | 守门 Boss 实例 | Boss 名称 |
|--------|------------|----------------|-----------|
| 41层 | I0BV | `gg_unit_ntka_0640` | 火焰狗领主 |
| 42层 | I0CM | `gg_unit_nfrs_0557` | 干旱中暴食者 |
| 43层 | I0CU | `gg_unit_nubk_0615` | 火焰烧烧魔 |
| 44层 | I0CO | `gg_unit_nfrg_0614` | 冰晶之地领主 |
| 45层 | I0CQ | `gg_unit_ntkw_0633` | 间奏·龙神 |
| 46层 | I0CR | `gg_unit_n024_0613` | 暗星 |
| 47层 | - | - | 同上（合并层） |
| 48层 | - | - | 同上（合并层） |
| 49层 | I0DB | `gg_unit_nlkl_0646` | Disaster |
| 50层 | I0CN | `gg_unit_nvdw_0563` | 传说·圣者 |

### 3.6 血盟副本（51-60 层）

| 目标层 | 传送物品ID | 本层 Boss 实例(key=0) | 守门 Boss(key=100) | Boss 名称 |
|--------|------------|----------------------|-------------------|-----------|
| 51层 | I0EA | (无key=0) | `gg_unit_n030_0018` | 黑死病之源 |
| 52层 | I0EC | `gg_unit_nwiz_0643` | `gg_unit_n02Z_0025` | Fenice(腾蛇) |
| 53层 | I0E9 | `gg_unit_n03R_0066` | `gg_unit_nwiz_0643` | 暗杀者 |
| 54层 | I0EB | key=1:`n012_0067` + key=2:`n014_0068` | `gg_unit_n03R_0066` | 悲哀魔人+死亡执行者 |
| 55层 | I0CT | `gg_unit_n03Q_0124` | 54层Boss | 后奏曲·女帝 |
| 56层 | I09Z | (无key=0) | `gg_unit_n03Q_0124` | 过渡层(废墟之城) |
| 57层 | I0GM | (无key=0) | `gg_unit_e068_0146` | 虫群 |
| 58层 | I0GN | (无key=0) | `gg_unit_n04Q_0444` | 元素人 |
| 59层 | I0GO | (无key=0) | `gg_unit_n04R_0452` | 史莱姆高级 |
| 60层 | I0GP | (无key=0) | `gg_unit_n04S_0458` | 怪异法师 |
| 60深处 | - | `gg_unit_n04T_0490` | - | 八重樱 |

> **注意**：51 层和 56-60 层的 dj_boss 注册中 key=0 为空，说明这些层的 Boss 实例通过其他方式注册（如 `Unit_GD` 系统），需要通过 `gg_unit_e05S_XXXX` 等马甲单位间接关联。

### 3.7 魔王塔（61-70 层）

| 目标层 | 传送物品ID | 守门 Boss(key=100) | Boss 名称 |
|--------|------------|-------------------|-----------|
| 61层 | I0HS | `gg_unit_n04T_0490` | 八重樱(守门) |
| 62层 | I0OW | `gg_unit_u02V_0518` | 吸血斧王 |
| 63层 | I0OX | `gg_unit_u02W_0527` | - |
| 64层 | I0OY | `gg_unit_u02X_0522` | 双头龙 |
| 65层 | I0OZ | `gg_unit_n053_0526` | 终幕-樱满集 |
| 66层 | I0ID | `gg_unit_n054_0539` | - |
| 67层 | I0IE | `gg_unit_u02Y_0541` | - |
| 68层 | I0IG | `gg_unit_n056_0528` | - |
| 69层 | I0II | `gg_unit_n057_0305` | - |
| 70层 | I0IH | `gg_unit_n058_0542` | 血色魔女 |

### 3.8 深渊（71 层）

| 目标层 | 传送物品ID | 守门 Boss(key=100) | Boss 名称 |
|--------|------------|-------------------|-----------|
| 71层 | I0Q6 | `gg_unit_n059_0303` | 深渊魔女 |

### 3.9 特殊/隐藏层

| 目标层 | 传送物品ID | 守门 Boss 实例 | Boss 名称 |
|--------|------------|----------------|-----------|
| 虚假的天空 | I070 | `gg_unit_ngnv_0599` | 隐藏 Boss |
| 三皇之地 | 区域触发 | `gg_unit_O003_0573` | 三皇（桐人） |
| 冰冻死原 | I09Z | `gg_unit_nlkl_0646` | Disaster(守门) |

---

## 四、Boss 技能分析方法

### 4.1 获取 Boss 类型 ID

从 `gg_unit_XXX_YYYY` 实例名中提取类型 ID（4字符）：

```
gg_unit_nanw_0140
       ^^^^ = nanw（单位类型ID）
```

### 4.2 在 unit.ini 中查找 Boss 基本信息

```bash
grep -A50 "^\[nanw\]" table/unit.ini
```

关键字段：

| 字段 | 含义 | 注意事项 |
|------|------|---------|
| `Name` | Boss 显示名称 | 可能含颜色代码 `\|cffXXXX` |
| `HP` | 生命值 | 直接数值 |
| `def` | 基础护甲 | 注意 `defType` 护甲类型 |
| `defType` | 护甲类型 | `fort`=城甲, `large`=大型甲, `hero`=英雄甲 |
| `dmgplus1` | 基础伤害 | 注意 `atkType1` 攻击类型 |
| `atkType1` | 攻击类型 | `chaos`=混乱, `siege`=攻城, `hero`=英雄 |
| `cool1` | 攻击间隔(秒) | 越小越快 |
| `rangeN1` | 攻击距离 | 近战通常 100-150 |
| `spd` | 移动速度 | 522 = 游戏上限 |
| `abilList` | 技能列表 | 逗号分隔的技能 ID |
| `acquire` | 主动攻击范围 | 超过此距离不会主动攻击 |
| `regenHP` | 生命回复/秒 | 高回复 Boss 需要持续输出 |
| `regenType` | 回复类型 | `always` = 战斗中也回复 |

**攻防类型速查**：

| 攻击类型 | 对城甲 | 对大型甲 | 对英雄甲 | 说明 |
|---------|--------|---------|---------|------|
| chaos(混乱) | 100% | 100% | 100% | 无视护甲类型 |
| siege(攻城) | 150% | 50% | 100% | 对城甲加伤 |
| hero(英雄) | 50% | 100% | 100% | 对城甲减伤 |
| normal(普通) | 70% | 100% | 100% | - |

### 4.3 在 ability.ini 中查找技能详情

```bash
grep -A20 "^\[A001\]" table/ability.ini
```

关键字段：
- `Name` = 技能名称
- `Cool` = 冷却时间
- `Cost` = 魔法消耗
- `DataA` ~ `DataF` = 各等级数值
- `Ubertip` = 工具提示（**注意：描述可能与实际不符**）

### 4.4 在 war3map.j 中找触发器逻辑

**方法 A：通过 Boss 类型 ID 搜索技能触发**

```bash
# 搜索 Boss 类型 ID 的技能分支
grep -n "GetUnitTypeId(un) == 'n02Z'" war3map.j
```

这是最可靠的方式——每个 Boss 的技能触发器都以 `GetUnitTypeId` 判断为入口。

**方法 B：通过技能 ID 搜索施法事件**

```bash
grep -n "GetSpellAbilityId() == 'A150'" war3map.j
```

**方法 C：通过 Boss 实例搜索攻击/半血触发**

```bash
# 搜索 Boss 实例的攻击触发
grep -n "GetAttacker() == gg_unit_n02Z_0025" war3map.j

# 搜索半血狂暴
grep -n "gg_unit_n02Z_0025.*0.5" war3map.j
```

**方法 D：通过喊话文字搜索**

```bash
grep -n "BOSS/黑死病" war3map.j
```

**方法 E：通过死亡事件搜索掉落**

```bash
# 搜索 Boss 类型 ID 的死亡掉落
grep -n "GetUnitTypeId(boss) == 'n02Z'" war3map.j
```

### 4.5 常见 Boss 机制模式

在 war3map.j 中，Boss 机制通常分布在以下几个位置：

| 机制类型 | 典型代码位置 | 搜索关键词 |
|---------|-------------|-----------|
| 受击触发 | `Trig____________________057Actions` | `GetAttacker() == gg_unit_` |
| 半血狂暴 | 受击事件中 | `UNIT_STATE_MAX_LIFE * 0.5` |
| 技能释放 | `Trig_game_3Actions` | `GetUnitTypeId(un) == 'nXXX'` |
| 被动惩罚 | 施法事件中 | `GetUnitAbilityLevel(un, 'AXXX')` |
| 死亡掉落 | `Trig_boss_kill` | `GetUnitTypeId(boss) == 'nXXX'` |
| 复活机制 | `unitFhBoss` | `GetUnitTypeId(un) == 'nXXX'` |
| 减伤被动 | `BossUnitInitChoose` | `减伤js` |

**特殊机制识别**：

- **盾/回血机制**：搜索 `SaveBoolean(BossTable, ..., StringHash("XXX的盾"), true)` + 受击事件中 `LoadBoolean` 判断
- **吞噬/消失机制**：搜索 `ShowUnit(mb, false)` + 定时器持续扣血
- **多体 Boss 互相复活**：搜索 `unitFhBoss` + `CreateUnit` 重新创建同伴
- **蓄力突袭**：搜索 `YDWETimerPatternRushSlide` + `chuxu` 计数器

---

## 五、实战案例：分析「黑死病之源」

### 5.1 定位 Boss 实例

从 dj_boss 注册表找到：
- 52 层 `I0EC` → key=100: `gg_unit_n02Z_0025` = 黑死病之源（51 层 Boss）

### 5.2 提取类型 ID

```
gg_unit_n02Z_0025 → n02Z（类型ID）
```

### 5.3 查询基本信息

```bash
grep -A50 "^\[n02Z\]" table/unit.ini
# HP=3000000, def=0, defType=fort, dmgplus1=5000, rangeN1=1000, abilList=A150,A14Z,A0QA,A154
```

### 5.4 搜索技能触发器

```bash
# 方法 A：按类型 ID 搜索
grep -n "GetUnitTypeId(un) == 'n02Z'" war3map.j
# → 找到技能释放分支（行 421972）

# 方法 B：按实例搜索受击/半血
grep -n "gg_unit_n02Z_0025" war3map.j
# → 找到盾机制（行 368838）和半血践踏（行 382343）
```

### 5.5 解读技能逻辑

从代码中提取：
- A150 → `heisibingQ`（瘟疫投放，二选一）
- A14Z → 盾/瘟疫爆发（二选一）
- 半血 → `stomp`（践踏，20秒CD）
- 盾机制 → 受击时伤害双倍回血（行 368838-368840）

---

## 六、注意事项

1. **war3map.j 严禁整文件读取**：43万行/15MB，始终先 grep 定位行号，每次 Read ≤ 150 行
2. **Ubertip ≠ 实际数值**：技能描述是策划手写，触发器才是真值
3. **合并层**：一只 Boss 镇守多层（如 36+37 层 = 雪地双头巨魔领主）
4. **隐藏层**：部分层有独立的隐藏 Boss（如虚假的天空、三皇之地）
5. **中文 grep 可能失败**：编码问题导致中文搜索无结果时，改用 4 字符 ID
6. **dj_boss key=0 可能为空**：51 层和 56-60 层的 Boss 实例通过 `Unit_GD` 系统注册，不在 key=0 中
7. **多体 Boss**：54 层魔人+死亡执行者使用 key=1, key=2 注册额外单位，需全部击杀
8. **减伤被动**：部分 Boss 在 `BossUnitInitChoose` 中注册了 `减伤js`（如暗杀者 0.18 = 18% 减伤）
9. **传送道具名 ≠ 场景名**：部分传送道具的 `Name` 字段是场景名（如「废墟之城」），`Tip` 才是「传送迷宫XX层」

---

## 七、快速参考

```bash
# 1. 搜索传送物品 → 场景名 + 掉落
grep -B5 "传送迷宫51层" table/item.ini

# 2. 搜索 dj_boss 注册表（全层通用）
grep -n "BossUnitInitChoose" war3map.j
# 然后从该行号附近 Read 150行

# 3. 搜索 Boss 实例的所有引用
grep -n "gg_unit_nXXX_YYYY" war3map.j

# 4. 搜索 Boss 技能触发器（最可靠）
grep -n "GetUnitTypeId(un) == 'nXXX'" war3map.j

# 5. 搜索 Boss 喊话
grep -n "BOSS/黑死病" war3map.j

# 6. 搜索 Boss 受击/半血触发
grep -n "GetAttacker() == gg_unit_nXXX" war3map.j

# 7. 搜索 Boss 死亡掉落
grep -n "GetUnitTypeId(boss) == 'nXXX'" war3map.j

# 8. 搜索减伤被动
grep -n "减伤js" war3map.j

# 9. 搜索特殊机制
grep -n "ShowUnit(mb, false)" war3map.j    # 吞噬
grep -n "YDWETimerPatternRushSlide" war3map.j  # 突袭
grep -n "unitFhBoss" war3map.j              # 复活
```

---

*最后更新：2026-05-19（v2 - 新增 dj_boss 注册表方法、51-70 层映射、机制模式识别）*
