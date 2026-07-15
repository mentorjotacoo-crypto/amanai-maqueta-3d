import fitz, pickle, math
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union, polygonize
from shapely import minimum_rotated_rectangle
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

L = pickle.load(open("layers6.pkl", "rb"))
blocks = L["blocks"] + [L["comercio"]]  # comercio excluded later by area filter anyway
blocks = L["blocks"]

DIVS = {(0.4,0.4,0.4),(0.5,0.5,0.5),(0.25,0.25,0.25),(0.5,0.0,1.0),(0.72,0.0,0.72)}
dashes = []
for d in page.get_drawings():
    s = ck(d.get("color"))
    if s not in DIVS: continue
    for it in d["items"]:
        if it[0] == "l":
            a, b = T(it[1].x,it[1].y), T(it[2].x,it[2].y)
            if 0.02 < math.dist(a,b):
                dashes.append((a,b))
        elif it[0] == "qu" or it[0] == "c":
            ps = [T(p.x,p.y) for p in it[1:] if hasattr(p,"x")]
            for i in range(len(ps)-1):
                if math.dist(ps[i],ps[i+1]) > 0.02: dashes.append((ps[i],ps[i+1]))
print("purple-ish segments:", len(dashes))

# extend each dash to bridge gaps
G = 1.5
ext_lines = []
for a, b in dashes:
    dx, dy = b[0]-a[0], b[1]-a[1]
    Ln = math.hypot(dx, dy)
    if Ln < 0.02: continue
    ux, uy = dx/Ln, dy/Ln
    g = min(G, 2.5)
    ext_lines.append(LineString([(a[0]-ux*g, a[1]-uy*g), (b[0]+ux*g, b[1]+uy*g)]))

# block boundaries as closing frame
frames = []
for blk in blocks:
    frames.append(LineString(list(blk.exterior.coords)))

union = unary_union(ext_lines + frames)
faces = [f for f in polygonize(union)]
print("raw faces:", len(faces))

block_union = unary_union(blocks)
bp = prep(block_union)
lots_real = []
for f in faces:
    a = f.area * S * S
    if not (22 <= a <= 130): continue
    if not bp.contains(f.representative_point()): continue
    r = minimum_rotated_rectangle(f)
    xs, ys = r.exterior.xy
    e1 = math.dist((xs[0],ys[0]),(xs[1],ys[1])); e2 = math.dist((xs[1],ys[1]),(xs[2],ys[2]))
    if min(e1,e2) < 1: continue
    if max(e1,e2)/min(e1,e2) > 4.5: continue
    lots_real.append(f)
print("real lot faces:", len(lots_real))

# dedupe overlaps (keep larger)
lots_real.sort(key=lambda f: -f.area)
kept = []
ku = None
for f in lots_real:
    if ku is not None and f.intersection(ku).area > 0.35*f.area: continue
    kept.append(f)
    ku = unary_union([ku, f]) if ku is not None else f
print("deduped:", len(kept))

# coverage per block
cov = sum(f.area for f in kept) / sum(b.area for b in blocks)
print("coverage of blocks:", round(cov*100,1), "%")

per_block = []
for bi, blk in enumerate(blocks):
    pb = prep(blk.buffer(1))
    mine = [f for f in kept if pb.contains(f.representative_point())]
    ratio = sum(f.area for f in mine)/blk.area if blk.area else 0
    per_block.append((bi, len(mine), round(ratio*100)))
print("per block (idx, n, cov%):", per_block)

pickle.dump(kept, open("lots_real.pkl","wb"))

fig, ax = plt.subplots(figsize=(16,12), dpi=140)
for b in blocks:
    xs, ys = b.exterior.xy
    ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#eee", edgecolor="#888", lw=.5, zorder=1))
for f in kept:
    xs, ys = f.exterior.xy
    ax.add_patch(MP(list(zip(xs,ys)), closed=True, facecolor="#cfe3f7", edgecolor="#2a5fa5", lw=.4, zorder=2))
ax.set_xlim(60,760); ax.set_ylim(560,20); ax.set_aspect("equal")
plt.tight_layout(); plt.savefig("debug7.png")
print("saved debug7.png")
