/**
 * UI Helpers - Tabler Toast, Spinners, Production Guards
 * Version: 2.0.1 (Production Hardened)
 */

// Configuration globale
window.APP_ENV = 'development'; // Sera remplacé dynamiquement par Python

/**
 * Affiche un toast de succès (Tabler natif)
 */
function toastOK(msg) {
  const toast = document.createElement('div');
  toast.className = 'toast show align-items-center text-bg-success border-0';
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  toast.setAttribute('aria-atomic', 'true');
  
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-check me-2" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
          <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
          <path d="M5 12l5 5l10 -10"></path>
        </svg>
        ${msg}
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;
  
  document.body.appendChild(toast);
  
  // Auto-remove après 3 secondes
  setTimeout(() => {
    toast.remove();
  }, 3000);
}

/**
 * Affiche un toast d'erreur (Tabler natif)
 */
function toastERR(msg) {
  const toast = document.createElement('div');
  toast.className = 'toast show align-items-center text-bg-danger border-0';
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  toast.setAttribute('aria-atomic', 'true');
  
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-alert-circle me-2" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
          <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
          <path d="M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0"></path>
          <path d="M12 8v4"></path>
          <path d="M12 16h.01"></path>
        </svg>
        ${msg}
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;
  
  document.body.appendChild(toast);
  
  // Auto-remove après 5 secondes (erreurs restent plus longtemps)
  setTimeout(() => {
    toast.remove();
  }, 5000);
}

/**
 * Affiche un toast d'avertissement (Tabler natif)
 */
function toastWARN(msg) {
  const toast = document.createElement('div');
  toast.className = 'toast show align-items-center text-bg-warning border-0';
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  toast.setAttribute('aria-atomic', 'true');
  
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-alert-triangle me-2" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
          <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
          <path d="M12 9v4"></path>
          <path d="M10.363 3.591l-8.106 13.534a1.914 1.914 0 0 0 1.636 2.871h16.214a1.914 1.914 0 0 0 1.636 -2.87l-8.106 -13.536a1.914 1.914 0 0 0 -3.274 0z"></path>
          <path d="M12 16h.01"></path>
        </svg>
        ${msg}
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

/**
 * Affiche un spinner de chargement
 */
function showSpinner(spinnerId) {
  const spinner = document.getElementById(spinnerId);
  if (spinner) {
    spinner.classList.remove('d-none');
  }
}

/**
 * Cache un spinner de chargement
 */
function hideSpinner(spinnerId) {
  const spinner = document.getElementById(spinnerId);
  if (spinner) {
    spinner.classList.add('d-none');
  }
}

/**
 * Désactive un bouton dangereux en production
 */
function disableIfProd(btnId) {
  if (window.APP_ENV === 'production') {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.setAttribute('disabled', 'disabled');
      btn.classList.add('btn-secondary');
      btn.classList.remove('btn-danger');
      btn.title = 'Action désactivée en production';
      
      // Ajouter un badge "PROD LOCK"
      const badge = document.createElement('span');
      badge.className = 'badge bg-red ms-2';
      badge.textContent = 'PROD LOCK';
      btn.appendChild(badge);
    }
  }
}

/**
 * Mesure la latence de connexion à la base de données
 */
async function measureLatency(appBridge) {
  const t0 = performance.now();
  try {
    // Ping via AppBridge
    const pingJson = await Promise.resolve(appBridge.ping());
    JSON.parse(pingJson); // Vérifier que c'est du JSON valide
  } catch (e) {
    console.error('Erreur ping latence:', e);
  }
  const t1 = performance.now();
  const ms = Math.round(t1 - t0);
  
  // Mettre à jour le badge
  const badge = document.getElementById('db-latency-badge');
  if (badge) {
    let cls = 'bg-green';
    if (ms > 500) cls = 'bg-red';
    else if (ms > 100) cls = 'bg-orange';
    
    badge.className = 'badge ' + cls;
    badge.textContent = `${ms} ms`;
  }
  
  return ms;
}

/**
 * Wrapper pour appels async avec spinner et gestion d'erreur
 */
async function withSpinnerAndToast(spinnerId, asyncFunc) {
  showSpinner(spinnerId);
  try {
    const result = await asyncFunc();
    hideSpinner(spinnerId);
    return result;
  } catch (error) {
    hideSpinner(spinnerId);
    toastERR(error.message || 'Erreur inconnue');
    throw error;
  }
}

/**
 * Désactive un bouton pendant une opération async
 */
async function withButtonDisabled(btnId, asyncFunc) {
  const btn = document.getElementById(btnId);
  if (btn) {
    btn.setAttribute('disabled', 'disabled');
    btn.setAttribute('aria-busy', 'true');
  }
  
  try {
    const result = await asyncFunc();
    return result;
  } finally {
    if (btn) {
      btn.removeAttribute('disabled');
      btn.removeAttribute('aria-busy');
    }
  }
}

// Export pour utilisation globale
window.toastOK = toastOK;
window.toastERR = toastERR;
window.toastWARN = toastWARN;
window.showSpinner = showSpinner;
window.hideSpinner = hideSpinner;
window.disableIfProd = disableIfProd;
window.measureLatency = measureLatency;
window.withSpinnerAndToast = withSpinnerAndToast;
window.withButtonDisabled = withButtonDisabled;

// =======================
// Formatage FR-CA standard
// =======================
function formatNumberFr(value, decimals = 0) {
  const n = Number(value || 0);
  return new Intl.NumberFormat('fr-CA', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(n);
}

function formatCurrencyFr(value, currency = 'CAD') {
  const n = Number(value || 0);
  return new Intl.NumberFormat('fr-CA', {
    style: 'currency',
    currency
  }).format(n);
}

function applyKpiFormatting() {
  document.querySelectorAll('[data-format="currency"]').forEach(el => {
    el.textContent = formatCurrencyFr(el.textContent);
  });
  document.querySelectorAll('[data-format="number"]').forEach(el => {
    const decimals = Number(el.getAttribute('data-decimals') || 0);
    el.textContent = formatNumberFr(el.textContent, decimals);
  });
}

window.formatNumberFr = formatNumberFr;
window.formatCurrencyFr = formatCurrencyFr;
window.applyKpiFormatting = applyKpiFormatting;

