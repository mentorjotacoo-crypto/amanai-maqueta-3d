import fitz, pickle, math, json, collections
from shapely.geometry import LineString, Polygon, Point, box
from shapely.ops import unary_union, polygonize
from shapely import minimum_rotated_rectangle, affinity
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP

S = 5.5 / 10.4
doc = fitz.open(r"C:\Users\Juan Camilo\Downloads\V.27 AMANAI.pdf")
page = doc[0]
RM = page.rotation_matrix
def T(x, y):
    p = fitz.Point(x, y) * RM
    return (p.x, p.y)
def ck(c): return None if c is None else tuple(round(x, 2) for x in c)
def poly_ok(p): return p if p.is_valid else p.buffer(0)

draw = page.get_drawings()
GRAY_CALZ = (0.9,0.9,0.9); GRAY_ANDEN = (0.78,0.78,0.79)
GREEN_FILL = (0.84,0.89,0.81)
ORANGE = (1.0,0.5,0.0)
TREE_COLORS = {(0.36,0.72,0.0),(0.34,0.45,0.0),(0.44,0.58,0.0)}
HATCH = {(0.54,0.72,0.0),(0.65,0.87,0.0),(0.75,1.0,0.0)}
CYAN = (0.0,0.72,0.72)

def rings_from_items(items):
    rings, cur = [], []
    for it in items:
        if it[0] != "l": continue
        a, b = T(it[1].x, it[1].y), T(it[2].x, it[2].y)
        if cur and math.dist(cur[-1], a) > 0.5:
            if len(cur) >= 3: rings.append(cur)
            cur = []
        if not cur: cur.append(a)
        cur.append(b)
    if len(cur) >= 3: rings.append(cur)
    return rings

calz_r, anden_r, green_r = [], [], []
orange_segs, tree_pts, hatch_pts, cyan_pts, purple = [], {}, [], [], []
def snap(p, g=0.15): return (round(p[0]/g)*g, round(p[1]/g)*g)

for d in draw:
    stroke, fill = ck(d.get("color")), ck(d.get("fill"))
    items = d["items"]
    if fill == GRAY_CALZ: calz_r.extend(rings_from_items(items))
    elif fill == GRAY_ANDEN: anden_r.extend(rings_from_items(items))
    elif fill == GREEN_FILL: green_r.extend(rings_from_items(items))
    if stroke == ORANGE:
        for it in items:
            if it[0] == "l":
                a, b = T(it[1].x,it[1].y), T(it[2].x,it[2].y)
                if math.dist(a,b) > 0.05: orange_segs.append((a,b))
    if stroke in TREE_COLORS:
        key = stroke
        for it in items:
            if it[0] == "l":
                a, b = T(it[1].x,it[1].y), T(it[2].x,it[2].y)
                tree_pts.setdefault(key, []).append(((a[0]+b[0])/2,(a[1]+b[1])/2))
    if stroke in HATCH:
        for it in items:
            if it[0] == "l":
                a, b = T(it[1].x,it[1].y), T(it[2].x,it[2].y)
                hatch_pts.append(((a[0]+b[0])/2,(a[1]+b[1])/2))
    if stroke == CYAN:
        for it in items:
            for p in it[1:]:
                if hasattr(p,"x"): cyan_pts.append(T(p.x,p.y))
    if stroke == (0.5,0.0,1.0):
        for it in items:
            if it[0] == "l":
                a, b = T(it[1].x,it[1].y), T(it[2].x,it[2].y)
                if math.dist(a,b) > 2: purple.append(LineString([snap(a),snap(b)]))

def mkpolys(rings):
    out = []
    for r in rings:
        try:
            p = poly_ok(Polygon(r))
            if p.area > 2: out.append(p)
        except Exception: pass
    return out
calz, anden, greens = mkpolys(calz_r), mkpolys(anden_r), mkpolys(green_r)
roads_union = unary_union(calz + anden)
print("calz:", len(calz), "anden:", len(anden), "greens:", len(greens))

# urban + comercio from orange blob
blob = unary_union([LineString(s).buffer(2.0) for s in orange_segs])
geoms = sorted((blob.geoms if blob.geom_type=="MultiPolygon" else [blob]), key=lambda g:-g.area)
urban, best = None, 0
band = None
for g in geoms:
    for r in g.interiors:
        a = abs(Polygon(r).area)
        if a > best: best, urban, band = a, Polygon(r), g
urban = urban.buffer(2.0)
others = [g for g in geoms if g is not band]
comercio = max(others, key=lambda g: g.area).buffer(-1).simplify(1)
if comercio.geom_type == "MultiPolygon": comercio = max(comercio.geoms, key=lambda g:g.area)
print("urban m2:", round(urban.area*S*S), "comercio m2:", round(comercio.area*S*S))

# perimeter lots
pf = [f for f in polygonize(unary_union(purple)) if 100 < f.area*S*S < 1300]
pf.sort(key=lambda f: -f.area)
perims = []
for f in pf:
    if all(f.intersection(k).area < 0.4*f.area for k in perims): perims.append(f)
print("perim lots:", len(perims))

# carve & blocks
EXT = 12 / S
carve_parts = [roads_union.buffer(0.8), comercio.buffer(1)]
carve_parts += [g.buffer(0.5) for g in greens]
for p in calz + anden:
    r = minimum_rotated_rectangle(p)
    xs, ys = r.exterior.xy
    e1 = math.dist((xs[0],ys[0]),(xs[1],ys[1])); e2 = math.dist((xs[1],ys[1]),(xs[2],ys[2]))
    if min(e1,e2) < 1 or max(e1,e2)/min(e1,e2) <= 2.5: continue
    ang = math.degrees(math.atan2(ys[1]-ys[0], xs[1]-xs[0]))
    rr = affinity.rotate(r, -ang, origin=r.centroid)
    b = rr.bounds
    if (b[2]-b[0]) >= (b[3]-b[1]):
        rr2 = Polygon([(b[0]-EXT,b[1]),(b[2]+EXT,b[1]),(b[2]+EXT,b[3]),(b[0]-EXT,b[3])])
    else:
        rr2 = Polygon([(b[0],b[1]-EXT),(b[2],b[1]-EXT),(b[2],b[3]+EXT),(b[0],b[3]+EXT)])
    carve_parts.append(affinity.rotate(rr2, ang, origin=r.centroid))
