"""验证 item_cx_add 更新是否真实写入文件"""
import os, re

BASE = r"D:\Program Files\maps\刀剑物语wiki建设\docs\items"
PLACEHOLDERS = {"待考证", "待查验", "暂不明确", "待补全", "待确认", "效果未知", "暂时未知"}

# 已知被更新的物品ID列表
UPDATED_IDS = [
    "I0PK","I0PJ","I0PP","I0OK","I0M7","I0F4","I0OL","I0LP","I0O7","I0LW",
    "I0O5","I0HL","I0LM","I069","I0LH","I0GW","I0LN","I0O9","I0J7","I0OP",
    "I0FF","I0FG","I0EM","I0HG","I0FD","I0I5","I0LD","I0GV","I0LY","I0F6",
    "I0F5","I0L5","I0GI","I0F8","I0NX","I0NU","I0NS","I0I4","I0NT","I0Q5",
    "I0Q4","I0NF","I0LF","I0EZ","I0NZ","I0ON","I0EO","I0N9","I0LX","I0EP",
    "I0PU","I0PX","I0P5"
]

confirmed = []
not_found = []
has_placeholder = []

for root, dirs, files in os.walk(BASE):
    for fname in files:
        if not fname.endswith(".md"):
            continue
        for uid in UPDATED_IDS:
            if fname.startswith(uid + "_"):
                fpath = os.path.join(root, fname)
                with open(fpath, encoding="utf-8") as f:
                    content = f.read()
                # 检查是否有技能表格且无占位符
                if "**技能效果**" in content:
                    lines = content.splitlines()
                    in_table = False
                    skill_lines = []
                    for line in lines:
                        if "**技能效果**" in line:
                            in_table = True
                        elif in_table and line.startswith("|") and "技能名" not in line and "---" not in line:
                            skill_lines.append(line)
                        elif in_table and line.strip() and not line.startswith("|"):
                            break
                    
                    has_ph = any(ph in sl for sl in skill_lines for ph in PLACEHOLDERS)
                    if has_ph:
                        has_placeholder.append((uid, fname, skill_lines[:1]))
                    else:
                        confirmed.append((uid, fname, skill_lines[:1]))
                break
        else:
            continue

print(f"=== 已验证真实更新（无占位符）: {len(confirmed)} 个 ===")
for uid, fname, sample in confirmed[:10]:
    print(f"  {uid} | {fname[:40]} | 示例: {sample[0][:60] if sample else '无'}")
if len(confirmed) > 10:
    print(f"  ... 还有 {len(confirmed)-10} 个")

if has_placeholder:
    print(f"\n=== 仍含占位符: {len(has_placeholder)} 个 ===")
    for uid, fname, sample in has_placeholder:
        print(f"  {uid} | {fname[:40]}")
