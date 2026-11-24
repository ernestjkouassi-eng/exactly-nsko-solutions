(function(){
"use strict";
/* ---------------- i18n ---------------- */
const T={
en:{water:"Water",farm:"Farming",cocoa:"Cocoa",command:"Command",hint:"Tap anywhere on Côte d'Ivoire to drop a pin",near:"Near",gw:"Groundwater chance",depth:"Est. depth",sun:"Sun hours / day",rain:"Rainfall / yr",people:"People in the village",full:"Full system · corporate",easy:"Easy route · village",design:"Instant system design",need:"Daily water need",flow:"Pump flow",solar:"Solar array",tank:"Storage tank",cost:"Indicative cost",check:"Water supply check",repair:"Repair alerts by text",route:"Easy route · no grant needed",safe:"Make it safe to drink",guide:"Open build guide",soil:"Soil moisture",season:"Rain seasons",calendar:"Planting calendar",crops:"Best crops for this spot",irrig:"Irrigation from the same pump",doctor:"Crop doctor",suit:"Cocoa suitability",forest:"Forest risk",voice:"Voice-first",price:"Fair price check",eu:"EU compliance certificate",forecast:"Harvest forecast",sites:"Sites live",served:"People served",working:"Systems working",alerts:"Open alerts",fleet:"Every site, one map",extra:"Extra · cost & impact",layerW:"Groundwater probability",layerF:"Soil moisture",layerC:"Cocoa belt · forest risk",layerX:"Installed sites"},
fr:{water:"Eau",farm:"Agriculture",cocoa:"Cacao",command:"Commande",hint:"Touchez la carte de la Côte d'Ivoire pour placer un repère",near:"Près de",gw:"Chance d'eau souterraine",depth:"Profondeur est.",sun:"Heures de soleil / jour",rain:"Pluie / an",people:"Habitants du village",full:"Système complet · entreprises",easy:"Voie facile · village",design:"Conception instantanée",need:"Besoin quotidien",flow:"Débit de la pompe",solar:"Panneaux solaires",tank:"Réservoir",cost:"Coût indicatif",check:"Contrôle de la ressource",repair:"Alertes de panne par SMS",route:"Voie facile · sans subvention",safe:"Rendre l'eau potable",guide:"Ouvrir le guide",soil:"Humidité du sol",season:"Saisons des pluies",calendar:"Calendrier de plantation",crops:"Cultures conseillées",irrig:"Irrigation avec la même pompe",doctor:"Docteur des plantes",suit:"Aptitude au cacao",forest:"Risque forestier",voice:"Voix d'abord",price:"Contrôle du prix juste",eu:"Certificat de conformité UE",forecast:"Prévision de récolte",sites:"Sites actifs",served:"Personnes servies",working:"Systèmes en marche",alerts:"Alertes ouvertes",fleet:"Tous les sites, une carte",extra:"Extra · coût et impact",layerW:"Probabilité d'eau souterraine",layerF:"Humidité du sol",layerC:"Ceinture cacao · risque forestier",layerX:"Sites installés"}};
const S={tab:"water",lang:"en",pin:null,pop:200,tier:"full",kg:850,price:2800,offer:2550,sms:[],userPinned:false};
const t=k=>(T[S.lang][k]||T.en[k]||k);

/* ---------------- geography ---------------- */
const BORDER=[[-7.53,4.36],[-7.36,4.43],[-6.95,4.6],[-6.64,4.75],[-6.08,4.95],[-5.57,5.08],[-5.03,5.15],[-4.42,5.2],[-4.0,5.27],[-3.74,5.2],[-3.3,5.12],[-3.1,5.1],[-2.93,5.38],[-2.97,5.75],[-3.05,6.2],[-3.22,6.6],[-3.25,7.0],[-2.98,7.3],[-2.8,7.9],[-2.75,8.3],[-2.6,8.8],[-2.66,9.2],[-2.7,9.5],[-2.86,9.75],[-3.1,9.88],[-3.6,9.92],[-4.3,9.65],[-4.72,9.72],[-5.0,10.18],[-5.5,10.42],[-5.9,10.26],[-6.2,10.52],[-6.45,10.6],[-6.9,10.3],[-7.4,10.42],[-7.62,10.15],[-7.98,10.2],[-8.22,10.05],[-8.1,9.55],[-7.8,9.0],[-8.1,8.4],[-8.2,7.9],[-8.47,7.56],[-8.35,7.25],[-8.55,6.55],[-8.25,6.2],[-7.85,5.85],[-7.6,5.45],[-7.48,4.95]];
const COAST=BORDER.slice(0,12);
const CITIES=[["Abidjan",-4.02,5.36,1],["Yamoussoukro",-5.28,6.82,1],["Bouaké",-5.03,7.69],["Daloa",-6.45,6.88],["San-Pédro",-6.64,4.75],["Korhogo",-5.63,9.46],["Man",-7.55,7.41],["Soubré",-6.6,5.79],["Gagnoa",-5.95,6.13],["Odienné",-7.56,9.51],["Bondoukou",-2.8,8.04],["Abengourou",-3.49,6.73],["Divo",-5.36,5.84],["Séguéla",-6.67,7.96]];
const LON0=-5.55,LAT0=7.45,K=9.5,CS=Math.cos(LAT0*Math.PI/180);
const toXZ=(lon,lat)=>[(lon-LON0)*K*CS,-(lat-LAT0)*K];
const toLL=(x,z)=>[x/(K*CS)+LON0,-z/K+LAT0];
function inside(lon,lat,poly){let c=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const[xi,yi]=poly[i],[xj,yj]=poly[j];if(((yi>lat)!==(yj>lat))&&(lon<(xj-xi)*(lat-yi)/(yj-yi)+xi))c=!c;}return c;}
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
function hash(x,y){const s=Math.sin(x*127.1+y*311.7)*43758.5453;return s-Math.floor(s);}
function vn(x,y){const xi=Math.floor(x),yi=Math.floor(y),xf=x-xi,yf=y-yi,u=xf*xf*(3-2*xf),v=yf*yf*(3-2*yf);const a=hash(xi,yi),b=hash(xi+1,yi),c=hash(xi,yi+1),d=hash(xi+1,yi+1);return a+(b-a)*u+(c-a)*v+(a-b-c+d)*u*v;}
function fbm(x,y){let s=0,a=.5,f=1;for(let i=0;i<4;i++){s+=a*vn(x*f,y*f);f*=2;a*=.5;}return s/.9375;}
const gs=(lon,lat,cx,cy,r)=>Math.exp(-((lon-cx)**2+(lat-cy)**2)/(2*r*r));
function geo(lon,lat){
  const n=fbm(lon*1.3+20,lat*1.3+20),n2=fbm(lon*2.1-7,lat*2.1+3);
  const south=clamp((10.6-lat)/6.3,0,1);
  const rain=Math.round(1150+south*850+(lon<-6?110:0)+(n2-.5)*300);
  const gw=clamp(.26+.38*south+(n-.5)*.8,.05,.96);
  const depth=Math.round(6+(1-gw)*55+n2*10);
  const psh=+(4.4+(1-south)*1.6+(n-.5)*.2).toFixed(1);
  const soil=clamp((rain-1000)/1100*.85+(n2-.5)*.4,.05,.97);
  const cocoa=clamp(Math.exp(-Math.pow((lat-6.15)/1.2,2))*(lon<-3.2?1:.6)*(.78+.5*(n-.5)),0,1);
  const forest=clamp(Math.max(gs(lon,lat,-7.2,5.7,.38),gs(lon,lat,-6.3,5.45,.18)*.85,gs(lon,lat,-3.6,8.9,.5)*.65,gs(lon,lat,-7.25,6.95,.2)*.85,gs(lon,lat,-3.95,6.05,.16)*.7)+(n2-.5)*.18,0,1);
  return {rain,gw,depth,psh,soil,cocoa,forest};
}
function nearest(lon,lat){let best=null,bd=1e9;for(const c of CITIES){const d=(c[1]-lon)**2+(c[2]-lat)**2;if(d<bd){bd=d;best=c;}}return {name:best[0],km:Math.round(Math.sqrt(bd)*110)};}

/* ---------------- three.js scene ---------------- */
const canvas=document.getElementById("c");
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false});
renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
renderer.setClearColor(0xF3F6FB,1);
const scene=new THREE.Scene();
scene.fog=new THREE.Fog(0xF3F6FB,120,230);
const camera=new THREE.PerspectiveCamera(38,1,.1,600);
const isMobile=()=>innerWidth<=860;
camera.position.set(0,140,140);
const controls=new THREE.OrbitControls(camera,canvas);
controls.enableDamping=true;controls.dampingFactor=.08;controls.maxPolarAngle=1.2;controls.minDistance=18;controls.maxDistance=210;
controls.target.set(0,0,0);
scene.add(new THREE.HemisphereLight(0xffffff,0xC9D6EA,.95));
const sun=new THREE.DirectionalLight(0xffffff,.75);sun.position.set(-40,90,60);scene.add(sun);
const rim=new THREE.DirectionalLight(0x7FD4FF,.25);rim.position.set(50,30,-60);scene.add(rim);

