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
def nearest_mz(c):
    best, bd = None, 1e18
    for name, p in mz_items:
        d = (c.x-p[0])**2 + (c.y-p[1])**2
        if d < bd: bd, best = d, name
    return best
flat_info = []
for l in flat:
    c = l.centroid
    mz = nearest_mz(c)
    r = minimum_rotated_rectangle(l)
    xs, ys = r.exterior.xy
    e1 = math.dist((xs[0],ys[0]),(xs[1],ys[1])); e2 = math.dist((xs[1],ys[1]),(xs[2],ys[2]))
    if e1 >= e2: ang = math.atan2(ys[1]-ys[0], xs[1]-xs[0])
    else: ang = math.atan2(ys[2]-ys[1], xs[2]-xs[1])
    flat_info.append((l, mz, c, ang, min(e1,e2)*S, max(e1,e2)*S))
# number lots within each mz by sweep order
by_mz = {}
for item in flat_info: by_mz.setdefault(item[1], []).append(item)
for mz, items in by_mz.items():
    ax = sum(i[3] for i in items)/len(items)
    ux, uy = math.cos(ax), math.sin(ax)
    items.sort(key=lambda i: (i[2].x*ux + i[2].y*uy, i[2].x*-uy + i[2].y*ux))
    for n, (l, _, c, ang, wm, lm) in enumerate(items, 1):
        lots_out.append({"p": [M(pt) for pt in list(l.simplify(0.25).exterior.coords)[:-1]],
                         "c": M((c.x, c.y)), "a": round(-ang, 4), "f": round(front_angle(c), 4),
                         "mz": mz, "n": n, "w": round(wm,1), "d": round(lm,1),
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
