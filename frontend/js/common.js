(function initEzhaTheme() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function createLoader() {
    if (document.getElementById('ezha-loader')) return;
    const loader = document.createElement('div');
    loader.id = 'ezha-loader';
    loader.setAttribute('role', 'status');
    loader.setAttribute('aria-live', 'polite');
    loader.setAttribute('aria-label', 'Loading EZHA');
    loader.innerHTML = `
      <div class="ezha-loader-emblem">
        <div class="ezha-loader-ring" aria-hidden="true"></div>
        <img src="/static/assets/ezha-logo.png" alt="" width="56" height="56" />
      </div>`;
    document.body.prepend(loader);
    window.addEventListener('load', () => {
      loader.classList.add('is-hidden');
      setTimeout(() => loader.remove(), 600);
    });
    setTimeout(() => loader.classList.add('is-hidden'), prefersReducedMotion ? 120 : 900);
  }

  function initHeaderScroll() {
    const header = document.querySelector('.site-header');
    if (!header) return;
    const onScroll = () => header.classList.toggle('is-scrolled', window.scrollY > 12);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  function initReveal() {
    if (prefersReducedMotion) {
      document.querySelectorAll('.reveal, .reveal-stagger').forEach((el) => el.classList.add('is-visible'));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' },
    );
    document.querySelectorAll('.reveal, .reveal-stagger').forEach((el) => observer.observe(el));
  }

  function initPageTransition() {
    if (prefersReducedMotion) return;
    document.body.classList.add('ezha-page-enter');
    document.querySelectorAll('a[href^="/"]').forEach((link) => {
      const href = link.getAttribute('href');
      if (!href || href.startsWith('//') || link.target === '_blank' || link.hasAttribute('download')) return;
      if (href.includes('#') && !href.startsWith('/#')) return;
      link.addEventListener('click', (event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        const url = new URL(href, window.location.origin);
        if (url.origin !== window.location.origin) return;
        event.preventDefault();
        document.body.classList.add('ezha-page-exit');
        window.setTimeout(() => { window.location.href = url.pathname + url.search + url.hash; }, 280);
      });
    });
  }

  function initMobileNav() {
    const toggle = document.querySelector('.mobile-menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    if (!toggle || !navLinks) return;
    toggle.addEventListener('click', () => {
      const isOpen = navLinks.style.display === 'flex';
      navLinks.style.display = isOpen ? 'none' : 'flex';
      navLinks.style.flexDirection = 'column';
      navLinks.style.position = 'absolute';
      navLinks.style.top = '76px';
      navLinks.style.right = '16px';
      navLinks.style.background = 'rgba(3, 42, 36, 0.96)';
      navLinks.style.border = '1px solid rgba(212, 175, 55, 0.28)';
      navLinks.style.padding = '18px';
      navLinks.style.borderRadius = '16px';
      navLinks.style.boxShadow = 'var(--shadow-royal)';
      navLinks.style.zIndex = '50';
      navLinks.style.gap = '14px';
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    createLoader();
    initHeaderScroll();
    initReveal();
    initPageTransition();
    initMobileNav();
  });
})();
