import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';

/* "Ask NSKO": the ceramic robot. Scroll through the tall section to move camera: intro, close-up, principles. */
export function initNova(root, opts = {}) {
  const stage = root.querySelector('.nv-stage'), canvas = root.querySelector('#nv-gl');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:true});
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), .04).texture;
  scene.environmentIntensity = .9;
  const camera = new THREE.PerspectiveCamera(30, 1, .1, 60);
  scene.add(new THREE.HemisphereLight(0xf2f7ff, 0xcfd6e0, .7));
  const key = new THREE.DirectionalLight(0xf2f6ff, 1.7); key.position.set(-3, 5, 4); key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024); key.shadow.radius = 6; key.shadow.bias = -.0005;
  Object.assign(key.shadow.camera, {left:-4, right:4, top:5, bottom:-5, near:1, far:20}); scene.add(key);
  const rim = new THREE.DirectionalLight(0xe6f0ff, 1.2); rim.position.set(4, 2, -4); scene.add(rim);
  const warm = new THREE.PointLight(0xE8541A, 2.2, 6); warm.position.set(-3.2, 1.2, .6); scene.add(warm);

  const shell = new THREE.MeshPhysicalMaterial({color:0xeeebe6, roughness:.38, clearcoat:.45, clearcoatRoughness:.3});
  const shellL = new THREE.MeshPhysicalMaterial({color:0xf8f6f2, roughness:.34, clearcoat:.45, clearcoatRoughness:.3});
  const dark = new THREE.MeshStandardMaterial({color:0x1b1b1f, roughness:.55, metalness:.3});
  const deep = new THREE.MeshStandardMaterial({color:0x0f0f12, roughness:.6});
  const pedMat = new THREE.MeshStandardMaterial({color:0x2a2928, roughness:.9});

  // gradient ring texture: NSKO blue -> ice -> teal
  const rc = document.createElement('canvas'); rc.width = rc.height = 512;
  { const c = rc.getContext('2d'), g = c.createConicGradient ? c.createConicGradient(Math.PI * .6, 256, 256) : null;
    if (g) { ['#1C1D21', '#8A8F98', '#E8541A', '#F5F5F2', '#E8541A', '#8A8F98', '#1C1D21'].forEach((col, i, a) => g.addColorStop(i / (a.length - 1), col)); c.fillStyle = g; } else c.fillStyle = '#1554E0';
    c.fillRect(0, 0, 512, 512); }
  const ringTex = new THREE.CanvasTexture(rc); ringTex.colorSpace = THREE.SRGBColorSpace;
  const ringMat = new THREE.MeshPhysicalMaterial({map:ringTex, emissiveMap:ringTex, emissive:0xffffff, emissiveIntensity:.22, roughness:.5, clearcoat:.35});

  const rr = (w, h, r) => { const s = new THREE.Shape(), x = -w / 2, y = -h / 2; s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r); s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h); s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r); s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y); return s; };
  const sh = m => { m.castShadow = true; m.receiveShadow = true; return m; };
  const box = (w, h, d, r, m) => sh(new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 4, r), m));

  const robot = new THREE.Group(); scene.add(robot);
  // pedestal
  const ped = new THREE.Mesh(new THREE.BoxGeometry(1.7, 1.6, 1.7), pedMat); ped.position.y = -2.22; ped.receiveShadow = true; scene.add(ped);
  // torso
  const torso = box(1.22, 1.12, .92, .24, shell); robot.add(torso);
  const slab = box(1.0, .12, .7, .05, shellL); slab.position.set(0, .56, 0); robot.add(slab);
  [[0xff5a3c, -.24], [0x19B8A6, 0], [0x1554E0, .24]].forEach(([c, x]) => { const m = new THREE.Mesh(new THREE.SphereGeometry(.045, 12, 10), new THREE.MeshStandardMaterial({color:c, emissive:c, emissiveIntensity:1.4})); m.position.set(x, .22, .47); robot.add(m); });
  [-.2, .2].forEach(x => { const s = box(.1, .34, .05, .02, deep); s.position.set(x, -.12, .47); robot.add(s); const lip = new THREE.Mesh(new THREE.TorusGeometry(.05, .014, 6, 12, Math.PI), dark); lip.position.set(x, .06, .47); robot.add(lip); });
  const pelvis = box(.9, .18, .7, .06, dark); pelvis.position.y = -.65; robot.add(pelvis);
  const neck = sh(new THREE.Mesh(new THREE.CylinderGeometry(.18, .22, .2, 16), dark)); neck.position.y = .66; robot.add(neck);
  // head
  const head = new THREE.Group(); head.position.set(0, .76, 0); robot.add(head);
  const hc = new THREE.Group(); hc.position.y = .78; head.add(hc);
  hc.add(box(1.5, 1.42, 1.3, .2, shell));
  const back = box(1.28, 1.14, .9, .1, dark); back.position.z = -.5; hc.add(back);
  for (let i = 0; i < 26; i++) { const b = new THREE.Mesh(new THREE.BoxGeometry(.05 + (i % 3) * .05, .02, .02), deep); b.position.set(((i * 37) % 100 / 100 - .5) * 1.0, ((i * 53) % 100 / 100 - .5) * .9, -.96); hc.add(b); }
  const frameShape = rr(1.5, 1.44, .3); frameShape.holes.push(new THREE.Path(rr(1.08, 1.02, .2).getPoints(14)));
  const fg = new THREE.ExtrudeGeometry(frameShape, {depth:.1, bevelEnabled:true, bevelSize:.03, bevelThickness:.03, bevelSegments:2, curveSegments:14});
  { fg.computeBoundingBox(); const bb = fg.boundingBox, uv = fg.attributes.uv, p = fg.attributes.position; for (let i = 0; i < uv.count; i++) uv.setXY(i, (p.getX(i) - bb.min.x) / (bb.max.x - bb.min.x), (p.getY(i) - bb.min.y) / (bb.max.y - bb.min.y)); }
  const frame = sh(new THREE.Mesh(fg, ringMat)); frame.position.z = .6; hc.add(frame);
  const bezel = new THREE.Mesh(new THREE.ExtrudeGeometry((() => { const s = rr(1.08, 1.02, .2); s.holes.push(new THREE.Path(rr(.92, .86, .13).getPoints(12))); return s; })(), {depth:.03, bevelEnabled:false}), shellL); bezel.position.z = .62; hc.add(bezel);
  const fc = document.createElement('canvas'); fc.width = fc.height = 512; const fx = fc.getContext('2d');
  const faceTex = new THREE.CanvasTexture(fc); faceTex.colorSpace = THREE.SRGBColorSpace;
  const screen = new THREE.Mesh(new RoundedBoxGeometry(.9, .84, .05, 3, .08), new THREE.MeshPhysicalMaterial({color:0x050507, roughness:.1, clearcoat:1, emissive:0xffffff, emissiveMap:faceTex, emissiveIntensity:1.6}));
  screen.position.z = .66; hc.add(screen);
  [-1, 1].forEach(s => { const ear = sh(new THREE.Mesh(new THREE.CylinderGeometry(.22, .22, .1, 24).rotateZ(Math.PI / 2), shellL)); ear.position.set(s * .8, 0, 0); hc.add(ear); const cap = sh(new THREE.Mesh(new THREE.CylinderGeometry(.14, .14, .06, 20).rotateZ(Math.PI / 2), dark)); cap.position.set(s * .86, 0, 0); hc.add(cap); });
  const cable = new THREE.Mesh(new THREE.TorusGeometry(.2, .03, 8, 20, Math.PI), dark); cable.position.set(.86, -.2, 0); cable.rotation.z = Math.PI; hc.add(cable);
  // arms and legs
  const arms = [];
  [-1, 1].forEach(s => {
    const sho = new THREE.Group(); sho.position.set(s * .72, .36, 0); robot.add(sho); sho.rotation.z = s * .16;
    const ball = sh(new THREE.Mesh(new THREE.SphereGeometry(.14, 16, 12), dark)); sho.add(ball);
    const up = box(.2, .55, .22, .08, shell); up.position.y = -.34; sho.add(up);
    const elbow = new THREE.Group(); elbow.position.y = -.64; sho.add(elbow);
    elbow.add(sh(new THREE.Mesh(new THREE.SphereGeometry(.11, 14, 10), dark)));
    const fore = new THREE.Group(); fore.rotation.x = -.35; elbow.add(fore);
    const fa = box(.18, .5, .2, .07, shell); fa.position.y = -.3; fore.add(fa);
    const hand = box(.22, .2, .24, .07, shellL); hand.position.y = -.62; fore.add(hand);
    const th = box(.07, .12, .08, .03, shellL); th.position.set(-s * .13, -.6, .04); fore.add(th);
    arms.push({sho, fore, s});
    const hip = sh(new THREE.Mesh(new THREE.SphereGeometry(.12, 14, 10), dark)); hip.position.set(s * .3, -.74, 0); robot.add(hip);
    const leg = box(.3, .42, .32, .09, shell); leg.position.set(s * .3, -.98, 0); robot.add(leg);
    const ank = sh(new THREE.Mesh(new THREE.SphereGeometry(.09, 12, 10), dark)); ank.position.set(s * .3, -1.22, 0); robot.add(ank);
    const foot = box(.38, .16, .55, .07, shellL); foot.position.set(s * .3, -1.34, .08); robot.add(foot);
  });

  // face
  let faceMode = 'eyes', faceA = 1, blink = 0, nextBlink = 2.5, drawn = '';
  const drawFace = (t) => {
    const k = blink > 0 ? 1 - .9 * Math.sin(Math.min(1, blink / .18) * Math.PI) : 1;
    const key = faceMode + k.toFixed(2); if (key === drawn && faceA >= 1) return; drawn = key;
    fx.globalAlpha = faceA < 1 ? .35 : 1; fx.fillStyle = '#000'; fx.fillRect(0, 0, 512, 512); fx.globalAlpha = 1;
    fx.fillStyle = '#fff'; fx.shadowColor = '#fff'; fx.shadowBlur = 18;
    if (faceMode === 'eyes') { [[196, 262], [316, 252]].forEach(([x, y]) => { fx.beginPath(); fx.ellipse(x, y, 30, 38 * k, 0, 0, Math.PI * 2); fx.fill(); }); }
    else { fx.font = '560px "Arial Black", Arial, sans-serif'; fx.textAlign = 'center'; fx.fillText('“', 256, 400); }
    fx.shadowBlur = 0; faceTex.needsUpdate = true;
  };
  drawFace(0);

  // scroll + pointer
  let sp = 0, mx = 0, my = 0, smx = 0, smy = 0, visible = root.dataset.on === '1';
  const ec = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2, mixn = (a, b, t) => a + (b - a) * t;
  const resize = () => { const w = stage.clientWidth, h = stage.clientHeight; renderer.setPixelRatio(Math.min(devicePixelRatio, innerWidth < 900 ? 1.5 : 1.75)); renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); };
  addEventListener('resize', resize); resize();
  addEventListener('pointermove', e => { mx = e.clientX / innerWidth * 2 - 1; my = e.clientY / innerHeight * 2 - 1; });
  new MutationObserver(() => { visible = root.dataset.on === '1'; if (visible) resize(); }).observe(root, {attributes:true, attributeFilter:['data-on']});
  const panels = [...root.querySelectorAll('[data-nvp]')];
  let panelIdx = -1;
  const setPanel = i => { if (i === panelIdx) return; panelIdx = i; panels.forEach(p => p.classList.toggle('on', +p.dataset.nvp === i)); root.dataset.panel = i; opts.onPanel && opts.onPanel(i); };

  let t0 = performance.now();
  const tick = () => {
    requestAnimationFrame(tick);
    if (!visible) return;
    const now = performance.now(), t = (now - t0) / 1000;
    const p = root.__p !== undefined ? root.__p : Math.min(2, Math.max(0, -root.getBoundingClientRect().top / innerHeight));
    sp += (p - sp) * .08;
    smx += (mx - smx) * .06; smy += (my - smy) * .06;
    const a = ec(Math.min(1, sp)), mob = innerWidth < 900 ? 1.25 : 1;
    camera.position.set(mixn(0, 0, a) + smx * .25, mixn(1.1, 1.95, a) - smy * .1, mixn(11.6, 6.9, a) * mob);
    camera.lookAt(0, mixn(.55, 1.72, a), 0);
    robot.rotation.y = mixn(-.42, -.2, a) + smx * .12;
    const idle = reduced ? 0 : 1;
    robot.position.y = Math.sin(t * 1.4) * .02 * idle;
    head.rotation.set(mixn(.16, .04, a) + smy * .18 + Math.sin(t * .9) * .02 * idle, mixn(-.6, -.06, a) + smx * .45, mixn(.22, 0, a) + Math.sin(t * .7) * .02 * idle);
    arms.forEach(m => { m.sho.rotation.x = Math.sin(t * 1.4 + m.s) * .05 * idle; m.fore.rotation.x = -.35 + Math.sin(t * 1.4 + m.s) * .06 * idle; });
    const wantQuote = sp > 1.55; if ((faceMode === 'quote') !== wantQuote) { faceMode = wantQuote ? 'quote' : 'eyes'; faceA = 0; drawn = ''; }
    if (faceA < 1) faceA = Math.min(1, faceA + .06);
    if (!reduced) { nextBlink -= 1 / 60; if (nextBlink < 0 && blink <= 0) { blink = .18; nextBlink = 2.5 + Math.random() * 3; } if (blink > 0) { blink -= 1 / 60; if (blink <= 0) drawn = ''; } }
    drawFace(t);
    setPanel(sp < .5 ? 0 : sp < 1.5 ? 1 : 2);
    renderer.render(scene, camera);
  };
  requestAnimationFrame(tick);

  // typing prompts + tab carousel
  const prompts = opts.prompts || [], el = root.querySelector('#nv-type'), nx = root.querySelector('#nv-next');
  if (el && prompts.length) {
    let pi = 0, ci = 0, dir = 1, wait = 0;
    const step = () => {
      const txt = prompts[pi];
      if (reduced) { el.textContent = txt; nx && (nx.textContent = prompts[(pi + 1) % prompts.length]); pi = (pi + 1) % prompts.length; setTimeout(step, 3500); return; }
      if (dir > 0) { ci++; el.textContent = txt.slice(0, ci); if (ci >= txt.length) { dir = -1; nx && (nx.textContent = prompts[(pi + 1) % prompts.length]); return setTimeout(step, 2600); } setTimeout(step, 38); }
      else { ci = Math.max(0, ci - 2); el.textContent = txt.slice(0, ci); if (ci === 0) { dir = 1; pi = (pi + 1) % prompts.length; return setTimeout(step, 250); } setTimeout(step, 14); }
    };
    step();
  }
  const strip = root.querySelector('#nv-strip');
  if (strip && !reduced) { let i = 0; const n = strip.children.length; setInterval(() => { if (!visible) return; i = (i + 1) % n; [...strip.children].forEach((c, k) => c.classList.toggle('act', k === i)); strip.style.transform = `translateX(${-i * 33}vw)`; }, 2400); }
  if (strip) strip.children[0].classList.add('act');
}
