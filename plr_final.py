# -*- coding: utf-8 -*-
import pickle, json, math, sys, collections
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

W=pickle.load(open('plr_words.pkl','rb'))
faces=pickle.load(open('plr_faces.pkl','rb'))
nums=W['nums']; other=W['other']
mz_words=[(x,y) for t,x,y in other if t=='MZ']
used=set(); mz_labels=[]
for mx,my in mz_words:
    best=None;bd=1e9
    for i,(v,x,y) in enumerate(nums):
        if i in used: continue
        dx=x-mx; dy=abs(y-my)
        if 0<dx<22 and dy<5 and dx+dy<bd: bd,best=dx+dy,i
    if best is not None:
        used.add(best); v,x,y=nums[best]; mz_labels.append((f'MZ {v}',(mx+x)/2,(my+y)/2))
Vpos=np.array([(x,y) for t,x,y in other if t=='V'])
tv=cKDTree(Vpos)
lot_nums=[]
for i,(v,x,y) in enumerate(nums):
    if i in used: continue
    dd,_=tv.query([x,y])
    if dd<7: continue
    lot_nums.append((v,x,y))
P=np.array([(x,y) for v,x,y in lot_nums]); VN=[v for v,_,_ in lot_nums]

d=json.loads(open('plan_data_pre_plr.js').read()[len('var PLAN='):-1])
OLDNEW={1:1,2:2,3:3,4:4,5:5,6:6,7:6,8:6,9:6,10:6,21:6,11:7,12:8,13:9,14:10,15:11,16:12,17:13,18:14,19:15,20:16}
newmz=[f"MZ {OLDNEW[int(l['mz'].replace('MZ ',''))]}" for l in d['lots']]
# lotes oficiales unicamente (excluir S/N: fantasmas y astillas que causan aliasing en el ICP)
oficial=[l['n']!='SN' for l in d['lots']]
C=np.array([l['c'] for l in d['lots']])
def pip(pts,x,z):
    inside=False
    for i in range(len(pts)):
        x1,z1=pts[i]; x2,z2=pts[i-1]
        if (z1>z)!=(z2>z) and x<(x2-x1)*(z-z1)/(z2-z1)+x1: inside=not inside
    return inside

# grupo MZ6 = numeros dentro del face que contiene el rotulo MZ 6
mz6=[l for l in mz_labels if l[0]=='MZ 6'][0]
face6=None
for f in faces:
    if f.area>300 and f.contains(Point(mz6[1],mz6[2])): face6=f; break
in6=[k for k in range(len(P)) if face6.contains(Point(P[k]))]
print('numeros en face MZ6:', len(in6))

# clusters (como match6) para el resto
tp=cKDTree(P)
par=list(range(len(P)))
def find(a):
    while par[a]!=a: par[a]=par[par[a]]; a=par[a]
    return a
for i,j in tp.query_pairs(13.0):
    ri,rj=find(i),find(j)
    if ri!=rj: par[ri]=rj
clusters=collections.defaultdict(list)
in6set=set(in6)
for i in range(len(P)):
    if i not in in6set: clusters[find(i)].append(i)
Lpos=[(nm,x,y) for nm,x,y in mz_labels if nm!='MZ 6']
groups=collections.defaultdict(list)
groups['MZ 6']=in6
resto=[]
for cid,members in clusters.items():
    mem=[m for m in members if m not in in6set]
    if not mem: continue
    dmin=1e9; best=None
    for nm,lx,ly in Lpos:
        dd=min(np.hypot(P[m][0]-lx,P[m][1]-ly) for m in mem)
        if dd<dmin: dmin,best=dd,nm
    if dmin<28: groups[best].extend(mem)
    else: resto.extend(mem)
print('grupos:', {k:len(v) for k,v in sorted(groups.items(),key=lambda z:int(z[0].split()[1]))}, '| resto:',len(resto))

S0=0.4885
fits={}; out={}
for nm,members in groups.items():
    idxs=[i for i in range(len(C)) if newmz[i]==nm and oficial[i]]
    if not idxs or not members: continue
    Pm=P[members]; Cm=C[idxs]; tcm=cKDTree(Cm)
    s=S0; R=np.eye(2); b=Cm.mean(0)-s*Pm.mean(0)
    for it in range(6):
        Q=s*(Pm@R.T)+b
        dist,ii=tcm.query(Q)
        thr=[10,7,5,3.5,2.5,2][it]
        m=dist<thr
        if m.sum()<3: break
        A=Pm[m]; B=Cm[ii[m]]
        Am=A-A.mean(0); Bm=B-B.mean(0)
        U,Sv,Vt=np.linalg.svd(Am.T@Bm)
        Rn=(U@Vt).T
        if np.linalg.det(Rn)<0: Vt[-1]*=-1; Rn=(U@Vt).T
        den=np.trace(Am.T@Am)
        s=np.trace(np.diag(Sv))/den if den>0 else s
        R=Rn; b=B.mean(0)-s*(A.mean(0)@R.T)
    fits[nm]=(s,R,b,idxs)
    Q=s*(Pm@R.T)+b
    dist,ii=tcm.query(Q)
    for k,mem in enumerate(members):
        i=idxs[ii[k]]
        if pip(d['lots'][i]['p'],Q[k][0],Q[k][1]) or dist[k]<2.5:
            if i in out and out[i][2]<=dist[k]: continue
            out[i]=(nm,VN[mem],dist[k])
