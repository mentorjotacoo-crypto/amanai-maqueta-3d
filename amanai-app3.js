/* Reservas de Amanai — maqueta 3D fiel al plano V.27 (geometría extraída del PDF) */
(function(){
'use strict';

var seed = 20260713;
function rnd(){ seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; }
var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

var COL = {
  sky:0xdfe8e0, groundFar:0xccd5bc, proteccion:0x8fb083, urbano:0xe7e1cf, band:0xefe9d6,
  calz:0x6e6b63, anden:0xc9c5b6, grass:0x8fb479,
  lot:0xf4efe2, perim:0xdce3c4, comercio:0xd9a441,
  wall:0xfaf6ec, roofClay:0xb9714f, roofSage:0x8fa08b,
  trunk:0x8a6e4b, leaf1:0x5f8a5a, leaf2:0x77a06b, leaf3:0x4e7a52,
  disponible:0xbcd79b, reservado:0xe9c46a, vendido:0xc96f57
};

var canvas = document.getElementById('scene');
var renderer = new THREE.WebGLRenderer({canvas:canvas, antialias:true});
renderer.setPixelRatio(Math.min(window.devicePixelRatio||1, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.18;

var scene = new THREE.Scene();
scene.background = new THREE.Color(COL.sky);
scene.fog = new THREE.Fog(COL.sky, 700, 1500);
var camera = new THREE.PerspectiveCamera(46, 1, 1, 4000);

scene.add(new THREE.HemisphereLight(0xf2f7ee, 0x9aa284, 0.85));
var sun = new THREE.DirectionalLight(0xfff3dd, 1.55);
sun.position.set(-220, 340, -160);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -280; sun.shadow.camera.right = 280;
sun.shadow.camera.top = 280; sun.shadow.camera.bottom = -280;
sun.shadow.camera.far = 1100;
sun.shadow.bias = -0.0006;
scene.add(sun);

var world = new THREE.Group();
scene.add(world);

function mat(hex, rough){ return new THREE.MeshStandardMaterial({color:hex, roughness:(rough==null?0.93:rough), metalness:0}); }
var tmpC = new THREE.Color();

/* shape helpers: data coords are [x, ySouth] meters; world x=x, z=ySouth */
function shapeFrom(pts){
  var s = new THREE.Shape();
  s.moveTo(pts[0][0], -pts[0][1]);
  for (var i=1;i<pts.length;i++) s.lineTo(pts[i][0], -pts[i][1]);
  s.closePath();
  return s;
}
function shapeObj(o){
  var s = shapeFrom(o.e);
  if (o.h) o.h.forEach(function(hpts){
    var hp = new THREE.Path();
    hp.moveTo(hpts[0][0], -hpts[0][1]);
    for (var i=1;i<hpts.length;i++) hp.lineTo(hpts[i][0], -hpts[i][1]);
    hp.closePath();
    s.holes.push(hp);
  });
  return s;
}
function extrudeLayer(objs, depth, color, y, rough){
  var shapes = objs.map(shapeObj);
  var g = new THREE.ExtrudeGeometry(shapes, {depth:depth, bevelEnabled:false});
  var m = new THREE.Mesh(g, mat(color, rough));
  m.rotation.x = -Math.PI/2;
  m.position.y = y;
  m.receiveShadow = true;
  world.add(m);
  return m;
}

/* ---------- capas del plano ---------- */
var ground = new THREE.Mesh(new THREE.PlaneGeometry(2200,2200), mat(COL.groundFar,1));
ground.rotation.x = -Math.PI/2; ground.position.y = -0.42; ground.receiveShadow = true;
world.add(ground);

extrudeLayer([PLAN.terrain], 0.5, COL.proteccion, 0, 1);
extrudeLayer([PLAN.band], 0.28, COL.band, 0.5, 0.97);
extrudeLayer([PLAN.urban], 0.3, COL.urbano, 0.5, 0.96);
var BASE = 0.8;
extrudeLayer(PLAN.calz, 0.22, COL.calz, BASE, 0.98);
extrudeLayer(PLAN.anden, 0.26, COL.anden, BASE, 0.95);
extrudeLayer(PLAN.greens, 0.24, COL.grass, BASE, 1);

var comercioMesh = extrudeLayer([PLAN.comercio], 0.4, COL.comercio, BASE, 0.88);
comercioMesh.castShadow = true;
comercioMesh.userData = {comercio:true};

/* edificios de comercio */
(function(){
  var cpts = PLAN.comercio.e;
  var cx=0, cz=0;
  cpts.forEach(function(p){ cx+=p[0]; cz+=p[1]; });
  cx/=cpts.length; cz/=cpts.length;
  [[cx-6, cz+2, 11, 4.6, 17, 1.05],[cx+7, cz-9, 13, 3.6, 9, 1.05]].forEach(function(bd){
    var b = new THREE.Mesh(new THREE.BoxGeometry(bd[2],bd[3],bd[4]), mat(COL.wall,0.85));
    b.position.set(bd[0], BASE+0.4+bd[3]/2, bd[1]); b.rotation.y = bd[5];
    b.castShadow = b.receiveShadow = true; world.add(b);
    var r = new THREE.Mesh(new THREE.BoxGeometry(bd[2]+0.8,0.45,bd[4]+0.8), mat(COL.comercio,0.8));
    r.position.set(bd[0], BASE+0.4+bd[3]+0.22, bd[1]); r.rotation.y = bd[5]; r.castShadow = true; world.add(r);
  });
})();

/* ---------- lotes de vivienda: geometría fusionada con color por vértice ---------- */
var lotRanges = [], lotBBox = [];
var lotMesh = (function(){
  var posA = [], normA = [], colA = [];
  var base = new THREE.Color(COL.lot);
  PLAN.lots.forEach(function(lot, i){
    var g = new THREE.ExtrudeGeometry(shapeFrom(lot.p), {depth:0.32, bevelEnabled:false});
    g.rotateX(-Math.PI/2);
    g.translate(0, BASE, 0);
    if (g.index) g = g.toNonIndexed();
    var p = g.attributes.position.array, n = g.attributes.normal.array;
    var start = posA.length/3;
    for (var k=0;k<p.length;k++){ posA.push(p[k]); normA.push(n[k]); }
    tmpC.copy(base).offsetHSL(0,0,(rnd()-0.5)*0.04);
    for (k=0;k<p.length/3;k++){ colA.push(tmpC.r, tmpC.g, tmpC.b); }
    lotRanges.push({start:start, count:p.length/3, color:tmpC.clone()});
    var xs = lot.p.map(function(q){return q[0];}), zs = lot.p.map(function(q){return q[1];});
    lotBBox.push([Math.min.apply(null,xs), Math.max.apply(null,xs), Math.min.apply(null,zs), Math.max.apply(null,zs)]);
    g.dispose();
  });
  var geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(posA,3));
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(normA,3));
  geo.setAttribute('color', new THREE.Float32BufferAttribute(colA,3));
  var m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({vertexColors:true, roughness:0.9, metalness:0}));
  m.receiveShadow = true;
  world.add(m);
  return m;
})();
document.getElementById('stLots').textContent = '332'; /* inventario oficial OPCION V4 */

function paintLot(i, color){
  var r = lotRanges[i], arr = lotMesh.geometry.attributes.color.array;
  for (var k=0;k<r.count;k++){
    arr[(r.start+k)*3] = color.r; arr[(r.start+k)*3+1] = color.g; arr[(r.start+k)*3+2] = color.b;
  }
  lotMesh.geometry.attributes.color.needsUpdate = true;
}
function pointInPoly(pts, x, z){
  var inside = false;
  for (var i=0, j=pts.length-1; i<pts.length; j=i++){
    var xi=pts[i][0], zi=pts[i][1], xj=pts[j][0], zj=pts[j][1];
    if ((zi>z)!==(zj>z) && x < (xj-xi)*(z-zi)/(zj-zi)+xi) inside = !inside;
  }
  return inside;
}
function lotAt(x, z){
  var best = -1, bd = 1e18;
  for (var i=0;i<PLAN.lots.length;i++){
    var b = lotBBox[i];
    if (x<b[0]||x>b[1]||z<b[2]||z>b[3]) continue;
    if (!pointInPoly(PLAN.lots[i].p, x, z)) continue;
    var c = PLAN.lots[i].c;
    var d = (x-c[0])*(x-c[0]) + (z-c[1])*(z-c[1]);
    if (d < bd){ bd = d; best = i; }
  }
  return best;
}

/* estados demo */
var estados = PLAN.lots.map(function(){ var r = rnd(); return r<0.55?0:(r<0.7?1:2); });
var EST_NAMES = ['Disponible','Reservado','Vendido'];
var EST_COLORS = [new THREE.Color(COL.disponible), new THREE.Color(COL.reservado), new THREE.Color(COL.vendido)];
var estadosOn = false;
var esqOn = false;
var ESQ_COLORS = {T1: new THREE.Color(0xc96b57), T2: new THREE.Color(0xe5a15c)};
function repaintAll(){
  for (var i=0;i<PLAN.lots.length;i++) paintLot(i, lotColor(i));
}

/* ---------- casas ---------- */
var houses = new THREE.Group(); world.add(houses);
(function(){
  function prismGeo(w, h, L){
    var hw=w/2, hl=L/2;
    var v = [
      -hl,0,-hw,  -hl,0,hw,  -hl,h,0,
       hl,0,-hw,   hl,h,0,   hl,0,hw,
      -hl,0,-hw,  -hl,h,0,   hl,h,0,  -hl,0,-hw,  hl,h,0,  hl,0,-hw,
      -hl,0, hw,   hl,0,hw,  hl,h,0,  -hl,0, hw,  hl,h,0, -hl,h,0
    ];
    var g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(v,3));
    g.computeVertexNormals();
    return g;
  }
  /* solo lotes rectangulares estándar con número oficial; el frente mira a la vía */
  var spots = [];
  PLAN.lots.forEach(function(lot){
    if (lot.n !== 'SN' && lot.w >= 4.6 && lot.w <= 6.6 && lot.d >= 8.6 && lot.d <= 11.5 &&
        lot.area >= 46 && rnd() < 0.6) spots.push(lot);
  });
  /* eje dominante por manzana: en la banda norte se alinean las casas de lotes torcidos */
  var mzAxis = {};
  (function(){
    var acc = {};
    PLAN.lots.forEach(function(l){
      if (l.n === 'SN') return;
      var a2 = -2*l.a;
      (acc[l.mz] = acc[l.mz] || [0,0]);
      acc[l.mz][0] += Math.cos(a2); acc[l.mz][1] += Math.sin(a2);
    });
    for (var k in acc) mzAxis[k] = Math.atan2(acc[k][1], acc[k][0]) / 2;
  })();
  var SNAP_MZ = {'MZ 1':1,'MZ 2':1,'MZ 3':1,'MZ 4':1,'MZ 5':1,'MZ 21':1};
  function axDiff(a,b){ var d = Math.abs((a-b) % Math.PI); return Math.min(d, Math.PI-d); }
  var HL = 6.4, HW = 4.1; /* fondo (X, hacia la vía) x frente (Z) */
  var bodyG = new THREE.BoxGeometry(HL, 1, HW);
  var body = new THREE.InstancedMesh(bodyG, mat(COL.wall, 0.85), spots.length);
  var roofG = prismGeo(4.5, 1.6, 6.9);
  var roof = new THREE.InstancedMesh(roofG, mat(COL.roofClay, 0.8), spots.length);
  var doorG = new THREE.BoxGeometry(0.1, 2.05, 0.95);
  var door = new THREE.InstancedMesh(doorG, mat(0x6b4a32, 0.8), spots.length);
  var winG = new THREE.BoxGeometry(0.1, 1.05, 1.5);
  var win = new THREE.InstancedMesh(winG, new THREE.MeshStandardMaterial({color:0x9fb9c4, roughness:0.35, metalness:0.15}), spots.length);
  var q = new THREE.Quaternion(), up = new THREE.Vector3(0,1,0);
  var pos = new THREE.Vector3(), sc = new THREE.Vector3(), m4 = new THREE.Matrix4();
  function angDiff(a, b){ return Math.abs(Math.atan2(Math.sin(a-b), Math.cos(a-b))); }
  for (var i=0;i<spots.length;i++){
    var sp = spots[i], two = rnd() < 0.3;
    var h = two ? 4.7 : 2.9;
    /* la casa siempre a lo largo del eje del lote (como sus vecinas);
       la fachada apunta al extremo del eje mas cercano a la via */
    var ax = -sp.a;
    if (SNAP_MZ[sp.mz] && mzAxis[sp.mz] !== undefined && axDiff(ax, mzAxis[sp.mz]) > 0.28) ax = mzAxis[sp.mz];
    var facing = angDiff(ax, sp.f) <= angDiff(ax + Math.PI, sp.f) ? ax : ax + Math.PI;
    var rotY = -facing;
    var fx = Math.cos(facing), fz = Math.sin(facing);
    var setback = sp.d/2 - 1.3 - HL/2;      /* antejardin de ~1,3 m */
    var cx0 = sp.c[0] + fx*setback, cz0 = sp.c[1] + fz*setback;
    q.setFromAxisAngle(up, rotY);
    sc.set(1, h, 1); pos.set(cx0, BASE+0.34+h/2, cz0);
    m4.compose(pos, q, sc); body.setMatrixAt(i, m4);
    sc.set(1,1,1); pos.set(cx0, BASE+0.34+h, cz0);
    m4.compose(pos, q, sc); roof.setMatrixAt(i, m4);
    /* puerta y ventana sobre la fachada (+X local, desplazadas en Z local) */
    var lx = HL/2 + 0.02;
    pos.set(cx0 + fx*lx - fz*(-1.05), BASE+0.34+1.03, cz0 + fz*lx + fx*(-1.05));
    m4.compose(pos, q, sc); door.setMatrixAt(i, m4);
    pos.set(cx0 + fx*lx - fz*(1.05), BASE+0.34+1.65, cz0 + fz*lx + fx*(1.05));
    m4.compose(pos, q, sc); win.setMatrixAt(i, m4);
    roof.setColorAt(i, tmpC.set(rnd()<0.72 ? COL.roofClay : COL.roofSage).offsetHSL(0,0,(rnd()-0.5)*0.05));
    body.setColorAt(i, tmpC.set(COL.wall).offsetHSL(0,0,(rnd()-0.5)*0.03));
  }
  body.castShadow = body.receiveShadow = true;
  roof.castShadow = true;
  houses.add(body); houses.add(roof); houses.add(door); houses.add(win);
})();

