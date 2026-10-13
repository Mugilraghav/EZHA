document.addEventListener('DOMContentLoaded', async () => {
  const formatCount = (value) => {
    const n = Number(value) || 0;
    if (n >= 1000) return `${Math.round(n / 100) / 10}k+`.replace('.0k', 'k');
    return `${n}`;
  };

  try {
    const statsResponse = await fetch('/api/v1/public/stats');
    const statsPayload = await statsResponse.json();
    if (statsPayload.success) {
      const { bookings_completed, verified_artists } = statsPayload.data;
      const bookingsEl = document.querySelector('[data-stat-bookings]');
      const artistsEl = document.querySelector('[data-stat-artists]');
      if (bookingsEl) bookingsEl.textContent = formatCount(bookings_completed);
      if (artistsEl) artistsEl.textContent = formatCount(verified_artists);
    }
  } catch {
    /* keep static fallbacks */
  }

  try {
    const configResponse = await fetch('/api/v1/public/site-config');
    const configPayload = await configResponse.json();
    if (configPayload.success) {
      const { hero_image_url, founder_image_url, founder_name, support_email } = configPayload.data;
      const heroImg = document.querySelector('#landing-hero-image');
      if (heroImg && hero_image_url) heroImg.src = hero_image_url;
      const founderImg = document.querySelector('#founder-image');
      if (founderImg && founder_image_url) founderImg.src = founder_image_url;
      const founderName = document.querySelector('#founder-name');
      if (founderName && founder_name) founderName.textContent = founder_name;
      const supportLink = document.querySelector('#footer-support-email');
      if (supportLink && support_email) {
        supportLink.href = `mailto:${support_email}`;
        supportLink.textContent = support_email;
      }
    }
  } catch {
    /* defaults remain in HTML */
  }
});
