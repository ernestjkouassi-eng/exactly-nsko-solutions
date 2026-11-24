// Impact tabs: click, arrow keys, and #water / #health / #climate links.
(() => { const tabs = [...document.querySelectorAll('[role=tab]')];
  const pick = (t, f) => { tabs.forEach(x => { const on = x === t; x.setAttribute('aria-selected', on); x.setAttribute('aria-pressed', on); x.tabIndex = on ? 0 : -1;
    document.getElementById(x.getAttribute('aria-controls')).classList.toggle('on', on); }); if (f) t.focus(); history.replaceState(null, '', '#' + t.getAttribute('aria-controls')); };
  tabs.forEach((t, i) => { t.addEventListener('click', () => pick(t)); t.addEventListener('keydown', e => { if (e.key === 'ArrowRight') pick(tabs[(i + 1) % tabs.length], 1); if (e.key === 'ArrowLeft') pick(tabs[(i + tabs.length - 1) % tabs.length], 1); }); });
  const h = location.hash.slice(1); const t = tabs.find(x => x.getAttribute('aria-controls') === h); if (t) pick(t);
})();
