import pickle, math
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP

L = pickle.load(open("layers.pkl", "rb"))
S = 5.5 / 10.4

def poly_ok(p):
    return p if p.is_valid else p.buffer(0)

road_polys = []
for ring in L["gray_rings"]:
    if len(ring) >= 3:
        try:
            p = poly_ok(Polygon(ring))
            if p.area > 2: road_polys.append(p)
        except Exception:
            pass
roads_union = unary_union(road_polys)

# ---- orange blob: dashed boundary -> band with interior hole; hatch -> thick core ----
blob = unary_union([seg.buffer(2.0) for seg in L["orange"]])
geoms = list(blob.geoms) if blob.geom_type == "MultiPolygon" else [blob]
geoms.sort(key=lambda g: -g.area)
print("orange blob geoms:", len(geoms), "areas_pt2:", [round(g.area) for g in geoms[:5]])
big = geoms[0]
print("interiors of biggest:", len(big.interiors), "areas m2:",
      sorted((round(abs(Polygon(r).area) * S * S) for r in big.interiors), reverse=True)[:5])

urban = None
best = 0
for g in geoms[:3]:
    for r in g.interiors:
        a = abs(Polygon(r).area)
        if a > best:
            best = a; urban = Polygon(r)
if urban: urban = urban.buffer(2.0)  # recover half band width
print("urban area m2:", round(urban.area * S * S) if urban else None)

core = blob.buffer(-3.5)
cg = list(core.geoms) if core.geom_type == "MultiPolygon" else [core]
cg = [c for c in cg if not c.is_empty]
cg.sort(key=lambda g: -g.area)
comercio = cg[0].buffer(3.5).simplify(1) if cg else None
print("comercio area m2:", round(comercio.area * S * S) if comercio else None)

blocks = []
if urban:
    carve = roads_union.buffer(0.6)
    if comercio: carve = unary_union([carve, comercio])
    diff = poly_ok(urban).difference(carve)
    geoms2 = list(diff.geoms) if diff.geom_type == "MultiPolygon" else [diff]
    blocks = [g for g in geoms2 if g.area * S * S > 60]
    blocks.sort(key=lambda g: -g.area)
    print("blocks:", len(blocks))
    print("block areas m2:", [round(b.area * S * S) for b in blocks])

pickle.dump({"roads": road_polys, "urban": urban, "comercio": comercio, "blocks": blocks},
            open("layers2.pkl", "wb"))

fig, ax = plt.subplots(figsize=(16, 12), dpi=140)
if urban:
    xs, ys = urban.exterior.xy
    ax.add_patch(MP(list(zip(xs, ys)), closed=True, facecolor="#f3edda", edgecolor="orange", lw=1.2, zorder=1))
for p in road_polys:
    xs, ys = p.exterior.xy
    ax.add_patch(MP(list(zip(xs, ys)), closed=True, facecolor="#999", edgecolor="none", zorder=2))
for i, b in enumerate(blocks):
    xs, ys = b.exterior.xy
    ax.add_patch(MP(list(zip(xs, ys)), closed=True, facecolor="#bcd4f5", edgecolor="#3355aa", lw=.4, zorder=3, alpha=.85))
    c = b.centroid
    ax.text(c.x, c.y, str(i), fontsize=5, ha="center", zorder=6)
if comercio:
    xs, ys = comercio.exterior.xy
    ax.add_patch(MP(list(zip(xs, ys)), closed=True, facecolor="#e8b34c", edgecolor="none", zorder=4, alpha=.9))
gp = L["green"][::30]
ax.scatter([p[0] for p in gp], [p[1] for p in gp], s=.3, c="#5a9a52", zorder=0)
ax.set_xlim(0, 792); ax.set_ylim(792, 0)
ax.set_aspect("equal"); plt.tight_layout(); plt.savefig("debug3.png")
print("saved debug3.png")