// ground + grid
const ground=new THREE.Mesh(new THREE.CircleGeometry(240,80),new THREE.MeshLambertMaterial({color:0xE7EDF6}));
ground.rotation.x=-Math.PI/2;ground.position.y=-.02;scene.add(ground);
const grid=new THREE.GridHelper(300,60,0xC7D3E6,0xD8E1EE);grid.position.y=0;grid.material.transparent=true;grid.material.opacity=.55;scene.add(grid);
// ocean
const oc=new THREE.Shape();
{const pts=COAST.map(p=>toXZ(p[0],p[1]));const w=toXZ(-9.5,4.36),e=toXZ(-1.5,5.1);
 oc.moveTo(w[0],-w[1]);pts.forEach(p=>oc.lineTo(p[0],-p[1]));oc.lineTo(e[0],-e[1]);const se=toXZ(-1.5,2.2),sw=toXZ(-9.5,2.2);oc.lineTo(se[0],-se[1]);oc.lineTo(sw[0],-sw[1]);}
const ocean=new THREE.Mesh(new THREE.ShapeGeometry(oc),new THREE.MeshLambertMaterial({color:0xBFD6F7}));
ocean.rotation.x=-Math.PI/2;ocean.position.y=.03;scene.add(ocean);

// country base
const BASE_H=1.1;
const shape=new THREE.Shape();
BORDER.forEach((p,i)=>{const[x,z]=toXZ(p[0],p[1]);i?shape.lineTo(x,-z):shape.moveTo(x,-z);});
const baseGeo=new THREE.ExtrudeGeometry(shape,{depth:BASE_H,bevelEnabled:true,bevelThickness:.15,bevelSize:.25,bevelSegments:2});
const baseMesh=new THREE.Mesh(baseGeo,[new THREE.MeshStandardMaterial({color:0xFFFFFF,roughness:.8}),new THREE.MeshStandardMaterial({color:0xD5E0F2,roughness:.9})]);
baseMesh.rotation.x=-Math.PI/2;scene.add(baseMesh);
const outlinePts=BORDER.concat([BORDER[0]]).map(p=>{const[x,z]=toXZ(p[0],p[1]);return new THREE.Vector3(x,BASE_H+.27,z);});
scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(outlinePts),new THREE.LineBasicMaterial({color:0x071A36,transparent:true,opacity:.55})));

// hex columns
const STEP=1.35,cells=[];
{const xs=BORDER.map(p=>toXZ(p[0],p[1])[0]),zs=BORDER.map(p=>toXZ(p[0],p[1])[1]);
 const x0=Math.min(...xs),x1=Math.max(...xs),z0=Math.min(...zs),z1=Math.max(...zs);let r=0;
 for(let z=z0;z<=z1;z+=STEP*.866,r++){for(let x=x0+(r%2?STEP/2:0);x<=x1;x+=STEP){const[lon,lat]=toLL(x,z);if(inside(lon,lat,BORDER)){cells.push({x,z,lon,lat,g:geo(lon,lat),h:.05,th:.05});}}}}
const colGeo=new THREE.CylinderGeometry(STEP*.47,STEP*.47,1,6);colGeo.translate(0,.5,0);colGeo.rotateY(Math.PI/6);
const colMat=new THREE.MeshStandardMaterial({roughness:.55,metalness:.05});
const cols=new THREE.InstancedMesh(colGeo,colMat,cells.length);
const dummy=new THREE.Object3D(),tmpC=new THREE.Color();
cells.forEach((c,i)=>{cols.setColorAt(i,tmpC.set(0xffffff));});
scene.add(cols);
const lerpC=(a,b,t)=>new THREE.Color(a).lerp(new THREE.Color(b),clamp(t,0,1));
function grad(stops,v){for(let i=1;i<stops.length;i++){if(v<=stops[i][0]){const[a0,c0]=stops[i-1],[a1,c1]=stops[i];return lerpC(c0,c1,(v-a0)/(a1-a0));}}return new THREE.Color(stops[stops.length-1][1]);}
const GW=[[0,0xE9F0FC],[.45,0x8FB3F2],[.75,0x1554E0],[1,0x0A2A7A]];
const SOIL=[[0,0xF2E6CB],[.45,0xBFD9B0],[.8,0x19B8A6],[1,0x0B7D70]];
const COC=[[0,0xF4EEE6],[.4,0xDCC2A0],[.75,0xA0683A],[1,0x5E3416]];
function applyLayer(){
  cells.forEach((c,i)=>{let v,col;const g=c.g;
    if(S.tab==="water"){v=g.gw;col=grad(GW,v);c.th=.15+v*v*5.2;}
    else if(S.tab==="farm"){v=g.soil;col=grad(SOIL,v);c.th=.15+v*3.6;}
    else if(S.tab==="cocoa"){v=g.cocoa;col=grad(COC,v);c.th=.1+v*4.4;if(g.forest>.62&&g.cocoa>.2){col=lerpC(col,0xFF5A3C,.6+.4*(g.forest-.62));c.th+=.6;}}
    else{col=new THREE.Color(0xF1F5FB).lerp(new THREE.Color(0xDCE6F6),g.gw*.6);c.th=.12+g.gw*.5;}
    cols.setColorAt(i,col);});
  cols.instanceColor.needsUpdate=true;
  sitesGroup.visible=(S.tab==="command"||S.tab==="water");
  renderLegend();
}

// labels
const labelsEl=document.getElementById("labels");
const labelEls=CITIES.map(c=>{const d=document.createElement("div");d.className="lbl"+(c[3]?" cap":"");d.textContent=c[0];labelsEl.appendChild(d);const[x,z]=toXZ(c[1],c[2]);return {el:d,v:new THREE.Vector3(x,BASE_H+.6,z)};});
CITIES.forEach(c=>{const[x,z]=toXZ(c[1],c[2]);const m=new THREE.Mesh(new THREE.SphereGeometry(.28,12,12),new THREE.MeshBasicMaterial({color:c[3]?0x071A36:0x42536B}));m.position.set(x,BASE_H+.3,z);scene.add(m);});

// sites
const SITES=[["Korhogo · N'Ganon",-5.75,9.6,"ok",1450],["Ferkessédougou · Koumbala",-5.25,9.42,"ok",980],["Boundiali · Kasséré",-6.45,9.65,"warn",620],["Odienné · Samatiguila",-7.6,9.82,"ok",410],["Katiola · Fronan",-4.9,8.25,"ok",760],["Bouaké · Brobo",-4.82,7.6,"down",1200],["Séguéla · Massala",-6.95,8.05,"ok",530],["Man · Logoualé",-7.4,7.2,"ok",880],["Daloa · Gonaté",-6.25,6.95,"warn",690],["Soubré · Méagui",-6.55,5.42,"ok",1320],["Gagnoa · Ouragahio",-5.9,6.35,"ok",900],["Dimbokro · Abigui",-4.6,6.7,"ok",470],["Bondoukou · Tanda",-3.15,7.82,"down",560],["Abengourou · Niablé",-3.3,6.65,"ok",740],["Bouna · Doropo",-3.25,9.55,"warn",380],["Tiassalé · N'Douci",-4.9,5.9,"ok",1100]];
const STATUSC={ok:0x19B8A6,warn:0xF2A33A,down:0xFF5A3C};
const sitesGroup=new THREE.Group();scene.add(sitesGroup);
const siteMeshes=SITES.map(s=>{const[x,z]=toXZ(s[1],s[2]);const g=new THREE.Group();g.position.set(x,BASE_H+.2,z);
  const stem=new THREE.Mesh(new THREE.CylinderGeometry(.08,.08,3.4,8),new THREE.MeshBasicMaterial({color:0x071A36}));stem.position.y=1.7;g.add(stem);
  const head=new THREE.Mesh(new THREE.SphereGeometry(.5,16,16),new THREE.MeshBasicMaterial({color:STATUSC[s[3]]}));head.position.y=3.5;g.add(head);
  const ring=new THREE.Mesh(new THREE.RingGeometry(.6,.85,32),new THREE.MeshBasicMaterial({color:STATUSC[s[3]],transparent:true,opacity:.6,side:THREE.DoubleSide}));ring.rotation.x=-Math.PI/2;ring.position.y=.12;g.add(ring);
  sitesGroup.add(g);return {g,ring,s};});

