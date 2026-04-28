import { initializeApp } from "https://www.gstatic.com/firebasejs/12.7.0/firebase-app.js";
import { getAnalytics, isSupported as analyticsSupported } from "https://www.gstatic.com/firebasejs/12.7.0/firebase-analytics.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/12.7.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyD5FP9BR3V8BvEyE_ZXS_9QqEed_QMBYj8",
  authDomain: "hospital-recommendation-9d085.firebaseapp.com",
  projectId: "hospital-recommendation-9d085",
  storageBucket: "hospital-recommendation-9d085.firebasestorage.app",
  messagingSenderId: "151453638726",
  appId: "1:151453638726:web:ff7cff61156aa8f7096a47",
  measurementId: "G-2HGZ32Q45N",
};

const firebaseApp = initializeApp(firebaseConfig);
const auth = getAuth(firebaseApp);

let analytics = null;

analyticsSupported()
  .then((supported) => {
    if (supported) {
      analytics = getAnalytics(firebaseApp);
    }
  })
  .catch(() => {
    analytics = null;
  });

window.firebaseApp = firebaseApp;
window.firebaseAuth = auth;

export { analytics, auth, firebaseApp };
