# -*- coding: utf-8 -*-
import pickle, math, sys, collections, json
import numpy as np
from shapely.geometry import Point, LineString
from shapely.ops import unary_union, nearest_points
from shapely import minimum_rotated_rectangle
from shapely.strtree import STRtree
from scipy.spatial import cKDTree
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

faces = pickle.load(open('plr_faces4.pkl', 'rb'))
W = pickle.load(open('plr_words.pkl', 'rb')); nums = W['nums']; other = W['other']
ago = json.load(open('file_ago.json')); agoL = json.load(open('file_ago_letters.json'))
cur = json.loads(open('plan_data_pre_plr.js').read()[len('var PLAN='):-1])
rep = json.loads(open(r'C:/Users/Juan Camilo/amanai-maqueta-3d/plan_data.js').read()[len('var PLAN='):-1])
EMAP = {}
for l in rep['lots']:
    if l['n'] != 'SN' and l.get('e'):
        EMAP[(l['mz'], l['n'])] = l['e']
EMAP[('MZ 6', 1)] = 'T2'
print('esquineros heredados:', len(EMAP))

mz_words = [(x, y) for t, x, y in other if t == 'MZ']
used = set(); mz_labels = []
for mx, my in mz_words:
    best = None; bd = 1e9
    for i, (v, x, y) in enumerate(nums):
        if i in used: continue
        dx = x - mx; dy = abs(y - my)
        if 0 < dx < 22 and dy < 5 and dx + dy < bd:
            bd, best = dx + dy, i
    if best is not None:
        used.add(best); v, x, y = nums[best]
        mz_labels.append(('MZ %d' % v, (mx + x) / 2, (my + y) / 2))
Vp = np.array([(x, y) for t, x, y in other if t == 'V']); tv = cKDTree(Vp)
lot_nums = [(v, x, y) for i, (v, x, y) in enumerate(nums) if i not in used and tv.query([x, y])[0] >= 7]
P = np.array([(x, y) for v, x, y in lot_nums])

faces53 = pickle.load(open('plr_faces.pkl', 'rb'))
mz6 = [l for l in mz_labels if l[0] == 'MZ 6'][0]
face6 = next(f for f in faces53 if f.area > 300 and f.contains(Point(mz6[1], mz6[2])))
in6 = set(k for k in range(len(P)) if face6.contains(Point(P[k])))
tp = cKDTree(P); par = list(range(len(P)))
def find(a):
    while par[a] != a:
        par[a] = par[par[a]]; a = par[a]
    return a
for i, j in tp.query_pairs(13.0):
    if (i in in6) != (j in in6): continue
    ri, rj = find(i), find(j)
    if ri != rj: par[ri] = rj
clusters = collections.defaultdict(list)
for k in range(len(P)):
    if k not in in6:
        clusters[find(k)].append(k)
Lpos = [(nm, x, y) for nm, x, y in mz_labels if nm != 'MZ 6']
num_mz = {k: 'MZ 6' for k in in6}; resto = []
for cid, members in clusters.items():
    dmin = 1e9; best = None
    for nm, lx, ly in Lpos:
        dd = min(np.hypot(P[m][0] - lx, P[m][1] - ly) for m in members)
        if dd < dmin: dmin, best = dd, nm
    if dmin < 28:
        for m in members: num_mz[m] = best
    else:
        resto.extend(members)
asg = [k for k in num_mz]; ta = cKDTree(P[asg])
for m in resto:
    dd, ii = ta.query(P[m]); num_mz[m] = num_mz[asg[ii]]
got = collections.defaultdict(list)
for k, nm in num_mz.items():
    got[int(nm.split()[1])].append(lot_nums[k][0])
ok = True
for mz in range(1, 17):
    want = sorted(int(k.split('|')[1]) for k in ago if int(k.split('|')[0]) == mz)
    have = sorted(got.get(mz, []))
    if want != have:
        ok = False; print('DIF MZ', mz, have[:6], 'vs', want[:6])
print('VALIDACION numeros/mz:', 'PERFECTA' if ok else 'FALLA')
assert ok

cells = [f for f in faces if 100 < f.area < 3500]
tree = STRtree(cells)
cell_of = {}
for k, (v, x, y) in enumerate(lot_nums):
    pt = Point(x, y); hit = None
    for idx in tree.query(pt):
        if cells[int(idx)].contains(pt):
            hit = int(idx); break
    assert hit is not None, (v, x, y)
    assert hit not in cell_of, ('celda doble', v)
    cell_of[hit] = (num_mz[k], lot_nums[k][0])
