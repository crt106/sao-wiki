# CLAUDE.md

## 项目环境说明

- 操作系统：Windows 11
- Python 环境建议：3.10+，推荐使用虚拟环境（.venv）
- 推荐编辑器：VS Code
- 推荐终端：PowerShell 或 CMD
- 本项目为 MkDocs + Material 主题构建的 War3 刀剑物语地图 Wiki 站点

## 主要依赖

- mkdocs-material
- mkdocs-awesome-pages-plugin

## 目录结构简述

- `docs/`：主文档目录，所有页面内容均在此维护
- `docs/heroes/`：英雄图鉴相关页面
- `docs/items/`：物品图鉴相关页面
- `docs/notes/`：补充说明、机制、日志等
- `wiki/`：旧版 Wiki 资料归档
- `site/`：MkDocs 构建后静态站点输出目录
- `scripts/`：批量处理与格式转换脚本
- `versions/`：地图历史版本资源

## 贡献说明

- 英雄/物品页面请参考 `docs/heroes/_template.md` 模板
- 统一使用 UTF-8 编码
- 站点导航结构在 `mkdocs.yml` 中维护
- 贡献内容请注明数据来源和作者

## 维护者

- 地图作者：忘川
- Wiki维护：crt106
