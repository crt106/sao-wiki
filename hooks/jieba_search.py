"""
MkDocs hook: 优化中文搜索

1. on_page_content: 用 jieba 对 HTML 文本节点做中文分词，
   在词间插入零宽空格 \u200b，配合 separator 让索引按词粒度切分。

2. on_post_build: 修改搜索 worker JS：
   (a) 修复 Material 内置 Han 分段函数 fe() 的 off-by-one bug
       (内层循环 `o<t.length` 漏掉了以最后一个字符结尾的子串，
        导致 "体力恢复" 只能识别出 "体力"，搜不到 "恢复")；
   (b) 将中文多词查询从 OR 改为 AND，使搜索 "体力恢复"
       只返回同时包含 "体力" 和 "恢复" 的页面。
"""
import re
import os
import glob
import jieba

# 匹配连续中文字符（2个以上才值得分词）
CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]{2,}')
# 匹配 HTML 标签（用于分割文本节点）
TAG_RE = re.compile(r'(<[^>]+>)')


def _segment(match: re.Match) -> str:
    """对匹配到的连续中文串用 jieba 分词，词间插入 \u200b"""
    text = match.group(0)
    words = jieba.lcut(text)
    return '\u200b'.join(words)


def on_page_content(html: str, **kwargs) -> str:
    """在渲染后的 HTML 中，只对文本节点做中文分词，保留标签属性不变"""
    parts = TAG_RE.split(html)
    for i, part in enumerate(parts):
        if not part.startswith('<'):  # 文本节点
            parts[i] = CJK_RE.sub(_segment, part)
    return ''.join(parts)


def on_post_build(config, **kwargs) -> None:
    """修改搜索 worker JS：修复 fe() off-by-one + OR→AND"""
    site_dir = config['site_dir']
    worker_pattern = os.path.join(site_dir, 'assets', 'javascripts', 'workers', 'search.*.min.js')
    for worker_path in glob.glob(worker_pattern):
        with open(worker_path, 'r', encoding='utf-8') as f:
            js = f.read()
        patched = js

        # (a) 修复 fe() 内层循环 off-by-one：
        #   原:  for(let o=s+1;o<t.length;o++)t.slice(s,o)in e
        #   改为:for(let o=s+1;o<=t.length;o++)t.slice(s,o)in e
        # 该函数负责把查询字符串按倒排索引里存在的词切分，
        # 原始 `<` 会漏掉以最后一个字符结尾的子串，
        # 例如 "体力恢复" 切出来只有 ["体力"]，"恢复" 永远找不到。
        patched = patched.replace(
            'for(let o=s+1;o<t.length;o++)t.slice(s,o)in e',
            'for(let o=s+1;o<=t.length;o++)t.slice(s,o)in e',
        )

        # (b) 将每个切出来的词前加 '+'，实现 AND：
        #   原:  ...fe(s,this.index.invertedIndex)].join("* ")
        #   改为:...fe(s,this.index.invertedIndex)].map(w=>"+"+w).join("* ")
        # 效果: "体力* 恢复*" → "+体力* +恢复" (两项都必须命中)
        patched = patched.replace(
            '].join("* ")',
            '].map(w=>"+"+w).join("* ")',
        )

        if patched != js:
            with open(worker_path, 'w', encoding='utf-8') as f:
                f.write(patched)

