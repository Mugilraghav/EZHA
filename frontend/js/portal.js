document.addEventListener('DOMContentLoaded', () => {
  const tokenKey = 'ezha_access_token';
  const userKey = 'ezha_user';
  const message = document.querySelector('#auth-message');
  const savedUser = () => {
    try { return JSON.parse(localStorage.getItem(userKey) || 'null'); } catch { return null; }
  };
  const destination = (role) => ({ CUSTOMER: '/customer/services', ARTISAN: '/artisan/dashboard', VENDOR: '/artisan/dashboard', ADMIN: '/admin/dashboard' })[role] || '/login';
  const showMessage = (text, isError = false) => {
    if (!message) return;
    message.textContent = text;
    message.dataset.error = String(isError);
  };
  const token = localStorage.getItem(tokenKey);
  const user = savedUser();
  const requiredRole = document.body.dataset.requiresRole;
  if (window.location.pathname === '/' && token && user) {
    document.querySelector('#header-login')?.setAttribute('hidden', '');
    document.querySelector('#header-register')?.setAttribute('hidden', '');
    const portalLink = document.querySelector('#header-portal');
    if (portalLink) {
      portalLink.href = destination(user.role);
      portalLink.textContent = `My EZHA · ${user.name}`;
      portalLink.hidden = false;
    }
    const logoutButton = document.querySelector('#header-logout');
    if (logoutButton) logoutButton.hidden = false;
  }
  if (requiredRole && (!token || !user || user.role !== requiredRole)) {
    const returnTo = `${window.location.pathname}${window.location.search}`;
    window.location.replace(`/login?role=${requiredRole}&return_to=${encodeURIComponent(returnTo)}`);
    return;
  }

  document.querySelector('[data-focus-search]')?.addEventListener('click', () => {
    document.querySelector('#service-search')?.focus();
  });

  document.querySelector('#landing-search-form')?.addEventListener('submit', (event) => {
    event.preventDefault();
    const serviceQuery = document.querySelector('#service-search').value.trim();
    const cityQuery = document.querySelector('#location-search').value.trim();
    const query = new URLSearchParams();
    if (serviceQuery) query.set('q', serviceQuery);
    if (cityQuery) query.set('city', cityQuery);
    const returnTo = `/customer/services${query.size ? `?${query.toString()}` : ''}`;
    if (token && user?.role === 'CUSTOMER') {
      window.location.assign(returnTo);
    } else {
      window.location.assign(`/login?role=CUSTOMER&return_to=${encodeURIComponent(returnTo)}`);
    }
  });

  document.querySelectorAll('[data-logout]').forEach((button) => button.addEventListener('click', () => {
    localStorage.removeItem(tokenKey);
    localStorage.removeItem(userKey);
    window.location.assign('/');
  }));

  const loginForm = document.querySelector('#login-form');
  if (loginForm) {
    const params = new URLSearchParams(window.location.search);
    const roleSelect = loginForm.elements.role;
    const usernameInput = loginForm.elements.username;
    const artisanPayoutLogin = document.querySelector('#artisan-payout-login');
    const syncLoginRole = () => {
      if (artisanPayoutLogin) artisanPayoutLogin.hidden = roleSelect.value !== 'ARTISAN';
    };
    if (['CUSTOMER', 'ARTISAN', 'ADMIN'].includes(params.get('role'))) roleSelect.value = params.get('role');
    if (params.has('username')) usernameInput.value = params.get('username');
    roleSelect.addEventListener('change', syncLoginRole);
    syncLoginRole();
    loginForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = new FormData(loginForm);
      showMessage('Signing in…');
      try {
        const response = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: form.get('username'), password: form.get('password'), role: form.get('role') }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error?.message || 'Unable to sign in. Check your credentials.');
        localStorage.setItem(tokenKey, payload.data.access_token);
        localStorage.setItem(userKey, JSON.stringify(payload.data.user));
        if (payload.data.user.role === 'ARTISAN' && form.get('account_number') && form.get('ifsc_code')) {
          await fetch('/api/v1/artisan/payout-profile', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${payload.data.access_token}` },
            body: JSON.stringify({
              account_holder_name: form.get('account_holder_name'),
              account_number: form.get('account_number'),
              ifsc_code: form.get('ifsc_code'),
            }),
          });
        }
        const returnTo = params.get('return_to') || '';
        const allowedReturn = {
          CUSTOMER: returnTo.startsWith('/customer/services') ? returnTo : '',
          ARTISAN: returnTo === '/artisan/dashboard' ? returnTo : '',
          ADMIN: returnTo === '/admin/dashboard' ? returnTo : '',
        }[payload.data.user.role];
        const artisanDest = payload.data.user.role === 'ARTISAN' && form.get('account_number') ? '/artisan/dashboard#payments' : '';
        window.location.assign(allowedReturn || artisanDest || destination(payload.data.user.role));
      } catch (error) {
        showMessage(error.message, true);
      }
    });
  }

  const registerForm = document.querySelector('#register-form');
  if (registerForm) {
    const params = new URLSearchParams(window.location.search);
    const artisanFields = document.querySelector('#artisan-fields');
    const customerAddressFields = document.querySelector('#customer-address-fields');
    const syncArtisanFields = () => {
      const isArtisan = registerForm.elements.role.value === 'ARTISAN';
      const isCustomer = registerForm.elements.role.value === 'CUSTOMER';
      artisanFields.hidden = !isArtisan;
      if (customerAddressFields) customerAddressFields.hidden = !isCustomer;
      registerForm.elements.city.required = isArtisan;
      ['account_holder_name', 'account_number', 'ifsc_code'].forEach((name) => {
        if (registerForm.elements[name]) registerForm.elements[name].required = isArtisan;
      });
    };
    if (params.get('role') === 'ARTISAN') registerForm.elements.role.value = 'ARTISAN';
    registerForm.elements.role.addEventListener('change', syncArtisanFields);
    syncArtisanFields();
    registerForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = new FormData(registerForm);
      showMessage('Creating your account…');
      try {
        const response = await fetch('/api/v1/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(Object.fromEntries(form.entries())),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error?.message || 'Unable to create account.');
        const role = payload.data.role;
        showMessage('Account created. Continue to your ' + role.toLowerCase() + ' sign in.');
        const link = document.createElement('a');
        link.href = `/login?role=${role}&username=${encodeURIComponent(payload.data.username)}`;
        link.className = 'btn btn-primary';
        link.textContent = 'Continue to sign in';
        registerForm.querySelector('button[type="submit"]').replaceWith(link);
      } catch (error) {
        showMessage(error.message, true);
      }
    });
  }

  const apiGet = async (path) => {
    const response = await fetch(path, { headers: { Authorization: `Bearer ${localStorage.getItem(tokenKey) || ''}` } });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error?.message || 'Unable to load this page.');
    return payload.data;
  };
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
  const currency = (amount) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount || 0);
  const categoryNamesForUi = { MAKEUP: 'Makeup', MEHENDI: 'Mehendi', DRESS: 'Dress & tailoring', FULL_PACKAGE: 'Full package' };
  const themePrimary = () => getComputedStyle(document.documentElement).getPropertyValue('--button').trim() || '#a67c2e';

  const bookingPage = document.querySelector('#booking-page');
  if (bookingPage) {
    const params = new URLSearchParams(window.location.search);
    const workId = params.get('work_id');
    const form = document.querySelector('#booking-form');
    form.elements.date.min = new Date().toISOString().slice(0, 10);
    if (!workId) {
      document.querySelector('#booking-message').textContent = 'Choose a portfolio work before booking.';
      form.querySelector('button[type="submit"]').disabled = true;
    } else {
      apiGet('/api/v1/customers/artisans').then((data) => {
        const artisan = data.artisans.find((entry) => entry.works.some((work) => work.id === workId));
        const work = artisan?.works.find((entry) => entry.id === workId);
        if (!artisan || !work) throw new Error('This work is no longer available. Return to the catalog to choose another.');
        document.querySelector('#booking-title').textContent = work.title;
        document.querySelector('#booking-artisan').textContent = `${artisan.name} · ${artisan.city || 'India'} · Artisan ID ${artisan.id}`;
        document.querySelector('#booking-summary-title').textContent = work.title;
        document.querySelector('#booking-category').textContent = categoryNamesForUi[work.category] || work.category;
        document.querySelector('#booking-summary-artisan').textContent = artisan.name;
        document.querySelector('#booking-price').textContent = currency(work.price);
        const modeNote = document.querySelector('#service-mode-note');
        if (modeNote) {
          modeNote.textContent = work.category === 'DRESS'
            ? 'Tailoring & saree prep: you will send your outfit to the artisan’s address. They return it when the work is complete. Your address is used for pickup and delivery.'
            : 'Doorstep service: your artist will come to the address below for bridal makeup, mehendi, or styling.';
        }
        const image = document.querySelector('#booking-image');
        image.src = work.image_url;
        image.hidden = false;
        apiGet('/api/v1/customers/me').then((profileData) => {
          const profile = profileData.profile || {};
          if (profile.address_line1) form.elements.address_line1.value = profile.address_line1;
          if (profile.address_line2) form.elements.address_line2.value = profile.address_line2;
          if (profile.city) form.elements.address_city.value = profile.city;
          if (profile.state) form.elements.address_state.value = profile.state;
          if (profile.pincode) form.elements.pincode.value = profile.pincode;
        }).catch(() => {});
        form.addEventListener('submit', async (event) => {
          event.preventDefault();
          const formData = new FormData(form);
          const submitButton = form.querySelector('button[type="submit"]');
          submitButton.disabled = true;
          document.querySelector('#booking-message').textContent = 'Submitting booking request…';
          try {
            const response = await fetch('/api/v1/bookings', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem(tokenKey) || ''}` },
              body: JSON.stringify({
                work_id: workId,
                date: formData.get('date'),
                time: formData.get('time'),
                notes: formData.get('notes'),
                address_line1: formData.get('address_line1'),
                address_line2: formData.get('address_line2'),
                address_city: formData.get('address_city'),
                address_state: formData.get('address_state'),
                pincode: formData.get('pincode'),
              }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error?.message || 'Unable to submit this booking.');
            window.location.assign(`/checkout?booking_id=${encodeURIComponent(payload.data.id)}`);
          } catch (error) {
            document.querySelector('#booking-message').textContent = error.message;
            submitButton.disabled = false;
          }
        });
      }).catch((error) => {
        document.querySelector('#booking-message').textContent = error.message;
        form.querySelector('button[type="submit"]').disabled = true;
      });
    }
  }

  const checkoutPage = document.querySelector('#checkout-page');
  if (checkoutPage) {
    const bookingId = new URLSearchParams(window.location.search).get('booking_id');
    if (!bookingId) {
      document.querySelector('#checkout-message').textContent = 'No booking was selected. Return to services to choose an artisan work.';
    } else {
      apiGet(`/api/v1/bookings/${encodeURIComponent(bookingId)}`).then((booking) => {
        document.querySelector('#checkout-message').textContent = `Booking request ${booking.status.toLowerCase()}; no payment has been collected.`;
        document.querySelector('#checkout-artisan').textContent = `${booking.artisan_name} · ${booking.artisan_city || 'India'} · @${booking.artisan_username}`;
        document.querySelector('#checkout-work').textContent = `${booking.work_title} · ${categoryNamesForUi[booking.category] || booking.category}`;
        document.querySelector('#checkout-schedule').textContent = `${booking.date} at ${booking.time}`;
        const address = booking.service_address;
        if (address) {
          document.querySelector('#checkout-address').textContent = `${address.line1}${address.line2 ? `, ${address.line2}` : ''}, ${address.city}, ${address.state} ${address.pincode}`;
        }
        document.querySelector('#checkout-service-mode').textContent = booking.service_mode === 'MAIL_IN'
          ? 'Mail-in tailoring: send your outfit to the artisan; they will ship it back after completion.'
          : 'Doorstep service at the address above.';
        document.querySelector('#checkout-line-title').textContent = booking.work_title;
        document.querySelector('#checkout-line-price').textContent = currency(booking.amount);
        document.querySelector('#checkout-platform-fee').textContent = currency(booking.platform_fee);
        document.querySelector('#checkout-artisan-share').textContent = currency(booking.artisan_payout);
        document.querySelector('#checkout-total').textContent = currency(booking.amount);
        const payButton = document.querySelector('#pay-button');
        payButton.disabled = booking.payment_status === 'PAID';
        if (booking.payment_status === 'PAID') {
          document.querySelector('#payment-status').textContent = 'Payment complete. Your booking is confirmed.';
          payButton.textContent = 'Payment complete';
        } else {
          document.querySelector('#payment-status').textContent = 'Your booking request is saved as pending. Complete payment to confirm it.';
          payButton.addEventListener('click', async () => {
            payButton.disabled = true;
            document.querySelector('#payment-status').textContent = 'Connecting to secure checkout…';
            try {
              const orderResponse = await fetch(`/api/v1/bookings/${encodeURIComponent(booking.id)}/payment/order`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${localStorage.getItem(tokenKey) || ''}` },
              });
              const orderPayload = await orderResponse.json();
              if (!orderResponse.ok) throw new Error(orderPayload.error?.message || 'Could not start payment.');
              if (typeof window.Razorpay !== 'function') throw new Error('Razorpay Checkout did not load. Check your internet connection and try again.');
              const checkout = new window.Razorpay({
                key: orderPayload.data.key_id,
                amount: orderPayload.data.amount,
                currency: orderPayload.data.currency,
                name: 'EZHA',
                description: booking.work_title,
                order_id: orderPayload.data.order_id,
                prefill: { name: user?.name || '', email: user?.email || '' },
                theme: { color: themePrimary() },
                handler: async (paymentResult) => {
                  try {
                    const verifyResponse = await fetch(`/api/v1/bookings/${encodeURIComponent(booking.id)}/payment/verify`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem(tokenKey) || ''}` },
                      body: JSON.stringify(paymentResult),
                    });
                    const verifyPayload = await verifyResponse.json();
                    if (!verifyResponse.ok) throw new Error(verifyPayload.error?.message || 'Payment verification failed.');
                    document.querySelector('#payment-status').textContent = 'Payment verified. Your booking is confirmed.';
                    document.querySelector('#checkout-message').textContent = `Booking ${booking.id} is confirmed.`;
                    payButton.textContent = 'Payment complete';
                  } catch (error) {
                    document.querySelector('#payment-status').textContent = `${error.message} Contact support before retrying payment.`;
                    payButton.disabled = false;
                  }
                },
                modal: { ondismiss: () => { payButton.disabled = false; document.querySelector('#payment-status').textContent = 'Payment was not completed. Your booking remains pending.'; } },
              });
              checkout.on('payment.failed', () => {
                payButton.disabled = false;
                document.querySelector('#payment-status').textContent = 'Payment failed. Your booking remains pending; you can retry.';
              });
              checkout.open();
            } catch (error) {
              document.querySelector('#payment-status').textContent = error.message;
              payButton.disabled = false;
            }
          });
        }
      }).catch((error) => { document.querySelector('#checkout-message').textContent = error.message; });
    }
  }

  const serviceGroups = document.querySelector('#service-groups');
  const customerAddressForm = document.querySelector('#customer-address-form');
  if (customerAddressForm) {
    apiGet('/api/v1/customers/me').then((data) => {
      const profile = data.profile || {};
      customerAddressForm.elements.phone.value = profile.phone || '';
      customerAddressForm.elements.address_line1.value = profile.address_line1 || '';
      customerAddressForm.elements.address_line2.value = profile.address_line2 || '';
      customerAddressForm.elements.address_city.value = profile.city || '';
      customerAddressForm.elements.address_state.value = profile.state || '';
      customerAddressForm.elements.pincode.value = profile.pincode || '';
    }).catch(() => {});
    customerAddressForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = new FormData(customerAddressForm);
      const messageEl = document.querySelector('#customer-address-message');
      messageEl.textContent = 'Saving…';
      const response = await fetch('/api/v1/customers/me', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem(tokenKey) || ''}` },
        body: JSON.stringify(Object.fromEntries(form.entries())),
      });
      const payload = await response.json();
      messageEl.textContent = response.ok ? 'Doorstep address saved.' : (payload.error?.message || 'Unable to save address.');
    });
  }
  if (serviceGroups) {
    let artisans = [];
    const categoryNames = { MAKEUP: 'Makeup', MEHENDI: 'Mehendi', DRESS: 'Dress', FULL_PACKAGE: 'Full package' };
    const renderArtisans = () => {
      const query = document.querySelector('#service-search').value.trim().toLowerCase();
      const category = document.querySelector('#category-filter').value;
      const city = document.querySelector('#city-filter').value.toLowerCase();
      const groups = new Map();
      artisans.forEach((artisan) => {
        if (city && artisan.city.toLowerCase() !== city) return;
        const works = artisan.works.filter((work) => (!category || work.category === category) && `${work.title} ${work.caption} ${artisan.name} ${artisan.username} ${artisan.city}`.toLowerCase().includes(query));
        if (category && !works.length) return;
        const visibleWorks = category ? works : works;
        const groupKeys = category ? [category] : [...new Set(visibleWorks.map((work) => work.category))];
        if (!groupKeys.length && !query && !category) groupKeys.push(artisan.category || 'MAKEUP');
        groupKeys.forEach((group) => groups.set(group, [...(groups.get(group) || []), { artisan, works: visibleWorks.filter((work) => work.category === group) }]));
      });
      serviceGroups.innerHTML = groups.size ? [...groups].map(([key, entries]) => `
        <section class="service-group"><h2>${escapeHtml(categoryNames[key] || key)}</h2><div class="artisan-grid">${entries.map(({ artisan, works }) => `
          <article class="artisan-card"><div class="artisan-heading"><div><h3>${escapeHtml(artisan.name)}</h3><p>@${escapeHtml(artisan.username)} · ${escapeHtml(artisan.city || 'India')}</p></div><span class="vendor-badge">Artisan</span></div><p class="artisan-id">Artisan ID: ${escapeHtml(artisan.id)}</p>${works.length ? `<div class="work-grid">${works.map((work) => `<article class="work-card"><img src="${escapeHtml(work.image_url)}" alt="${escapeHtml(work.title)} by ${escapeHtml(artisan.name)}"><div class="work-copy"><h4>${escapeHtml(work.title)}</h4><p>${escapeHtml(work.caption)}</p><div class="work-price">${currency(work.price)}</div><a class="btn btn-primary" href="/booking?work_id=${encodeURIComponent(work.id)}">Book this work</a></div></article>`).join('')}</div>` : '<p class="no-work">This artisan is setting up their portfolio.</p>'}</article>`).join('')}</div></section>`).join('') : '<p class="empty-state">No artisans or works match these filters yet.</p>';
    };
    apiGet('/api/v1/customers/artisans').then((data) => {
      artisans = data.artisans;
      const params = new URLSearchParams(window.location.search);
      document.querySelector('#service-search').value = params.get('q') || '';
      document.querySelector('#city-filter').value = params.get('city') || '';
      document.querySelector('#category-filter').value = params.get('category') || '';
      if (params.has('service_id')) document.querySelector('#category-filter').value = 'MAKEUP';
      renderArtisans();
    }).catch((error) => { serviceGroups.innerHTML = `<p class="empty-state">${escapeHtml(error.message)} <a href="/login">Sign in</a></p>`; });
    document.querySelector('#service-search').addEventListener('input', renderArtisans);
    document.querySelector('#category-filter').addEventListener('change', renderArtisans);
    document.querySelector('#city-filter').addEventListener('change', renderArtisans);
  }

  const artisanRoot = document.querySelector('#artisan-dashboard');
  if (artisanRoot) {
    apiGet('/api/v1/artisan/dashboard').then((data) => {
      document.querySelector('#artisan-name').textContent = data.profile.name;
      document.querySelector('#artisan-orders').textContent = data.metrics.total_orders;
      document.querySelector('#artisan-earnings').textContent = currency(data.payments.available_balance);
      document.querySelector('#artisan-pending').textContent = currency(data.payments.pending_balance);
      document.querySelector('#artisan-orders-list').innerHTML = data.orders.map((order) => `<div class="table-row"><div><strong>${escapeHtml(order.service)}</strong><small>${escapeHtml(order.customer)} · ${escapeHtml(order.date)} · ${escapeHtml(order.service_address || '')}</small></div><span class="status status-${escapeHtml(order.status.toLowerCase())}">${escapeHtml(order.status)}</span><strong>${currency(order.artisan_payout || order.amount)}</strong></div>`).join('') || '<p>No orders yet.</p>';
      const notificationsEl = document.querySelector('#artisan-notifications');
      if (notificationsEl) {
        notificationsEl.innerHTML = (data.notifications || []).length
          ? data.notifications.map((note) => `<article class="notification-item ${note.is_read ? '' : 'unread'}"><strong>${escapeHtml(note.title)}</strong><p>${escapeHtml(note.message)}</p></article>`).join('')
          : '<p class="empty-state">No notifications yet. You will be alerted when a customer books or pays.</p>';
      }
      const payout = data.payments?.payout_account;
      const payoutForm = document.querySelector('#payout-form');
      if (payoutForm && payout?.configured) {
        payoutForm.elements.account_holder_name.value = payout.account_holder_name || '';
        payoutForm.elements.ifsc_code.value = payout.ifsc_code || '';
      }
      renderPortfolio(data.portfolio);
    }).catch((error) => { document.querySelector('#artisan-error').textContent = error.message; });
    document.querySelector('#payout-form')?.addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const response = await fetch('/api/v1/artisan/payout-profile', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem(tokenKey) || ''}` },
        body: JSON.stringify(Object.fromEntries(form.entries())),
      });
      const payload = await response.json();
      document.querySelector('#payout-message').textContent = response.ok ? payload.message : (payload.error?.message || 'Unable to save bank details.');
    });
    const renderPortfolio = (items) => {
      const grid = document.querySelector('#portfolio-grid');
      grid.innerHTML = items.length ? items.map((item) => `<figure class="work-item"><img src="${escapeHtml(item.url)}" alt="${escapeHtml(item.caption || 'Portfolio work')}"><figcaption>${escapeHtml(item.caption || 'Portfolio work')}</figcaption></figure>`).join('') : '<p class="empty-state">Your portfolio is ready for its first piece.</p>';
    };
    document.querySelector('#portfolio-form').addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const response = await fetch('/api/v1/artisan/portfolio', { method: 'POST', headers: { Authorization: `Bearer ${localStorage.getItem(tokenKey) || ''}` }, body: form });
      const payload = await response.json();
      if (!response.ok) { document.querySelector('#portfolio-message').textContent = payload.error?.message || 'Upload failed.'; return; }
      const existing = [...document.querySelectorAll('#portfolio-grid .work-item')].map((item) => item.outerHTML);
      existing.unshift(`<figure class="work-item"><img src="${escapeHtml(payload.data.url)}" alt="${escapeHtml(payload.data.caption || 'Portfolio work')}"><figcaption>${escapeHtml(payload.data.caption || 'Portfolio work')}</figcaption></figure>`);
      document.querySelector('#portfolio-grid').innerHTML = existing.join('');
      document.querySelector('#portfolio-message').textContent = 'Work added to your portfolio.';
      event.currentTarget.reset();
    });
  }

  const adminRoot = document.querySelector('#admin-dashboard');
  if (adminRoot) {
    apiGet('/api/v1/admin/dashboard').then((data) => {
      document.querySelector('#admin-customers').textContent = data.kpis.customers;
      document.querySelector('#admin-artisans').textContent = data.kpis.artisans;
      document.querySelector('#admin-orders').textContent = data.kpis.orders;
      document.querySelector('#admin-revenue').textContent = currency(data.kpis.revenue);
      document.querySelector('#admin-order-list').innerHTML = data.recent_orders.map((order) => `<div class="table-row"><div><strong>${escapeHtml(order.service)}</strong><small>${escapeHtml(order.customer)} · ${escapeHtml(order.date)}</small></div><span class="status">${escapeHtml(order.status)}</span><strong>${currency(order.amount)}</strong></div>`).join('') || '<p>No recent orders.</p>';
      document.querySelector('#admin-artisan-list').innerHTML = data.artisan_list.map((artisan) => `<div class="artisan-admin-row"><div><strong>${escapeHtml(artisan.name)}</strong><small>@${escapeHtml(artisan.username)} · ${escapeHtml(artisan.city || 'City not added')}</small></div><span>${escapeHtml(categoryNamesForUi[artisan.category] || artisan.category)}</span><code>${escapeHtml(artisan.id)}</code></div>`).join('') || '<p>No artisans have registered yet.</p>';
    }).catch((error) => { document.querySelector('#admin-error').textContent = error.message; });
  }
});