/* ---------- lotes perimetrales ---------- */
var perimMeshes = [];
PLAN.perims.forEach(function(pl){
  var g = new THREE.ExtrudeGeometry(shapeFrom(pl.p), {depth:0.34, bevelEnabled:false});
  var m = new THREE.Mesh(g, mat(COL.perim, 0.95));
  m.rotation.x = -Math.PI/2;
  m.position.y = 0.78;
  m.receiveShadow = true;
  m.userData = {perim: pl};
  world.add(m); perimMeshes.push(m);
});

/* ---------- contorno de lotes ---------- */
(function(){
  var pos = [];
  function outline(pts, y){
    for (var i=0;i<pts.length;i++){
      var a = pts[i], b = pts[(i+1)%pts.length];
      pos.push(a[0], y, a[1], b[0], y, b[1]);
    }
  }
  PLAN.lots.forEach(function(l){ outline(l.p, BASE+0.345); });
  PLAN.perims.forEach(function(p){ outline(p.p, 0.78+0.36); });
  var g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos,3));
  var lines = new THREE.LineSegments(g, new THREE.LineBasicMaterial({color:0x8f8672, transparent:true, opacity:0.5}));
  world.add(lines);
})();

/* ---------- árboles y vegetación ---------- */
var arbGroup = new THREE.Group(); world.add(arbGroup);
(function(){
  var inTerr = function(p){ return pointInPoly(PLAN.terrain.e, p[0], p[1]); };
  var bigTrees = PLAN.trees.filter(inTerr);
  var bushPts = [];
  PLAN.scatter.filter(inTerr).forEach(function(p){
    if (rnd() < 0.32) bigTrees.push(p); else bushPts.push(p);
  });
  var trunkG = new THREE.CylinderGeometry(0.35,0.5,1.8,6);
  var leafG = new THREE.IcosahedronGeometry(2.2,0);
  var n = bigTrees.length;
  var trunks = new THREE.InstancedMesh(trunkG, mat(COL.trunk,1), n);
  var leaves = new THREE.InstancedMesh(leafG, mat(COL.leaf1,0.95), n);
  var m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), up = new THREE.Vector3(0,1,0);
  var pos = new THREE.Vector3(), sc = new THREE.Vector3();
  var cols = [COL.leaf1, COL.leaf2, COL.leaf3];
  for (var i=0;i<n;i++){
    var t = bigTrees[i], s = 0.8 + rnd()*0.8;
    q.setFromAxisAngle(up, rnd()*Math.PI);
    sc.set(s,s,s); pos.set(t[0], 0.6+0.9*s, t[1]);
    m4.compose(pos,q,sc); trunks.setMatrixAt(i,m4);
    pos.y = 0.6 + 3.4*s; sc.set(s, s*1.12, s);
    m4.compose(pos,q,sc); leaves.setMatrixAt(i,m4);
    leaves.setColorAt(i, tmpC.set(cols[Math.floor(rnd()*3)]).offsetHSL(0,0,(rnd()-0.5)*0.06));
  }
  trunks.castShadow = leaves.castShadow = true;
  arbGroup.add(trunks); arbGroup.add(leaves);

  var m = bushPts.length;
  var bushG = new THREE.IcosahedronGeometry(1.6,0);
  var bushes = new THREE.InstancedMesh(bushG, mat(COL.leaf2,1), m);
  for (i=0;i<m;i++){
    var p = bushPts[i], bs = 0.5 + rnd()*0.8;
    q.setFromAxisAngle(up, rnd()*Math.PI);
    sc.set(bs, bs*0.55, bs); pos.set(p[0], 0.55, p[1]);
    m4.compose(pos,q,sc); bushes.setMatrixAt(i,m4);
    bushes.setColorAt(i, tmpC.set(cols[Math.floor(rnd()*3)]).offsetHSL(0.01*rnd(),0,(rnd()-0.5)*0.08));
  }
  bushes.castShadow = false;
  arbGroup.add(bushes);
})();