diff = poly_ok(urban).difference(unary_union(carve_parts))
geoms2 = list(diff.geoms) if diff.geom_type=="MultiPolygon" else [diff]
blocks = sorted([g for g in geoms2 if g.area*S*S > 100], key=lambda g:-g.area)
print("blocks:", len(blocks), [round(b.area*S*S) for b in blocks])

# ---- lots: grid subdivision per block, oriented to block axis ----
LOT_W_PT, LOT_D_PT = 5.5/S, 10.0/S
all_lots = []
for bi, blk in enumerate(blocks):
    r = minimum_rotated_rectangle(blk)
    xs, ys = r.exterior.xy
    e1 = math.dist((xs[0],ys[0]),(xs[1],ys[1])); e2 = math.dist((xs[1],ys[1]),(xs[2],ys[2]))
    if e1 >= e2: ang = math.degrees(math.atan2(ys[1]-ys[0], xs[1]-xs[0]))
    else: ang = math.degrees(math.atan2(ys[2]-ys[1], xs[2]-xs[1]))
    rb = affinity.rotate(blk, -ang, origin=blk.centroid)
    b = rb.bounds
    W, H = b[2]-b[0], b[3]-b[1]
    nrows = max(1, round(H / LOT_D_PT))
    rowh = H / nrows
    cells = []
    y = b[1]
    for row in range(nrows):
        x = b[0]
        while x < b[2] - 0.3:
            cells.append(box(x, y, min(x+LOT_W_PT, b[2]), y+rowh))
            x += LOT_W_PT
        y += rowh
    lots_here = []
    for c in cells:
        inter = rb.intersection(c)
        if inter.is_empty: continue
        polys = list(inter.geoms) if inter.geom_type in ("MultiPolygon","GeometryCollection") else [inter]
        for pp in polys:
            if pp.geom_type == "Polygon" and pp.area*S*S >= 28:
                lots_here.append(affinity.rotate(pp, ang, origin=blk.centroid))
    all_lots.append(lots_here)
print("lots per block:", [len(l) for l in all_lots], "total:", sum(len(l) for l in all_lots))

# ---- trees from symbol clusters ----
trees = []
for col, pts in tree_pts.items():
    u = unary_union([Point(p).buffer(3) for p in pts])
    for g in (u.geoms if u.geom_type=="MultiPolygon" else [u]):
        c = g.centroid
        r_est = math.sqrt(g.area/math.pi)
        trees.append((c.x, c.y, r_est))
print("tree symbols:", len(trees))

# protection blob from hatch
hb = unary_union([Point(p).buffer(9) for p in hatch_pts[::4]])
hg = sorted((hb.geoms if hb.geom_type=="MultiPolygon" else [hb]), key=lambda g:-g.area)
prot = hg[0].buffer(-4).simplify(2)
if prot.geom_type == "MultiPolygon": prot = max(prot.geoms, key=lambda g:g.area)
print("protection m2:", round(prot.area*S*S))
hatch_sample = hatch_pts[::40]

# cyan clusters
cyu = unary_union([Point(p).buffer(4) for p in cyan_pts])
clusters = [c.bounds for c in (cyu.geoms if cyu.geom_type=="MultiPolygon" else [cyu])
            if (c.bounds[2]-c.bounds[0]) > 6 and (c.bounds[3]-c.bounds[1]) > 2]
print("cyan clusters:", len(clusters))

pickle.dump({"calz":calz,"anden":anden,"greens":greens,"urban":urban,"comercio":comercio,
             "blocks":blocks,"lots":all_lots,"perims":perims,"trees":trees,"prot":prot,
             "hatch":hatch_sample,"cyan":clusters}, open("layers5.pkl","wb"))

fig, ax = plt.subplots(figsize=(16,12), dpi=140)
xs, ys = prot.exterior.xy
ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#cfe0c3", edgecolor="none", zorder=0))
xs, ys = urban.exterior.xy
ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#f3edda", edgecolor="orange", lw=1, zorder=1))
for p in calz:
    xs, ys = p.exterior.xy
    ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#8b8b86", edgecolor="none", zorder=2))
for p in anden:
    xs, ys = p.exterior.xy
    ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#c5c2b8", edgecolor="none", zorder=2))
for p in greens:
    xs, ys = p.exterior.xy
    ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#7ab86f", edgecolor="none", zorder=3))
for lots_here in all_lots:
    for l in lots_here:
        xs, ys = l.exterior.xy
        ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#faf5e6", edgecolor="#b09c7a", lw=.3, zorder=4))
for f in perims:
    xs, ys = f.exterior.xy
    ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#e7edd3", edgecolor="#88a05e", lw=.6, zorder=4))
xs, ys = comercio.exterior.xy
ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#e8b34c", edgecolor="none", zorder=4))
for (x,y,r) in trees:
    ax.add_patch(plt.Circle((x,y), max(r,2), facecolor="#4e7a3e", edgecolor="none", zorder=6, alpha=.8))
ax.set_xlim(60,760); ax.set_ylim(560,20); ax.set_aspect("equal")
plt.tight_layout(); plt.savefig("debug6.png")
print("saved debug6.png")
