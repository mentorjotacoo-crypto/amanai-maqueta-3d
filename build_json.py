import pickle, math, json
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union, nearest_points
from shapely import minimum_rotated_rectangle

S = 5.5 / 10.4
L = pickle.load(open("layers6.pkl", "rb"))

MZ_LABELS = {
 "MZ 1":(350,105),"MZ 2":(400,115),"MZ 3":(455,130),"MZ 4":(508,138),"MZ 5":(560,148),
 "MZ 21":(450,188),"MZ 6":(300,212),"MZ 7":(370,218),"MZ 8":(455,228),"MZ 9":(508,236),
 "MZ 10":(555,243),"MZ 11":(618,232),"MZ 12":(672,238),
 "MZ 20":(218,362),"MZ 19":(272,350),"MZ 18":(330,350),"MZ 17":(388,356),"MZ 16":(450,368),
 "MZ 15":(512,368),"MZ 14":(558,352),"MZ 13":(640,330)}
LOTE_AREAS = {"A":412.25,"B":346.43,"C":478.36,"D":413.80,"E":407.75,"F":467.74,"G":564.50,
 "H":949.44,"I":697.48,"J":673.71,"K":723.97,"L":676.98,"M":474.02,"N":790.72,"O":846.03,
 "P":489.99,"Q":285.49,"R":718.05}
# sheet index -> letter, using saved label_pos order
SHEET = {1:"R",2:"Q",3:"P",4:"O",5:"N",9:"M",10:"L",17:"A",19:"K",24:"B",26:"J",
         30:"C",32:"I",35:"D",39:"H",40:"E",43:"G",44:"F"}
label_pos = L["label_pos"]
LOTE_POS = {letter: label_pos[i] for i, letter in SHEET.items()}

# center: urban centroid
cx, cy = L["urban"].centroid.x, L["urban"].centroid.y
def M(pt):  # pdf pt -> meters centered
    return [round((pt[0]-cx)*S, 2), round((pt[1]-cy)*S, 2)]
def poly_m(p, simp=0.4):
    p = p.simplify(simp)
    ext = [M(c) for c in list(p.exterior.coords)[:-1]]
    holes = [[M(c) for c in list(r.coords)[:-1]] for r in p.interiors]
    return {"e": ext, "h": holes} if holes else {"e": ext}

def union_polys(polys, simp=0.4):
    u = unary_union(polys)
    gs = list(u.geoms) if u.geom_type == "MultiPolygon" else [u]
    return [poly_m(g, simp) for g in gs if g.area > 4]

data = {}
data["calz"] = union_polys(L["calz"])
data["anden"] = union_polys(L["anden"])
data["greens"] = union_polys(L["greens"])
data["comercio"] = poly_m(L["comercio"], 0.8)
data["terrain"] = poly_m(L["terrain"], 1.5)
data["band"] = poly_m(L["band"], 0.8)
data["urban"] = poly_m(L["urban"], 0.8)

# lots
lots_out = []
mz_items = list(MZ_LABELS.items())
counters = {}
flat = pickle.load(open("lots_final.pkl", "rb"))
roads_u = unary_union(L["calz"] + L["anden"])
def front_angle(c):
    np_ = nearest_points(Point(c.x, c.y), roads_u)[1]
    return math.atan2(np_.y - c.y, np_.x - c.x)

# --- asignacion de manzana: componentes + eje del lote en el tejido superior ---
comps = pickle.load(open("comps.pkl", "rb"))["parent"]
from collections import defaultdict
lab_comp = {}
for name, p in MZ_LABELS.items():
    pt = Point(p)
    bi = min(range(len(flat)), key=lambda i: flat[i].distance(pt))
    lab_comp[name] = comps[bi]
comp_labels = defaultdict(list)
for name, c in lab_comp.items(): comp_labels[c].append(name)
u_ang = math.atan2(232-212, 618-300)
ub = (math.cos(u_ang), math.sin(u_ang)); uc = (-ub[1], ub[0])

