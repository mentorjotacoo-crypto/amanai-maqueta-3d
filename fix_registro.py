# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
old = json.loads(open('plan_data_pre_plr.js').read()[len('var PLAN='):-1])
m = json.load(open('plr_map.json'))
# indices por (viejo mz, viejo n)
idx_of = {}
for i,l in enumerate(old['lots']):
    if l['n']!='SN': idx_of[(l['mz'], l['n'])] = str(i)
# MZ 20 -> MZ 16: PLR k = viejo k+2 (viejos 1,2 eliminados)
for k in list(m):
    if m[k][0]=='MZ 16': del m[k]
for vn in range(3,10):
    i=idx_of[('MZ 20',vn)]
    m[i]=['MZ 16', vn-2]
# MZ 5 -> MZ 5: PLR k = viejo k+1 (viejo 1 eliminado)
for k in list(m):
    if m[k][0]=='MZ 5': del m[k]
for vn in range(2,6):
    i=idx_of[('MZ 5',vn)]
    m[i]=['MZ 5', vn-1]
json.dump(m, open('plr_map.json','w'))
print('map corregido:', len(m))
