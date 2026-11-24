// Prototype Lab viewer: poster first, then the GLB on a canvas you can drag. dpr capped at 1.5.
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
export function mount(host, name) {
  let gl; try { gl = new THREE.WebGLRenderer({antialias: true, alpha: true, powerPreference: 'low-power'}); } catch { return null; }
  const rm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  gl.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5)); gl.toneMapping = THREE.ACESFilmicToneMapping; gl.toneMappingExposure = .9; gl.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(30, 1, .01, 50);
  const pm = new THREE.PMREMGenerator(gl); scene.environment = pm.fromScene(new RoomEnvironment(), .04).texture;
  const rim = new THREE.DirectionalLight(0xcfe0ec, 2.2); rim.position.set(2, 2, -3); scene.add(rim);
  const key = new THREE.DirectionalLight(0xffffff, 1.2); key.position.set(-2, 3, 2); scene.add(key);
  const c = gl.domElement; c.style.cssText = 'position:absolute;inset:0;opacity:0;transition:opacity .8s cubic-bezier(.22,1,.36,1);touch-action:none;cursor:grab';
  c.setAttribute('aria-label', 'Drag to turn the model'); c.setAttribute('role', 'img'); host.appendChild(c);
  const ctl = new OrbitControls(cam, c); ctl.enableZoom = false; ctl.enablePan = false; ctl.enableDamping = true; ctl.autoRotate = !rm; ctl.autoRotateSpeed = .8;
  let raf = 0, dead = false;
  const size = () => { const w = host.clientWidth, h = host.clientHeight; gl.setSize(w, h, false); c.style.width = '100%'; c.style.height = '100%'; cam.aspect = w / h; cam.updateProjectionMatrix(); };
  const ro = new ResizeObserver(size); ro.observe(host); size();
  new GLTFLoader().load(`/media/v42/glb/${name}.glb`, g => {
    if (dead) return; const o = g.scene; const box = new THREE.Box3().setFromObject(o), ctr = box.getCenter(new THREE.Vector3()), r = box.getSize(new THREE.Vector3()).length() / 2;
    o.position.sub(ctr); scene.add(o); cam.position.set(0, r * .55, r * 3.2); ctl.target.set(0, 0, 0); ctl.update();
    const loop = () => { if (dead) return; ctl.update(); gl.render(scene, cam); raf = requestAnimationFrame(loop); }; loop();
    c.style.opacity = 1; const img = host.querySelector('img'); if (img) img.style.opacity = 0;
  });
  return {dispose() { dead = true; cancelAnimationFrame(raf); ro.disconnect(); ctl.dispose(); gl.dispose(); pm.dispose(); c.remove(); }};
}
