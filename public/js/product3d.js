// NSKO product viewer: live 3D, 360° spin, explode and reassemble, zoom to a part. dpr capped at 1.5.
// Poster first; the GLB loads only when its section is on screen, and the WebGL context is freed when it leaves.
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const ease = t => 1 - Math.pow(1 - t, 3);
export function mount(host, opts = {}) {
  let gl; try { gl = new THREE.WebGLRenderer({antialias: true, alpha: true, powerPreference: 'high-performance'}); } catch { return null; }
  gl.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5)); gl.toneMapping = THREE.ACESFilmicToneMapping; gl.toneMappingExposure = 1.0;
  gl.outputColorSpace = THREE.SRGBColorSpace; gl.shadowMap.enabled = true; gl.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(32, 1, .01, 100);
  const pm = new THREE.PMREMGenerator(gl); scene.environment = pm.fromScene(new RoomEnvironment(), .03).texture; scene.environmentIntensity = .55;
  const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(-2.5, 4, 3); key.castShadow = true; key.shadow.mapSize.set(1024, 1024); key.shadow.radius = 6;
  Object.assign(key.shadow.camera, {left: -2, right: 2, top: 2, bottom: -2, near: .1, far: 12}); scene.add(key);
  const rim = new THREE.DirectionalLight(0xcfe0ec, 2.6); rim.position.set(3, 2.5, -3); scene.add(rim);
  const rim2 = new THREE.DirectionalLight(0xcfe0ec, 1.2); rim2.position.set(-3, 1.5, -2.5); scene.add(rim2);
  const ground = new THREE.Mesh(new THREE.CircleGeometry(3, 64), new THREE.ShadowMaterial({opacity: .45})); ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);
  const c = gl.domElement; c.className = 'p3d-c'; c.setAttribute('role', 'img'); c.setAttribute('aria-label', (opts.label || 'NSKO product') + ', interactive 3D. Drag to turn.'); host.appendChild(c);
  const ctl = new OrbitControls(cam, c); ctl.enableZoom = false; ctl.enablePan = false; ctl.enableDamping = true; ctl.dampingFactor = .08;
  ctl.autoRotate = !RM; ctl.autoRotateSpeed = 1.1; ctl.minPolarAngle = .35; ctl.maxPolarAngle = 1.45;
  const model = new THREE.Group(); scene.add(model);
  let parts = [], amt = 0, target = 0, raf = 0, dead = false, tween = null, home = null, ready = false;
  const size = () => { const w = host.clientWidth, h = host.clientHeight; if (!w || !h) return; gl.setSize(w, h, false); c.style.width = '100%'; c.style.height = '100%'; cam.aspect = w / h; cam.updateProjectionMatrix(); };
  const ro = new ResizeObserver(size); ro.observe(host); size();
  new GLTFLoader().load(opts.src, g => {
    if (dead) return;
    const src = g.scene; src.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(src), ctr = box.getCenter(new THREE.Vector3()), sz = box.getSize(new THREE.Vector3()), s = 1.6 / Math.max(sz.x, sz.y, sz.z);
    const meshes = []; src.traverse(o => { if (o.isMesh) meshes.push(o); });
    for (const m of meshes) { model.attach(m); m.castShadow = true; m.receiveShadow = true; if (m.material) { m.material.envMapIntensity = 1; } }
    model.scale.setScalar(s); model.position.set(-ctr.x * s, -box.min.y * s, -ctr.z * s);
    model.updateMatrixWorld(true);
    const mc = new THREE.Vector3(0, sz.y * s / 2, 0);
    for (const m of meshes) {
      const wc = new THREE.Box3().setFromObject(m).getCenter(new THREE.Vector3());
      const d = wc.clone().sub(mc); const len = d.length(); d.normalize(); d.y *= 1.35;
      const off = d.multiplyScalar(.06 + len * .42).divideScalar(s);   // in model space
      parts.push({m, base: m.position.clone(), off, wc});
    }
    const H = sz.y * s; ground.position.y = 0; home = {pos: new THREE.Vector3(2.6, H * .55 + .55, 3.4).multiplyScalar(opts.hero ? .62 : 1), tgt: new THREE.Vector3(0, H * .48, 0)};
    cam.position.copy(home.pos); ctl.target.copy(home.tgt); ctl.update();
    host.classList.add('live'); ready = true; opts.onReady?.();
    if (opts.intro && !RM) { setTimeout(() => set(true), 700); setTimeout(() => set(false), 3300); }
  }, undefined, () => host.classList.add('err'));
  function set(on) { target = on ? 1 : 0; opts.onExplode?.(on); }
  function focus(at) {  // at = [fx,fy,fz] fractions of the bounding box; zoom to the nearest part as it is now
    if (!ready) return; ctl.autoRotate = false; opts.onSpin?.(false);
    const b = new THREE.Box3().setFromObject(model), p = new THREE.Vector3(b.min.x + (b.max.x - b.min.x) * at[0], b.min.y + (b.max.y - b.min.y) * at[1], b.min.z + (b.max.z - b.min.z) * at[2]);
    let best = null, bd = 1e9; for (const q of parts) { const wc = new THREE.Box3().setFromObject(q.m).getCenter(new THREE.Vector3()); const d = wc.distanceTo(p); if (d < bd) { bd = d; best = wc; } }
    const tgt = best.clone().lerp(p, .35), dir = cam.position.clone().sub(ctl.target).normalize();
    go(tgt.clone().add(dir.multiplyScalar(.75)), tgt);
  }
  function go(pos, tgt) { tween = {t: 0, p0: cam.position.clone(), t0: ctl.target.clone(), p1: pos, t1: tgt}; }
  function reset() { set(false); if (home) go(home.pos.clone(), home.tgt.clone()); }
  let last = performance.now();
  const loop = now => {
    if (dead) return; const dt = Math.min(.05, (now - last) / 1000); last = now;
    if (Math.abs(amt - target) > .001) { amt += (target - amt) * Math.min(1, dt * 3.2); const e = ease(amt); for (const q of parts) q.m.position.copy(q.base).addScaledVector(q.off, e); }
    if (tween) { tween.t = Math.min(1, tween.t + dt / .9); const e = ease(tween.t); cam.position.lerpVectors(tween.p0, tween.p1, e); ctl.target.lerpVectors(tween.t0, tween.t1, e); if (tween.t >= 1) tween = null; }
    ctl.update(); gl.render(scene, cam); raf = requestAnimationFrame(loop);
  };
  raf = requestAnimationFrame(loop);
  return {
    explode: on => set(on), get exploded() { return target === 1; },
    spin: on => { ctl.autoRotate = on && !RM; }, focus, reset,
    dispose() { dead = true; cancelAnimationFrame(raf); ro.disconnect(); ctl.dispose(); scene.traverse(o => { o.geometry?.dispose?.(); }); gl.dispose(); pm.dispose(); c.remove(); host.classList.remove('live'); },
  };
}