# primera pasada: geometria por lote
info = []
for l in flat:
    c = l.centroid
    r = minimum_rotated_rectangle(l)
    xs, ys = r.exterior.xy
    e1 = math.dist((xs[0],ys[0]),(xs[1],ys[1])); e2 = math.dist((xs[1],ys[1]),(xs[2],ys[2]))
    if e1 >= e2: ang = math.atan2(ys[1]-ys[0], xs[1]-xs[0])
    else: ang = math.atan2(ys[2]-ys[1], xs[2]-xs[1])
    info.append({"l": l, "c": c, "ang": ang, "w": min(e1,e2)*S, "d": max(e1,e2)*S})

def angdiff(a2, b2):
    d = abs((a2-b2) % math.pi)
    return min(d, math.pi-d)

mz_of = [None]*len(flat)
fabric = [i for i in range(len(flat)) if len(comp_labels.get(comps[i], [])) > 1]
fabric_set = set(fabric)
# banda (eje ~perpendicular a u_ang) -> MZ 21 ; columnas -> recluster
band_is, col_is = [], []
for i in fabric:
    if angdiff(info[i]["ang"], u_ang) > math.pi/4: band_is.append(i)
    else: col_is.append(i)
band_pending = band_is  # se asignan tras calcular separadores
# recluster columnas sin la banda
from shapely.strtree import STRtree
cb = [flat[i].buffer(1.2) for i in col_is]
tree = STRtree(cb)
par = list(range(len(col_is)))
def find(x):
    while par[x] != x: par[x] = par[par[x]]; x = par[x]
    return x
for ii, g in enumerate(cb):
    for jj in tree.query(g):
        jj = int(jj)
        if jj > ii and cb[jj].intersects(g):
            ra, rb2 = find(ii), find(jj)
            if ra != rb2: par[ra] = rb2
groups = defaultdict(list)
for ii in range(len(col_is)): groups[find(ii)].append(col_is[ii])
COLS = ["MZ 1","MZ 2","MZ 3","MZ 4","MZ 5","MZ 6","MZ 7","MZ 8","MZ 9","MZ 10","MZ 11"]
ubv = ub; ucv = uc
def proj(px, py, vec): return px*vec[0] + py*vec[1]
# separadores: calzadas verticales dentro del tejido superior
SOUTH_COLS = ["MZ 6","MZ 7","MZ 8","MZ 9","MZ 10"]
seps = []
for rp in L["calz"] + L["anden"]:
    c = rp.centroid
    if not (250 < c.x < 620 and 140 < c.y < 300): continue
    r = minimum_rotated_rectangle(rp)
    xs2, ys2 = r.exterior.xy
    e1 = math.dist((xs2[0],ys2[0]),(xs2[1],ys2[1])); e2 = math.dist((xs2[1],ys2[1]),(xs2[2],ys2[2]))
    if min(e1,e2) < 1 or max(e1,e2) < 40: continue
    if e1 >= e2: a2 = math.atan2(ys2[1]-ys2[0], xs2[1]-xs2[0])
    else: a2 = math.atan2(ys2[2]-ys2[1], xs2[2]-xs2[1])
    d = abs((a2 - u_ang) % math.pi)
    d = min(d, math.pi - d)
    if d > math.pi/3:  # perpendicular a la banda = via vertical
        seps.append(proj(c.x, c.y, ubv))
seps = sorted(set(round(s,1) for s in seps))
def interval(t):
    k = 0
    for s in seps:
        if t > s: k += 1
    return k
