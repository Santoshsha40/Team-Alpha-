const API_BASE = `${window.location.origin}/api/v1`;
const DEMO_CREDENTIALS = {
  email: "studenta@campus.edu",
  password: "Student123!",
};

const state = {
  items: [],
  requests: [],
  categories: [],
  category: "All",
  selectedItem: null,
  currentUser: null,
  accessToken: localStorage.getItem("campusloop-token") || "",
  cart: [],
};

const formatCurrency = (amount) =>
  `₹${Number(amount).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

const normalizeUiCategory = (categoryName = "") => {
  const normalized = categoryName.toLowerCase();

  if (
    normalized.includes("book") ||
    normalized.includes("stationery") ||
    normalized.includes("study") ||
    normalized.includes("academic") ||
    normalized.includes("lab")
  ) {
    return "Study";
  }

  if (
    normalized.includes("elect") ||
    normalized.includes("adapter") ||
    normalized.includes("charger") ||
    normalized.includes("tech")
  ) {
    return "Tech";
  }

  if (
    normalized.includes("sport") ||
    normalized.includes("outdoor") ||
    normalized.includes("gear")
  ) {
    return "Outdoors";
  }

  return "Creative";
};

const getVisualForCategory = (categoryName = "") => {
  const mapped = normalizeUiCategory(categoryName);
  const visuals = {
    Study: "▦",
    Tech: "▭",
    Outdoors: "♢",
    Creative: "◉",
  };
  return visuals[mapped] || "◈";
};

const itemPriceByName = (name = "") => {
  const normalized = name.toLowerCase();
  if (normalized.includes("calculator")) return 1499;
  if (normalized.includes("headphone")) return 2499;
  if (normalized.includes("camera")) return 3499;
  if (normalized.includes("charger")) return 1299;
  if (normalized.includes("stove")) return 2899;
  if (normalized.includes("graph")) return 799;
  return 1299;
};

const mapApiItem = (resource) => ({
  id: resource.resource_id,
  name: resource.name,
  category: normalizeUiCategory(resource.category_name),
  categoryId: resource.category_id,
  description: resource.description,
  location: resource.pickup_location,
  owner: resource.owner_name || "Campus student",
  visual: getVisualForCategory(resource.category_name),
  available:
    !["ON_LOAN", "RESERVED", "MAINTENANCE"].includes(
      (resource.availability_status || "").toUpperCase(),
    ),
  rawStatus: resource.availability_status,
  price: itemPriceByName(resource.name),
  rating: 4.8 + ((resource.resource_id || 1) % 2) * 0.1,
  reviews: 42 + (resource.resource_id || 1) * 6,
});

const saveToken = () => {
  localStorage.setItem("campusloop-token", state.accessToken || "");
};

const addToCart = (itemId) => {
  const item = state.items.find((entry) => entry.id === itemId);
  if (!item) return;

  const existing = state.cart.find((entry) => entry.id === itemId);
  if (existing) {
    existing.quantity += 1;
  } else {
    state.cart.push({ ...item, quantity: 1 });
  }

  renderCart();
  showToast(`${item.name} added to cart.`);
};

const renderCart = () => {
  const cartItems = document.querySelector("#cart-items");
  const cartCount = document.querySelector("#cart-count");
  const cartTotal = document.querySelector("#cart-total");
  const totalItems = state.cart.reduce((sum, item) => sum + item.quantity, 0);
  const subtotal = state.cart.reduce((sum, item) => sum + item.price * item.quantity, 0);

  cartCount.textContent = String(totalItems);
  cartTotal.textContent = formatCurrency(subtotal);

  if (!state.cart.length) {
    cartItems.innerHTML = '<p class="muted cart-empty">Your cart is empty.</p>';
    return;
  }

  cartItems.innerHTML = state.cart
    .map(
      (item) => `
        <div class="cart-item">
          <div class="cart-item-copy">
            <strong>${item.name}</strong>
            <span>${item.quantity} x ${formatCurrency(item.price)}</span>
          </div>
          <button class="remove-cart" data-remove-cart="${item.id}" aria-label="Remove ${item.name}">x</button>
        </div>
      `,
    )
    .join("");

  document.querySelectorAll("[data-remove-cart]").forEach((button) => {
    button.addEventListener("click", () => {
      const id = Number(button.dataset.removeCart);
      state.cart = state.cart.filter((item) => item.id !== id);
      renderCart();
    });
  });
};

const openProductDetail = (id) => {
  const item = state.items.find((entry) => entry.id === id);
  if (!item) return;

  const modal = document.querySelector("#product-detail");
  modal.innerHTML = `
    <div class="product-visual-wrap">
      <div class="product-visual large image-${item.category.toLowerCase()}"><span>${item.visual}</span></div>
    </div>
    <div class="product-detail-copy">
      <p class="eyebrow product-eyebrow">${item.category}</p>
      <h2>${item.name}</h2>
      <div class="product-detail-meta">
        <span>★ ${item.rating.toFixed(1)}</span>
        <span>${item.reviews} reviews</span>
      </div>
      <div class="product-price-row">
        <strong>${formatCurrency(item.price)}</strong>
        <span>Pickup: ${item.location}</span>
      </div>
      <p>${item.description}</p>
      <div class="product-actions">
        <button class="primary-button" data-cart-detail="${item.id}">Add to cart</button>
        <button class="outline-button" data-request-detail="${item.id}">Request item</button>
      </div>
    </div>
  `;

  document.querySelector("#product-modal").classList.remove("hidden");

  const addButton = document.querySelector("[data-cart-detail]");
  addButton?.addEventListener("click", () => {
    addToCart(item.id);
    document.querySelector("#product-modal").classList.add("hidden");
  });

  const requestButton = document.querySelector("[data-request-detail]");
  requestButton?.addEventListener("click", () => {
    document.querySelector("#product-modal").classList.add("hidden");
    openRequest(item.id);
  });
};

const openCheckout = () => {
  if (!state.cart.length) {
    showToast("Your cart is empty.");
    return;
  }

  const checkout = document.querySelector("#checkout-items");
  const checkoutTotal = document.querySelector("#checkout-total");
  const subtotal = state.cart.reduce((sum, item) => sum + item.price * item.quantity, 0);

  checkout.innerHTML = state.cart
    .map(
      (item) => `
        <div class="checkout-row">
          <div>
            <strong>${item.name}</strong>
            <span>Qty ${item.quantity}</span>
          </div>
          <strong>${formatCurrency(item.price * item.quantity)}</strong>
        </div>
      `,
    )
    .join("");

  checkoutTotal.textContent = formatCurrency(subtotal);
  document.querySelector("#checkout-modal").classList.remove("hidden");
};

const requestJson = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.detail || response.statusText || "Request failed");
  }

  return payload;
};

const ensureSession = async () => {
  if (state.accessToken) return;

  try {
    const payload = await requestJson(`${API_BASE}/auth/login`, {
      method: "POST",
      body: JSON.stringify(DEMO_CREDENTIALS),
    });

    state.accessToken = payload.access_token;
    state.currentUser = {
      id: payload.user_id,
      name: payload.full_name || DEMO_CREDENTIALS.email,
      email: DEMO_CREDENTIALS.email,
    };
    saveToken();
  } catch (error) {
    console.warn("Session bootstrap failed:", error);
  }
};

const loadCategories = async () => {
  const categories = await requestJson(`${API_BASE}/resources/categories`);
  state.categories = categories;
};

const loadItems = async () => {
  const resources = await requestJson(`${API_BASE}/resources`);
  state.items = resources.map(mapApiItem);
  renderItems();
  renderListings();
};

const loadRequests = async () => {
  await ensureSession();
  if (!state.accessToken) {
    state.requests = [];
    renderRequests();
    return;
  }

  const requests = await requestJson(`${API_BASE}/borrow-requests`, {
    headers: {
      Authorization: `Bearer ${state.accessToken}`,
    },
  });

  state.requests = requests.map((request) => ({
    id: request.request_id,
    itemId: request.resource_id,
    status: request.status,
    dates: `${request.requested_from} - ${request.requested_until}`,
    note: request.message || "No note added",
    itemName: request.resource_name,
  }));

  renderRequests();
};

const initializeApp = async () => {
  try {
    await ensureSession();
    await loadCategories();
    await loadItems();
    await loadRequests();
    renderCart();
  } catch (error) {
    console.error("CampusLoop backend connection failed:", error);
    showToast("Could not reach the CampusLoop API. Start the backend server and refresh.");
    state.items = [];
    renderItems();
    renderRequests();
    renderCart();
  }
};

const $ = (selector) => document.querySelector(selector);
const showToast = (message) => {
  const toast = $("#toast");
  const target = toast || document.createElement("div");
  if (!toast) {
    target.id = "toast";
    target.className = "toast";
    document.body.appendChild(target);
  }
  target.textContent = message;
  target.classList.add("show");
  setTimeout(() => target.classList.remove("show"), 2600);
};

function renderItems() {
  const query = $("#search-input") ? $("#search-input").value.toLowerCase() : "";
  const visible = state.items.filter(
    (item) =>
      (state.category === "All" || item.category === state.category) &&
      `${item.name} ${item.description} ${item.location}`
        .toLowerCase()
        .includes(query),
  );

  $("#item-total").textContent = visible.length;
  $("#item-grid").innerHTML = visible.length
    ? visible
        .map(
          (item) =>
            `<article class="item-card">
              <div class="item-image image-${item.category.toLowerCase()}">
                <span class="availability">${item.available ? "Available" : "On loan"}</span>
                <span class="item-visual">${item.visual}</span>
              </div>
              <div class="item-content">
                <div class="item-topline">
                  <span class="item-category">${item.category}</span>
                  <span class="item-price">${formatCurrency(item.price)}</span>
                </div>
                <h3>${item.name}</h3>
                <div class="item-rating">
                  <span>★ ${item.rating.toFixed(1)}</span>
                  <small>(${item.reviews} reviews)</small>
                </div>
                <p class="item-description">${item.description}</p>
                <div class="item-meta">
                  <span>${item.location}</span>
                  <div class="card-actions">
                    <button class="mini-button" data-cart="${item.id}">Add to cart</button>
                    <button class="mini-button detail-button" data-detail="${item.id}">View</button>
                    <button class="request-button" data-request="${item.id}">Request -></button>
                  </div>
                </div>
              </div>
            </article>`,
        )
        .join("")
    : '<p class="muted">No items match that search yet.</p>';

  document
    .querySelectorAll("[data-request]")
    .forEach((button) =>
      button.addEventListener("click", () => openRequest(button.dataset.request)),
    );

  document
    .querySelectorAll("[data-cart]")
    .forEach((button) =>
      button.addEventListener("click", () => addToCart(Number(button.dataset.cart))),
    );

  document
    .querySelectorAll("[data-detail]")
    .forEach((button) =>
      button.addEventListener("click", () => openProductDetail(Number(button.dataset.detail))),
    );
}

function renderRequests() {
  const pending = state.requests.filter((request) => request.status === "PENDING" || request.status === "Pending").length;
  $("#request-count").textContent = pending;
  $("#request-list").innerHTML = state.requests.length
    ? state.requests
        .map((request) => {
          const item = state.items.find((entry) => entry.id === request.itemId) || { name: request.itemName || "Campus item" };
          return `<div class="request-row"><div><div class="row-title">${item.name}</div><div class="row-meta">${request.dates} · ${request.note || "No note added"}</div></div><span class="status ${request.status.toLowerCase()}">${request.status}</span></div>`;
        })
        .join("")
    : '<p class="muted">You have no requests yet.</p>';
}

function renderListings() {
  const listings = state.items.filter((item) => {
    const owner = item.owner || "";
    return owner.toLowerCase().includes(state.currentUser?.name?.toLowerCase() || "") || owner === "Campus student";
  });

  $("#listing-list").innerHTML = listings.length
    ? listings
        .map(
          (item) =>
            `<div class="listing-row"><div><div class="row-title">${item.name}</div><div class="row-meta">${item.category} · ${item.location}</div></div><div class="row-actions"><span class="status">${item.available ? "Available" : "On loan"}</span>${item.id === "demo" ? '<button class="small-button" data-handover>Handover</button>' : ""}</div></div>`,
        )
        .join("")
    : '<p class="muted">Your shared shelf is empty.</p>';

  document.querySelectorAll("[data-handover]").forEach((button) =>
    button.addEventListener("click", () => {
      showToast("Handover confirmed. QR token CL-84A7 is active.");
      button.textContent = "Returned";
      button.classList.add("primary");
    }),
  );
}

function switchView(view) {
  document
    .querySelectorAll(".nav-link")
    .forEach((link) => link.classList.toggle("active", link.dataset.view === view));

  $("#browse-view").classList.toggle("hidden", view !== "browse");
  $("#requests-view").classList.toggle("hidden", view !== "requests");
  $("#listings-view").classList.toggle("hidden", view !== "listings");

  if (view === "requests") renderRequests();
  if (view === "listings") renderListings();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function openRequest(id) {
  const item = state.items.find((entry) => entry.id === id);
  if (!item) return;

  state.selectedItem = item;
  $("#modal-item").innerHTML = `<span class="item-visual">${item.visual}</span><div><strong>${item.name}</strong><br /><small>${item.location} · owned by ${item.owner}</small></div>`;
  $("#request-modal").classList.remove("hidden");
}

function closeModals() {
  $("#request-modal").classList.add("hidden");
  $("#list-modal").classList.add("hidden");
}

document
  .querySelectorAll("[data-view]")
  .forEach((button) => button.addEventListener("click", () => switchView(button.dataset.view)));

document.querySelectorAll(".filter-button").forEach((button) =>
  button.addEventListener("click", () => {
    state.category = button.dataset.category;
    document
      .querySelectorAll(".filter-button")
      .forEach((filter) => filter.classList.toggle("active", filter === button));
    renderItems();
  }),
);

$("#search-input").addEventListener("input", renderItems);
$("#modal-close").addEventListener("click", closeModals);
$("#product-close").addEventListener("click", () => {
  document.querySelector("#product-modal").classList.add("hidden");
});
$("#checkout-close").addEventListener("click", () => {
  document.querySelector("#checkout-modal").classList.add("hidden");
});
$("#list-close").addEventListener("click", closeModals);
document.querySelectorAll(".modal-backdrop").forEach((backdrop) =>
  backdrop.addEventListener("click", (event) => {
    if (event.target === backdrop) closeModals();
  }),
);

const checkoutButton = document.querySelector(".cart-button");
checkoutButton?.addEventListener("click", openCheckout);

const checkoutSubmitButton = document.querySelector("#checkout-submit");
checkoutSubmitButton?.addEventListener("click", () => {
  state.cart = [];
  renderCart();
  document.querySelector("#checkout-modal").classList.add("hidden");
  showToast("Order placed successfully.");
});

$("#request-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const start = $("#start-date").value;
  const end = $("#end-date").value;

  if (end < start) {
    showToast("End date must be after the start date.");
    return;
  }

  if (!state.selectedItem) {
    showToast("Select an item first.");
    return;
  }

  try {
    await ensureSession();
    await requestJson(`${API_BASE}/borrow-requests`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${state.accessToken}`,
      },
      body: JSON.stringify({
        resource_id: state.selectedItem.id,
        requested_from: start,
        requested_until: end,
        message: $("#request-note").value || "No note added",
      }),
    });

    await loadRequests();
    closeModals();
    showToast("Request sent to the owner.");
  } catch (error) {
    showToast(error.message || "Could not create request.");
  }
});

function openListModal() {
  $("#list-modal").classList.remove("hidden");
}

$("#list-item-button").addEventListener("click", openListModal);
$("#list-item-button-two").addEventListener("click", openListModal);
$("#list-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    await ensureSession();
    const category = $("#new-category").value;
    const categoryMatch = state.categories.find((cat) => cat.name.toLowerCase() === category.toLowerCase());

    await requestJson(`${API_BASE}/resources`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${state.accessToken}`,
      },
      body: JSON.stringify({
        name: $("#new-name").value,
        description: $("#new-description").value,
        category_id: categoryMatch ? categoryMatch.category_id : state.categories[0]?.category_id,
        condition: "GOOD",
        pickup_location: $("#new-location").value,
        optional_deposit: 0,
      }),
    });

    await loadItems();
    closeModals();
    event.target.reset();
    showToast("Your item is now on the community shelf.");
  } catch (error) {
    showToast(error.message || "Could not publish listing.");
  }
});

initializeApp();
