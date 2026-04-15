"""
物品文档质量扫描脚本
扫描四类质量问题：
E: 标题格式错误（含 # --- 污染）
B_new: 获取途径未知/待考证
F: 有技能名但无详细效果列表
G: 引用其他物品/英雄但无链接
"""

import os
import re

ITEMS_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs', 'items')

def scan_items():
    results = {'E': [], 'B_new': [], 'F': [], 'G': []}

    for root, dirs, files in os.walk(ITEMS_DIR):
        dirs.sort()
        for fname in sorted(files):
            if not fname.endswith('.md') or fname == 'index.md':
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, ITEMS_DIR).replace('\\', '/')
            category = rel.split('/')[0]

            try:
                content = open(fpath, encoding='utf-8').read()
            except Exception:
                continue

            lines = content.split('\n')

            # E类: 标题含 '# ---' 或含 'hide: true' 的注释残留
            # 通常出现在前几行，如: # ---\n# hide: true\n# ---
            for line in lines[:15]:
                stripped = line.strip()
                if stripped == '# ---' or stripped == '# hide: true' or stripped == '# hide:true':
                    results['E'].append((category, fname, rel))
                    break

            # B_new类: 获取途径写了 未知 或 待考证
            for line in lines:
                if re.search(r'\*\*获取\*\*\s*[：:]\s*(未知|待考证)', line):
                    results['B_new'].append((category, fname, rel))
                    break

            # F类: 有能力/技能行，但没有详细技能表格
            # 特征：有 "- 能力：XXX" 或 "Lv" 标记的技能名，但无效果描述表格
            skill_name_lines = []
            has_skill_detail_table = False
            for line in lines:
                # 技能名行：如 "- 能力：潘多拉之力量 Lv5（E级）"
                if re.search(r'^[-\*]\s*能力\s*[：:]', line):
                    skill_name_lines.append(line)
                # 有详细技能效果表格的标志：含技能名列+效果列的表格
                if '技能名' in line and '效果' in line and '|' in line:
                    has_skill_detail_table = True
                    break
                # 或有 **技能效果** 标题下的描述
                if re.search(r'\*\*技能效果\*\*', line) and '待查验' not in line and '待补全' not in line:
                    # Check if next lines have actual content (not just placeholder)
                    has_skill_detail_table = True

            if skill_name_lines and not has_skill_detail_table:
                # 额外确认：检查这些技能行是否只是列了名字没有效果
                results['F'].append((category, fname, rel, skill_name_lines))

            # G类: 提及其他物品名或英雄名但没有链接
            # 链接格式：[XXX](../path) 或 [XXX][ref]
            # 常见引用模式：合成需要 "龙之牙"，专属英雄 "桐人" 等
            # 检测：含【】书名号引用、含中文物品名但非链接格式
            content_no_links = re.sub(r'\[.*?\]\(.*?\)', '', content)  # 去掉已有链接
            content_no_links = re.sub(r'\[.*?\]\[.*?\]', '', content_no_links)  # 去掉参考链接

            # 查找引用模式（不含链接的）
            unlinked_refs = []
            # 模式1: 「物品名」或 『物品名』
            for m in re.finditer(r'[「『【](.*?)[」』】]', content_no_links):
                name = m.group(1)
                if len(name) >= 2 and len(name) <= 20 and not name.startswith('注'):
                    unlinked_refs.append(name)
            # 模式2: 合成/材料/专属等后跟中文名称
            for m in re.finditer(r'(?:合成[需要为：:]+|材料[：:]|专属[英雄]*[：:])\s*([\u4e00-\u9fff·《》（）\w]+)', content_no_links):
                name = m.group(1).strip()
                if len(name) >= 2:
                    unlinked_refs.append(name)

            if unlinked_refs:
                results['G'].append((category, fname, rel, list(set(unlinked_refs))[:5]))

    return results

def format_item_id(fname):
    """从文件名提取物品ID，如 I08R_云霞（传说）.md -> I08R"""
    m = re.match(r'^([A-Z][0-9A-Z]{3})[_\.]', fname)
    if m:
        return m.group(1)
    return ''

def format_item_name(fname):
    """从文件名提取物品名，如 I08R_云霞（传说）.md -> 云霞（传说）"""
    name = fname.replace('.md', '')
    parts = name.split('_', 1)
    if len(parts) == 2:
        return parts[1]
    return name

def category_zh(cat):
    mapping = {
        '武器': '二、武器',
        '副武器': '三、副武器',
        '装备道具': '四、装备道具',
        '装甲': '五、装甲',
        '头部道具': '六、头部道具',
        '不归类': '七、不归类',
        '消耗物品': '八、消耗物品',
        '特殊': '九、特殊',
        '素材': '一、素材',
    }
    return mapping.get(cat, cat)