/* ---------- etiquetas ---------- */
var lblGroup = new THREE.Group(); world.add(lblGroup);
function makeLabel(text, x, z, y, hScreen, alpha){
  var probe = document.createElement('canvas').getContext('2d');
  probe.font = '600 44px "Palatino Linotype", Georgia, serif';
  var tw = Math.ceil(probe.measureText(text).width);
  var W = tw + 48, H = 96;
  var cv = document.createElement('canvas'); cv.width = W; cv.height = H;
  var ctx = cv.getContext('2d');
  ctx.font = '600 44px "Palatino Linotype", Georgia, serif';
  ctx.textAlign='center'; ctx.textBaseline='middle';
  ctx.fillStyle = 'rgba(28,44,35,'+(alpha||0.55)+')';
  ctx.beginPath(); ctx.roundRect(4, 16, W-8, 64, 12); ctx.fill();
  ctx.fillStyle = '#f3f1e7';
  ctx.fillText(text, W/2, 50);
  var tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  var sp = new THREE.Sprite(new THREE.SpriteMaterial({map:tex, transparent:true, depthTest:false, sizeAttenuation:false}));
  sp.scale.set(hScreen*W/H, hScreen, 1);
  sp.position.set(x, y, z);
  sp.renderOrder = 5;
  lblGroup.add(sp);
}
PLAN.mzLabels.forEach(function(L){ makeLabel(L.t, L.c[0], L.c[1], 13, 0.034, 0.6); });
PLAN.loteLabels.forEach(function(L){ makeLabel(L.t, L.c[0], L.c[1], 8, 0.024, 0.45); });
PLAN.extraLabels.forEach(function(L){ makeLabel(L.t, L.c[0], L.c[1], 11, 0.028, 0.35); });

