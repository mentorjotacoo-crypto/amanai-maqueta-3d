# -*- coding: utf-8 -*-
import pickle, math, sys, collections
from shapely.geometry import LineString, Point
from shapely.ops import polygonize, unary_union, linemerge
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
segs=pickle.load(open('svg_segs.pkl','rb'))
def snap(p,g=0.05): return (round(p[0]/g)*g, round(p[1]/g)*g)
G=0.9
lines=[]
for a,b in segs:
    d=math.dist(a,b)
    ux,uy=(b[0]-a[0])/d,(b[1]-a[1])/d
    lines.append(LineString([snap((a[0]-ux*G,a[1]-uy*G)),snap((b[0]+ux*G,b[1]+uy*G))]))
u=unary_union(lines)
# grado de cada endpoint tras noding
deg=collections.Counter()
geoms=list(u.geoms) if u.geom_type=='MultiLineString' else [u]
for g in geoms:
    c=list(g.coords)
    for p in (c[0],c[-1]): deg[(round(p[0],2),round(p[1],2))]+=1
dangles=[p for p,n in deg.items() if n==1]
print('dangles:',len(dangles))
# emparejar dangles cercanos (greedy por distancia)
import numpy as np
from scipy.spatial import cKDTree
D=np.array(dangles)
tk=cKDTree(D)
pairs=[]
useda=set()
cand=sorted((math.dist(D[i],D[j]),i,j) for i,j in tk.query_pairs(7.0))
for dd,i,j in cand:
    if i in useda or j in useda: continue
    useda.add(i); useda.add(j); pairs.append((tuple(D[i]),tuple(D[j]),round(dd,2)))
print('puentes creados:',len(pairs))
bridges=[LineString([a,b]) for a,b,dd in pairs]
faces=[f for f in polygonize(unary_union(geoms+bridges)) if f.area>0.5]
print('faces:',len(faces))
W=pickle.load(open('plr_words.pkl','rb')); other=W['other']
letters=[(t,x,y) for t,x,y in other if len(t)==1 and t.isalpha() and t!='V']
mall=[(x,y) for t,x,y in other if t=='MALL'][0]
okL={}
for t,x,y in letters:
    for f in faces:
        if 400<f.area<12000 and f.contains(Point(x,y)): okL[t]=round(f.area); break
print('letras cerradas:',len(okL), dict(sorted(okL.items())))
mok=None
for f in faces:
    if 2000<f.area<20000 and f.contains(Point(*mall)): mok=round(f.area); break
S=0.48365
print('mall face pt2:',mok,'-> m2:',round(mok*S*S) if mok else None)
ncells=sum(1 for f in faces if 100<f.area<3500)
print('celdas rango lote:',ncells)
pickle.dump(faces, open('plr_faces4.pkl','wb'))
