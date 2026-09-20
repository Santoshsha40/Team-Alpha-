const API_BASE = "http://localhost:8000/api/v1";
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
};

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
});

const saveToken = () => {
  localStorage.setItem("campusloop-token", state.accessToken || "");
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
  } catch (error) {
    console.error("CampusLoop backend connection failed:", error);
    showToast("Could not reach the CampusLoop API. Start the backend server and refresh.");
    state.items = [];
    renderItems();
    renderRequests();
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
            `<article class="item-card"><div class="item-image image-${item.category.toLowerCase()}"><span class="availability">${item.available ? "Available" : "On loan"}</span><span class="item-visual">${item.visual}</span></div><div class="item-content"><span class="item-category">${item.category}</span><h3>${item.name}</h3><p class="item-description">${item.description}</p><div class="item-meta"><span>${item.location}</span><button class="request-button" data-request="${item.id}">Request -></button></div></div></article>`,
        )
        .join("")
    : '<p class="muted">No items match that search yet.</p>';

  document
    .querySelectorAll("[data-request]")
    .forEach((button) =>
      button.addEventListener("click", () => openRequest(button.dataset.request)),
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
$("#list-close").addEventListener("click", closeModals);
document.querySelectorAll(".modal-backdrop").forEach((backdrop) =>
  backdrop.addEventListener("click", (event) => {
    if (event.target === backdrop) closeModals();
  }),
);

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
