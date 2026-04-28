const byId = (id) => document.getElementById(id);
let firebaseRuntimePromise = null;

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  return response.json();
}

function showStatus(targetId, message) {
  const target = byId(targetId);
  if (target) {
    target.textContent = message;
  }
}

function setStatusState(targetId, tone = "muted") {
  const target = byId(targetId);
  if (!target) {
    return;
  }
  target.dataset.tone = tone;
  target.style.color = tone === "success" ? "#2f6f3e" : tone === "error" ? "#9f3d2f" : "";
}

function formatFirebaseError(error, fallbackMessage) {
  const code = String(error?.code || "");
  const codeMap = {
    "auth/email-already-in-use": "Please verify your email address through the link sent to your email. You can also use resend verification if needed.",
    "auth/invalid-email": "Enter a valid email address.",
    "auth/missing-password": "Enter your password.",
    "auth/weak-password": "Choose a stronger password.",
    "auth/invalid-credential": "Invalid email or password.",
    "auth/user-not-found": "No account exists for this email.",
    "auth/wrong-password": "Invalid email or password.",
    "auth/network-request-failed": "Network error while contacting Firebase.",
  };
  return codeMap[code] || error?.message || fallbackMessage;
}

async function getFirebaseToken(user) {
  return user.getIdToken(true);
}

async function loadFirebaseRuntime() {
  if (!firebaseRuntimePromise) {
    firebaseRuntimePromise = Promise.all([
      import("./firebase-config.js"),
      import("https://www.gstatic.com/firebasejs/12.7.0/firebase-auth.js"),
    ]).then(([firebaseConfig, firebaseAuthSdk]) => ({
      auth: firebaseConfig.auth,
      createUserWithEmailAndPassword: firebaseAuthSdk.createUserWithEmailAndPassword,
      fetchSignInMethodsForEmail: firebaseAuthSdk.fetchSignInMethodsForEmail,
      sendPasswordResetEmail: firebaseAuthSdk.sendPasswordResetEmail,
      sendEmailVerification: firebaseAuthSdk.sendEmailVerification,
      signInWithEmailAndPassword: firebaseAuthSdk.signInWithEmailAndPassword,
      signOut: firebaseAuthSdk.signOut,
      updateProfile: firebaseAuthSdk.updateProfile,
    }));
  }
  return firebaseRuntimePromise;
}

function renderCards(targetId, hospitals = [], visited = false) {
  const target = byId(targetId);
  target.innerHTML = "";
  hospitals.forEach((hospital) => {
    const card = document.createElement("article");
    card.className = "card";
    const distance = hospital.distance_km ?? "N/A";
    card.innerHTML = `
      <h3>${hospital.name || hospital.hospital_name}</h3>
      <p>${hospital.city || hospital.hospital_city || ""}</p>
      <p>${hospital.specialization || ""}</p>
      ${visited ? "" : `<p>Score: ${hospital.recommendation_score ?? "-"}</p>`}
      <p>Distance: ${distance}</p>
      <p>${hospital.emergency_services ? "Emergency ready" : "Standard care"}</p>
      <p class="mini">ID: ${hospital.id || hospital.hospital_id || "-"}</p>
    `;
    target.appendChild(card);
  });
}

function renderSummary(data) {
  const summary = byId("summary");
  summary.innerHTML = `
    <div class="summary-chip">${data.title || "Recommendations"}</div>
    <div class="summary-chip">Disease: ${data.disease || "-"}</div>
    <div class="summary-chip">Department: ${data.department || "-"}</div>
    <div class="summary-chip">Severity: ${data.severity || "-"}</div>
    ${data.emergency_mode ? `<div class="summary-chip alert">${data.emergency_note}</div>` : ""}
  `;
}

byId("signup-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());
  try {
    const { auth, createUserWithEmailAndPassword, sendEmailVerification, updateProfile } = await loadFirebaseRuntime();
    const credential = await createUserWithEmailAndPassword(auth, payload.email, payload.password);
    if (payload.name) {
      await updateProfile(credential.user, { displayName: payload.name });
    }
    await sendEmailVerification(credential.user);
    const idToken = await getFirebaseToken(credential.user);
    const result = await api("/signup", {
      method: "POST",
      body: JSON.stringify({
        id_token: idToken,
        name: payload.name,
        city: payload.city,
        language: payload.language,
      }),
    });
    if (result.status === "success") {
      setStatusState("signup-status", "success");
      showStatus("signup-status", "Account created. Please verify your email through the link sent to your email before logging in.");
      return;
    }
    setStatusState("signup-status", "error");
    showStatus("signup-status", result.message || "Signup failed.");
  } catch (error) {
    setStatusState("signup-status", "error");
    showStatus("signup-status", formatFirebaseError(error, "Signup failed."));
  }
});