/* ---------- cámara / controles ---------- */
var TARGET0 = new THREE.Vector3(0, 2, -10);
var cur = {theta: 0.65, phi: 0.9, r: 480, target: TARGET0.clone()};
var des = {theta: 0.65, phi: 0.9, r: 430, target: TARGET0.clone()};
if (!reduceMotion){ cur.r = 1300; cur.phi = 1.3; cur.theta = 1.8; }
var VIEWS = {
  aerea: {theta: 0.001, phi: 0.1, r: 520},
  iso:   {theta: 0.65, phi: 0.9, r: 430},
  calle: {theta: 2.3, phi: 1.38, r: 170, target: new THREE.Vector3(-150, 4, 60)}
};
function applyCam(){
  var sp = Math.sin(cur.phi);
  camera.position.set(cur.target.x + cur.r*sp*Math.sin(cur.theta),
                      cur.target.y + cur.r*Math.cos(cur.phi),
                      cur.target.z + cur.r*sp*Math.cos(cur.theta));
  camera.lookAt(cur.target);
}
function clamp(v,a,b){ return Math.max(a, Math.min(b, v)); }
var dragging=false, panning=false, moved=0, lastX=0, lastY=0, pinchD=0, ptrs={};
canvas.addEventListener('pointerdown', function(e){
  ptrs[e.pointerId] = [e.clientX, e.clientY];
  var n = Object.keys(ptrs).length;
  if (n===1){ dragging=true; moved=0; panning=(e.button===2); lastX=e.clientX; lastY=e.clientY; canvas.classList.add('dragging'); }
  if (n===2){ var k=Object.keys(ptrs); pinchD=Math.hypot(ptrs[k[0]][0]-ptrs[k[1]][0], ptrs[k[0]][1]-ptrs[k[1]][1]); }
  canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener('pointermove', function(e){
  if (ptrs[e.pointerId]) ptrs[e.pointerId] = [e.clientX, e.clientY];
  var keys = Object.keys(ptrs);
  if (keys.length === 2){
    var nd = Math.hypot(ptrs[keys[0]][0]-ptrs[keys[1]][0], ptrs[keys[0]][1]-ptrs[keys[1]][1]);
    if (pinchD > 0) des.r = clamp(des.r * pinchD/nd, 50, 1300);
    pinchD = nd; return;
  }
  if (!dragging){ hover(e); return; }
  var dx=e.clientX-lastX, dy=e.clientY-lastY; lastX=e.clientX; lastY=e.clientY;
  moved += Math.abs(dx)+Math.abs(dy);
  if (panning){
    var k = des.r/900;
    des.target.x += (-dx*Math.cos(cur.theta) + dy*Math.sin(cur.theta)) * k;
    des.target.z += ( dx*Math.sin(cur.theta) + dy*Math.cos(cur.theta)) * k;
  } else {
    des.theta -= dx*0.0052;
    des.phi = clamp(des.phi - dy*0.0042, 0.08, 1.45);
  }
});
function endPtr(e){
  if (dragging && moved < 6 && e.button !== 2) select(e);
  delete ptrs[e.pointerId];
  if (!Object.keys(ptrs).length){ dragging=false; panning=false; canvas.classList.remove('dragging'); }
  pinchD = 0;
}
canvas.addEventListener('pointerup', endPtr);
canvas.addEventListener('pointercancel', function(e){ delete ptrs[e.pointerId]; dragging=false; });
canvas.addEventListener('contextmenu', function(e){ e.preventDefault(); });
canvas.addEventListener('wheel', function(e){ e.preventDefault(); des.r = clamp(des.r*(e.deltaY>0?1.1:0.9), 50, 1300); }, {passive:false});

/* ---------- picking ---------- */
var ray = new THREE.Raycaster(), mouse = new THREE.Vector2(), tip = document.getElementById('tip');
var lastHi = -1, selected = -1, hiColor = new THREE.Color(0xe2b64f), selColor = new THREE.Color(0xd4a017);
function pickLot(e){
  mouse.x = (e.clientX/innerWidth)*2-1; mouse.y = -(e.clientY/innerHeight)*2+1;
  ray.setFromCamera(mouse, camera);
  var o = ray.ray.origin, d = ray.ray.direction;
  if (Math.abs(d.y) > 1e-6){
    var t = (BASE + 0.32 - o.y)/d.y;
    if (t > 0){
      var x = o.x + d.x*t, z = o.z + d.z*t;
      var i = lotAt(x, z);
      if (i >= 0) return {type:'lot', i:i};
    }
  }
  var hits = ray.intersectObjects(perimMeshes.concat([comercioMesh]), false);
  if (hits.length){
    var u = hits[0].object.userData;
    if (u.perim) return {type:'perim', pl:u.perim};
    if (u.comercio) return {type:'com'};
  }
  return null;
}
function lotColor(i){
  if (esqOn){
    var e = PLAN.lots[i].e;
    return e ? ESQ_COLORS[e] : lotRanges[i].color;
  }
  return estadosOn ? EST_COLORS[estados[i]] : lotRanges[i].color;
}
function esqName(lot){ return lot.e === 'T1' ? 'Esquinero Tipo 1' : (lot.e === 'T2' ? 'Esquinero Tipo 2' : null); }
function lotNum(lot){ return lot.n === 'SN' ? 'S/N' : lot.n; }
function fmtLot(lot, i){
  var est = estadosOn ? '<br><span>Estado: '+EST_NAMES[estados[i]]+' (demo)</span>' : '';
  if (esqName(lot)) est = '<br><span>'+esqName(lot)+'</span>' + est;
  return '<b>'+lot.mz+' &middot; Lote '+lotNum(lot)+'</b><span>'+
    (lot.w>=5.4 && lot.d>=9.8 ? '5,50 &times; 10,00 m &mdash; 55 m&sup2;' : lot.w.toFixed(1).replace('.',',')+' &times; '+lot.d.toFixed(1).replace('.',',')+' m &mdash; '+lot.area+' m&sup2;')+
    '</span>'+est;
}
function hover(e){
  var hit = pickLot(e);
  if (lastHi >= 0 && lastHi !== selected){ paintLot(lastHi, lotColor(lastHi)); lastHi = -1; }
  canvas.style.cursor = hit ? 'pointer' : '';
  if (!hit){ tip.style.display='none'; return; }
  var html = '';
  if (hit.type === 'lot'){
    html = fmtLot(PLAN.lots[hit.i], hit.i);
    if (hit.i !== selected){ paintLot(hit.i, hiColor); lastHi = hit.i; }
  } else if (hit.type === 'perim'){
    html = '<b>Lote '+hit.pl.letter+'</b><span>'+String(hit.pl.area).replace('.',',')+' m&sup2; seg&uacute;n plano'+(hit.pl.approx?' &middot; posici&oacute;n aproximada':'')+'</span>';
  } else {
    html = '<b>Zona de comercio</b><span>2.501,37 m&sup2; seg&uacute;n plano</span>';
  }
  tip.innerHTML = html;
  tip.style.display = 'block';
  tip.style.left = Math.min(e.clientX+16, innerWidth-250)+'px';
  tip.style.top = (e.clientY+14)+'px';
}
var card = document.getElementById('card'), cardBody = document.getElementById('cardBody');
function select(e){
  var hit = pickLot(e);
  if (selected >= 0){ paintLot(selected, lotColor(selected)); selected = -1; }
  if (!hit){ card.style.display='none'; return; }
  var html = '';
  if (hit.type === 'lot'){
    selected = hit.i;
    paintLot(hit.i, selColor);
    var lot = PLAN.lots[hit.i];
    var esq = esqName(lot) ? '<br><b style="font-size:12px;color:#a05a3c">'+esqName(lot)+'</b>' : '';
    html = '<b>'+lot.mz+' &middot; Lote '+lotNum(lot)+'</b><div class="d">Frente &times; fondo: '+lot.w.toFixed(1).replace('.',',')+' &times; '+lot.d.toFixed(1).replace('.',',')+' m<br>&Aacute;rea: '+lot.area+' m&sup2;'+esq+'<br><em>Numeraci&oacute;n seg&uacute;n plano</em></div>';
    if (estadosOn){
      var ec = ['#b5d69c','#e9c46a','#c96f57'][estados[hit.i]];
      html += '<span class="est" style="background:'+ec+'33;color:#22352b;border:1px solid '+ec+'">'+EST_NAMES[estados[hit.i]]+' (demo)</span>';
    }
  } else if (hit.type === 'perim'){
    html = '<b>Lote '+hit.pl.letter+'</b><div class="d">Lote perimetral<br>&Aacute;rea seg&uacute;n plano: '+String(hit.pl.area).replace('.',',')+' m&sup2;'+(hit.pl.approx?'<br><em>Posici&oacute;n aproximada</em>':'')+'</div>';
  } else {
    html = '<b>Zona de comercio</b><div class="d">&Aacute;rea seg&uacute;n plano: 2.501,37 m&sup2;</div>';
  }
  cardBody.innerHTML = html;
  card.style.display = 'block';
}
document.getElementById('cardX').addEventListener('click', function(){
  if (selected >= 0){ paintLot(selected, lotColor(selected)); selected = -1; }
  card.style.display = 'none';
});

/* ---------- UI ---------- */
var autoRotate = !reduceMotion;
function bindTog(id, fn, initial){
  var el = document.getElementById(id);
  el.classList.toggle('on', initial);
  el.addEventListener('click', function(){
    var on = !el.classList.contains('on');
    el.classList.toggle('on', on); fn(on);
  });
}
bindTog('tCasas', function(on){ houses.visible = on; }, true);
bindTog('tEtiq', function(on){ lblGroup.visible = on; }, true);
bindTog('tArb', function(on){ arbGroup.visible = on; }, true);
bindTog('tEst', function(on){
  estadosOn = on;
  if (on && esqOn){
    esqOn = false;
    document.getElementById('tEsq').classList.remove('on');
    document.getElementById('lgEsq').style.display = 'none';
  }
  document.getElementById('lgEst').style.display = on ? 'block' : 'none';
  repaintAll();
  if (selected >= 0) paintLot(selected, selColor);
}, false);
bindTog('tEsq', function(on){
  esqOn = on;
  if (on && estadosOn){
    estadosOn = false;
    document.getElementById('tEst').classList.remove('on');
    document.getElementById('lgEst').style.display = 'none';
  }
  document.getElementById('lgEsq').style.display = on ? 'block' : 'none';
  repaintAll();
  if (selected >= 0) paintLot(selected, selColor);
}, false);
bindTog('tRot', function(on){ autoRotate = on; }, autoRotate);
document.querySelectorAll('#views .btn').forEach(function(btn){
  if (!btn.dataset.v) return;
  btn.addEventListener('click', function(){
    document.querySelectorAll('#views .btn').forEach(function(b){ b.classList.remove('active'); });
    btn.classList.add('active');
    var v = VIEWS[btn.dataset.v];
    des.theta = v.theta; des.phi = v.phi; des.r = v.r;
    des.target.copy(v.target || TARGET0);
  });
});

var needle = document.getElementById('needle');
function resize(){
  renderer.setSize(innerWidth, innerHeight, false);
  camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix();
}
addEventListener('resize', resize); resize();

var idle = 0;
function animate(){
  requestAnimationFrame(animate);
  if (autoRotate && !dragging){ idle++; if (idle > 120) des.theta += 0.001; }
  else idle = 0;
  var k = 0.07;
  cur.theta += (des.theta-cur.theta)*k;
  cur.phi += (des.phi-cur.phi)*k;
  cur.r += (des.r-cur.r)*k;
  cur.target.lerp(des.target, k);
  applyCam();
  if (needle) needle.style.transform = 'rotate('+cur.theta+'rad)';
  renderer.render(scene, camera);
}
animate();
})();
