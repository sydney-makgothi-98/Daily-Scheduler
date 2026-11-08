/* Home-page hero: a slowly turning "clock" made of a ring, an icosahedron and orbiting dots (Three.js r128).
   Respects prefers-reduced-motion and pauses when the tab is hidden. */
(function () {
  'use strict';
  var canvas = document.getElementById('hero3d');
  if (!canvas || !window.THREE) return;
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  camera.position.z = 6;

  var group = new THREE.Group();
  scene.add(group);
  var ring = new THREE.Mesh(new THREE.TorusGeometry(1.8, 0.06, 16, 120),
    new THREE.MeshStandardMaterial({ color: 0x7c3aed, metalness: 0.6, roughness: 0.3 }));
  var core = new THREE.Mesh(new THREE.IcosahedronGeometry(0.9, 1),
    new THREE.MeshStandardMaterial({ color: 0x0ea5e9, metalness: 0.3, roughness: 0.4, flatShading: true }));
  var wire = new THREE.Mesh(new THREE.IcosahedronGeometry(1.15, 1),
    new THREE.MeshBasicMaterial({ color: 0xa78bfa, wireframe: true, transparent: true, opacity: 0.35 }));
  group.add(ring, core, wire);

  var dots = [];
  for (var i = 0; i < 5; i++) {            // five dots: one per daily prayer
    var d = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 16), new THREE.MeshStandardMaterial({ color: 0xfacc15, emissive: 0x8a6d00 }));
    d.userData.angle = (i / 5) * Math.PI * 2;
    group.add(d); dots.push(d);
  }
  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  var light = new THREE.PointLight(0xffffff, 1.2); light.position.set(4, 4, 6); scene.add(light);

  var mx = 0, my = 0;
  addEventListener('mousemove', function (e) { mx = e.clientX / innerWidth - 0.5; my = e.clientY / innerHeight - 0.5; });

  function resize() {
    var w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  addEventListener('resize', resize); resize();

  var t = 0, running = true;
  document.addEventListener('visibilitychange', function () { running = !document.hidden; if (running) loop(); });
  function frame() {
    t += 0.01;
    ring.rotation.x = 1.1 + Math.sin(t) * 0.1; ring.rotation.z = t * 0.4;
    core.rotation.y = t * 0.8; core.rotation.x = t * 0.3; wire.rotation.y = -t * 0.5;
    dots.forEach(function (d) {
      var a = d.userData.angle + t;
      d.position.set(Math.cos(a) * 1.8, Math.sin(a) * 0.5, Math.sin(a) * 1.8);
    });
    group.rotation.y += (mx * 0.8 - group.rotation.y) * 0.05;
    group.rotation.x += (my * 0.5 - group.rotation.x) * 0.05;
    renderer.render(scene, camera);
  }
  function loop() { if (!running || reduce) return; frame(); requestAnimationFrame(loop); }
  frame();                                  // always draw one frame (static scene when motion is reduced)
  loop();
})();