// pin
const pin=new THREE.Group();
{const stem=new THREE.Mesh(new THREE.CylinderGeometry(.12,.04,7,10),new THREE.MeshStandardMaterial({color:0x071A36}));stem.position.y=3.5;pin.add(stem);
 const head=new THREE.Mesh(new THREE.SphereGeometry(.95,24,24),new THREE.MeshStandardMaterial({color:0xFF5A3C,emissive:0xFF5A3C,emissiveIntensity:.25,roughness:.3}));head.position.y=7.4;pin.add(head);
 const glow=new THREE.Mesh(new THREE.SphereGeometry(.42,16,16),new THREE.MeshBasicMaterial({color:0xffffff}));glow.position.set(-.3,7.7,.5);pin.add(glow);}
const pinRing=new THREE.Mesh(new THREE.RingGeometry(1,1.25,48),new THREE.MeshBasicMaterial({color:0xFF5A3C,transparent:true,opacity:.8,side:THREE.DoubleSide}));pinRing.rotation.x=-Math.PI/2;
const pinRing2=pinRing.clone();pinRing2.material=pinRing.material.clone();
const pinWrap=new THREE.Group();pinWrap.add(pin,pinRing,pinRing2);pinWrap.visible=false;scene.add(pinWrap);
let pinDrop=0;

// fly
let fly=null;
function flyTo(x,z,dist){const tgt=new THREE.Vector3(x,0,z);const dir=camera.position.clone().sub(controls.target).normalize();const d=dist||(isMobile()?96:52);
  fly={t:0,p0:camera.position.clone(),t0:controls.target.clone(),p1:tgt.clone().add(dir.multiplyScalar(d)),t1:tgt};
  if(fly.p1.y<18)fly.p1.y=18;}
const ease=t=>t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;

function setPin(lon,lat,doFly){S.pin={lon,lat,g:geo(lon,lat),near:nearest(lon,lat)};
  const[x,z]=toXZ(lon,lat);pinWrap.position.set(x,BASE_H+.25,z);pinWrap.visible=true;pinDrop=0;
  if(doFly)flyTo(x,z);renderPanel();}

// picking
const ray=new THREE.Raycaster(),mouse=new THREE.Vector2();let down=null;
canvas.addEventListener("pointerdown",e=>{down={x:e.clientX,y:e.clientY};});
canvas.addEventListener("pointerup",e=>{if(!down)return;const moved=Math.hypot(e.clientX-down.x,e.clientY-down.y);down=null;if(moved>6)return;
  const r=canvas.getBoundingClientRect();mouse.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);ray.setFromCamera(mouse,camera);
  const hits=ray.intersectObjects([cols,baseMesh],false);if(!hits.length)return;const p=hits[0].point;const[lon,lat]=toLL(p.x,p.z);
  if(!inside(lon,lat,BORDER))return;S.userPinned=true;document.getElementById("hint").style.opacity=0;setPin(lon,lat,true);});

function resize(){const w=innerWidth,h=innerHeight;renderer.setSize(w,h,false);camera.aspect=w/h;
  // shift view so map isn't hidden behind the panel
  if(isMobile()){camera.setViewOffset(w,h,0,h*.2,w,h);}else{camera.setViewOffset(w,h,210,0,w,h);}
  camera.updateProjectionMatrix();}
addEventListener("resize",resize);resize();

const clock=new THREE.Clock();
function loop(){requestAnimationFrame(loop);const dt=Math.min(clock.getDelta(),.05),tt=clock.elapsedTime;
  let changed=false;
  cells.forEach((c,i)=>{if(Math.abs(c.h-c.th)>.002){c.h+=(c.th-c.h)*Math.min(1,dt*5);changed=true;}dummy.position.set(c.x,BASE_H+.2,c.z);dummy.scale.set(1,c.h,1);dummy.updateMatrix();cols.setMatrixAt(i,dummy.matrix);});
  if(changed||tt<1)cols.instanceMatrix.needsUpdate=true;
  if(pinWrap.visible){pinDrop=Math.min(1,pinDrop+dt*2.2);const b=1-Math.pow(1-pinDrop,3);pin.position.y=(1-b)*12;
    const k=(tt*.7)%1,k2=(tt*.7+.5)%1;pinRing.scale.setScalar(1+k*3.2);pinRing.material.opacity=.75*(1-k);pinRing2.scale.setScalar(1+k2*3.2);pinRing2.material.opacity=.75*(1-k2);pinRing.position.y=pinRing2.position.y=.1;}
  siteMeshes.forEach((m,i)=>{const k=(tt*.6+i*.13)%1;m.ring.scale.setScalar(1+k*2.2);m.ring.material.opacity=.6*(1-k);});
  if(fly){fly.t=Math.min(1,fly.t+dt/1.3);const e=ease(fly.t);camera.position.lerpVectors(fly.p0,fly.p1,e);controls.target.lerpVectors(fly.t0,fly.t1,e);if(fly.t>=1)fly=null;}
  controls.update();renderer.render(scene,camera);
  const w=innerWidth,h=innerHeight;
  labelEls.forEach(l=>{const v=l.v.clone().project(camera);if(v.z>1){l.el.style.display="none";return;}l.el.style.display="";l.el.style.left=((v.x+1)/2*w)+"px";l.el.style.top=((-v.y+1)/2*h)+"px";});
}

/* ---------------- calculations ---------------- */
const fmt=n=>Math.round(n).toLocaleString("en-GB");
const XOF=600; // indicative USD→XOF
function design(g,pop){
  const V=pop*20/1000; // m3/day at 20 L/person
  const head=g.depth+6;
  const Eh=.002725*V*head; // kWh/day hydraulic
  const kWp=Eh/(g.psh*.38*.85);
  const panels=Math.max(1,Math.ceil(kWp*1000/450));
  const flow=V/g.psh;
  const tankL=Math.ceil(V*1000/5000)*5000;
  const drill=g.depth>22;
  const cost={pv:panels*450*.85,pump:650+head*14+kWp*380,tank:tankL*.22,bore:drill?g.depth*55+900:450,pipe:550+pop*.9};
  cost.total=Object.values(cost).reduce((a,b)=>a+b,0);
  const recharge=g.rain/1000*.06*(.6+g.gw)*.12e6; // m3/yr over a small catchment
  const ratio=recharge/(V*365);
  const dieselL=Eh/.3/2.6; // litres/day avoided
  return {V,head,Eh,kWp,panels,flow,tankL,drill,cost,ratio,co2:dieselL*2.68*365/1000};
}
function supplyStatus(r){return r>=2.2?["ok","Sustainable year-round","Durable toute l'année"]:r>=1.2?["warn","Watch dry-season levels","Surveiller en saison sèche"]:["bad","Will over-pump the source","Surexploitation de la source"];}
function routes(g,pop){
  const homes=Math.max(1,Math.round(pop/6));
  const rainL=g.rain*30*.8*homes; const needL=pop*20*365;
  const cover=clamp(rainL/needL,0,1);
  const R=[];
  R.push({k:"rain",title:S.lang==="fr"?"Récupération d'eau de pluie":"Rainwater harvesting",cost:homes*85,score:cover*1.25,cover,ok:true,
    text:S.lang==="fr"?`Gouttières sur ${homes} toits vers des réservoirs couverts. Couvre environ ${Math.round(cover*100)}% du besoin annuel.`:`Gutters on ${homes} roofs feeding covered tanks. Covers about ${Math.round(cover*100)}% of yearly need here.`});
  const ropeOk=g.depth<=35;
  R.push({k:"rope",title:S.lang==="fr"?"Pompe à corde sur puits":"Rope pump on a well",cost:ropeOk?(g.depth<=22?180+g.depth*28:g.depth*55+900):0,score:ropeOk?1.15-g.depth/60:-1,ok:ropeOk,
    text:ropeOk?(S.lang==="fr"?`Tuyau PVC, corde et une vieille roue de vélo. Eau estimée à ${g.depth} m : faisable.`:`PVC pipe, rope and an old bicycle wheel. Water at about ${g.depth} m: workable.`):(S.lang==="fr"?`Eau trop profonde (${g.depth} m) pour une pompe à corde.`:`Water too deep here (${g.depth} m) for a rope pump.`)});
  const digOk=g.depth<=22;
  R.push({k:"dig",title:S.lang==="fr"?"Puits creusé à la main":"Hand-dug well",cost:digOk?g.depth*28:0,score:digOk?.9-g.depth/50:-1,ok:digOk,
    text:digOk?(S.lang==="fr"?`Creuser environ ${g.depth+3} m et poser des buses en béton pour éviter l'effondrement.`:`Dig about ${g.depth+3} m and line it with concrete rings so it can't collapse.`):(S.lang==="fr"?"Trop profond pour creuser en sécurité. Forage nécessaire.":"Too deep to dig safely. Needs a drilled borehole.")});
  const d=design(g,pop);
  R.push({k:"solar",title:S.lang==="fr"?"Petite pompe solaire":"Small solar pump",cost:d.cost.total,score:.55,ok:true,
    text:S.lang==="fr"?`${d.panels} panneau(x) et une pompe immergée. La voie la plus fiable si un budget existe.`:`${d.panels} panel${d.panels>1?"s":""} and a submersible pump. Most reliable if any budget exists.`});
  return R.sort((a,b)=>b.score-a.score);
}