print('celdas numeradas:', len(cell_of))

mods = []
for i in cell_of:
    c = cells[i]
    if 200 < c.area < 300:
        r = minimum_rotated_rectangle(c); xs, ys = r.exterior.xy
        mods.append(min(math.dist((xs[0], ys[0]), (xs[1], ys[1])), math.dist((xs[1], ys[1]), (xs[2], ys[2]))))
S = 5.5 / np.median(mods)
print('S = %.5f' % S)
diffs = []
for i, (nm, v) in cell_of.items():
    k = nm.replace('MZ ', '') + '|' + str(v)
    a_of = ago.get(k, [None])[0]
    if a_of is None: continue
    if abs(a_of - 55) > 0.6:
        a_geo = cells[i].area * S * S
        diffs.append((k, a_of, round(a_geo, 1), round(abs(a_of - a_geo), 1)))
bad = [d for d in diffs if d[3] > 8]
print('fingerprints no-55:', len(diffs), '| desviacion>8m2:', len(bad), bad[:6])

letters = [(t, x, y) for t, x, y in other if len(t) == 1 and t.isalpha() and t != 'V']
mall = [(x, y) for t, x, y in other if t == 'MALL'][0]
perims = {}
for t, x, y in letters:
    for f in faces:
        if 400 < f.area < 12000 and f.contains(Point(x, y)):
            perims[t] = f; break
mallface = next(f for f in faces if 2000 < f.area < 20000 and f.contains(Point(*mall)))
assert len(perims) == 17, sorted(perims)
faces3 = pickle.load(open('plr_faces3.pkl', 'rb'))
giants3 = sorted([f for f in faces3 if f.area > 20000], key=lambda f: -f.area)
def touch_count(f):
    n = 0
    for idx in tree.query(f):
        if cells[int(idx)].distance(f) < 0.5: n += 1
    return n
tc = [(touch_count(f), f) for f in giants3[:4]]
tc.sort(key=lambda z: -z[0])
roads = tc[0][1]
prot = max((f for n, f in tc[1:]), key=lambda f: f.area) if len(tc) > 1 else None
print('giants3:', len(giants3), '| vial m2:', round(roads.area * S * S), '| prot m2:', round(prot.area * S * S) if prot is not None else None)
numbered = set(cell_of)
cells3 = [f for f in faces3 if 100 < f.area < 3500]
tree3 = STRtree(cells3)
numbered3 = set()
for v, x, y in lot_nums:
    pt = Point(x, y)
    for idx in tree3.query(pt):
        if cells3[int(idx)].contains(pt): numbered3.add(int(idx)); break
parking = [c for i, c in enumerate(cells3) if i not in numbered3 and c.distance(mallface) < 25]
slivers = [f for f in faces3 if 2 < f.area < 100 and f.distance(roads) < 1.5]
print('parqueos:', len(parking), 'sardineles:', len(slivers))

allpts = np.vstack([np.array(c.exterior.coords) for c in cells])
cx, cy = allpts[:, 0].mean(), allpts[:, 1].mean()
def M(pt):
    return [round((pt[0] - cx) * S, 2), round((pt[1] - cy) * S, 2)]
def poly_m(p, simp=0.3):
    p = p.simplify(simp)
    out = {'e': [M(c) for c in list(p.exterior.coords)[:-1]]}
    hs = [[M(c) for c in list(r.coords)[:-1]] for r in p.interiors]
    if hs: out['h'] = hs
    return out
