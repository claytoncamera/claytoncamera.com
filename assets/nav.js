/* Mobile menu for the site header (620px and below).
   The same code runs inline on /index.html, which must render with zero
   extra requests; if you change one, change the other. Without JS the
   header keeps its pre-menu behaviour (the html.js class gates the CSS). */
(function () {
  var header = document.querySelector('.top-header');
  var btn = header && header.querySelector('.nav-toggle');
  var nav = document.getElementById('primary-nav');
  if (!btn || !nav) return;

  function setOpen(open) {
    header.classList.toggle('menu-open', open);
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  function isOpen() { return header.classList.contains('menu-open'); }

  btn.addEventListener('click', function (e) {
    var open = !isOpen();
    setOpen(open);
    // Opened from the keyboard (detail 0): move focus into the panel.
    if (open && e.detail === 0) { var first = nav.querySelector('a'); if (first) first.focus(); }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isOpen()) { setOpen(false); btn.focus(); }
  });
  document.addEventListener('click', function (e) {
    if (isOpen() && !header.contains(e.target)) setOpen(false);
  });
  header.addEventListener('focusout', function (e) {
    if (isOpen() && e.relatedTarget && !header.contains(e.relatedTarget)) setOpen(false);
  });
  var wide = window.matchMedia('(min-width: 621px)');
  var onWide = function (e) { if (e.matches) setOpen(false); };
  if (wide.addEventListener) wide.addEventListener('change', onWide);
  else if (wide.addListener) wide.addListener(onWide);
})();