/* ---------------- panel rendering ---------------- */
const panel=document.getElementById("panel");
function kpi(v,unit,label,meter){return `<div class="kpi"><b>${v}<small>${unit||""}</small></b><span class="mono">${label}</span>${meter!=null?`<div class="meter"><div style="width:${Math.round(meter*100)}%"></div></div>`:""}</div>`;}
function header(sub){const p=S.pin;return `<div class="eyebrow mono">${t(S.tab)} · ${sub}</div><h2>${t("near")} ${p.near.name}</h2><div class="sub mono">${p.lat.toFixed(3)}° N · ${Math.abs(p.lon).toFixed(3)}° W · ~${p.near.km} km</div>`;}

function renderPanel(){
  if(S.tab==="command")return renderCommand();
  if(!S.pin)return;
  if(S.tab==="water")renderWater();else if(S.tab==="farm")renderFarm();else renderCocoa();
}
function renderWater(){
  const g=S.pin.g,d=design(g,S.pop),st=supplyStatus(d.ratio),fr=S.lang==="fr";
  let h=header(fr?"analyse du site":"site analysis");
  h+=`<div class="kpis">${kpi(Math.round(g.gw*100),"%",t("gw"),g.gw)}${kpi(g.depth," m",t("depth"))}${kpi(g.psh,"",t("sun"))}${kpi(fmt(g.rain)," mm",t("rain"))}</div>`;
  h+=`<div class="slider"><label>${t("people")} <b>${fmt(S.pop)}</b></label><input type="range" id="pop" min="50" max="5000" step="50" value="${S.pop}"></div>`;
  h+=`<div class="seg"><button data-tier="full" class="${S.tier==="full"?"on":""}">${t("full")}</button><button data-tier="easy" class="${S.tier==="easy"?"on":""}">${t("easy")}</button></div>`;
  if(S.tier==="full"){
    h+=`<div class="card"><h3>${t("design")}<span class="pill ok">${fr?"Prêt":"Ready"}</span></h3>
      <div class="row"><span>${t("need")}</span><b>${d.V.toFixed(1)} m³ · ${fmt(d.V*1000)} L</b></div>
      <div class="row"><span>${t("flow")}</span><b>${d.flow.toFixed(2)} m³/h · ${d.head} m ${fr?"de hauteur":"head"}</b></div>
      <div class="row"><span>${t("solar")}</span><b>${d.panels} × 450 W · ${d.kWp.toFixed(2)} kWp</b></div>
      <div class="row"><span>${t("tank")}</span><b>${fmt(d.tankL)} L</b></div>
      <div class="row"><span>${fr?"Accès à l'eau":"Water access"}</span><b>${d.drill?(fr?`Forage ~${g.depth+15} m`:`Borehole ~${g.depth+15} m`):(fr?"Puits peu profond":"Shallow well")}</b></div>
      <div class="row"><span>${t("cost")}</span><b>$${fmt(d.cost.total)} · ${fmt(d.cost.total*XOF/1000)}k FCFA</b></div>
      <div class="note">${fr?"Prédiction à partir de données satellite et géologiques. L'équipe de forage confirme sur site.":"Predicted from satellite and geological data. The drilling team confirms on site before work starts."}</div></div>`;
  }else{
    const R=routes(g,S.pop);
    h+=`<div class="card"><h3>${t("route")}<span class="pill ok">${fr?"Gratuit":"Free"}</span></h3>${R.map((r,i)=>`<div class="route ${i===0&&r.ok?"best":""}"><div class="rank">${i+1}</div><div style="flex:1"><h4>${r.title}</h4><p>${r.text}</p><div class="meta">${r.ok?`<span class="tag">~$${fmt(r.cost)}</span><span class="tag">${fmt(r.cost*XOF/1000)}k FCFA</span>`:`<span class="pill bad">${fr?"Pas ici":"Not here"}</span>`}${i===0&&r.ok?`<span class="pill ok">${fr?"Meilleur choix":"Best match"}</span>`:""}</div>${(r.k==="rope"||r.k==="rain")&&r.ok?`<button class="link" data-guide="${r.k}">${t("guide")} →</button>`:""}</div></div>`).join("")}</div>`;
    h+=`<div class="card"><h3>${t("safe")}</h3><div class="row"><span>${fr?"Faire bouillir":"Boil"}</span><b>${fr?"1 minute à gros bouillons":"1 minute at a rolling boil"}</b></div><div class="row"><span>SODIS</span><b>${fr?"Bouteilles claires, 6 h au soleil":"Clear bottles, 6 h in full sun"}</b></div><div class="row"><span>${fr?"Filtre tissu":"Cloth filter"}</span><b>${fr?"D'abord, si l'eau est trouble":"First, if water is cloudy"}</b></div></div>`;
  }
  h+=`<div class="card"><h3>${t("check")}<span class="pill ${st[0]}">${fr?st[2]:st[1]}</span></h3><div class="meter" style="height:8px"><div style="width:${Math.round(clamp(d.ratio/4,0,1)*100)}%;background:${st[0]==="ok"?"#19B8A6":st[0]==="warn"?"#F2A33A":"#FF5A3C"}"></div></div><div class="note">${fr?`Recharge estimée ${d.ratio.toFixed(1)}× le pompage annuel.`:`Estimated recharge is ${d.ratio.toFixed(1)}× the yearly pumping. Try raising the population to see the warning.`}</div></div>`;
  h+=smsCard();
  h+=`<div class="card"><h3>${t("extra")}<span class="tag">${fr?"Optionnel":"Optional"}</span></h3><div class="row"><span>${fr?"Coût par personne":"Cost per person"}</span><b>$${(d.cost.total/S.pop).toFixed(0)}</b></div><div class="row"><span>${fr?"CO₂ évité vs diesel":"CO₂ avoided vs diesel"}</span><b>${d.co2.toFixed(1)} t/${fr?"an":"yr"}</b></div></div>`;
  h+=foot();panel.innerHTML=h;bindWater();
}
function smsCard(){const fr=S.lang==="fr";
  if(!S.sms.length)S.sms=[{in:1,f:"+225 07 •• •• 41",m:"P2"},{in:0,m:fr?"NSKO : Débit faible signalé. Nettoyez le filtre d'entrée et vérifiez que les panneaux sont propres. Technicien Koné prévenu (Bouaké)." :"NSKO: Low flow logged. Clean the intake filter and wipe the panels. Technician Koné alerted (Bouaké)."}];
  return `<div class="card"><h3>${t("repair")}<span class="tag mono">SMS · USSD</span></h3><div class="feed" id="feed">${S.sms.map(m=>`<div class="msg ${m.in?"in":"out"}">${m.in?`<small>${m.f}</small>`:"<small>NSKO</small>"}${m.m}</div>`).join("")}</div>
  <div class="codes">${["P1","P2","S1","T1"].map(c=>`<button data-code="${c}">${c}</button>`).join("")}</div>
  <div class="smsbar"><input id="smsIn" placeholder="${fr?"Envoyer un code, ex. P1":"Text a code, e.g. P1"}"><button class="btn" id="smsGo">${fr?"Envoyer":"Send"}</button></div>
  <div class="note">P1 ${fr?"pas d'eau":"no water"} · P2 ${fr?"débit faible":"low flow"} · S1 ${fr?"panneau abîmé":"panel damaged"} · T1 ${fr?"fuite du réservoir":"tank leak"}</div></div>`;}
const REPLIES={en:{P1:"No water logged. Check the controller light: if red, the pump is dry-running. Switch off for 30 min. Technician dispatched within 24 h.",P2:"Low flow logged. Clean the intake filter and wipe the panels. Technician Koné alerted.",S1:"Panel damage logged. Photo requested by reply. Replacement panel reserved at the nearest depot.",T1:"Tank leak logged. Close the inlet valve. Repair kit and sealant sent with the next visit."},
fr:{P1:"Pas d'eau signalé. Vérifiez le voyant : s'il est rouge, la pompe tourne à sec. Coupez 30 min. Technicien envoyé sous 24 h.",P2:"Débit faible signalé. Nettoyez le filtre d'entrée et les panneaux. Technicien Koné prévenu.",S1:"Panneau abîmé signalé. Envoyez une photo en réponse. Panneau de rechange réservé au dépôt le plus proche.",T1:"Fuite signalée. Fermez la vanne d'entrée. Kit de réparation envoyé à la prochaine visite."}};
function sendCode(code){code=(code||"").trim().toUpperCase();if(!code)return;const r=REPLIES[S.lang][code]||(S.lang==="fr"?"Code inconnu. Envoyez P1, P2, S1 ou T1.":"Unknown code. Send P1, P2, S1 or T1.");
  S.sms.push({in:1,f:"+225 05 •• •• 18",m:code},{in:0,m:"NSKO: "+r});renderPanel();const f=document.getElementById("feed");if(f)f.scrollTop=f.scrollHeight;}