lab_int = {name: interval(proj(*MZ_LABELS[name], ubv)) for name in SOUTH_COLS}
uc21 = proj(*MZ_LABELS["MZ 21"], ucv)
for g in groups.values():
    if len(g) <= 40:
        gx = sum(info[i]["c"].x for i in g)/len(g); gy = sum(info[i]["c"].y for i in g)/len(g)
        best, bd = None, 1e18
        for name in COLS:
            p = MZ_LABELS[name]
            d = (gx-p[0])**2 + (gy-p[1])**2
            if d < bd: bd, best = d, name
        for i in g: mz_of[i] = best
    else:
        for i in g:
            ct = info[i]["c"]
            if proj(ct.x, ct.y, ucv) < uc21 - 8:
                # zona norte: MZ 1-5
                best, bd = None, 1e18
                for name in ["MZ 1","MZ 2","MZ 3","MZ 4","MZ 5"]:
                    p = MZ_LABELS[name]
                    d = (ct.x-p[0])**2 + (ct.y-p[1])**2
                    if d < bd: bd, best = d, name
                mz_of[i] = best
            else:
                k = interval(proj(ct.x, ct.y, ubv))
                cand = [n for n in SOUTH_COLS if lab_int[n] == k]
                if cand: mz_of[i] = cand[0]
                else:
                    best, bd = None, 1e18
                    for name in SOUTH_COLS:
                        d = abs(proj(ct.x,ct.y,ubv) - proj(*MZ_LABELS[name], ubv))
                        if d < bd: bd, best = d, name
                    mz_of[i] = best
# ajuste de la fila MZ 21: regresion sobre los lotes de banda cercanos al rotulo
_seed = [i for i in band_pending if abs(proj(info[i]["c"].x, info[i]["c"].y, ucv) - uc21) <= 10]
if len(_seed) >= 5:
    _ts = [proj(info[i]["c"].x, info[i]["c"].y, ubv) for i in _seed]
    _us = [proj(info[i]["c"].x, info[i]["c"].y, ucv) for i in _seed]
    _tm = sum(_ts)/len(_ts); _um = sum(_us)/len(_us)
    _den = sum((t-_tm)**2 for t in _ts) or 1.0
    _b = sum((t-_tm)*(u-_um) for t,u in zip(_ts,_us)) / _den
    def band_dist(ct):
        t = proj(ct.x, ct.y, ubv); u = proj(ct.x, ct.y, ucv)
        return abs(u - (_um + _b*(t-_tm)))
else:
    def band_dist(ct):
        return abs(proj(ct.x, ct.y, ucv) - uc21)

# lotes de banda: fila de MZ 21 o remates de columna / zona norte
for i in band_pending:
    ct = info[i]["c"]
    tu = proj(ct.x, ct.y, ucv)
    if band_dist(ct) <= 7:
        mz_of[i] = "MZ 21"
    elif tu < uc21 - 8:
        best, bd = None, 1e18
        for name in ["MZ 1","MZ 2","MZ 3","MZ 4","MZ 5"]:
            p = MZ_LABELS[name]
            d = (ct.x-p[0])**2 + (ct.y-p[1])**2
            if d < bd: bd, best = d, name
        mz_of[i] = best
    else:
        k = interval(proj(ct.x, ct.y, ubv))
        cand = [n for n in SOUTH_COLS if lab_int[n] == k]
        if cand: mz_of[i] = cand[0]
        else:
            best, bd = None, 1e18
            for name in SOUTH_COLS + ["MZ 11"]:
                d = abs(proj(ct.x,ct.y,ubv) - proj(*MZ_LABELS[name], ubv))
                if d < bd: bd, best = d, name
            mz_of[i] = best

# resto: componentes de una sola etiqueta o huerfanos -> etiqueta mas cercana
for i in range(len(flat)):
    if mz_of[i] is not None: continue
    labs = comp_labels.get(comps[i], [])
    if len(labs) == 1: mz_of[i] = labs[0]
    else:
        ct = info[i]["c"]
        best, bd = None, 1e18
        for name, p in MZ_LABELS.items():
            d = (ct.x-p[0])**2 + (ct.y-p[1])**2
            if d < bd: bd, best = d, name
        mz_of[i] = best

