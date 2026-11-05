"""Injection navigateur : balayage tactile entre tableaux de bord.

Le serveur ajoute ce bloc dans chaque page de compteur. Un balayage horizontal
(ou les fleches gauche/droite) passe au compteur precedent/suivant du
catalogue `/api/dashboards`. Desactive dans une iframe (apercu des reglages).
"""

NAV_HTML = """<style>
  html, body { touch-action: none; overscroll-behavior: none; }
</style>
<script>
/* idash-swipe */
(() => {
  const META = window.__IDASH__ || {};
  if (!META.spec || window.top !== window.self) return;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const store = {
    get(k) { try { return sessionStorage.getItem(k); } catch (_) { return null; } },
    set(k, v) { try { sessionStorage.setItem(k, v); } catch (_) {} },
    del(k) { try { sessionStorage.removeItem(k); } catch (_) {} },
  };
  let items = null, busy = false;

  async function target(dir) {
    if (items === null) {
      try {
        const r = await fetch('/api/dashboards', { cache: 'no-store' });
        items = (await r.json()).dashboards || [];
      } catch (_) {
        items = [];
      }
    }
    if (items.length < 2) return null;
    const i = items.findIndex(x => x.spec === META.spec);
    if (i < 0) return null;
    return items[(i + dir + items.length) % items.length];
  }

  async function go(dir) {
    if (busy) return;
    busy = true;
    const item = await target(dir);
    if (!item) { busy = false; return; }
    store.set('idash-dir', String(dir));
    const qs = location.search.slice(1).split('&')
      .filter(p => p && !/^dashboard(=|$)/.test(p)).join('&');
    const url = item.url + (qs ? '?' + qs : '');
    const svg = document.querySelector('svg');
    if (!svg || reduce) { location.href = url; return; }
    svg.style.transition = 'transform .16s ease, opacity .16s ease';
    svg.style.transform = 'translateX(' + (dir > 0 ? -60 : 60) + 'px)';
    svg.style.opacity = '0';
    setTimeout(() => { location.href = url; }, 150);
  }

  const prev = Number(store.get('idash-dir') || 0);
  store.del('idash-dir');
  if (prev && !reduce) {
    addEventListener('DOMContentLoaded', () => {
      const svg = document.querySelector('svg');
      if (!svg) return;
      svg.animate([
        { opacity: .25, transform: 'translateX(' + (prev > 0 ? 60 : -60) + 'px)' },
        { opacity: 1, transform: 'translateX(0)' },
      ], { duration: 200, easing: 'ease-out' });
    });
  }

  let sx = 0, sy = 0, st = 0, tracking = false;
  addEventListener('touchstart', e => {
    if (e.touches.length !== 1) return;
    sx = e.touches[0].clientX;
    sy = e.touches[0].clientY;
    st = performance.now();
    tracking = true;
  }, { passive: true });
  addEventListener('touchcancel', () => { tracking = false; }, { passive: true });
  addEventListener('touchend', e => {
    if (!tracking) return;
    tracking = false;
    const t = e.changedTouches[0];
    if (!t || performance.now() - st > 900) return;
    const dx = t.clientX - sx, dy = t.clientY - sy;
    if (Math.abs(dx) < 70 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
    e.preventDefault();
    go(dx < 0 ? 1 : -1);
  }, { passive: false });

  addEventListener('keydown', e => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); go(1); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); go(-1); }
  });
})();
</script>"""
