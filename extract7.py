import fitz, pickle, math, collections
from shapely.geometry import LineString, Polygon, Point
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

L3 = pickle.load(open("layers3.pkl", "rb"))
road_polys, green_polys, urban = L3["roads"], L3["greens"], L3["urban"]
roads_union = unary_union(road_polys)
def poly_ok(p): return p if p.is_valid else p.buffer(0)

# ---- purple faces -> perimeter lots ----
draw = page.get_drawings()
def ck(c): return None if c is None else tuple(round(x,2) for x in c)
purple = []
def snap(p, g=0.15): return (round(p[0]/g)*g, round(p[1]/g)*g)
for d in draw:
    if ck(d.get("color")) == (0.5, 0.0, 1.0):
        for it in d["items"]:
            if it[0] == "l":
                a, b = T(it[1].x, it[1].y), T(it[2].x, it[2].y)
                if math.dist(a, b) > 2:
                    purple.append(LineString([snap(a), snap(b)]))
print("purple long segs:", len(purple))
pf = [f for f in polygonize(unary_union(purple)) if 100 < f.area * S * S < 1300]
pf.sort(key=lambda f: -f.area)
kept = []
for f in pf:
    if all(f.intersection(k).area < 0.4 * f.area for k in kept): kept.append(f)
print("purple faces (perimeter lots):", len(kept), [round(f.area*S*S) for f in kept])

# ---- carve with 12 m extensions ----
EXT = 12 / S
carve_parts = [roads_union.buffer(0.8)]
for p in road_polys:
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
carve = unary_union(carve_parts)

diff = poly_ok(urban).difference(carve)
geoms2 = list(diff.geoms) if diff.geom_type == "MultiPolygon" else [diff]
blocks = sorted([g for g in geoms2 if g.area*S*S > 60], key=lambda g: -g.area)
print("blocks:", len(blocks), "areas m2:", [round(b.area*S*S) for b in blocks])

# ---- comercio via text ----
words = page.get_text("words")
com_w = [w for w in words if "COMERCIO" in w[4].upper()]
print("comercio words:", [(w[4], round((w[0]+w[2])/2), round((w[1]+w[3])/2)) for w in com_w])
com_pt = Point((com_w[0][0]+com_w[0][2])/2, (com_w[0][1]+com_w[0][3])/2) if com_w else None
com_idx = None
if com_pt is not None:
    for i, b in enumerate(blocks):
        if com_pt.within(b): com_idx = i; break
print("comercio block idx:", com_idx,
      "area m2:", round(blocks[com_idx].area*S*S) if com_idx is not None else None)

pickle.dump({"roads": road_polys, "greens": green_polys, "urban": urban,
             "blocks": blocks, "perims": kept, "com_idx": com_idx,
             "trees": L3["trees"], "cyan": L3["cyan"]}, open("layers4.pkl", "wb"))

fig, ax = plt.subplots(figsize=(16, 12), dpi=140)
xs, ys = urban.exterior.xy
ax.add_patch(MP(list(zip(xs, ys)), closed=True, facecolor="#f3edda", edgecolor="orange", lw=1.2, zorder=1))
for p in road_polys:
    xs, ys = p.exterior.xy
    ax.add_patch(MP(list(zip(xs, ys)), closed=True, facecolor="#999", edgecolor="none", zorder=2))
for p in green_polys:
    xs, ys = p.exterior.xy
    ax.add_patch(MP(list(zip(xs, ys)), closed=True, facecolor="#7ab86f", edgecolor="none", zorder=3))
for i, b in enumerate(blocks):
    fc = "#e8b34c" if i == com_idx else "#bcd4f5"
    xs, ys = b.exterior.xy
    ax.add_patch(MP(list(zip(xs, ys)), closed=True, facecolor=fc, edgecolor="#3355aa", lw=.4, zorder=4, alpha=.9))
    c = b.centroid; ax.text(c.x, c.y, str(i), fontsize=6, ha="center", zorder=8)
for f in kept:
    xs, ys = f.exterior.xy
    ax.add_patch(MP(list(zip(xs, ys)), closed=True, facecolor="#d6e6b8", edgecolor="#557733", lw=.6, zorder=4))
ax.set_xlim(60, 760); ax.set_ylim(560, 20); ax.set_aspect("equal")
plt.tight_layout(); plt.savefig("debug5.png")
print("saved debug5.png")
