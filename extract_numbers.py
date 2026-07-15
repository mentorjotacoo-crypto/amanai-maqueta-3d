import fitz, json, math, pickle
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from PIL import Image, ImageDraw

S = 5.5 / 10.4
L = pickle.load(open("layers6.pkl", "rb"))
CX, CY = L["urban"].centroid.x, L["urban"].centroid.y

doc = fitz.open(r"C:\Users\Juan Camilo\Downloads\V.27 AMANAI.pdf")
page = doc[0]
RM = page.rotation_matrix
def T(x, y):
    p = fitz.Point(x, y) * RM
    return (p.x, p.y)
def ck(c): return None if c is None else tuple(round(x,2) for x in c)

# cyan strokes
cyan_segs = []
for d in page.get_drawings():
    if ck(d.get("color")) != (0.0,0.72,0.72): continue
    for it in d["items"]:
        pts = [T(p.x,p.y) for p in it[1:] if hasattr(p,"x")]
        for i in range(len(pts)-1):
            cyan_segs.append((pts[i], pts[i+1]))
cyan = [((a[0]+b[0])/2, (a[1]+b[1])/2) for a,b in cyan_segs]
print("cyan segs:", len(cyan_segs))

# glyph clusters
u = unary_union([Point(p).buffer(1.0) for p in cyan])
glyphs = []
for g in (u.geoms if u.geom_type=="MultiPolygon" else [u]):
    b = g.bounds
    w, h = b[2]-b[0], b[3]-b[1]
    if h <= 7.5 and w <= 14 and h >= 1.5:
        glyphs.append(b)
print("small glyph clusters:", len(glyphs))

PLAN = json.loads(open("plan_data.js").read()[len("var PLAN="):-1])
def m2pt(p):  # meters -> pdf pt
    return (p[0]/S + CX, p[1]/S + CY)

lots = PLAN["lots"]
polys = [Polygon([m2pt(q) for q in lot["p"]]) for lot in lots]
lot_glyphs = [[] for _ in lots]
for gb in glyphs:
    c = Point((gb[0]+gb[2])/2, (gb[1]+gb[3])/2)
    for i, poly in enumerate(polys):
        if c.within(poly):
            lot_glyphs[i].append(gb); break
have = sum(1 for g in lot_glyphs if g)
print("lots with glyphs:", have, "/", len(lots))

# contact sheets per manzana
Z = 8
pixfull = page.get_pixmap(matrix=fitz.Matrix(Z, Z))
BIG = Image.frombytes("RGB", (pixfull.width, pixfull.height), pixfull.samples)
print("big render:", BIG.size)
mzs = {}
for i, lot in enumerate(lots): mzs.setdefault(lot["mz"], []).append(i)
inv = ~RM  # rotated -> unrotated coords for clip
sheets = []
order = ["MZ 1","MZ 2","MZ 3","MZ 4","MZ 5","MZ 6","MZ 7","MZ 8","MZ 9","MZ 10","MZ 11",
         "MZ 12","MZ 13","MZ 14","MZ 15","MZ 16","MZ 17","MZ 18","MZ 19","MZ 20","MZ 21"]
TW, TH, COLS = 150, 110, 8
group, gi = [], 1
def flush(group, gi):
    rows = []
    for mz in group:
        idxs = sorted(mzs[mz], key=lambda i: lots[i]["n"])
        rows.append((mz, idxs))
    total_rows = sum(1 + (len(ix)+COLS-1)//COLS for _, ix in rows)
    img = Image.new("RGB", (COLS*TW, total_rows*TH), (255,255,255))
    dr = ImageDraw.Draw(img)
    y = 0
    for mz, idxs in rows:
        dr.rectangle([0, y, COLS*TW, y+28], fill=(31,91,65))
        dr.text((8, y+6), mz + "  (ref 1.." + str(len(idxs)) + ")", fill=(255,255,255))
        y += 32
        x = 0; col = 0
        for i in idxs:
            gbs = lot_glyphs[i]
            if gbs:
                x0 = min(g[0] for g in gbs)-1.0; y0 = min(g[1] for g in gbs)-1.0
                x1 = max(g[2] for g in gbs)+1.0; y1 = max(g[3] for g in gbs)+1.0
                segs = [(a,b) for a,b in cyan_segs
                        if x0 <= (a[0]+b[0])/2 <= x1 and y0 <= (a[1]+b[1])/2 <= y1]
                ZT = min((TW-14)/(x1-x0), (TH-38)/(y1-y0))
                tile = Image.new("RGB", (int((x1-x0)*ZT)+2, int((y1-y0)*ZT)+2), (255,255,255))
                td = ImageDraw.Draw(tile)
                for a,b in segs:
                    td.line([(a[0]-x0)*ZT, (a[1]-y0)*ZT, (b[0]-x0)*ZT, (b[1]-y0)*ZT], fill=(10,10,10), width=3)
            else:
                tile = Image.new("RGB", (60, 40), (250,240,240))
            img.paste(tile, (x+5, y+26))
            dr.text((x+5, y+4), "ref "+str(lots[i]["n"]), fill=(180,0,0))
            dr.rectangle([x, y, x+TW-1, y+TH-1], outline=(210,210,210))
            col += 1; x += TW
            if col == COLS: col = 0; x = 0; y += TH
        if col != 0: y += TH
    name = f"nums_sheet_{gi}.png"
    img.save(name)
    print("saved", name, img.size)

count = 0
for mz in order:
    group.append(mz)
    count += len(mzs.get(mz, []))
    if count >= 55:
        flush(group, gi); gi += 1; group = []; count = 0
if group: flush(group, gi)