function bindWater(){
  const pop=document.getElementById("pop");pop.oninput=e=>{S.pop=+e.target.value;clearTimeout(pop._t);pop._t=setTimeout(()=>{const y=panel.scrollTop;renderPanel();panel.scrollTop=y;const p=document.getElementById("pop");p&&p.focus();},120);document.querySelector(".slider label b").textContent=fmt(S.pop);};
  panel.querySelectorAll("[data-tier]").forEach(b=>b.onclick=()=>{S.tier=b.dataset.tier;const y=panel.scrollTop;renderPanel();panel.scrollTop=y;});
  panel.querySelectorAll("[data-guide]").forEach(b=>b.onclick=()=>openGuide(b.dataset.guide));
  bindSms();}
function bindSms(){panel.querySelectorAll("[data-code]").forEach(b=>b.onclick=()=>{const y=panel.scrollTop;sendCode(b.dataset.code);panel.scrollTop=y;});
  const go=document.getElementById("smsGo"),inp=document.getElementById("smsIn");if(go){go.onclick=()=>{const y=panel.scrollTop;sendCode(inp.value);panel.scrollTop=y;};inp.onkeydown=e=>{if(e.key==="Enter"){const y=panel.scrollTop;sendCode(inp.value);panel.scrollTop=y;}};}}

function renderFarm(){
  const g=S.pin.g,fr=S.lang==="fr",lat=S.pin.lat;
  const two=lat<7.6;
  const zone=lat<6.6?"south":lat<8.4?"centre":"north";
  const crops={south:["Cacao","Banane plantain","Manioc","Hévéa","Riz de bas-fond"],centre:["Igname","Maïs","Anacarde","Cacao (ouest)","Arachide"],north:["Coton","Maïs","Sorgho","Anacarde","Riz irrigué"]}[zone];
  const cropsEn={south:["Cocoa","Plantain","Cassava","Rubber","Lowland rice"],centre:["Yam","Maize","Cashew","Cocoa (west)","Groundnut"],north:["Cotton","Maize","Sorghum","Cashew","Irrigated rice"]}[zone];
  const rainy=two?[3,4,5,6,8,9,10]:[4,5,6,7,8,9];const plant=two?[3,4,8]:[4,5];
  const M=fr?["J","F","M","A","M","J","J","A","S","O","N","D"]:["J","F","M","A","M","J","J","A","S","O","N","D"];
  const head=(Math.min(g.depth,40))+6,ha=.5,V=40*ha,E=.002725*V*head,kwp=E/(g.psh*.38*.85),pan=Math.ceil(kwp*1000/450);
  let h=header(fr?"conseil agricole":"farm advice");
  h+=`<div class="kpis">${kpi(fmt(g.rain)," mm",t("rain"))}${kpi(Math.round(g.soil*100),"%",t("soil"),g.soil)}${kpi(two?"2":"1","",t("season"))}${kpi(g.psh,"",t("sun"))}</div>`;
  h+=`<div class="card"><h3>${t("calendar")}<span class="tag">${fr?"Vert = pluie · plein = semer":"Green = rain · solid = plant"}</span></h3><div class="cal">${M.map((m,i)=>`<div class="${plant.includes(i)?"p":rainy.includes(i)?"r":""}">${m}</div>`).join("")}</div></div>`;
  h+=`<div class="card"><h3>${t("crops")}</h3><div class="chips">${(fr?crops:cropsEn).map(c=>`<span class="chip">${c}</span>`).join("")}</div></div>`;
  h+=`<div class="card"><h3>${t("irrig")}<span class="pill ok">${fr?"Lié à l'eau":"Linked to Water"}</span></h3>
   <div class="row"><span>${fr?"Surface en goutte-à-goutte":"Drip-irrigated plot"}</span><b>${ha} ha</b></div>
   <div class="row"><span>${fr?"Eau en saison sèche":"Dry-season water"}</span><b>${V} m³/${fr?"jour":"day"}</b></div>
   <div class="row"><span>${fr?"Panneaux en plus":"Extra panels"}</span><b>+${pan} × 450 W</b></div>
   <div class="note">${fr?"La pompe du village peut aussi arroser les cultures en saison sèche.":"The village pump can also water a crop plot through the dry season, so one install feeds people and fields."}</div></div>`;
  h+=`<div class="card"><h3>${t("doctor")}<span class="tag">${fr?"Exemple":"Sample output"}</span></h3>
   <div class="row"><span>${fr?"Photo":"Photo"}</span><b>${fr?"Feuille de maïs":"Maize leaf"}</b></div>
   <div class="row"><span>${fr?"Diagnostic":"Diagnosis"}</span><b>${fr?"Chenille légionnaire (probable)":"Fall armyworm (likely)"}</b></div>
   <div class="row"><span>${fr?"Action":"Action"}</span><b>${fr?"Inspecter les cornets, traiter tôt":"Check the whorls, treat early"}</b></div>
   <div class="note">${fr?"Le modèle de diagnostic est entraîné pendant la phase de construction.":"The diagnosis model is trained in the build phase. This shows the output format."}</div></div>`;
  h+=foot();panel.innerHTML=h;
}

