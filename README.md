# 刀剑物语地图 Wiki

本项目为 War3 地图《刀剑物语2.3（忘川）》的非官方 Wiki 站点源码，基于 MkDocs + Material 主题构建，旨在为玩家和制作者提供详尽的英雄、物品、机制等资料。

## 功能特色

- 英雄图鉴、物品图鉴、专属机制、楼层信息等全方位数据
- 站点内容均基于地图实际代码（war3map.j、unit.ini、item.ini、ability.ini）解析
- 支持本地 MkDocs 预览与一键构建

## 快速开始

1. 克隆本仓库
2. 安装 Python 3.10+，推荐使用虚拟环境
3. 安装依赖：
   ```sh
   pip install mkdocs-material mkdocs-awesome-pages-plugin
   ```
4. 本地预览：
   ```sh
   mkdocs serve
   ```
5. 构建静态站点：
   ```sh
   mkdocs build
   ```

## 目录结构

```
.
├── docs/                        # Wiki 页面（MkDocs 源文件）
│   ├── heroes/                  # 英雄图鉴（每英雄一个 .md 文件）
│   ├── items/                   # 物品图鉴（按类别分子目录）
│   │   ├── 武器/
│   │   ├── 装甲/
│   │   ├── 副武器/
│   │   ├── 头部道具/
│   │   ├── 装备道具/
│   │   ├── 素材/
│   │   ├── 消耗物品/
│   │   ├── 特殊/
│   │   └── 不归类/
│   ├── changelogs/              # 版本更新日志（MkDocs Blog）
│   │   └── posts/
│   ├── info/                    # 其他站点信息（楼层信息、好玩的等）
│   └── stylesheets/             # 自定义 CSS
│
├── docs_template/               # 页面模板
│   ├── hero_template.md         # 英雄页面模板
│   ├── item_template_武器.md
│   ├── item_template_装甲.md    # …各类物品模板
│   └── …
│
├── dev/                         # 调研工作区（不发布到 Wiki）
│   ├── hero.md                  # 英雄详细数据（调研成果）
│   ├── hero_task.md             # 英雄调研任务与进度
│   ├── item_wiki.md             # 物品详细数据
│   ├── item_wiki_task.md        # 物品待补全清单
│   ├── 探索笔记.md              # 合成公式、专属武器、Boss 掉落等
│   └── tmp/                     # 临时文件（原始更新日志等）
│
├── scripts/                     # 批量处理脚本
│   ├── split_items_to_pages.py  # 将物品大表拆分为独立页面
│   ├── link_hero_items.py       # 为英雄页面注入物品链接
│   ├── diff_versions.py         # 对比两版本地图数据差异
│   ├── quality_scan.py          # 扫描 Wiki 页面质量问题
│   ├── import_to_bitable.py     # 导出数据到飞书多维表格（需配置密钥）
│   └── …
│
├── versions/                    # 地图历史版本资源（已 .gitignore）
│   ├── 刀剑物语2.3(忘川)测试版/
│   │   ├── map/war3map.j        # 主脚本（43万行）
│   │   └── table/              # unit/ability/item/buff.ini
│   └── 刀剑物语2.41测试版/      # 同上结构
│
├── mkdocs.yml                   # MkDocs 站点配置
└── site/                        # 构建产物（已 .gitignore）
```

## 贡献

- 英雄/物品页面请参考 `docs_template/` 下对应模板
- 数值须经触发器（war3map.j）验证，不得仅凭工具提示文字填写
- 统一使用 UTF-8 编码

## 维护者

- 改图作者：泠
- Wiki 维护：crt106
