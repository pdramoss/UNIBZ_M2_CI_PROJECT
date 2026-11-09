const API = "/api/v1";
const TOKEN_KEY = "token";
const TAB_KEY = "tab";
const TOAST_MS = 3500;
const MAX_TOASTS = 3;

let token = sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
let me = null;
let events = [];

const $ = (sel) => document.querySelector(sel);
const isManager = () => me?.role === "manager";
const pad = (n) => String(n).padStart(2, "0");

// ---------------- infrastructure ----------------

function log(method, url, status, body) {
  $("#log").textContent = `${method} ${url} → ${status}\n` + (body ? JSON.stringify(body, null, 2) : "");
  $("#log").className = status >= 400 ? "error" : "ok";
}

function toast(message, isError = false) {
  const el = document.createElement("div");
  el.className = "toast" + (isError ? " error" : "");
  el.textContent = message;
  const box = $("#toasts");
  box.append(el);
  while (box.children.length > MAX_TOASTS) box.firstElementChild.remove();
  setTimeout(() => el.remove(), TOAST_MS);
}

async function call(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  log(method, API + path, res.status, data);
  if (res.status === 401 && path !== "/sessions") logoutLocal();
  if (!res.ok) {
    const message = data?.error?.message || res.statusText;
    toast(message, true);
    throw new Error(message);
  }
  return data;
}

/** Runs an action with the button disabled, showing a toast on success. */
async function busy(button, action, successMessage) {
  if (button) button.disabled = true;
  try {
    await action();
    if (successMessage) toast(successMessage);
  } catch {
    // error already reported by call()
  } finally {
    if (button) button.disabled = false;
  }
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  node.append(...children.filter((c) => c !== null && c !== undefined));
  return node;
}

function button(label, cls, onClick) {
  const b = el("button", { type: "button", className: cls, textContent: label });
  b.addEventListener("click", () => onClick(b));
  return b;
}

/** Numbered, expandable list item (FAQ pattern). */
function listItem(number, title, sub, bodyChildren) {
  const item = el("div", { className: "item" });
  const head = el("button", { type: "button", className: "item-head" },
    el("span", { className: "badge-num", textContent: pad(number) }),
    el("span", { className: "item-main" },
      el("span", { className: "item-title", textContent: title }),
      sub),
    el("span", { className: "toggle", ariaHidden: "true" }));
  head.setAttribute("aria-expanded", "false");
  const body = el("div", { className: "item-body", hidden: true }, ...bodyChildren);
  head.addEventListener("click", () => {
    const open = body.hidden;
    body.hidden = !open;
    item.classList.toggle("open", open);
    head.setAttribute("aria-expanded", String(open));
  });
  item.append(head, body);
  return item;
}

function emptyState(text) {
  return el("div", { className: "empty", textContent: text });
}

// ---------------- tabs ----------------

function showTab(name) {
  sessionStorage.setItem(TAB_KEY, name);
  document.querySelectorAll(".tab[data-tab]").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  $("#events-view").hidden = name !== "events";
  $("#registrations-view").hidden = name !== "registrations";
}

document.querySelectorAll("[data-tab]").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));
document.querySelectorAll("[data-goto]").forEach((a) => a.addEventListener("click", (e) => {
  e.preventDefault();
  if (me) { showTab(a.dataset.goto); window.scrollTo({ top: 0, behavior: "smooth" }); }
}));

// ---------------- events ----------------

async function loadEvents(min) {
  const query = min !== undefined && min !== "" ? `?minAvailablePlaces=${encodeURIComponent(min)}` : "";
  const list = await call("GET", `/events${query}`);
  if (!query) events = list;
  renderEvents(list, Boolean(query));
  fillEventSelect();
}

function renderEvents(list, filtered) {
  const container = $("#events-list");
  container.replaceChildren();
  if (!list.length) {
    container.append(emptyState(filtered ? "No events match this filter."
      : isManager() ? "No events yet. Create the first one." : "No events available yet."));
    return;
  }
  for (const ev of list) {
    const full = ev.availablePlaces <= 0;
    const used = ev.capacity ? Math.min(100, ((ev.capacity - ev.availablePlaces) / ev.capacity) * 100) : 100;
    const sub = el("span", { className: "item-sub" },
      el("span", { textContent: `${ev.availablePlaces} of ${ev.capacity} places free` }),
      el("span", { className: "progress" }, el("span", { style: `width:${used}%` })),
      full ? el("span", { className: "pill red", textContent: "Full" }) : null);

    const register = button("Register", "primary small", (b) => busy(b, async () => {
      await call("POST", "/registrations", { eventId: ev.id });
      await refresh();
    }, `Registered to ${ev.name}`));
    register.disabled = full;

    const actions = el("div", { className: "item-actions" }, register);
    if (isManager()) {
      actions.append(
        button("Edit", "secondary small", () => openEventForm(ev)),
        button("Delete", "danger small", (b) => {
          if (!confirm(`Delete event "${ev.name}"?`)) return;
          busy(b, async () => { await call("DELETE", `/events/${ev.id}`); await refresh(); }, `Event ${ev.id} deleted`);
        }),
      );
    }
    container.append(listItem(ev.id, ev.name, sub, [actions]));
  }
}

