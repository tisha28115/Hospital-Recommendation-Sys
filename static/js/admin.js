const adminById = (id) => document.getElementById(id);

async function adminApi(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  return response.json();
}

function renderAdminHospitals(hospitals) {
  const target = adminById("admin-hospitals");
  target.innerHTML = "";
  hospitals.forEach((hospital) => {
    const card = document.createElement("article");
    card.className = "card";
    card.innerHTML = `
      <h3>${hospital.name}</h3>
      <p>${hospital.city}</p>
      <p>${hospital.specialization}</p>
      <p>Rating: ${hospital.rating}</p>
      <p class="mini">ID: ${hospital.id}</p>
    `;
    target.appendChild(card);
  });
}

function showStatsMessage(message) {
  const target = adminById("stats-grid");
  if (!target) return;
  target.innerHTML = `<div class="stat-card empty-state"><span>${message}</span></div>`;
}

async function loadAdminData() {
  const result = await adminApi("/admin_api/stats");
  if (result.status !== "success") {
    adminById("admin-status").textContent = result.message || "Admin data unavailable.";
    showStatsMessage(result.message || "Admin data unavailable.");
    return;
  }
  adminById("stats-grid").innerHTML = `
    <div class="stat-card"><strong>${result.stats.users}</strong><span>Users</span></div>
    <div class="stat-card"><strong>${result.stats.hospitals}</strong><span>Hospitals</span></div>
    <div class="stat-card"><strong>${result.stats.appointments}</strong><span>Appointments</span></div>
    <div class="stat-card"><strong>${result.stats.searches}</strong><span>Searches</span></div>
  `;
  renderAdminHospitals(result.hospitals || []);
}

adminById("admin-hospital-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());
  payload.emergency_services = formData.get("emergency_services") === "on";
  const hospitalId = payload.hospital_id;
  delete payload.hospital_id;
  const method = hospitalId ? "PUT" : "POST";
  const path = hospitalId ? `/admin_api/hospitals/${hospitalId}` : "/admin_api/hospitals";
  const result = await adminApi(path, { method, body: JSON.stringify(payload) });
  adminById("admin-status").textContent = result.message || "Hospital saved.";
  loadAdminData();
});

adminById("delete-hospital")?.addEventListener("click", async () => {
  const hospitalId = document.querySelector('input[name="hospital_id"]').value;
  if (!hospitalId) {
    adminById("admin-status").textContent = "Enter a hospital ID first.";
    return;
  }
  await adminApi(`/admin_api/hospitals/${hospitalId}`, { method: "DELETE" });
  adminById("admin-status").textContent = "Hospital deleted.";
  loadAdminData();
});

loadAdminData();

adminById("admin-logout-btn")?.addEventListener("click", async () => {
  await adminApi("/logout", { method: "POST" });
  window.location.href = "/";
});
