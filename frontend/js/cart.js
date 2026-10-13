const EZHA_CART_KEY = 'ezha_cart';

function readCart() {
  try {
    return JSON.parse(localStorage.getItem(EZHA_CART_KEY) || '[]');
  } catch {
    return [];
  }
}

function writeCart(items) {
  localStorage.setItem(EZHA_CART_KEY, JSON.stringify(items));
  document.querySelectorAll('#cart-count').forEach((el) => {
    const count = items.length;
    el.textContent = String(count);
    el.hidden = count === 0;
  });
}

function addToCart(work) {
  const items = readCart();
  if (items.some((entry) => entry.id === work.id)) return items;
  items.push(work);
  writeCart(items);
  return items;
}

function removeFromCart(workId) {
  const items = readCart().filter((entry) => entry.id !== workId);
  writeCart(items);
  return items;
}

function syncCartBadge() {
  writeCart(readCart());
}

document.addEventListener('DOMContentLoaded', syncCartBadge);
