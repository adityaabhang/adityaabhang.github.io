import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js';
import { PLYLoader } from 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/loaders/PLYLoader.js';

document.querySelectorAll('.pc-viewer[data-clouds]').forEach(initViewer);

function initViewer(root) {
  const clouds = JSON.parse(root.dataset.clouds);
  const defaultKey = root.dataset.default || clouds[0].key;
  const wrap = root.querySelector('.pc-canvas-wrap');
  const canvas = root.querySelector('.pc-canvas');
  const status = root.querySelector('.pc-status');
  const select = root.querySelector('.pc-select');
  const resetBtn = root.querySelector('.pc-reset');

  clouds.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.key;
    opt.textContent = c.label;
    if (c.key === defaultKey) opt.selected = true;
    select.appendChild(opt);
  });

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x12151a, 1);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, 1, 0.01, 1000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;

  let currentPoints = null;
  let defaultView = null;
  let loadToken = 0;

  function resize() {
    const w = wrap.clientWidth, h = wrap.clientHeight;
    if (w === 0 || h === 0) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(wrap);
  resize();

  const loader = new PLYLoader();

  function loadCloud(key) {
    const entry = clouds.find(c => c.key === key);
    if (!entry) return;
    const token = ++loadToken;
    status.textContent = 'Loading reconstruction…';
    status.classList.remove('hidden');

    loader.load(entry.file, geometry => {
      if (token !== loadToken) return; // a newer selection superseded this load

      geometry.rotateX(Math.PI / 2); // reconstruction is Z-forward with floor at +Z; rotate so floor sits at the bottom in Three.js's Y-up frame

      const posAttr = geometry.getAttribute('position');
      const n = posAttr.count;
      const box = new THREE.Box3().setFromBufferAttribute(posAttr);
      const center = box.getCenter(new THREE.Vector3());
      geometry.translate(-center.x, -center.y, -center.z);

      // percentile extent: a robust radius that ignores stray outlier points
      const dists = new Float32Array(n);
      for (let i = 0; i < n; i++) {
        const dx = posAttr.getX(i) - 0, dy = posAttr.getY(i) - 0, dz = posAttr.getZ(i) - 0;
        dists[i] = Math.sqrt(dx * dx + dy * dy + dz * dz);
      }
      const sorted = Array.from(dists).sort((a, b) => a - b);
      const radius = sorted[Math.floor(n * 0.95)] || sorted[n - 1] || 1;

      if (currentPoints) {
        scene.remove(currentPoints);
        currentPoints.geometry.dispose();
        currentPoints.material.dispose();
      }

      const hasColor = geometry.hasAttribute('color');
      const material = new THREE.PointsMaterial({
        size: Math.max(radius / 220, 0.004),
        vertexColors: hasColor,
        color: hasColor ? 0xffffff : 0x8fb3d9,
      });

      currentPoints = new THREE.Points(geometry, material);
      scene.add(currentPoints);

      camera.near = Math.max(radius / 100, 0.001);
      camera.far = radius * 20;
      camera.updateProjectionMatrix();

      const dist = radius * 2.4;
      camera.position.set(dist * 0.5, dist * 0.35, dist * 0.9);
      controls.target.set(0, 0, 0);
      controls.update();
      defaultView = { pos: camera.position.clone(), target: controls.target.clone() };

      status.classList.add('hidden');
    }, undefined, err => {
      if (token !== loadToken) return;
      status.textContent = 'Could not load this reconstruction.';
      console.error('[pointcloud-viewer]', err);
    });
  }

  select.addEventListener('change', () => loadCloud(select.value));
  resetBtn.addEventListener('click', () => {
    if (!defaultView) return;
    camera.position.copy(defaultView.pos);
    controls.target.copy(defaultView.target);
    controls.update();
  });

  (function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  })();

  loadCloud(defaultKey);
}