# rescate: numeros no asignados prueban todos los fits
assigned_nums=collections.defaultdict(set)
for i,(nm,v,dd) in out.items(): assigned_nums[nm].add(v)
rescued=0
for k in range(len(P)):
    already=False
    for i,(nm,v,dd) in out.items():
        pass
    # esta k asignado? construir set de (miembro->asignado) seria mejor; aproximamos: si su valor+posicion ya presentes, saltar
for nm2,(s,R,b,idxs) in fits.items():
    pass
# construir lista de indices PLR no usados
used_pairs=set()
for i,(nm,v,dd) in out.items(): used_pairs.add((nm,v))
un=[]
for k in range(len(P)):
    # se asigno? un numero se identifica por posicion; recomputar: probar si quedo en out con su valor y mz de grupo
    pass
# mas simple: repetir asignacion y registrar cuales k quedaron sin lote
kk_assigned=set()
for nm,members in groups.items():
    if nm not in fits: continue
    s,R,b,idxs=fits[nm]
    Cm=C[idxs]; tcm=cKDTree(Cm)
    Q=s*(P[members]@R.T)+b
    dist,ii=tcm.query(Q)
    for k2,mem in enumerate(members):
        i=idxs[ii[k2]]
        if (pip(d['lots'][i]['p'],Q[k2][0],Q[k2][1]) or dist[k2]<2.5) and i in out and out[i][1]==VN[mem]:
            kk_assigned.add(mem)
pend=[k for k in range(len(P)) if k not in kk_assigned]
for k in pend:
    best=None; bd=1e9
    for nm,(s,R,b,idxs) in fits.items():
        q=s*(P[k]@R.T)+b
        for i in idxs:
            c=C[i]
            dd=math.hypot(q[0]-c[0],q[1]-c[1])
            if dd<6 and (pip(d['lots'][i]['p'],q[0],q[1]) or dd<3.5):
                if dd<bd: bd,best=dd,(nm,i)
    if best:
        nm,i=best
        if i not in out:
            out[i]=(nm,VN[k],bd); rescued+=1
print('rescatados:',rescued)
final={i:(nm,v) for i,(nm,v,dd) in out.items()}
seen=collections.defaultdict(list)
for i,(nm,v) in final.items(): seen[nm].append(v)
tot=0
for nm in sorted(seen,key=lambda z:int(z.split()[1])):
    vals=sorted(seen[nm]); tot+=len(vals)
    dup=[v for v,c in collections.Counter(vals).items() if c>1]
    falt=[v for v in range(1,max(vals)+1) if v not in vals]
    print(f'  {nm}: n={len(vals)} 1..{max(vals)} faltan={falt[:8]} dup={dup}')
print('TOTAL:',tot,'de',len(P))
json.dump({str(k):v for k,v in final.items()}, open('plr_map.json','w'))
mzout=[]
for nm,x,y in mz_labels:
    if nm in fits:
        s,R,b,_=fits[nm]
        q=s*(np.array([x,y])@R.T)+b
        mzout.append({'t':nm,'c':[round(float(q[0]),1),round(float(q[1]),1)]})
# letras: transformar con el fit de la manzana con numeros mas cercanos (fits exactos)
def tr_local(x,y):
    best=None; bd=1e18
    for nm,(s,R,b,idxs) in fits.items():
        mem=groups.get(nm,[])
        if not mem: continue
        dd=min((P[m][0]-x)**2+(P[m][1]-y)**2 for m in mem)
        if dd<bd: bd,best=dd,nm
    s,R,b,_=fits[best]
    q=s*(np.array([x,y])@R.T)+b
    return [round(float(q[0]),1),round(float(q[1]),1)]
def trg(x,y): return tr_local(x,y)
letters=[(t2,x,y) for t2,x,y in other if len(t2)==1 and t2.isalpha() and t2!='V']
mall=[(x,y) for t2,x,y in other if t2=='MALL']
json.dump({'mz':mzout,'lote':[{'t':f'Lote {t}','c':trg(x,y)} for t,x,y in letters],
           'mall':trg(*mall[0]) if mall else None}, open('plr_labels.json','w'))
print('labels:',len(mzout))
