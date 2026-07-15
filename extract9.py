import fitz, pickle, math, json
from shapely.geometry import LineString, Polygon, Point, box
from shapely.ops import unary_union
import matplotlib
matplotlib.use("Agg")

S = 5.5 / 10.4
doc = fitz.open(r"C:\Users\Juan Camilo\Downloads\V.27 AMANAI.pdf")
page = doc[0]
RM = page.rotation_matrix
def T(x, y):
    p = fitz.Point(x, y) * RM
    return (p.x, p.y)
def ck(c): return None if c is None else tuple(round(x,2) for x in c)

L = pickle.load(open("layers5.pkl", "rb"))
calz, anden, greens = L["calz"], L["anden"], L["greens"]
urban, blocks, lots, perims = L["urban"], L["blocks"], L["lots"], L["perims"]

# 1) comercio = block containing the label point
cpt = Point(235, 234)
com_idx = next(i for i, b in enumerate(blocks) if cpt.within(b))
comercio = blocks[com_idx]
print("comercio block:", com_idx, "area m2:", round(comercio.area*S*S))
blocks = [b for i, b in enumerate(blocks) if i != com_idx]
lots = [l for i, l in enumerate(lots) if i != com_idx]

# 2) recollect hatch/trees/orange from pdf
orange_segs, tree_pts, hatch_pts = [], [], []
TREE_COLORS = {(0.36,0.72,0.0),(0.34,0.45,0.0),(0.44,0.58,0.0)}
HATCH = {(0.54,0.72,0.0),(0.65,0.87,0.0),(0.75,1.0,0.0)}
for d in doc[0].get_drawings():
    s = ck(d.get("color"))
    for it in d["items"]:
        if it[0] != "l": continue
        a, b = T(it[1].x,it[1].y), T(it[2].x,it[2].y)
        if s == (1.0,0.5,0.0) and math.dist(a,b) > 0.05: orange_segs.append((a,b))
        elif s in TREE_COLORS: tree_pts.append(((a[0]+b[0])/2,(a[1]+b[1])/2))
        elif s in HATCH: hatch_pts.append(((a[0]+b[0])/2,(a[1]+b[1])/2))

# southern band = interior of 2nd orange ring
blob = unary_union([LineString(x).buffer(2.0) for x in orange_segs])
geoms = sorted(blob.geoms, key=lambda g: -g.area)
band = None
for g in geoms:
    c = g.centroid
    if g.interiors and not c.within(urban) and c.y > 350:
        band = max((Polygon(r) for r in g.interiors), key=lambda p: p.area).buffer(2.0)
        break
if band is None:
    g = geoms[1]
    band = max((Polygon(r) for r in g.interiors), key=lambda p: p.area).buffer(2.0)
print("band m2:", round(band.area*S*S))

# 3) terrain = hatch blobs + urban + band merged
hb = unary_union([Point(p).buffer(16) for p in hatch_pts[::3]])
terrain = unary_union([hb, urban.buffer(8), band.buffer(8)])
tg = sorted((terrain.geoms if terrain.geom_type=="MultiPolygon" else [terrain]), key=lambda g:-g.area)
terrain = tg[0].buffer(-6).simplify(2)
if terrain.geom_type == "MultiPolygon": terrain = max(terrain.geoms, key=lambda g:g.area)
print("terrain m2:", round(terrain.area*S*S))

# 4) trees: cluster small, split elongated blobs on grid
tb = unary_union([Point(p).buffer(1.4) for p in tree_pts])
trees = []
for g in (tb.geoms if tb.geom_type=="MultiPolygon" else [tb]):
    b = g.bounds
    if max(b[2]-b[0], b[3]-b[1]) <= 14:
        c = g.centroid; trees.append((c.x, c.y))
    else:
        step = 11
        y = b[1]
        while y < b[3]:
            x = b[0]
            while x < b[2]:
                cell = box(x, y, x+step, y+step).intersection(g)
                if not cell.is_empty and cell.area > 3:
                    c = cell.centroid; trees.append((c.x, c.y))
                x += step
            y += step
print("trees:", len(trees))

# hatch scatter sample for ground texture (thinned, outside urban/band)
seen = set(); scatter = []
for p in hatch_pts:
    k = (round(p[0]/14), round(p[1]/14))
    if k in seen: continue
    seen.add(k); scatter.append(p)
print("scatter:", len(scatter))

# 5) cyan label clusters -> contact sheet
cl = [c for c in L["cyan"] if 8 < (c[2]-c[0]) < 70 and 3 < (c[3]-c[1]) < 22]
# merge near-duplicates
merged = []
for c in cl:
    cx, cy = (c[0]+c[2])/2, (c[1]+c[3])/2
    if any(abs(cx-m[0]) < 12 and abs(cy-m[1]) < 8 for m in merged): continue
    merged.append((cx, cy, c))
print("label candidates:", len(merged))

Z = 4
pix = page.get_pixmap(matrix=fitz.Matrix(Z, Z))
pix.save("render4x.png")
from PIL import Image, ImageDraw
img = Image.open("render4x.png")
PAD = 14
tiles = []
for i, (cx, cy, c) in enumerate(merged):
    x0, y0, x1, y1 = [v*Z for v in c]
    tile = img.crop((max(0,int(x0-PAD)), max(0,int(y0-PAD)), int(x1+PAD), int(y1+PAD)))
    tiles.append((i, tile))
COLS = 6
tw = max(t.width for _, t in tiles) + 8
th = max(t.height for _, t in tiles) + 26
rows = (len(tiles)+COLS-1)//COLS
sheet = Image.new("RGB", (COLS*tw, rows*th), (255,255,255))
dr = ImageDraw.Draw(sheet)
for i, tile in tiles:
    r, cc = divmod(i, COLS)
    sheet.paste(tile, (cc*tw+4, r*th+22))
    dr.text((cc*tw+4, r*th+3), f"#{i}", fill=(180,0,0))
    dr.rectangle([cc*tw, r*th, cc*tw+tw-1, r*th+th-1], outline=(200,200,200))
sheet.save("labels_sheet.png")
print("sheet:", sheet.size)

pickle.dump({"calz":calz,"anden":anden,"greens":greens,"urban":urban,"comercio":comercio,
             "blocks":blocks,"lots":lots,"perims":perims,"trees":trees,"terrain":terrain,
             "band":band,"scatter":scatter,"label_pos":[(m[0],m[1]) for m in merged]},
            open("layers6.pkl","wb"))
print("saved layers6.pkl")