function renderCocoa(){
  const g=S.pin.g,fr=S.lang==="fr";
  const flagged=g.forest>.62&&g.cocoa>.2;const suit=g.cocoa;
  const due=S.kg*S.price,paid=S.kg*S.offer,gap=due-paid;
  let h=header(fr?"traçabilité cacao":"cocoa traceability");
  h+=`<div class="kpis">${kpi(Math.round(suit*100),"%",t("suit"),suit)}${kpi(Math.round(g.forest*100),"%",t("forest"),g.forest)}</div>`;
  if(suit<.18)h+=`<div class="card"><h3>${fr?"Hors de la ceinture cacao":"Outside the cocoa belt"}<span class="pill warn">${fr?"Info":"Info"}</span></h3><div class="sub">${fr?"Placez le repère dans le sud-ouest ou le centre-ouest pour voir une ferme cacaoyère.":"Drop the pin in the south-west or centre-west to see a cocoa farm. Try near Soubré or Daloa."}</div><div class="btns"><button class="btn ghost" data-jump="-6.6,5.79">Soubré</button><button class="btn ghost" data-jump="-6.45,6.88">Daloa</button></div></div>`;
  h+=`<div class="card"><h3>${t("voice")}<span class="tag">FR · Baoulé · Dioula</span></h3><div class="sub">${fr?"Le planteur écoute son résumé, pas besoin de lire.":"Farmers hear their summary read aloud, so reading isn't needed."}</div><div class="btns"><button class="btn" id="speak">🔊 ${fr?"Écouter en français":"Play in French"}</button></div><div class="note">${fr?"Voix baoulé et dioula enregistrées en phase de construction.":"Baoulé and Dioula voice packs are recorded with native speakers in the build phase."}</div></div>`;
  h+=`<div class="card"><h3>${t("price")}<span class="pill ${gap>0?"bad":"ok"}">${gap>0?(fr?"Sous le prix officiel":"Below official price"):(fr?"Prix juste":"Fair price")}</span></h3>
   <div class="fields"><label class="field"><span>${fr?"Poids pesé (kg)":"Weighed (kg)"}</span><input id="kg" type="number" value="${S.kg}"></label><label class="field"><span>${fr?"Prix officiel /kg":"Official /kg"}</span><input id="price" type="number" value="${S.price}"></label><label class="field"><span>${fr?"Offre acheteur /kg":"Buyer offer /kg"}</span><input id="offer" type="number" value="${S.offer}"></label></div>
   <div class="row" style="margin-top:8px"><span>${fr?"Montant dû":"Amount due"}</span><b>${fmt(due)} FCFA</b></div>
   <div class="row"><span>${fr?"Offre de l'acheteur":"Buyer is offering"}</span><b>${fmt(paid)} FCFA</b></div>
   <div class="row"><span>${fr?"Écart":"Shortfall"}</span><b style="color:${gap>0?"#c93a1e":"#0b7d70"}">${gap>0?"−":""}${fmt(Math.abs(gap))} FCFA</b></div>
   <div class="btns"><button class="btn navy" id="receipt">${fr?"Reçu de pesée numérique":"Digital weighing receipt"}</button></div>
   <div class="note">${fr?"Prix de démonstration. En production, il suit l'annonce du Conseil du Café-Cacao.":"Demo price. In production it updates from the Conseil du Café-Cacao announcement each season."}</div></div>`;
  h+=`<div class="card"><h3>${t("eu")}<span class="pill ${flagged?"bad":"ok"}">${flagged?(fr?"À vérifier":"Review needed"):(fr?"Conforme":"Compliant")}</span></h3><div class="sub">${flagged?(fr?"Couvert forestier en baisse détecté près de cette parcelle depuis le 31/12/2020.":"Tree-cover loss detected near this plot after 31 Dec 2020. Flagged for a field check."):(fr?"Aucune déforestation détectée après le 31/12/2020.":"No deforestation detected on this plot after 31 Dec 2020, the EU cut-off date.")}</div><div class="btns"><button class="btn" id="cert">${fr?"Générer en un clic":"Generate in one click"}</button></div></div>`;
  h+=`<div class="card"><h3>${t("forecast")}<span class="tag">${fr?"Simulé":"Simulated"}</span></h3><div class="sub">${fr?"Arrivées mensuelles au port, campagne 2026/27":"Monthly port arrivals, 2026/27 season"}</div><canvas class="chart" id="chart"></canvas>
   <div class="row"><span>${fr?"Total prévu":"Season forecast"}</span><b>1.85 Mt ± 0.12</b></div>
   <div class="bars">${[["Nawa · Soubré",.21],["Haut-Sassandra",.13],["Gôh · Gagnoa",.1],["San-Pédro",.09],["Lôh-Djiboua",.08],["Indénié-Djuablin",.06]].map(r=>`<div class="b"><span>${r[0]}</span><div style="width:${r[1]*260}px"></div><em>${Math.round(r[1]*100)}%</em></div>`).join("")}</div>
   <div class="note">${fr?"Modèle satellite : vigueur des cacaoyers, pluie et humidité du sol, mis à jour chaque semaine.":"Satellite model: tree vigour, rainfall and soil moisture, updated weekly. Traders see the crop months before arrivals."}</div></div>`;
  h+=foot();panel.innerHTML=h;
  drawChart();
  const sp=document.getElementById("speak");sp.onclick=()=>speak();
  ["kg","price","offer"].forEach(id=>{const el=document.getElementById(id);el.onchange=()=>{S[id]=Math.max(0,+el.value||0);const y=panel.scrollTop;renderPanel();panel.scrollTop=y;};});
  document.getElementById("receipt").onclick=openReceipt;document.getElementById("cert").onclick=openCert;
  panel.querySelectorAll("[data-jump]").forEach(b=>b.onclick=()=>{const[lo,la]=b.dataset.jump.split(",").map(Number);setPin(lo+.05,la-.04,true);});
}
function drawChart(){const cv=document.getElementById("chart");if(!cv)return;const dpr=Math.min(devicePixelRatio||1,2),w=cv.clientWidth,h=170;cv.width=w*dpr;cv.height=h*dpr;const c=cv.getContext("2d");c.scale(dpr,dpr);
  const A=[180,290,330,265,190,120,80,100,120,90,45,35],L=["O","N","D","J","F","M","A","M","J","J","A","S"];const max=380,px=i=>12+i*(w-24)/11,py=v=>h-22-v/max*(h-34);
  c.strokeStyle="rgba(10,27,51,.07)";c.lineWidth=1;for(let i=0;i<4;i++){c.beginPath();c.moveTo(0,py(i*100));c.lineTo(w,py(i*100));c.stroke();}
  c.beginPath();A.forEach((v,i)=>{const u=v*(1.08+i*.012);i?c.lineTo(px(i),py(u)):c.moveTo(px(i),py(u));});for(let i=11;i>=0;i--)c.lineTo(px(i),py(A[i]*(.92-i*.012)));c.closePath();c.fillStyle="rgba(21,84,224,.12)";c.fill();
  c.beginPath();A.forEach((v,i)=>i?c.lineTo(px(i),py(v)):c.moveTo(px(i),py(v)));c.strokeStyle="#1554E0";c.lineWidth=2.4;c.stroke();
  A.forEach((v,i)=>{c.beginPath();c.arc(px(i),py(v),i===2?4.5:2.6,0,7);c.fillStyle=i===2?"#FF5A3C":"#1554E0";c.fill();});
  c.fillStyle="#6B7A90";c.font="500 10px JetBrains Mono";c.textAlign="center";L.forEach((l,i)=>c.fillText(l,px(i),h-6));
  c.textAlign="left";c.fillStyle="#0A1B33";c.font="700 11px Inter";c.fillText((S.lang==="fr"?"Pic déc. ":"Dec peak ")+"330 kt",px(2)+8,py(330)+4);}
function speak(){const g=S.pin.g;const txt=`Bonjour. Votre parcelle près de ${S.pin.near.name}. Aptitude au cacao : ${Math.round(g.cocoa*100)} pour cent. Prix officiel : ${fmt(S.price)} francs CFA le kilo. Pour ${fmt(S.kg)} kilos, vous devez recevoir ${fmt(S.kg*S.price)} francs CFA.`;
  try{const u=new SpeechSynthesisUtterance(txt);u.lang="fr-FR";u.rate=.95;speechSynthesis.cancel();speechSynthesis.speak(u);}catch(e){openModal(`<h2>🔊</h2><p class="sub" style="margin-top:10px">${txt}</p><p class="note">Voice playback isn't available in this viewer. The app reads this aloud.</p>`);}}

function renderCommand(){const fr=S.lang==="fr";const served=SITES.filter(s=>s[3]!=="down").reduce((a,s)=>a+s[4],0),ok=SITES.filter(s=>s[3]==="ok").length,al=SITES.filter(s=>s[3]!=="ok").length;
  let h=`<div class="eyebrow mono">${t("command")} · ${fr?"vue nationale":"national view"}</div><h2>${t("fleet")}</h2><div class="sub">${fr?"Pour les gouvernements, ONG et grands installateurs.":"For governments, NGOs and large installers. Tap a site to fly to it."}</div>`;
  h+=`<div class="kpis">${kpi(SITES.length,"",t("sites"))}${kpi(fmt(served),"",t("served"))}${kpi(Math.round(ok/SITES.length*100),"%",t("working"),ok/SITES.length)}${kpi(al,"",t("alerts"))}</div>`;
  h+=`<div class="card"><h3>${fr?"Sites":"Sites"}<span class="tag mono">LIVE · DEMO</span></h3>${SITES.map((s,i)=>`<div class="site" data-site="${i}"><span class="dot" style="background:#${STATUSC[s[3]].toString(16).padStart(6,"0")}"></span><div><b>${s[0]}</b><span>${fmt(s[4])} ${fr?"personnes":"people"}</span></div><span class="pill ${s[3]==="ok"?"ok":s[3]==="warn"?"warn":"bad"}">${s[3]==="ok"?(fr?"En marche":"Working"):s[3]==="warn"?(fr?"Alerte":"Alert"):(fr?"En panne":"Down")}</span></div>`).join("")}</div>`;
  h+=foot();panel.innerHTML=h;
  panel.querySelectorAll("[data-site]").forEach(el=>el.onclick=()=>{const s=SITES[+el.dataset.site];const[x,z]=toXZ(s[1],s[2]);flyTo(x,z,isMobile()?60:44);});}
function foot(){return `<div class="foot mono">NSKO SOLUTIONS · ${S.lang==="fr"?"DÉMO · DONNÉES SIMULÉES":"DEMO · SIMULATED DATA"}<br>${S.lang==="fr"?"Construit en code, sans matériel":"Built in code, no hardware"}</div>`;}

/* ---------------- modals ---------------- */
const modal=document.getElementById("modal"),mbody=document.getElementById("mbody");
function openModal(html){mbody.innerHTML=html;modal.classList.add("open");}
document.getElementById("mclose").onclick=()=>modal.classList.remove("open");
modal.onclick=e=>{if(e.target===modal)modal.classList.remove("open");};

