document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.mobile-menu-toggle');
  const navLinks = document.querySelector('.nav-links');

  if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
      const isOpen = navLinks.style.display === 'flex';
      navLinks.style.display = isOpen ? 'none' : 'flex';
      navLinks.style.flexDirection = 'column';
      navLinks.style.position = 'absolute';
      navLinks.style.top = '72px';
      navLinks.style.right = '18px';
      navLinks.style.background = 'rgba(255,255,255,0.96)';
      navLinks.style.border = '1px solid rgba(110, 33, 66, 0.08)';
      navLinks.style.padding = '18px';
      navLinks.style.borderRadius = '18px';
      navLinks.style.boxShadow = '0 20px 40px rgba(94, 49, 69, 0.12)';
    });
  }
});
