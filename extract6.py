import fitz, pickle, math, collections
from shapely.geometry import LineString, Polygon, Point, MultiPoint
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

draw = page.get_drawings()
def ck(c):
    return None if c is None else tuple(round(x, 2) for x in c)

GRAY_FILLS = {(0.9,0.9,0.9),(0.78,0.78,0.79)}
GREEN_FILL = (0.84,0.89,0.81)
ORANGE = (1.0,0.5,0.0)
GREEN_HATCH = {(0.54,0.72,0.0),(0.65,0.87,0.0),(0.75,1.0,0.0)}
CYAN = (0.0,0.72,0.72)
EXCLUDE_STRUCT = GREEN_HATCH | {(0.65,0.0,0.0),(1.0,0.0,0.0),(0.5,0.0,1.0),(0.72,0.0,0.72),(0.58,0.15,0.56)}

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

gray_rings, green_rings, orange_segs, green_mid, cyan_pts, struct_lines = [], [], [], [], [], []
def snap(p, g=0.15): return (round(p[0]/g)*g, round(p[1]/g)*g)

for d in draw:
    stroke, fill = ck(d.get("color")), ck(d.get("fill"))
    items = d["items"]
    if fill in GRAY_FILLS: gray_rings.extend(rings_from_items(items))
    if fill == GREEN_FILL: green_rings.extend(rings_from_items(items))
    if stroke == ORANGE:
        for it in items:
            if it[0] == "l":
                a, b = T(it[1].x,it[1].y), T(it[2].x,it[2].y)
                if math.dist(a,b) > 0.05: orange_segs.append((a,b))
    if stroke in GREEN_HATCH:
        for it in items:
            if it[0] == "l":
                a, b = T(it[1].x,it[1].y), T(it[2].x,it[2].y)
                green_mid.append(((a[0]+b[0])/2,(a[1]+b[1])/2))
    if stroke == CYAN:
        for it in items:
            for p in it[1:]:
                if hasattr(p,"x"): cyan_pts.append(T(p.x,p.y))
    if stroke is not None and stroke not in EXCLUDE_STRUCT:
        for it in items:
            if it[0] == "l":
                a, b = T(it[1].x,it[1].y), T(it[2].x,it[2].y)
                if (a[0]-b[0])**2+(a[1]-b[1])**2 > 0.02:
                    struct_lines.append(LineString([snap(a), snap(b)]))

def poly_ok(p): return p if p.is_valid else p.buffer(0)
road_polys = []
for ring in gray_rings:
    try:
        p = poly_ok(Polygon(ring))
        if p.area > 2: road_polys.append(p)
    except Exception: pass
green_polys = []
for ring in green_rings:
    try:
        p = poly_ok(Polygon(ring))
        if p.area > 2: green_polys.append(p)
    except Exception: pass
roads_union = unary_union(road_polys)
print("roads:", len(road_polys), "green fills:", len(green_polys))

# carve set: elongated road polys extended along major axis
EXT = 10 / S / 2  # 10 m in pt (half added each side -> use full below)
carve_parts = [roads_union.buffer(0.8)]
for p in road_polys:
    r = minimum_rotated_rectangle(p)
    xs, ys = r.exterior.xy
    e1 = math.dist((xs[0],ys[0]),(xs[1],ys[1])); e2 = math.dist((xs[1],ys[1]),(xs[2],ys[2]))
    if min(e1,e2) < 1: continue
    if max(e1,e2)/min(e1,e2) > 3:
        f = (max(e1,e2) + 2*EXT) / max(e1,e2)
        if e1 >= e2: r2 = affinity.scale(r, xfact=f, yfact=1, origin="centroid")
        else: r2 = affinity.scale(r, xfact=1, yfact=f, origin="centroid")
        # rotate scale to axis: use generic - scale along axis via rotation
        ang = math.degrees(math.atan2(ys[1]-ys[0], xs[1]-xs[0]))
        rr = affinity.rotate(r, -ang, origin="centroid")
        b = rr.bounds
        if (b[2]-b[0]) >= (b[3]-b[1]):
            rr2 = Polygon([(b[0]-EXT,b[1]),(b[2]+EXT,b[1]),(b[2]+EXT,b[3]),(b[0]-EXT,b[3])])
        else:
            rr2 = Polygon([(b[0],b[1]-EXT),(b[2],b[1]-EXT),(b[2],b[3]+EXT),(b[0],b[3]+EXT)])
        carve_parts.append(affinity.rotate(rr2, ang, origin=r.centroid))
carve = unary_union(carve_parts)