const GUIDES={
rope:{en:"Rope pump build guide",fr:"Guide : pompe à corde",svg:`<svg viewBox="0 0 560 320" xmlns="http://www.w3.org/2000/svg" font-family="Inter" font-size="11">
<rect x="0" y="150" width="560" height="170" fill="#E9DFCF"/><rect x="0" y="146" width="560" height="6" fill="#C9B796"/>
<g class="part" data-s="0"><rect x="215" y="150" width="70" height="160" fill="#F7F2EA" stroke="#8A7558" stroke-width="2"/>${[0,1,2,3,4].map(i=>`<rect x="211" y="${158+i*30}" width="78" height="24" rx="3" fill="none" stroke="#6B7A90" stroke-width="3"/>`).join("")}<rect x="219" y="268" width="62" height="38" fill="#7FD4FF" opacity=".7"/><text x="300" y="250" fill="#42536B">concrete rings</text></g>
<g class="part" data-s="1"><rect x="244" y="60" width="12" height="244" fill="#E6EEFD" stroke="#1554E0" stroke-width="2"/><path d="M256 92 h36 v10" fill="none" stroke="#1554E0" stroke-width="7"/><text x="300" y="120" fill="#1554E0">PVC rising pipe</text></g>
<g class="part" data-s="2"><path d="M200 146 L232 40 L268 40 L300 146" fill="none" stroke="#071A36" stroke-width="5"/><circle cx="250" cy="52" r="34" fill="none" stroke="#071A36" stroke-width="5"/><circle cx="250" cy="52" r="5" fill="#071A36"/><path d="M250 52 L300 30" stroke="#FF5A3C" stroke-width="5"/><circle cx="300" cy="30" r="6" fill="#FF5A3C"/><text x="315" y="34" fill="#071A36">bicycle wheel + handle</text></g>
<g class="part" data-s="3"><path d="M216 52 V300 M284 52 V80" stroke="#A0683A" stroke-width="2.5" fill="none" stroke-dasharray="1 0"/>${[0,1,2,3,4,5,6].map(i=>`<rect x="243" y="${110+i*28}" width="14" height="5" fill="#A0683A"/>`).join("")}<text x="60" y="210" fill="#A0683A">rope + washers</text><text x="60" y="224" fill="#A0683A">every ~1 m</text></g>
<g class="part" data-s="4"><rect x="180" y="140" width="140" height="12" rx="3" fill="#B8C2D2"/><rect x="292" y="100" width="40" height="30" rx="4" fill="#19B8A6" opacity=".85"/><text x="340" y="120" fill="#0b7d70">bucket · test flow</text></g>
</svg>`,steps:{en:[["Dig and line the well","Dig to below the dry-season water level. Lower concrete rings as you go so the walls can't collapse. Never dig alone, and keep a rope and helper at the top."],["Fit the rising pipe","Run 1-inch PVC pipe from the top to about 50 cm above the bottom of the well. Add a spout at the top where the water will come out."],["Build the wheel frame","Mount an old bicycle rim on a steel or hardwood frame over the well, with a crank handle. The rim carries the rope."],["Thread the rope and washers","Tie rubber or plastic washers onto the rope about every metre. The loop goes down outside the pipe and comes up inside it, lifting water."],["Seal the top and test","Pour a concrete slab with a sealed cover to keep dirt and animals out. Turn the handle and time how fast a bucket fills."]],
fr:[["Creuser et cuveler le puits","Creusez sous le niveau d'eau de saison sèche. Descendez des buses en béton au fur et à mesure. Ne creusez jamais seul."],["Poser le tuyau montant","Tuyau PVC de 1 pouce jusqu'à 50 cm du fond du puits, avec un bec de sortie en haut."],["Monter la roue","Fixez une jante de vélo sur un cadre au-dessus du puits, avec une manivelle."],["Enfiler la corde et les rondelles","Attachez des rondelles tous les mètres environ. La corde descend dehors et remonte dans le tuyau."],["Fermer et tester","Coulez une dalle avec couvercle étanche. Tournez et mesurez le temps pour remplir un seau."]]},
parts:{en:"1\" PVC pipe · rope (8 mm) · rubber washers · old bicycle rim · steel or wood frame · cement + sand for rings and slab",fr:"Tuyau PVC 1\" · corde 8 mm · rondelles caoutchouc · jante de vélo · cadre acier ou bois · ciment + sable"}},
rain:{en:"Rainwater harvesting guide",fr:"Guide : eau de pluie",svg:`<svg viewBox="0 0 560 320" xmlns="http://www.w3.org/2000/svg" font-family="Inter" font-size="11">
<rect x="0" y="280" width="560" height="40" fill="#E9DFCF"/>
<path d="M70 150 L190 80 L310 150 Z" fill="#B8C2D2"/><rect x="90" y="150" width="200" height="130" fill="#F7F2EA" stroke="#8A7558"/><rect x="170" y="210" width="40" height="70" fill="#8A7558"/>
<g class="part" data-s="0"><path d="M300 152 h40" stroke="#1554E0" stroke-width="8" stroke-linecap="round"/><text x="300" y="140" fill="#1554E0">gutter</text></g>
<g class="part" data-s="1"><path d="M336 152 v40" stroke="#1554E0" stroke-width="7"/><rect x="326" y="192" width="20" height="40" rx="4" fill="#E6EEFD" stroke="#1554E0" stroke-width="2"/><text x="250" y="250" fill="#1554E0">first-flush</text></g>
<g class="part" data-s="2"><rect x="380" y="262" width="130" height="18" fill="#9AA6B8"/><text x="400" y="300" fill="#42536B">raised base</text></g>
<g class="part" data-s="3"><path d="M346 200 h44" stroke="#1554E0" stroke-width="6"/><rect x="390" y="150" width="110" height="112" rx="10" fill="#E6EEFD" stroke="#0D3FB3" stroke-width="3"/><rect x="394" y="196" width="102" height="62" rx="6" fill="#7FD4FF" opacity=".75"/><rect x="420" y="142" width="50" height="10" rx="3" fill="#071A36"/><text x="410" y="135" fill="#071A36">screened lid</text></g>
<g class="part" data-s="4"><path d="M500 245 h22 v14" stroke="#19B8A6" stroke-width="6" fill="none"/><circle cx="522" cy="268" r="5" fill="#19B8A6"/><text x="440" y="120" fill="#0b7d70">tap · clean twice a year</text></g>
</svg>`,steps:{en:[["Fit gutters","Fix gutters along the lower edge of a metal roof, sloping gently towards one corner."],["Add a first-flush diverter","A short closed pipe catches the first dirty water from the roof before it reaches the tank. Empty it after each storm."],["Build a raised base","Make a level concrete or block base so the tank sits above the ground and gravity feeds the tap."],["Install a covered tank","Use a covered plastic or ferro-cement tank with a mesh screen on the inlet to keep mosquitoes and leaves out."],["Add a tap and keep it clean","Fit the tap a few centimetres above the tank floor. Clean the tank and gutters before each rainy season."]],
fr:[["Poser les gouttières","Fixez des gouttières sous le bord du toit en tôle, en légère pente vers un coin."],["Ajouter un séparateur de premières eaux","Un tuyau fermé recueille la première eau sale du toit. Videz-le après chaque pluie."],["Construire un socle","Socle en béton ou en parpaings pour surélever le réservoir."],["Installer un réservoir couvert","Réservoir fermé avec moustiquaire à l'entrée contre les moustiques et les feuilles."],["Robinet et entretien","Robinet à quelques centimètres du fond. Nettoyez avant chaque saison des pluies."]]},
parts:{en:"Gutters + brackets · 100 mm downpipe · first-flush pipe · mesh screen · plastic or ferro-cement tank · tap · blocks + cement",fr:"Gouttières · descente 100 mm · séparateur · moustiquaire · réservoir · robinet · parpaings + ciment"}}};
let gStep=0,gKey="rope";
function openGuide(k){gKey=k;gStep=0;drawGuide();}
function drawGuide(){const G=GUIDES[gKey],L=S.lang,st=G.steps[L];
  openModal(`<div class="guide"><div class="eyebrow mono">${S.lang==="fr"?"Guide de construction":"Build guide"} · ${gStep+1}/${st.length}</div><h2>${G[L]}</h2>${G.svg}<div class="steps">${st.map((s,i)=>`<button class="${i<=gStep?"on":""}" data-st="${i}"></button>`).join("")}</div><div class="stepbox"><h4>${gStep+1}. ${st[gStep][0]}</h4><p>${st[gStep][1]}</p></div><div class="btns"><button class="btn ghost" id="gPrev">← ${S.lang==="fr"?"Retour":"Back"}</button><button class="btn" id="gNext">${gStep<st.length-1?(S.lang==="fr"?"Étape suivante":"Next step")+" →":(S.lang==="fr"?"Terminé":"Done")+" ✓"}</button></div><div class="parts"><h3>${S.lang==="fr"?"Liste des pièces · marchés locaux":"Parts list · local markets"}</h3><div class="sub">${G.parts[L]}</div><div class="note">${S.lang==="fr"?"Guide animé en 3D et PDF hors-ligne dans l'application finale.":"The full app animates each step in 3D and saves an offline PDF in the local language."}</div></div></div>`);
  mbody.querySelectorAll(".part").forEach(p=>{const s=+p.dataset.s;p.classList.toggle("hl",s===gStep);p.classList.toggle("done",s<gStep);});
  mbody.querySelectorAll("[data-st]").forEach(b=>b.onclick=()=>{gStep=+b.dataset.st;drawGuide();});
  document.getElementById("gPrev").onclick=()=>{gStep=Math.max(0,gStep-1);drawGuide();};
  document.getElementById("gNext").onclick=()=>{if(gStep<st.length-1){gStep++;drawGuide();}else modal.classList.remove("open");};}
