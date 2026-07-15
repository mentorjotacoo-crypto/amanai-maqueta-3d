import fitz, json, math, collections, pickle
from shapely.geometry import LineString, MultiPoint, Point, Polygon, MultiLineString
from shapely.ops import polygonize, unary_union, linemerge

doc = fitz.open(r"C:\Users\Juan Camilo\Downloads\V.27 AMANAI.pdf")
page = doc[0]
print("rotation:", page.rotation)
RM = page.rotation_matrix  # maps unrotated point coords -> rotated (displayed) coords
def T(x, y):
    p = fitz.Point(x, y) * RM
    return (p.x, p.y)

draw = page.get_drawings()
def ck(c):
    return None if c is None else tuple(round(x, 2) for x in c)

GRAY_FILLS = {(0.9,0.9,0.9),(0.78,0.78,0.79)}
ORANGE = (1.0,0.5,0.0)
REDS = {(0.65,0.0,0.0),(1.0,0.0,0.0)}
GREEN_HATCH = {(0.54,0.72,0.0),(0.65,0.87,0.0),(0.75,1.0,0.0)}
CYAN = (0.0,0.72,0.72)

gray_rings, orange_lines, red_lines, green_mid, cyan_pts = [], [], [], [], []

def rings_from_items(items):
    """Rebuild closed rings from a path's consecutive 'l' segments."""
    rings, cur = [], []
    for it in items:
        if it[0] != "l":
            continue
        a, b = T(it[1].x, it[1].y), T(it[2].x, it[2].y)
        if cur and math.dist(cur[-1], a) > 0.5:
            if len(cur) >= 3: rings.append(cur)
            cur = []
        if not cur: cur.append(a)
        cur.append(b)
    if len(cur) >= 3: rings.append(cur)
    return rings

for d in draw:
    stroke, fill = ck(d.get("color")), ck(d.get("fill"))
    items = d["items"]
    if fill in GRAY_FILLS:
        gray_rings.extend(rings_from_items(items))
    if stroke == ORANGE:
        for it in items:
            if it[0] == "l":
                a, b = T(it[1].x,it[1].y), T(it[2].x,it[2].y)
                if math.dist(a,b) > 0.05: orange_lines.append(LineString([a,b]))
    if stroke in REDS:
        for it in items:
            if it[0] == "l":
                a, b = T(it[1].x,it[1].y), T(it[2].x,it[2].y)
                if math.dist(a,b) > 0.05: red_lines.append(LineString([a,b]))
    if stroke in GREEN_HATCH:
        for it in items:
            if it[0] == "l":
                a, b = T(it[1].x,it[1].y), T(it[2].x,it[2].y)
                green_mid.append(((a[0]+b[0])/2, (a[1]+b[1])/2))
    if stroke == CYAN:
        for it in items:
            for p in it[1:]:
                if hasattr(p, "x"):
                    q = T(p.x, p.y); cyan_pts.append(q)

print("gray rings:", len(gray_rings), "orange lines:", len(orange_lines),
      "red lines:", len(red_lines), "green pts:", len(green_mid))

# ---- scale from red dimension chains ----
red_m = linemerge(unary_union(red_lines))
chains = list(red_m.geoms) if red_m.geom_type == "MultiLineString" else [red_m]
chains = [c for c in chains if c.length > 40]
chains.sort(key=lambda c: -c.length)
print("longest red chains (len_pt, midpoint):")
for c in chains[:8]:
    mid = c.interpolate(0.5, normalized=True)
    print("  ", round(c.length,1), (round(mid.x), round(mid.y)))
pickle.dump({"gray_rings":gray_rings, "orange":orange_lines, "green":green_mid,
             "cyan":cyan_pts, "red_chains":[list(c.coords) for c in chains[:12]]},
            open("layers.pkl","wb"))