# urban boundary from dashed orange band
blob = unary_union([LineString(s).buffer(2.0) for s in orange_segs])
geoms = list(blob.geoms) if blob.geom_type=="MultiPolygon" else [blob]
urban, best = None, 0
for g in geoms:
    for r in g.interiors:
        a = abs(Polygon(r).area)
        if a > best: best, urban = a, Polygon(r)
urban = urban.buffer(2.0)
print("urban m2:", round(urban.area*S*S))

# comercio via hatch angle
angs = collections.Counter()
for a,b in orange_segs:
    L = math.dist(a,b)
    if L < 2: continue
    ang = round(math.degrees(math.atan2(b[1]-a[1], b[0]-a[0])) % 180)
    angs[ang] += 1
top_angles = angs.most_common(6)
print("orange angle modes:", top_angles)
ha = top_angles[0][0]
hatch = [LineString([a,b]) for a,b in orange_segs
         if math.dist(a,b) >= 2 and abs((math.degrees(math.atan2(b[1]-a[1],b[0]-a[0])) % 180) - ha) < 3]
print("hatch segs:", len(hatch))
hb = unary_union([h.buffer(6) for h in hatch])
hg = list(hb.geoms) if hb.geom_type=="MultiPolygon" else [hb]
hg.sort(key=lambda g:-g.area)
comercio = hg[0].buffer(-5).buffer(4).simplify(1)
if comercio.geom_type=="MultiPolygon": comercio = max(comercio.geoms, key=lambda g:g.area)
print("comercio m2:", round(comercio.area*S*S))

# blocks
carve2 = unary_union([carve, comercio.buffer(1)])
diff = poly_ok(urban).difference(carve2)
geoms2 = list(diff.geoms) if diff.geom_type=="MultiPolygon" else [diff]
blocks = sorted([g for g in geoms2 if g.area*S*S > 60], key=lambda g:-g.area)
print("blocks:", len(blocks), "areas m2:", [round(b.area*S*S) for b in blocks])

# perimeter lots from structural polygonize, outside urban
faces = [f for f in polygonize(unary_union(struct_lines)) if 150 < f.area*S*S < 1200]
inner = urban.buffer(-3)
perims = [f for f in faces if not f.centroid.within(inner)]
# dedupe overlapping faces (keep bigger)
perims.sort(key=lambda f:-f.area)
kept = []
for f in perims:
    if all(f.intersection(k).area < 0.4*f.area for k in kept): kept.append(f)
print("perimeter lot candidates:", len(kept), [round(f.area*S*S) for f in kept[:25]])

# cyan clusters
cyu = unary_union([Point(p).buffer(4) for p in cyan_pts])
clusters = [c for c in (cyu.geoms if cyu.geom_type=="MultiPolygon" else [cyu]) if c.bounds[2]-c.bounds[0] > 5]
print("cyan clusters:", len(clusters))

pickle.dump({"roads":road_polys,"greens":green_polys,"urban":urban,"comercio":comercio,
             "blocks":blocks,"perims":kept,"trees":green_mid,"cyan":[c.bounds for c in clusters]},
            open("layers3.pkl","wb"))

fig, ax = plt.subplots(figsize=(16,12), dpi=140)
xs, ys = urban.exterior.xy
ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#f3edda", edgecolor="orange", lw=1.2, zorder=1))
for p in road_polys:
    xs, ys = p.exterior.xy
    ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#999", edgecolor="none", zorder=2))
for p in green_polys:
    xs, ys = p.exterior.xy
    ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#7ab86f", edgecolor="none", zorder=3))
for i,b in enumerate(blocks):
    xs, ys = b.exterior.xy
    ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#bcd4f5", edgecolor="#3355aa", lw=.4, zorder=4, alpha=.85))
    c=b.centroid; ax.text(c.x,c.y,str(i),fontsize=6,ha="center",zorder=8)
for f in kept:
    xs, ys = f.exterior.xy
    ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#d6e6b8", edgecolor="#557733", lw=.5, zorder=4))
xs, ys = comercio.exterior.xy
ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#e8b34c", edgecolor="none", zorder=5, alpha=.9))
for bnd in [c.bounds for c in clusters]:
    ax.add_patch(plt.Rectangle((bnd[0],bnd[1]), bnd[2]-bnd[0], bnd[3]-bnd[1], fill=False, ec="teal", lw=.5, zorder=9))
ax.set_xlim(60,760); ax.set_ylim(560,20); ax.set_aspect("equal")
plt.tight_layout(); plt.savefig("debug4.png")
print("saved debug4.png")