byId("login-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());
  try {
    const { auth, signInWithEmailAndPassword, signOut } = await loadFirebaseRuntime();
    const credential = await signInWithEmailAndPassword(auth, payload.email, payload.password);
    if (!credential.user.emailVerified) {
      setStatusState("auth-status", "error");
      showStatus("auth-status", "Verify your email before logging in. Use the resend link if needed.");
      await signOut(auth).catch(() => null);
      return;
    }
    const idToken = await getFirebaseToken(credential.user);
    const result = await api("/login", {
      method: "POST",
      body: JSON.stringify({
        id_token: idToken,
      }),
    });
    if (result.status === "success") {
      window.location.href = "/user";
      return;
    }
    setStatusState("auth-status", "error");
    showStatus("auth-status", result.message || "Login failed.");
  } catch (error) {
    setStatusState("auth-status", "error");
    showStatus("auth-status", formatFirebaseError(error, "Login failed."));
  }
});

byId("resend-verification-btn")?.addEventListener("click", async () => {
  const email = String(document.querySelector('input[name="email"]')?.value || "").trim();
  const password = String(document.querySelector('input[name="password"]')?.value || "").trim();

  if (!email || !password) {
    setStatusState("auth-status", "error");
    showStatus("auth-status", "Enter your email and password first to resend the verification email.");
    return;
  }

  try {
    const { auth, fetchSignInMethodsForEmail, sendEmailVerification, signInWithEmailAndPassword, signOut } = await loadFirebaseRuntime();
    const signInMethods = await fetchSignInMethodsForEmail(auth, email);
    if (!signInMethods.includes("password")) {
      setStatusState("auth-status", "error");
      showStatus("auth-status", "No email/password account was found for that address.");
      return;
    }

    const credential = await signInWithEmailAndPassword(auth, email, password);
    if (credential.user.emailVerified) {
      setStatusState("auth-status", "success");
      showStatus("auth-status", "This email is already verified. You can log in now.");
      await signOut(auth).catch(() => null);
      return;
    }

    await sendEmailVerification(credential.user);
    setStatusState("auth-status", "success");
    showStatus("auth-status", "Verification email sent again. Please check your inbox.");
    await signOut(auth).catch(() => null);
  } catch (error) {
    setStatusState("auth-status", "error");
    showStatus("auth-status", formatFirebaseError(error, "Unable to resend verification email."));
  }
});

byId("reset-password-btn")?.addEventListener("click", async () => {
  const email = String(document.querySelector('input[name="email"]')?.value || "").trim();

  if (!email) {
    setStatusState("auth-status", "error");
    showStatus("auth-status", "Enter your email address first to receive a password reset link.");
    return;
  }

  try {
    const { auth, sendPasswordResetEmail } = await loadFirebaseRuntime();
    await sendPasswordResetEmail(auth, email);
    setStatusState("auth-status", "success");
    showStatus("auth-status", "Password reset email sent. Please check your inbox.");
  } catch (error) {
    setStatusState("auth-status", "error");
    showStatus("auth-status", formatFirebaseError(error, "Unable to send password reset email."));
  }
});

byId("admin-login-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());
  const result = await api("/admin/login", { method: "POST", body: JSON.stringify(payload) });
  if (result.status === "success") {
    window.location.href = "/admin/dashboard";
    return;
  }
  showStatus("admin-login-status", result.message || "Admin login failed.");
});

byId("recommend-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());
  const result = await api("/recommend", { method: "POST", body: JSON.stringify(payload) });
  if (result.status !== "success") {
    byId("summary").textContent = result.message || "Recommendation failed.";
    return;
  }
  renderSummary(result);
  renderCards("recommendation-cards", result.recommended_hospitals || []);
  renderCards("history-cards", result.previously_visited_hospitals || [], true);
});

byId("booking-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());
  const result = await api("/book_appointment", { method: "POST", body: JSON.stringify(payload) });
  showStatus("booking-status", result.message || `Appointment booked at ${result.appointment?.hospital_name || "hospital"}`);
});

byId("load-history")?.addEventListener("click", async () => {
  const result = await api("/history");
  if (result.status !== "success") {
    byId("history-cards").textContent = result.message || "Unable to load history.";
    return;
  }
  renderCards("history-cards", result.search_history || [], true);
});

byId("logout-btn")?.addEventListener("click", async () => {
  const runtime = await loadFirebaseRuntime().catch(() => null);
  await runtime?.signOut(runtime.auth).catch(() => null);
  await api("/logout", { method: "POST" });
  window.location.href = "/";
});
