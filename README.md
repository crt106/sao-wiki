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
   pip install -r requirements.txt
   # 或
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

- `docs/`：主文档内容
- `wiki/`：旧版 Wiki 资料
- `site/`：构建输出目录
- `scripts/`：批量处理脚本
- `versions/`：地图历史资源

## 贡献

- 英雄/物品页面请参考 `docs/heroes/_template.md` 模板
- 内容补充请注明数据来源和作者
- 统一使用 UTF-8 编码

## 维护者

- 地图作者：忘川
- Wiki维护：crt106
