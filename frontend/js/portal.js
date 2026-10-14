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
    if (['CUSTOMER', 'ARTISAN', 'ADMIN'].includes(params.get('role'))) roleSelect.value = params.get('role');
    if (params.has('username')) usernameInput.value = params.get('username');
    document.querySelector('#toggle-forgot')?.addEventListener('click', () => {
      const panel = document.querySelector('#forgot-panel');
      if (panel) panel.dataset.open = panel.dataset.open === 'true' ? 'false' : 'true';
    });
    document.querySelector('#forgot-send')?.addEventListener('click', async () => {
      const identifier = document.querySelector('#forgot-identifier')?.value.trim();
      if (!identifier) return showMessage('Enter your email or mobile number.', true);
      showMessage('Sending reset code…');
      try {
        const response = await fetch('/api/v1/auth/forgot-password', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ identifier }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error?.message || 'Unable to send code.');
        const hint = payload.data?.dev_code ? ` Dev code: ${payload.data.dev_code}` : '';
        showMessage(`Reset code sent.${hint}`);
      } catch (error) {
        showMessage(error.message, true);
      }
    });
    document.querySelector('#forgot-submit')?.addEventListener('click', async () => {
      const identifier = document.querySelector('#forgot-identifier')?.value.trim();
      const otp = document.querySelector('#forgot-otp')?.value.trim();
      const newPassword = document.querySelector('#forgot-password')?.value;
      showMessage('Updating password…');
      try {
        const response = await fetch('/api/v1/auth/reset-password', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ identifier, otp, new_password: newPassword }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error?.message || 'Unable to reset password.');
        showMessage(payload.message || 'Password updated. Sign in with your new password.');
      } catch (error) {
        showMessage(error.message, true);
      }
    });
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
        const returnTo = params.get('return_to') || '';
        const allowedReturn = {
          CUSTOMER: returnTo.startsWith('/customer/services') ? returnTo : '',
          ARTISAN: returnTo === '/artisan/dashboard' ? returnTo : '',
          ADMIN: returnTo === '/admin/dashboard' ? returnTo : '',
        }[payload.data.user.role];
        window.location.assign(allowedReturn || destination(payload.data.user.role));
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
      if (registerForm.elements.city) registerForm.elements.city.required = isArtisan;
    };
    if (params.get('role') === 'ARTISAN') registerForm.elements.role.value = 'ARTISAN';
    registerForm.elements.role.addEventListener('change', syncArtisanFields);
    syncArtisanFields();
    registerForm.querySelectorAll('[data-send-otp]').forEach((button) => {
      button.addEventListener('click', async () => {
        const channel = button.getAttribute('data-send-otp');
        const destination = channel === 'email'
          ? registerForm.elements.email.value.trim()
          : registerForm.elements.phone.value.trim();
        if (!destination) {
          showMessage(channel === 'email' ? 'Enter your email first.' : 'Enter your mobile number first.', true);
          return;
        }
        showMessage(`Sending ${channel} code…`);
        try {
          const response = await fetch('/api/v1/auth/otp/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel, destination }),
          });
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.error?.message || 'Unable to send code.');
          if (payload.data?.dev_code) {
            const field = channel === 'email' ? 'email_otp' : 'phone_otp';
            if (registerForm.elements[field]) registerForm.elements[field].value = payload.data.dev_code;
          }
          showMessage(payload.message || `Verification code sent to your ${channel}. Check your inbox or SMS.`);
        } catch (error) {
          showMessage(error.message, true);
        }
      });
    });
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
      apiGet('/api/v1/customers/works?per_page=48').then((data) => {
        const work = (data.works || []).find((entry) => entry.id === workId);
        if (!work) throw new Error('This work is no longer available. Return to the catalog to choose another.');
        const artisan = { id: work.artisan_id, name: work.artisan_name, city: work.artisan_city };
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
        const calendarPanel = document.querySelector('#artisan-calendar-panel');
        const calendarGrid = document.querySelector('#artisan-calendar-grid');
        const dateInput = document.querySelector('#booking-date');
        const timeInput = document.querySelector('#booking-time');
        const slotMessage = document.querySelector('#slot-availability-message');
        const paintCalendar = (calendarData) => {
          if (!calendarGrid) return;
          const days = calendarData.days || {};
          calendarGrid.innerHTML = Object.keys(days).sort().map((dateKey) => {
            const day = days[dateKey];
            const dayNum = dateKey.split('-')[2];
            const classes = ['calendar-day', day.status === 'available' ? 'available' : (day.status === 'blocked' ? 'blocked' : 'partial')];
            if (dateInput?.value === dateKey) classes.push('selected');
            return `<button type="button" class="${classes.join(' ')}" data-cal-date="${dateKey}">${dayNum}</button>`;
          }).join('');
          calendarGrid.querySelectorAll('[data-cal-date]').forEach((button) => {
            button.addEventListener('click', () => {
              if (dateInput) dateInput.value = button.getAttribute('data-cal-date');
              paintCalendar(calendarData);
              checkSlot();
            });
          });
        };
        const checkSlot = async () => {
          if (!dateInput?.value || !timeInput?.value || !slotMessage) return;
          const result = await apiGet(`/api/v1/customers/artisans/${encodeURIComponent(artisan.id)}/slot-check?date=${encodeURIComponent(dateInput.value)}&time=${encodeURIComponent(timeInput.value)}`);
          slotMessage.textContent = result.available ? 'This slot is available.' : 'This slot is unavailable — choose another date or time (shown in red on the calendar).';
          slotMessage.style.color = result.available ? '#0f7a50' : '#991b1b';
        };
        const now = new Date();
        apiGet(`/api/v1/customers/artisans/${encodeURIComponent(artisan.id)}/calendar?year=${now.getFullYear()}&month=${now.getMonth() + 1}`).then((calendarData) => {
          if (calendarPanel) calendarPanel.hidden = false;
          paintCalendar(calendarData);
        }).catch(() => {});
        dateInput?.addEventListener('change', checkSlot);
        timeInput?.addEventListener('change', checkSlot);
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
      if (profile.address_line1 && profile.pincode) {
        document.querySelector('#customer-address-panel')?.setAttribute('hidden', '');
      }
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
      if (!response.ok) {
        messageEl.textContent = payload.error?.message || 'Unable to save address.';
        return;
      }
      messageEl.textContent = '';
      const panel = document.querySelector('#customer-address-panel');
      const hurray = document.querySelector('#address-hurray');
      if (panel) panel.hidden = true;
      if (hurray) hurray.hidden = false;
      document.querySelector('#hurray-dismiss')?.addEventListener('click', () => { hurray.hidden = true; }, { once: true });
    });
  }
  const workCardPayload = (work) => ({
    id: work.id,
    title: work.title,
    price: work.price,
    image_url: work.image_url,
    artisan_name: work.artisan_name,
    artisan_id: work.artisan_id,
    category: work.category,
  });

  if (serviceGroups) {
    let currentPage = 1;
    const renderWorksPage = async () => {
      const q = document.querySelector('#service-search')?.value.trim() || '';
      const category = document.querySelector('#category-filter')?.value || '';
      const city = document.querySelector('#city-filter')?.value || '';
      const query = new URLSearchParams({ page: String(currentPage), per_page: '8' });
      if (q) query.set('q', q);
      if (category) query.set('category', category);
      if (city) query.set('city', city);
      serviceGroups.innerHTML = '<p class="empty-state" style="grid-column:1/-1">Loading services…</p>';
      try {
        const data = await apiGet(`/api/v1/customers/works?${query.toString()}`);
        const works = data.works || [];
        serviceGroups.innerHTML = works.length ? works.map((work) => `
          <article class="product-card">
            <img src="${escapeHtml(work.image_url)}" alt="${escapeHtml(work.title)}" loading="lazy" />
            <div class="product-body">
              <h3>${escapeHtml(work.title)}</h3>
              <p class="product-meta">${escapeHtml(work.artisan_name)} · ${escapeHtml(work.artisan_city || 'India')}</p>
              <div class="product-price">${currency(work.price)}</div>
              <div class="product-actions">
                <button type="button" class="btn btn-secondary" data-add-cart="${escapeHtml(work.id)}">Add to cart</button>
                <a class="btn btn-primary" href="/booking?work_id=${encodeURIComponent(work.id)}">Buy now</a>
              </div>
            </div>
          </article>`).join('') : '<p class="empty-state" style="grid-column:1/-1">No services match your filters yet.</p>';
        const pagination = document.querySelector('#works-pagination');
        if (pagination && data.pagination) {
          const { page, total_pages } = data.pagination;
          pagination.innerHTML = total_pages > 1 ? Array.from({ length: total_pages }, (_, index) => {
            const pageNumber = index + 1;
            return `<button type="button" class="btn ${pageNumber === page ? 'btn-primary' : 'btn-secondary'}" data-page="${pageNumber}">${pageNumber}</button>`;
          }).join('') : '';
          pagination.querySelectorAll('[data-page]').forEach((button) => {
            button.addEventListener('click', () => {
              currentPage = Number(button.getAttribute('data-page'));
              renderWorksPage();
            });
          });
        }
        serviceGroups.querySelectorAll('[data-add-cart]').forEach((button) => {
          button.addEventListener('click', () => {
            const work = works.find((entry) => entry.id === button.getAttribute('data-add-cart'));
            if (work && typeof addToCart === 'function') {
              addToCart(workCardPayload(work));
              button.textContent = 'Added';
            }
          });
        });
      } catch (error) {
        serviceGroups.innerHTML = `<p class="empty-state" style="grid-column:1/-1">${escapeHtml(error.message)}</p>`;
      }
    };
    const params = new URLSearchParams(window.location.search);
    if (document.querySelector('#service-search')) document.querySelector('#service-search').value = params.get('q') || '';
    if (document.querySelector('#city-filter')) document.querySelector('#city-filter').value = params.get('city') || '';
    if (document.querySelector('#category-filter')) document.querySelector('#category-filter').value = params.get('category') || '';
    renderWorksPage();
    document.querySelector('#service-search')?.addEventListener('input', () => { currentPage = 1; renderWorksPage(); });
    document.querySelector('#category-filter')?.addEventListener('change', () => { currentPage = 1; renderWorksPage(); });
    document.querySelector('#city-filter')?.addEventListener('change', () => { currentPage = 1; renderWorksPage(); });
  }

  const cartItemsEl = document.querySelector('#cart-items');
  if (cartItemsEl && typeof readCart === 'function') {
    const renderCart = () => {
      const items = readCart();
      cartItemsEl.innerHTML = items.length ? items.map((work) => `
        <article class="cart-row">
          <img src="${escapeHtml(work.image_url)}" alt="${escapeHtml(work.title)}" />
          <div><strong>${escapeHtml(work.title)}</strong><p>${escapeHtml(work.artisan_name)} · ${currency(work.price)}</p></div>
          <div class="cart-actions">
            <a class="btn btn-primary" href="/booking?work_id=${encodeURIComponent(work.id)}">Buy now</a>
            <button type="button" class="btn btn-ghost" data-remove-cart="${escapeHtml(work.id)}">Remove</button>
          </div>
        </article>`).join('') : '<p class="empty-state">Your cart is empty.</p>';
      cartItemsEl.querySelectorAll('[data-remove-cart]').forEach((button) => {
        button.addEventListener('click', () => {
          removeFromCart(button.getAttribute('data-remove-cart'));
          renderCart();
        });
      });
    };
    renderCart();
  }

  const artisanRoot = document.querySelector('#artisan-dashboard');
  if (artisanRoot) {
    apiGet('/api/v1/artisan/dashboard').then((data) => {
      document.querySelector('#artisan-name').textContent = data.profile.name;
      document.querySelector('#artisan-orders').textContent = data.metrics.total_orders;
      document.querySelector('#artisan-earnings').textContent = currency(data.payments.available_balance);
      document.querySelector('#artisan-pending').textContent = currency(data.payments.pending_balance);
      document.querySelector('#artisan-orders-list').innerHTML = data.orders.map((order) => `
        <article class="notification-item" style="margin-bottom:12px">
          <div class="table-row" style="border:none;padding:0">
            <div>
              <strong>${escapeHtml(order.service)}</strong>
              <small>${escapeHtml(order.customer)} · ${escapeHtml(order.customer_phone || '')} · ${escapeHtml(order.customer_email || '')}</small>
              <small>${escapeHtml(order.date)} ${escapeHtml(order.time || '')} · ${escapeHtml(order.service_address || '')}</small>
              <small>Notes: ${escapeHtml(order.notes || '—')}</small>
            </div>
            <span class="status status-${escapeHtml((order.status || 'pending').toLowerCase())}">${escapeHtml(order.status)}</span>
            <strong>${currency(order.artisan_payout || order.amount)}</strong>
          </div>
          ${order.can_respond ? `<div style="display:flex;gap:8px;margin-top:10px">
            <button type="button" class="btn btn-primary" data-accept-order="${escapeHtml(order.id)}">Confirm order</button>
            <button type="button" class="btn btn-secondary" data-reject-order="${escapeHtml(order.id)}">Reject & refund</button>
          </div>` : ''}
        </article>`).join('') || '<p>No orders yet.</p>';
      document.querySelectorAll('[data-accept-order]').forEach((button) => {
        button.addEventListener('click', async () => {
          const orderId = button.getAttribute('data-accept-order');
          const response = await fetch(`/api/v1/artisan/orders/${encodeURIComponent(orderId)}/accept`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${localStorage.getItem(tokenKey) || ''}` },
          });
          const payload = await response.json();
          document.querySelector('#artisan-error').textContent = response.ok ? payload.message : (payload.error?.message || 'Unable to accept order.');
          if (response.ok) window.location.reload();
        });
      });
      document.querySelectorAll('[data-reject-order]').forEach((button) => {
        button.addEventListener('click', async () => {
          const orderId = button.getAttribute('data-reject-order');
          const response = await fetch(`/api/v1/artisan/orders/${encodeURIComponent(orderId)}/reject`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${localStorage.getItem(tokenKey) || ''}` },
          });
          const payload = await response.json();
          document.querySelector('#artisan-error').textContent = response.ok ? payload.message : (payload.error?.message || 'Unable to reject order.');
          if (response.ok) window.location.reload();
        });
      });
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
      const steps = [
        { label: 'City & category', done: Boolean(data.profile?.city && data.profile?.category) },
        { label: 'Portfolio work uploaded', done: (data.portfolio || []).length > 0 },
        { label: 'Payout bank details', done: Boolean(payout?.configured) },
      ];
      const completed = steps.filter((step) => step.done).length;
      const pct = Math.round((completed / steps.length) * 100);
      const ring = document.querySelector('#profile-ring');
      if (ring) {
        ring.style.setProperty('--pct', String(pct));
        ring.dataset.label = `${pct}%`;
      }
      const checklist = document.querySelector('#profile-checklist');
      if (checklist) {
        checklist.innerHTML = steps.map((step) => `<span class="${step.done ? 'done' : ''}">${step.done ? '✓' : '○'} ${step.label}</span>`).join('');
      }
      renderPortfolio(data.portfolio);
    }).catch((error) => { document.querySelector('#artisan-error').textContent = error.message; });
    document.querySelector('#calendar-block-form')?.addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const response = await fetch('/api/v1/artisan/calendar/blocks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem(tokenKey) || ''}` },
        body: JSON.stringify(Object.fromEntries(form.entries())),
      });
      const payload = await response.json();
      document.querySelector('#calendar-block-message').textContent = response.ok ? payload.message : (payload.error?.message || 'Unable to save.');
      if (response.ok) event.currentTarget.reset();
    });
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