# numeracion por manzana (serpentina geometrica de referencia)
by_mz = defaultdict(list)
for i in range(len(flat)): by_mz[mz_of[i]].append(i)
lots_out = []
for mz, idxs in by_mz.items():
    sx = math.atan2(sum(math.sin(2*info[i]["ang"]) for i in idxs), sum(math.cos(2*info[i]["ang"]) for i in idxs)) / 2
    ux2, uy2 = math.cos(sx), math.sin(sx)          # eje de los lotes (fondo)
    vx2, vy2 = -uy2, ux2                            # a lo largo de la franja
    cxm = sum(info[i]["c"].x for i in idxs)/len(idxs)
    cym = sum(info[i]["c"].y for i in idxs)/len(idxs)
    def sideof(i): return 0 if (info[i]["c"].x-cxm)*ux2 + (info[i]["c"].y-cym)*uy2 < 0 else 1
    def along(i): return info[i]["c"].x*vx2 + info[i]["c"].y*vy2
    west = sorted([i for i in idxs if sideof(i)==0], key=along)
    east = sorted([i for i in idxs if sideof(i)==1], key=along, reverse=True)
    idxs[:] = west + east                           # numeracion en U (referencia)
    for n, i in enumerate(idxs, 1):
        l, c = info[i]["l"], info[i]["c"]
        lots_out.append({"p": [M(pt) for pt in list(l.simplify(0.25).exterior.coords)[:-1]],
                         "c": M((c.x, c.y)), "a": round(-info[i]["ang"], 4),
                         "f": round(front_angle(c), 4), "mz": mz, "n": n,
                         "w": round(info[i]["w"],1), "d": round(info[i]["d"],1),
                         "area": round(l.area*S*S)})
data["lots"] = lots_out
print("lots:", len(lots_out))
print("per mz:", {k: len(v) for k, v in sorted(by_mz.items())})

# perimeter lots matched to letters
perims_out, used = [], set()
for f in L["perims"]:
    c = f.centroid
    best, bd = None, 1e18
    for letter, p in LOTE_POS.items():
        if letter in used: continue
        d = (c.x-p[0])**2 + (c.y-p[1])**2
        if d < bd: bd, best = d, letter
    ag = f.area*S*S
    if best is None or abs(ag - LOTE_AREAS[best]) > 0.3*LOTE_AREAS[best]:
        continue
    used.add(best)
    perims_out.append({"p": [M(pt) for pt in list(f.simplify(0.4).exterior.coords)[:-1]],
                       "c": M((c.x, c.y)), "letter": best,
                       "area": LOTE_AREAS.get(best, round(ag)),
                       "area_geom": round(ag)})
missing = [l for l in LOTE_AREAS if l not in used]
print("perim matched:", [(p["letter"], p["area"], p["area_geom"]) for p in perims_out])
print("missing letters:", missing)
from shapely import affinity as _aff
for letter in missing:
    p = LOTE_POS[letter]
    others = sorted(perims_out, key=lambda q: (q["c"][0]-(p[0]-cx)*S)**2 + (q["c"][1]-(p[1]-cy)*S)**2)[:2]
    if len(others) == 2:
        angp = math.atan2(others[1]["c"][1]-others[0]["c"][1], others[1]["c"][0]-others[0]["c"][0])
    else:
        angp = 0.0
    w = math.sqrt(LOTE_AREAS[letter]) / S / 1.3
    sq = Polygon([(p[0]-w*0.65,p[1]-w*0.5),(p[0]+w*0.65,p[1]-w*0.5),(p[0]+w*0.65,p[1]+w*0.5),(p[0]-w*0.65,p[1]+w*0.5)])
    sq = _aff.rotate(sq, math.degrees(angp), origin=(p[0],p[1]))
    perims_out.append({"p": [M(pt) for pt in list(sq.exterior.coords)[:-1]],
                       "c": M(p), "letter": letter, "area": LOTE_AREAS[letter], "approx": True})
data["perims"] = perims_out

data["trees"] = [M(t) for t in L["trees"]]
data["scatter"] = [M(t) for t in L["scatter"]]
data["mzLabels"] = [{"t": k, "c": M(v)} for k, v in MZ_LABELS.items()]
data["loteLabels"] = [{"t": "Lote " + p["letter"], "c": p["c"]} for p in perims_out]
data["extraLabels"] = [
  {"t":"Comercio", "c": M((235,234))},
  {"t":"Protección Ambiental 5", "c": M((455,70))},
  {"t":"Protección Ambiental 4", "c": M((150,195))},
  {"t":"Protección Ambiental 6", "c": M((460,535))}]

js = "var PLAN=" + json.dumps(data, separators=(",",":")) + ";"
open("plan_data.js","w").write(js)
print("plan_data.js bytes:", len(js))