data = {}
data['calz'] = [poly_m(roads, 0.3)]
data['anden'] = [poly_m(c, 0.2) for c in parking]
data['greens'] = [poly_m(f, 0.12) for f in slivers]
data['comercio'] = poly_m(mallface, 0.4)
_halo = _uu2 = None
_uu_pre = unary_union([roads.buffer(3)] + [c.buffer(3) for c in cells] + [p.buffer(3) for p in perims.values()] + [mallface.buffer(3)])
if _uu_pre.geom_type == 'MultiPolygon': _uu_pre = max(_uu_pre.geoms, key=lambda g: g.area)
data['terrain'] = poly_m(_uu_pre.buffer(55).simplify(4), 1.2)
data['band'] = {'e': [[400, 400], [401, 400], [400, 401]]}
_uu = unary_union([roads.buffer(3)] + [c.buffer(3) for c in cells] + [p.buffer(3) for p in perims.values()] + [mallface.buffer(3)]).simplify(1)
if _uu.geom_type == 'MultiPolygon': _uu = max(_uu.geoms, key=lambda g: g.area)
data['urban'] = poly_m(_uu, 0.8)
lots = []
for i, (nm, v) in sorted(cell_of.items(), key=lambda z: (int(z[1][0].split()[1]), z[1][1])):
    c = cells[i]
    k = nm.replace('MZ ', '') + '|' + str(v)
    r = minimum_rotated_rectangle(c); xs, ys = r.exterior.xy
    e1 = math.dist((xs[0], ys[0]), (xs[1], ys[1])); e2 = math.dist((xs[1], ys[1]), (xs[2], ys[2]))
    ang = math.atan2(ys[1] - ys[0], xs[1] - xs[0]) if e1 >= e2 else math.atan2(ys[2] - ys[1], xs[2] - xs[1])
    ct = c.centroid
    npt = nearest_points(ct, roads)[1]
    rec = {'p': [M(q) for q in list(c.simplify(0.2).exterior.coords)[:-1]],
           'c': M((ct.x, ct.y)), 'a': round(-ang, 4),
           'f': round(math.atan2(npt.y - ct.y, npt.x - ct.x), 4),
           'mz': nm, 'n': v, 'w': round(min(e1, e2) * S, 1), 'd': round(max(e1, e2) * S, 1),
           'area': ago.get(k, [round(c.area * S * S)])[0]}
    e = EMAP.get((nm, v))
    if e: rec['e'] = e
    lots.append(rec)
data['lots'] = lots
pers = []
for t, f in sorted(perims.items()):
    ct = f.centroid
    pers.append({'p': [M(q) for q in list(f.simplify(0.4).exterior.coords)[:-1]],
                 'c': M((ct.x, ct.y)), 'letter': t, 'area': agoL.get(t), 'area_geom': round(f.area * S * S)})
data['perims'] = pers
data['mzLabels'] = [{'t': nm, 'c': M((x, y))} for nm, x, y in mz_labels]
data['loteLabels'] = [{'t': 'Lote ' + p['letter'], 'c': p['c']} for p in pers]
data['extraLabels'] = [{'t': 'Mall Comercial', 'c': M(mall)}]
Aaf = np.load('plr_affine.npy'); Ag = Aaf[:4].reshape(2, 2); bg = Aaf[4:]
Ai = np.linalg.inv(Ag)
lots_u = unary_union([c.buffer(0.5) for c in cells])
def old2new_ok(pm):
    q = (np.array(pm) - bg) @ Ai.T
    P2 = Point(q[0], q[1])
    if roads.contains(P2) or lots_u.contains(P2) or mallface.contains(P2): return None
    return [round((q[0] - cx) * S, 2), round((q[1] - cy) * S, 2)]
data['trees'] = [t2 for t2 in (old2new_ok(t) for t in cur['trees']) if t2]
# sembrar arboles sobre el anillo de proteccion junto al casco urbano (deterministico)
try:
    ring = _uu.exterior
    Ltot = ring.length
    seed_ts = [i * 38.0 for i in range(int(Ltot / 38.0))]
    for tpos in seed_ts:
        pnt = ring.interpolate(tpos)
        p2 = ring.interpolate(min(tpos + 1.0, Ltot))
        dx, dy = p2.x - pnt.x, p2.y - pnt.y
        L2 = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L2, dx / L2
        for sgn in (1, -1):
            q = (pnt.x + sgn * nx * 9, pnt.y + sgn * ny * 9)
            if prot.contains(Point(q)) and not _uu.contains(Point(q)):
                data['trees'].append([round((q[0] - cx) * S, 2), round((q[1] - cy) * S, 2)])
                break
except Exception as ex:
    print('seed arboles fallo:', ex)
data['scatter'] = [t2 for t2 in (old2new_ok(t) for t in cur['scatter']) if t2]
print('trees:', len(data['trees']), 'scatter:', len(data['scatter']))
js = 'var PLAN=' + json.dumps(data, separators=(',', ':')) + ';'
open('plan_data.js', 'w').write(js)
print('plan_data bytes:', len(js), '| lots:', len(lots), '| perims:', len(pers))
