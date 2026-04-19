import re
path = r'd:\Program Files\maps\刀剑物语wiki建设\versions\刀剑物语2.41测试版\map\war3map.j'
with open(path, encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# O01Y skill handling
print('=== O01Y GetUnitTypeId checks ===')
for i, line in enumerate(lines):
    if 'O01Y' in line and 'GetUnitTypeId' in line:
        print(f'L{i+1}: {line.rstrip()[:200]}')

# Search for O01Y/O01Z skill ability IDs
skill_ids = ["'A1LN'", "'A1LO'", "'A1LP'", "'A1LQ'"]
print('\n=== A1LN/A1LO/A1LP/A1LQ (雷电芽衣技能ID) ===')
for i, line in enumerate(lines):
    if any(x in line for x in skill_ids):
        print(f'L{i+1}: {line.rstrip()[:200]}')

# 雷电芽衣的函数前缀
print('\n=== ldyy/hero_ld/huangquan functions ===')
func_starts = {}
for i, line in enumerate(lines):
    m = re.match(r'^function (\w+) takes', line)
    if m:
        func_starts[m.group(1)] = i
for fname in sorted(func_starts.keys()):
    fl = fname.lower()
    if 'ldyy' in fl or 'hero_ld' in fl or 'huangquan' in fl or 'hero_hq' in fl:
        print(f'  {fname} at L{func_starts[fname]+1}')

# thunder_fury functions (可能是雷电芽衣的)
print('\n=== thunder_fury functions ===')
for fname in sorted(func_starts.keys()):
    if 'thunder_fury' in fname:
        print(f'  {fname} at L{func_starts[fname]+1}')

# nh_ functions (用于H08A)
print('\n=== nh_ prefix functions (前20个) ===')
count = 0
for fname in sorted(func_starts.keys()):
    if fname.startswith('nh_'):
        print(f'  {fname} at L{func_starts[fname]+1}')
        count += 1
        if count >= 20:
            break
