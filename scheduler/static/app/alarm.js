/* Browser fallback alarm. The desktop .exe runs its own native engine and sets
   "DailyScheduleDesktop" in the user agent, so this stays idle there. */
(function () {
  'use strict';
  if (navigator.userAgent.indexOf('DailyScheduleDesktop') !== -1) return;

  var fired = {}, timers = [], audioCtx = null, ringTimer = null, overlay = null;
  var enabled = false;
  try { enabled = localStorage.getItem('alarmArmed') === '1'; } catch (e) {}

  function ctx() {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    return audioCtx;
  }

  function tone() {
    if (!audioCtx) return;
    [880, 1100, 880, 1100].forEach(function (f, i) {
      var o = audioCtx.createOscillator(), g = audioCtx.createGain();
      o.type = 'square';
      o.frequency.value = f;
      g.gain.value = 0.15 * (window.__alarmVolume || 0.8);
      o.connect(g);
      g.connect(audioCtx.destination);
      var t = audioCtx.currentTime + i * 0.22;
      o.start(t);
      o.stop(t + 0.16);
    });
  }

  function stopRing() {
    clearInterval(ringTimer);
    ringTimer = null;
    if (overlay) { overlay.remove(); overlay = null; }
  }

  function ring(ev, cfg) {
    stopRing();
    if (window.Notification && Notification.permission === 'granted') {
      new Notification(ev.title, { body: ev.message, requireInteraction: true });
    }
    overlay = document.createElement('div');
    overlay.setAttribute('role', 'alertdialog');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;' +
      'background:rgba(10,14,39,.92);color:#f8fafc;font-family:system-ui,sans-serif;text-align:center';
    var btn = 'padding:.8rem 1.4rem;margin:.3rem;border-radius:10px;border:0;color:#fff;font-size:1rem;cursor:pointer;';
    overlay.innerHTML = '<div><div style="font-size:4rem">' + (ev.kind === 'prayer' ? '🕌' : '⏰') + '</div>' +
      '<h1 style="font-size:2.2rem;margin:.5rem 0"></h1><p style="color:#cbd5e1;margin-bottom:1.5rem"></p>' +
      '<button data-a="snooze" style="' + btn + 'background:#7c3aed">Snooze ' + cfg.snooze_minutes + ' min</button>' +
      '<button data-a="dismiss" style="' + btn + 'background:#334155">Dismiss</button></div>';
    overlay.querySelector('h1').textContent = ev.title;
    overlay.querySelector('p').textContent = ev.message;
    overlay.addEventListener('click', function (e) {
      var a = e.target.getAttribute && e.target.getAttribute('data-a');
      if (a === 'snooze') {
        stopRing();
        setTimeout(function () { ring(ev, cfg); }, cfg.snooze_minutes * 60000);
      }
      if (a === 'dismiss') stopRing();
    });
    document.body.appendChild(overlay);
    tone();
    ringTimer = setInterval(tone, 1500);
    setTimeout(function () { if (overlay) stopRing(); }, cfg.ring_seconds * 1000);
  }

  function schedule() {
    timers.forEach(clearTimeout);
    timers = [];
    if (!enabled) return;
    fetch('/api/alarms/today/').then(function (r) { return r.json(); }).then(function (d) {
      window.__alarmVolume = d.settings.volume / 100;
      var now = Date.now();
      d.events.forEach(function (ev) {
        if (fired[ev.key]) return;
        var delay = new Date(ev.at).getTime() - now;
        if (delay < -60000) return;
        timers.push(setTimeout(function () { fired[ev.key] = 1; ring(ev, d.settings); }, Math.max(0, delay)));
      });
    }).catch(function () {});
  }

  function badge() {
    var b = document.createElement('button');
    b.id = 'alarmArmBtn';
    b.style.cssText = 'position:fixed;right:14px;bottom:14px;z-index:9000;padding:.5rem .9rem;border-radius:999px;' +
      'border:1px solid rgba(124,58,237,.5);background:rgba(15,23,42,.9);color:#e2e8f0;cursor:pointer;font-size:.85rem';
    function label() { b.textContent = enabled ? '⏰ Alarms armed' : '🔕 Enable alarms'; }
    label();
    b.onclick = function () {
      enabled = !enabled;
      try { localStorage.setItem('alarmArmed', enabled ? '1' : '0'); } catch (e) {}
      if (enabled) {
        ctx();
        if (window.Notification && Notification.permission === 'default') Notification.requestPermission();
        tone();
      }
      label();
      schedule();
    };
    document.body.appendChild(b);
  }

  badge();
  if (enabled) {
    // Browsers need a click before audio can play; unlock on the first interaction.
    document.addEventListener('click', function init() {
      ctx();
      document.removeEventListener('click', init);
    });
  }
  schedule();
  setInterval(schedule, 5 * 60000);
})();