function qr(seed){let s="";for(let y=0;y<21;y++)for(let x=0;x<21;x++){const f=(x<7&&y<7)||(x>13&&y<7)||(x<7&&y>13);let on;if(f){const lx=x>13?x-14:x,ly=y>13?y-14:y;on=(lx===0||lx===6||ly===0||ly===6||(lx>1&&lx<5&&ly>1&&ly<5));}else on=hash(x+seed,y*1.7+seed)>.5;s+=`<i class="${on?"":"o"}"></i>`;}return `<div class="qr">${s}</div>`;}
function openReceipt(){const fr=S.lang==="fr",id="RC-"+Math.floor(hash(S.pin.lon,S.pin.lat)*900000+100000),now=new Date();const due=S.kg*S.price,paid=S.kg*S.offer;
  openModal(`<div class="eyebrow mono">${fr?"Reçu numérique":"Digital receipt"}</div><h2>${fr?"Reçu de pesée":"Weighing receipt"}</h2><div class="receipt" style="margin-top:14px">
  <div class="row"><span>${fr?"Reçu n°":"Receipt"}</span><b>${id}</b></div><div class="row"><span>${fr?"Date":"Date"}</span><b>${now.toLocaleDateString("en-GB")} ${now.toTimeString().slice(0,5)}</b></div>
  <div class="row"><span>${fr?"Coopérative":"Co-op"}</span><b>COOP-${S.pin.near.name.toUpperCase().slice(0,4)}-07</b></div><div class="row"><span>${fr?"Planteur":"Farmer"}</span><b>CI-${Math.floor(hash(S.pin.lat,1)*90000+10000)}</b></div>
  <div class="row"><span>${fr?"Poids net":"Net weight"}</span><b>${fmt(S.kg)} kg</b></div><div class="row"><span>${fr?"Prix officiel":"Official price"}</span><b>${fmt(S.price)} FCFA/kg</b></div>
  <div class="row"><span>${fr?"Montant dû":"Amount due"}</span><b>${fmt(due)} FCFA</b></div><div class="row"><span>${fr?"Payé":"Paid"}</span><b>${fmt(paid)} FCFA</b></div>
  <div class="row"><span>${fr?"Statut":"Status"}</span><b style="color:${due>paid?"#c93a1e":"#0b7d70"}">${due>paid?(fr?"ÉCART SIGNALÉ":"SHORTFALL FLAGGED"):"OK"}</b></div>${qr(S.kg%97)}</div>
  <div class="note">${fr?"Copie envoyée par SMS au téléphone du planteur (démo).":"A copy goes to the farmer's phone by text, so the weight and price can't be changed later. (Demo)"}</div>`);}
function openCert(){const g=S.pin.g,fr=S.lang==="fr",flag=g.forest>.62&&g.cocoa>.2,id="NSKO-CI-"+Math.floor(hash(S.pin.lon*3,S.pin.lat)*9e6+1e6),area=(1.2+hash(S.pin.lat,S.pin.lon)*4).toFixed(2);
  const fc20=Math.round(18+g.forest*40),fcNow=flag?Math.round(fc20-6-g.forest*10):fc20+1;
  openModal(`<div class="cert"><div style="display:flex;gap:14px;align-items:center"><div class="seal" style="background:${flag?"#FF5A3C":"#19B8A6"}">${flag?(fr?"À<br>VÉRIFIER":"REVIEW"):(fr?"CONFORME":"PASS")}</div><div><div class="eyebrow mono">${fr?"Diligence raisonnée · RDUE":"Due diligence · EUDR"}</div><h2>${fr?"Certificat zéro déforestation":"Deforestation-free certificate"}</h2></div></div>
  <div style="margin-top:16px"><div class="row"><span>${fr?"Identifiant parcelle":"Plot ID"}</span><b class="mono">${id}</b></div><div class="row"><span>${fr?"Géolocalisation":"Geolocation"}</span><b class="mono">${S.pin.lat.toFixed(5)}, ${S.pin.lon.toFixed(5)}</b></div><div class="row"><span>${fr?"Surface (polygone)":"Area (polygon)"}</span><b>${area} ha</b></div><div class="row"><span>${fr?"Couvert arboré au 31/12/2020":"Tree cover at 31 Dec 2020"}</span><b>${fc20}%</b></div><div class="row"><span>${fr?"Couvert arboré actuel":"Tree cover now"}</span><b>${fcNow}%</b></div><div class="row"><span>${fr?"Production":"Commodity"}</span><b>${fr?"Fèves de cacao":"Cocoa beans"} · HS 1801</b></div><div class="row"><span>${fr?"Résultat":"Result"}</span><b style="color:${flag?"#c93a1e":"#0b7d70"}">${flag?(fr?"Perte de couvert, contrôle terrain requis":"Cover loss, field check required"):(fr?"Aucune déforestation après la date limite":"No deforestation after the cut-off date")}</b></div></div>
  <div class="btns"><button class="btn" id="copyCert">${fr?"Copier le résumé":"Copy summary"}</button></div><div class="note">${fr?"Certificat de démonstration, pas un document légal.":"Demo certificate built from simulated imagery. Not a legal document."}</div></div>`);
  document.getElementById("copyCert").onclick=async e=>{try{await navigator.clipboard.writeText(`${id} | ${S.pin.lat.toFixed(5)},${S.pin.lon.toFixed(5)} | ${area} ha | ${flag?"REVIEW":"PASS"}`);e.target.textContent=fr?"Copié ✓":"Copied ✓";}catch(_){e.target.textContent=fr?"Copie impossible ici":"Copy blocked here";}};}

/* ---------------- chrome ---------------- */
const tabsEl=document.getElementById("tabs");
function renderTabs(){tabsEl.innerHTML=["water","farm","cocoa","command"].map(k=>`<button class="tab ${S.tab===k?"on":""}" data-tab="${k}"><i></i>${t(k)}</button>`).join("");
  tabsEl.querySelectorAll("[data-tab]").forEach(b=>b.onclick=()=>{S.tab=b.dataset.tab;renderTabs();applyLayer();
    if(S.tab==="cocoa"&&S.pin&&S.pin.g.cocoa<.18&&!S.userPinned)setPin(-6.55,5.85,true);
    if(S.tab==="command")flyTo(0,0,isMobile()?185:118);else if(S.pin){const[x,z]=toXZ(S.pin.lon,S.pin.lat);flyTo(x,z);}
    panel.scrollTop=0;renderPanel();});
  document.getElementById("lang").textContent=S.lang==="en"?"FR":"EN";
  document.getElementById("hintText").textContent=t("hint");
  document.getElementById("badge").textContent=S.lang==="fr"?"DÉMO · DONNÉES SIMULÉES":"DEMO · SIMULATED DATA";}
document.getElementById("lang").onclick=()=>{S.lang=S.lang==="en"?"fr":"en";S.sms=[];renderTabs();renderLegend();renderPanel();};
function renderLegend(){const L=document.getElementById("legend");const m={water:[t("layerW"),"linear-gradient(90deg,#E9F0FC,#8FB3F2,#1554E0,#0A2A7A)","Low","High"],farm:[t("layerF"),"linear-gradient(90deg,#F2E6CB,#BFD9B0,#19B8A6,#0B7D70)","Dry","Wet"],cocoa:[t("layerC"),"linear-gradient(90deg,#F4EEE6,#DCC2A0,#A0683A,#5E3416)","Low","High"],command:[t("layerX"),"linear-gradient(90deg,#19B8A6 0 33%,#F2A33A 33% 66%,#FF5A3C 66%)","Working","Down"]}[S.tab];
  L.innerHTML=`<div class="t"><span>${m[0]}</span><span class="mono" style="color:var(--muted)">LAYER</span></div><div class="g" style="background:${m[1]}"></div><div class="s mono"><span>${m[2]}</span><span>${m[3]}</span></div>${S.tab==="cocoa"?`<div class="x"><span style="color:#FF5A3C">■</span> ${S.lang==="fr"?"Rouge : cacao près d'une forêt à risque":"Red: cocoa near at-risk forest"}</div>`:""}<div class="x">${S.lang==="fr"?"Glisser pour tourner · pincer pour zoomer":"Drag to orbit · pinch or scroll to zoom"}</div>`;}

renderTabs();applyLayer();
setPin(-6.35,7.05,false);
{const[x,z]=toXZ(-6.35,7.05);fly={t:0,p0:camera.position.clone(),t0:controls.target.clone(),p1:new THREE.Vector3(x+8,isMobile()?118:62,z+(isMobile()?112:62)),t1:new THREE.Vector3(x*.4,0,z*.4)};}
loop();
})();
