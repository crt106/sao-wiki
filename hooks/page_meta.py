"""
MkDocs hook: 自动注入页面元信息

- git_date: 该页文件的最后 git 提交日期（YYYY-MM-DD），若无 git 历史则为构建日期
- map_version: 来自 mkdocs.yml extra.map_version 的地图版本字符串
"""
import subprocess
import os
from datetime import date, timezone


def _git_date(src_path: str) -> str:
    """返回文件最后一次 git 提交的 ISO 日期，失败则返回今天。"""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci", "--", src_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        output = result.stdout.strip()
        if output:
            # 格式如 "2026-04-26 15:30:00 +0800"，取前10字符
            return output[:10]
    except Exception:
        pass
    return date.today().isoformat()


def on_page_context(context, page, config, **kwargs):
    """在每个页面渲染前注入 git_date 和 map_version 到模板 context。"""
    src_path = page.file.abs_src_path
    context["git_date"] = _git_date(src_path) if src_path and os.path.exists(src_path) else date.today().isoformat()
    context["map_version"] = config.get("extra", {}).get("map_version", "")
    return context
