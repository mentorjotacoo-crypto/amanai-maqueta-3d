# -*- coding: utf-8 -*-
import re, math, sys, pickle
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
svg=open('plr.svg',encoding='utf-8').read()
# parsear elementos path con transform opcional (los de defs/symbol tienen d en 0..1 => glifos, saltarlos por bbox)
segs=[]
# capturar cada <path ...> con atributos
for m in re.finditer(r'<path([^>]+)>', svg):
    attrs=m.group(1)
    dm=re.search(r'\bd="([^"]+)"', attrs)
    if not dm: continue
    d=dm.group(1)
    tm=re.search(r'transform="matrix\(([^)]+)\)"', attrs)
    if tm:
        a,b,c,dd,e,f=[float(x) for x in tm.group(1).split(',')]
    else:
        a,b,c,dd,e,f=1,0,0,1,0,0
    def ap(x,y): return (a*x+c*y+e, b*x+dd*y+f)
    # parser de d: M L H V Z (y C aproximada por extremos)
    toks=re.findall(r'([MLHVCZmlhvcz])|(-?\d*\.?\d+(?:e-?\d+)?)', d)
    pts=[]; cur=None; start=None; cmd=None; buf=[]
    def flush_seg(p1,p2):
        segs.append((ap(*p1),ap(*p2)))
    i=0
    nums=[]
    seq=[]
    for t in toks:
        if t[0]: seq.append(('cmd',t[0]))
        else: seq.append(('num',float(t[1])))
    idx=0
    cur=None; start=None
    while idx<len(seq):
        k,v=seq[idx]
        if k=='cmd':
            cmd=v; idx+=1
            if cmd in 'Zz' and cur and start and cur!=start:
                flush_seg(cur,start); cur=start
            continue
        # numeros segun cmd
        if cmd in 'ML':
            x=v; y=seq[idx+1][1]; idx+=2
            p=(x,y)
            if cmd=='L' and cur: flush_seg(cur,p)
            if cmd=='M': start=p
            cur=p; cmd='L' if cmd=='M' else cmd
        elif cmd=='H':
            x=v; idx+=1
            p=(x,cur[1]); flush_seg(cur,p); cur=p
        elif cmd=='V':
            y=v; idx+=1
            p=(cur[0],y); flush_seg(cur,p); cur=p
        elif cmd=='C':
            xs=[v]+[seq[idx+j][1] for j in range(1,6)]; idx+=6
            p=(xs[4],xs[5]); flush_seg(cur,p); cur=p
        else:
            idx+=1
print('segmentos SVG:', len(segs))
# filtrar glifos: segmentos diminutos (<0.5pt) fuera... y clips gigantes
segs=[(p,q) for p,q in segs if 0.05<math.dist(p,q)<5000]
print('tras filtro:', len(segs))
pickle.dump(segs, open('svg_segs.pkl','wb'))
# el SVG está en espacio display? el viewBox:
vb=re.search(r'viewBox="([^"]+)"', svg)
print('viewBox:', vb.group(1) if vb else None)
# plot zona MZ2: en SVG display space la pagina es 842x595? probar bbox de todo
xs=[p[0] for p,q in segs]+[q[0] for p,q in segs]
ys=[p[1] for p,q in segs]+[q[1] for p,q in segs]
print('bbox:', min(xs),max(xs),min(ys),max(ys))
fig,ax=plt.subplots(figsize=(10,9),dpi=130)
n=0
for p,q in segs:
    if 340<p[0]<480 and 80<p[1]<210:
        ax.plot([p[0],q[0]],[p[1],q[1]],'k-',lw=.7); n+=1
ax.set_xlim(340,480); ax.set_ylim(210,80); ax.set_aspect('equal'); ax.set_title(f'SVG zona MZ2: {n} segs')
plt.savefig('svg_mz2.png'); print('zona MZ2 segs:', n)