function openEventForm(ev) {
  const form = $("#event-form");
  const f = form.elements;
  form.reset();
  f.namedItem("id").value = ev ? ev.id : "";
  if (ev) {
    f.namedItem("name").value = ev.name;
    f.namedItem("capacity").value = ev.capacity;
  }
  $("#event-form-title").textContent = ev ? `Edit event ${pad(ev.id)}` : "New event";
  form.hidden = false;
  f.namedItem("name").focus();
}

function closeEventForm() {
  $("#event-form").reset();
  $("#event-form").hidden = true;
}

$("#new-event-btn").addEventListener("click", () => openEventForm(null));
$("#event-cancel").addEventListener("click", closeEventForm);

$("#event-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const d = formData(e.target);
  const payload = { name: d.name, capacity: Number(d.capacity) };
  busy(e.submitter, async () => {
    if (d.id) await call("PATCH", `/events/${d.id}`, payload);
    else await call("POST", "/events", payload);
    closeEventForm();
    await refresh();
  }, d.id ? `Event ${d.id} updated` : "Event created");
});

$("#search-form").addEventListener("submit", (e) => {
  e.preventDefault();
  busy(e.submitter, () => loadEvents(formData(e.target).min));
});

// ---------------- registrations ----------------

function eventName(id) {
  return events.find((e) => e.id === id)?.name ?? `Event ${id}`;
}

function fillEventSelect() {
  const select = $("#registration-form").elements.namedItem("eventId");
  const current = select.value;
  select.replaceChildren(...events.map((ev) =>
    el("option", { value: ev.id, textContent: `${pad(ev.id)} · ${ev.name} (${ev.availablePlaces} free)`, disabled: ev.availablePlaces <= 0 })));
  if (current) select.value = current;
}

async function loadRegistrations() {
  const regs = await call("GET", "/registrations");
  const container = $("#registrations-list");
  container.replaceChildren();
  $("#registrations-lead").textContent = isManager()
    ? "All registrations across every event."
    : "Your bookings. Open one to cancel it.";
  if (!regs.length) {
    container.append(emptyState("No registrations yet. Register to an event to see it here."));
    return;
  }
  for (const r of regs) {
    const sub = el("span", { className: "item-sub", textContent: `Attendee: ${r.userName}` });
    const actions = el("div", { className: "item-actions" });
    const body = [actions];
    if (isManager()) {
      const edit = el("form", { className: "inline-edit" },
        el("input", { name: "attendee", value: r.userName, required: true, ariaLabel: "New attendee" }),
        el("button", { type: "submit", className: "secondary small", textContent: "Change attendee" }));
      edit.addEventListener("submit", (e) => {
        e.preventDefault();
        const attendee = formData(edit).attendee.trim();
        if (!attendee || attendee === r.userName) return;
        busy(e.submitter, async () => {
          await call("PATCH", `/registrations/${r.id}`, { attendee });
          await refresh();
        }, `Registration ${r.id} updated`);
      });
      body.unshift(edit);
    }
    actions.append(button("Cancel registration", "danger small", (b) => busy(b, async () => {
      await call("DELETE", `/registrations/${r.id}`);
      await refresh();
    }, `Registration ${r.id} cancelled`)));
    container.append(listItem(r.id, eventName(r.eventId), sub, body));
  }
}

$("#new-registration-btn").addEventListener("click", () => {
  const form = $("#registration-form");
  form.hidden = !form.hidden;
  if (!form.hidden) fillEventSelect();
});
$("#registration-cancel").addEventListener("click", () => { $("#registration-form").reset(); $("#registration-form").hidden = true; });

$("#registration-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const d = formData(e.target);
  if (!d.eventId) { toast("Create an event first", true); return; }
  const payload = { eventId: Number(d.eventId) };
  if (d.attendee?.trim()) payload.attendee = d.attendee.trim();
  busy(e.submitter, async () => {
    await call("POST", "/registrations", payload);
    e.target.reset();
    e.target.hidden = true;
    await refresh();
  }, "Registration created");
});

// ---------------- session ----------------

async function refresh() {
  await loadEvents();
  await loadRegistrations();
}

function logoutLocal() {
  token = null;
  me = null;
  sessionStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TOKEN_KEY);
  document.body.classList.remove("is-manager");
  for (const id of ["#tabs", "#nav-user", "#events-view", "#registrations-view", "#cta"]) $(id).hidden = true;
  $("#login-view").hidden = false;
}

async function enter() {
  me = await call("GET", "/users/me");
  $("#whoami-name").textContent = me.name;
  $("#whoami-role").textContent = me.role;
  $("#whoami-role").className = "pill" + (isManager() ? " red" : "");
  document.body.classList.toggle("is-manager", isManager());
  $("#login-view").hidden = true;
  for (const id of ["#tabs", "#nav-user", "#cta"]) $(id).hidden = false;
  showTab(sessionStorage.getItem(TAB_KEY) || "events");
  await refresh();
}

$("#login-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const d = formData(e.target);
  if (!d.name?.trim() || !d.password) { toast("Name and password are required", true); return; }
  busy(e.submitter, async () => {
    const session = await call("POST", "/sessions", {
      role: d.role, name: d.name.trim(), password: d.password, age: Number(d.age || 0),
    });
    token = session.token;
    (d.remember ? localStorage : sessionStorage).setItem(TOKEN_KEY, token);
    e.target.reset();
    await enter();
  }, "Welcome!");
});

$("#logout-btn").addEventListener("click", async () => {
  try { await call("DELETE", "/sessions/current"); } catch {}
  logoutLocal();
  toast("Logged out");
});

if (token) enter().catch(logoutLocal);
