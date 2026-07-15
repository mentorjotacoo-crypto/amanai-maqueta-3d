import fitz, math, pickle
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union, polygonize
from shapely.prepared import prep
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
def ck(c): return None if c is None else tuple(round(x,2) for x in c)

quads = pickle.load(open("lot_quads.pkl", "rb"))
L = pickle.load(open("layers6.pkl", "rb"))
blocks = L["blocks"]

# purple polylines -> irregular corner lots
lines = []
for d in page.get_drawings():
    if ck(d.get("color")) not in {(0.5,0.0,1.0),(0.72,0.0,0.72),(0.58,0.15,0.56)}: continue
    for it in d["items"]:
        if it[0] == "l":
            a, b = T(it[1].x, it[1].y), T(it[2].x, it[2].y)
            Ln = math.dist(a, b)
            if Ln < 0.02: continue
            ux, uy = (b[0]-a[0])/Ln, (b[1]-a[1])/Ln
            g = 1.2
            lines.append(LineString([(a[0]-ux*g, a[1]-uy*g), (b[0]+ux*g, b[1]+uy*g)]))
        elif it[0] == "qu":
            q = it[1]
            pts = [T(q.ul.x,q.ul.y), T(q.ur.x,q.ur.y), T(q.lr.x,q.lr.y), T(q.ll.x,q.ll.y), T(q.ul.x,q.ul.y)]
            lines.append(LineString(pts))
for blk in blocks:
    lines.append(LineString(list(blk.exterior.coords)))
faces = [f for f in polygonize(unary_union(lines))]
qu_union = unary_union(quads)
roads_u = unary_union(L["calz"] + L["anden"])
com = L["comercio"]
bp = prep(L["urban"].buffer(2))
from shapely import minimum_rotated_rectangle as _mrr
def dims(f):
    r = _mrr(f); xs, ys = r.exterior.xy
    e1 = math.dist((xs[0],ys[0]),(xs[1],ys[1])); e2 = math.dist((xs[1],ys[1]),(xs[2],ys[2]))
    return min(e1,e2), max(e1,e2)
irregular = []
for f in faces:
    a = f.area * S * S
    if not (25 <= a <= 130): continue
    if not bp.contains(f.representative_point()): continue
    if f.intersection(roads_u).area > 0.15 * f.area: continue
    if f.intersection(com).area > 0.3 * f.area: continue
    if f.intersection(qu_union).area > 0.35 * f.area: continue
    mn, mx = dims(f)
    if mn*S < 3.4 or mx/mn > 3.5: continue
    irregular.append(f)
# dedupe among themselves
irregular.sort(key=lambda f: -f.area)
kept = []
ku = None
for f in irregular:
    if ku is not None and f.intersection(ku).area > 0.3*f.area: continue
    kept.append(f)
    ku = unary_union([ku, f]) if ku is not None else f
print("quads:", len(quads), "irregular corner lots:", len(kept))

all_lots = quads + kept
cov = sum(f.area for f in all_lots) / sum(b.area for b in blocks)
print("total lots:", len(all_lots), "block coverage:", round(cov*100, 1), "%")
per_block = []
for bi, blk in enumerate(blocks):
    pb = prep(blk.buffer(2))
    mine = [f for f in all_lots if pb.contains(f.representative_point())]
    per_block.append((bi, len(mine), round(100*sum(f.area for f in mine)/blk.area)))
print("per block (idx,n,cov%):", per_block)

# fill remnants of undercovered blocks with local grid
from shapely import affinity
from shapely.geometry import box as _box
lots_union = unary_union([f.buffer(0.5) for f in all_lots])
fill = []
LOT_W_PT, LOT_D_PT = 5.5/S, 10.0/S
for blk in blocks:
    rem = blk.difference(lots_union).difference(com.buffer(1))
    parts = list(rem.geoms) if rem.geom_type == "MultiPolygon" else [rem]
    for piece in parts:
        if piece.area*S*S < 45: continue
        r = _mrr(piece); xs, ys = r.exterior.xy
        e1 = math.dist((xs[0],ys[0]),(xs[1],ys[1])); e2 = math.dist((xs[1],ys[1]),(xs[2],ys[2]))
        if min(e1,e2)*S < 4.5: continue
        if e1 >= e2: ang = math.degrees(math.atan2(ys[1]-ys[0], xs[1]-xs[0]))
        else: ang = math.degrees(math.atan2(ys[2]-ys[1], xs[2]-xs[1]))
        rb = affinity.rotate(piece, -ang, origin=piece.centroid)
        b = rb.bounds
        W, H = b[2]-b[0], b[3]-b[1]
        nrows = max(1, round(H / LOT_D_PT))
        rowh = H / nrows
        y = b[1]
        cells = []
        for row in range(nrows):
            x = b[0]
            while x < b[2]-0.3:
                cells.append(_box(x, y, min(x+LOT_W_PT,b[2]), y+rowh))
                x += LOT_W_PT
            y += rowh
        for c in cells:
            inter = rb.intersection(c)
            polys = list(inter.geoms) if inter.geom_type in ("MultiPolygon","GeometryCollection") else [inter]
            for pp in polys:
                if pp.geom_type == "Polygon" and 28 <= pp.area*S*S <= 130:
                    mn2, mx2 = dims(pp)
                    if mn2*S >= 3.2 and mx2/mn2 <= 4:
                        fill.append(affinity.rotate(pp, ang, origin=piece.centroid))
print("fill lots:", len(fill))
all_lots = all_lots + fill
cov2 = sum(f.area for f in all_lots) / sum(b.area for b in blocks)
print("FINAL lots:", len(all_lots), "coverage:", round(cov2*100,1), "%")
pickle.dump(all_lots, open("lots_final.pkl", "wb"))

fig, ax = plt.subplots(figsize=(16,12), dpi=140)
for b in blocks:
    xs, ys = b.exterior.xy
    ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#f2ecd9", edgecolor="#999", lw=.5, zorder=1))
for f in quads:
    xs, ys = f.exterior.xy
    ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#d8e8fb", edgecolor="#2a5fa5", lw=.4, zorder=2))
for f in kept:
    xs, ys = f.exterior.xy
    ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#ffd9b0", edgecolor="#b06a1f", lw=.5, zorder=3))
ax.set_xlim(60,760); ax.set_ylim(560,20); ax.set_aspect("equal")
plt.tight_layout(); plt.savefig("debug9.png")
print("saved debug9.png")
