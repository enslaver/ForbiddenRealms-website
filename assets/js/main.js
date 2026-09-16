/* Forbidden Realms site behaviour. No dependencies. */
(function () {
  'use strict';

  document.documentElement.classList.add('js');

  // Set to your mailing-list endpoint (Buttondown, Mailchimp, Formspree...) that
  // accepts POST {"email": "..."}. Empty shows the holding message.
  var FOLLOW_ENDPOINT = '';

  /* Top bar */
  var top = document.querySelector('.top');
  var toggle = document.querySelector('.top__toggle');
  var nav = document.getElementById('menu');

  function onScroll() { top.classList.toggle('is-scrolled', window.scrollY > 40); }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!open));
      toggle.setAttribute('aria-label', open ? 'Open menu' : 'Close menu');
      nav.classList.toggle('is-open', !open);
      top.classList.toggle('is-open', !open);
      document.body.style.overflow = open ? '' : 'hidden';
    });
    nav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () { if (nav.classList.contains('is-open')) toggle.click(); });
    });
  }

  /* The road: one stop open at a time */
  var stops = Array.prototype.slice.call(document.querySelectorAll('.road__stop'));
  stops.forEach(function (stop, i) {
    var btn = stop.querySelector('button');
    var text = stop.querySelector('.road__text');
    btn.addEventListener('click', function () {
      stops.forEach(function (s) {
        var open = s === stop;
        s.classList.toggle('is-active', open);
        s.querySelector('button').setAttribute('aria-expanded', String(open));
        s.querySelector('.road__text').hidden = !open;
      });
    });
    btn.addEventListener('keydown', function (e) {
      var next = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? i + 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? i - 1 : null;
      if (next === null || !stops[next]) return;
      e.preventDefault();
      stops[next].querySelector('button').focus();
    });
  });

  /* Class idle loops: attach sources and play only while on screen */
  var loops = Array.prototype.slice.call(document.querySelectorAll('.classes__loop'));
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (loops.length && !reduce && 'IntersectionObserver' in window) {
    var lio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var v = e.target;
        if (e.isIntersecting) {
          if (!v.dataset.loaded) {
            v.querySelectorAll('source').forEach(function (s) { s.src = s.dataset.src; });
            v.load();
            v.dataset.loaded = '1';
          }
          v.play().catch(function () {});
        } else {
          v.pause();
        }
      });
    }, { rootMargin: '200px 0px' });
    loops.forEach(function (v) { lio.observe(v); });
  }

  /* Lightbox */
  var box = document.getElementById('lightbox');
  if (box) {
    var items = Array.prototype.slice.call(document.querySelectorAll('.gallery__item'));
    var img = box.querySelector('.lightbox__img');
    var cap = box.querySelector('.lightbox__cap');
    var closeBtn = box.querySelector('.lightbox__close');
    var current = 0, lastFocus = null;

    function show(i) {
      current = (i + items.length) % items.length;
      var a = items[current];
      img.src = a.getAttribute('href');
      img.alt = a.querySelector('img').alt;
      cap.textContent = a.getAttribute('data-caption') || '';
      [1, -1].forEach(function (d) { new Image().src = items[(current + d + items.length) % items.length].getAttribute('href'); });
    }
    function open(i) {
      lastFocus = document.activeElement;
      box.hidden = false;
      requestAnimationFrame(function () { box.classList.add('is-visible'); });
      document.body.style.overflow = 'hidden';
      show(i);
      closeBtn.focus();
    }
    function close() {
      box.classList.remove('is-visible');
      document.body.style.overflow = '';
      setTimeout(function () { box.hidden = true; img.src = ''; }, 200);
      if (lastFocus) lastFocus.focus();
    }

    items.forEach(function (a, i) { a.addEventListener('click', function (e) { e.preventDefault(); open(i); }); });
    closeBtn.addEventListener('click', close);
    box.querySelector('.lightbox__prev').addEventListener('click', function () { show(current - 1); });
    box.querySelector('.lightbox__next').addEventListener('click', function () { show(current + 1); });
    box.addEventListener('click', function (e) { if (e.target === box) close(); });
    document.addEventListener('keydown', function (e) {
      if (box.hidden) return;
      if (e.key === 'Escape') close();
      else if (e.key === 'ArrowLeft') show(current - 1);
      else if (e.key === 'ArrowRight') show(current + 1);
    });
    var touchX = null;
    box.addEventListener('touchstart', function (e) { touchX = e.changedTouches[0].clientX; }, { passive: true });
    box.addEventListener('touchend', function (e) {
      if (touchX === null) return;
      var dx = e.changedTouches[0].clientX - touchX;
      if (Math.abs(dx) > 50) show(current + (dx < 0 ? 1 : -1));
      touchX = null;
    }, { passive: true });
  }

  /* Release-news form */
  var form = document.getElementById('follow-form');
  if (form) {
    var input = form.querySelector('input[type=email]');
    var msg = form.querySelector('.follow__msg');
    var btn = form.querySelector('button');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      msg.classList.remove('is-error');
      var email = (input.value || '').trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        msg.textContent = 'Enter a full email address, like you@example.com.';
        msg.classList.add('is-error');
        input.focus();
        return;
      }
      if (!FOLLOW_ENDPOINT) {
        msg.textContent = 'Sign-ups are not open yet. Check back soon.';
        return;
      }
      btn.disabled = true;
      fetch(FOLLOW_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ email: email })
      }).then(function (r) {
        if (!r.ok) throw new Error(r.status);
        msg.textContent = 'Added. We will notify ' + email + ' when there is news.';
        form.reset();
      }).catch(function () {
        msg.textContent = 'Could not add you just now. Try again in a minute.';
        msg.classList.add('is-error');
      }).then(function () { btn.disabled = false; });
    });
  }
})();