def group_by_category(items):
    groups = {}
    for item in items:
        cat = item[0]
        groups.setdefault(cat, []).append(item)
    return groups

CAT_ORDER = ['素材', '武器', '副武器', '装备道具', '装甲', '头部道具', '不归类', '消耗物品', '特殊']

def print_group(items_list, section_prefix, with_detail=None):
    """按分类输出物品列表"""
    groups = {}
    for item in items_list:
        cat = item[0]
        groups.setdefault(cat, []).append(item)

    total = sum(len(v) for v in groups.values())
    print(f"\n### 合计：{total} 项")
    for cat in CAT_ORDER:
        if cat not in groups:
            continue
        g = groups[cat]
        print(f"\n#### {category_zh(cat)}（{len(g)}）")
        for item in g:
            cat_, fname, rel = item[:3]
            item_id = format_item_id(fname)
            item_name = format_item_name(fname)
            extra = ''
            if with_detail and len(item) > 3:
                detail = item[3]
                if isinstance(detail, list):
                    extra = ' - ' + ' / '.join(str(x) for x in detail[:3])
            print(f"- [ ] {item_id} {item_name}{extra}")


if __name__ == '__main__':
    import sys
    results = scan_items()

    # 写扫描汇总文件
    out = open('dev/quality_scan_result.txt', 'w', encoding='utf-8')
    def p(s=''):
        out.write(s + '\n')

    p(f"=== 质量扫描汇总 ===")
    p(f"E类（标题格式错误）: {len(results['E'])} 项")
    p(f"B_new类（获取未知/待考证）: {len(results['B_new'])} 项")
    p(f"F类（有技能名但无详细效果）: {len(results['F'])} 项")
    p(f"G类（引用未链接化）: {len(results['G'])} 项")

    def pg(items_list, with_detail=None):
        groups = {}
        for item in items_list:
            cat = item[0]
            groups.setdefault(cat, []).append(item)
        total = sum(len(v) for v in groups.values())
        p(f"\n合计：{total} 项")
        for cat in CAT_ORDER:
            if cat not in groups:
                continue
            g = groups[cat]
            p(f"\n#### {category_zh(cat)}（{len(g)}）")
            for item in g:
                cat_, fname, rel = item[:3]
                item_id = format_item_id(fname)
                item_name = format_item_name(fname)
                extra = ''
                if with_detail and len(item) > 3:
                    detail = item[3]
                    if isinstance(detail, list):
                        extra = ' - ' + ' / '.join(str(x)[:20] for x in detail[:3])
                p(f"- [ ] {item_id} {item_name}{extra}")

    p("\n\n=== E类：标题格式错误 ===")
    pg(results['E'])
    p("\n\n=== B_new类：获取未知/待考证 ===")
    pg(results['B_new'])
    p("\n\n=== F类：有技能但无详细效果 ===")
    pg(results['F'], with_detail=True)
    p("\n\n=== G类：引用未链接化 ===")
    pg(results['G'], with_detail=True)
    out.close()

    # 生成 task 区段 markdown（用于更新 item_wiki_task.md）
    def gen_section(title, items_list, with_refs=False):
        lines_out = [f"\n## {title}\n"]
        groups = {}
        for item in items_list:
            cat = item[0]
            groups.setdefault(cat, []).append(item)
        for cat in CAT_ORDER:
            if cat not in groups:
                continue
            g = groups[cat]
            lines_out.append(f"### {category_zh(cat)}（{len(g)}）")
            for item in g:
                cat_, fname, rel = item[:3]
                item_id = format_item_id(fname)
                item_name = format_item_name(fname)
                extra = ''
                if with_refs and len(item) > 3:
                    detail = item[3]
                    if isinstance(detail, list):
                        extra = ' - 引用: ' + ' / '.join(str(x)[:20] for x in detail[:3])
                lines_out.append(f"- [ ] {item_id} {item_name}{extra}")
            lines_out.append('')
        return '\n'.join(lines_out)

    with open('dev/quality_task_sections.md', 'w', encoding='utf-8') as f:
        f.write(gen_section('B_current. 获取未知/待考证（当前扫描：95项）', results['B_new']))
        f.write(gen_section('E. 标题格式错误（# --- 污染，共180项）', results['E']))
        f.write(gen_section('F. 有技能但无详细效果描述（共129项）', results['F']))
        f.write(gen_section('G. 引用未链接化（共34项）', results['G'], with_refs=True))

    print(f"Done. E={len(results['E'])} B={len(results['B_new'])} F={len(results['F'])} G={len(results['G'])}")
