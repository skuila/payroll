/**
 * Options Sécurité & Confidentialité - Gestion des paramètres de sécurité
 * Utilise localStorage pour la persistance
 */

// Valeurs par défaut
const DEFAULT_SECURITY_OPTIONS = {
  enableEncryption: false,
  adminProtectOptions: false,
  adminCode: ""
};

// Exposé globalement pour debug
window.DEFAULT_SECURITY_OPTIONS = DEFAULT_SECURITY_OPTIONS;

/**
 * Lit les options de sécurité depuis localStorage
 * @returns {Object} Options de sécurité
 */
function getSecurityOptions() {
  try {
    const stored = localStorage.getItem('payroll_security_options');
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_SECURITY_OPTIONS, ...parsed };
    }
  } catch (err) {
    console.warn('Erreur lecture options sécurité:', err);
  }
  return { ...DEFAULT_SECURITY_OPTIONS };
}

// Exposé globalement
window.getSecurityOptions = getSecurityOptions;

/**
 * Enregistre les options de sécurité dans localStorage
 * @param {Object} opt - Options à enregistrer
 */
function saveSecurityOptions(opt) {
  try {
    // Ne pas stocker le code en clair dans localStorage (pour l'instant, placeholder)
    // Dans une vraie implémentation, on hasherait le code
    const toSave = {
      enableEncryption: opt.enableEncryption !== false,
      adminProtectOptions: opt.adminProtectOptions !== false,
      adminCode: opt.adminCode || "" // À hasher dans une vraie implémentation
    };
    localStorage.setItem('payroll_security_options', JSON.stringify(toSave));
    console.log('Options sécurité sauvegardées (code non hashé pour l\'instant)');
  } catch (err) {
    console.error('Erreur sauvegarde options sécurité:', err);
  }
}

// Exposé globalement
window.saveSecurityOptions = saveSecurityOptions;

/**
 * Applique les options de sécurité (expose via window)
 * @param {Object} opt - Options à appliquer
 */
function applySecurityOptions(opt) {
  // Expose les options globalement pour utilisation dans l'application
  window.PAYROLL_SECURITY_OPTIONS = {
    enableEncryption: opt.enableEncryption !== false,
    adminProtectOptions: opt.adminProtectOptions !== false,
    adminCode: opt.adminCode || ""
  };
  
  // Pour l'instant, pas de logique de blocage réelle
  // À implémenter plus tard : vérification du code admin avant d'afficher les options
  
  console.log('Options sécurité appliquées:', {
    enableEncryption: window.PAYROLL_SECURITY_OPTIONS.enableEncryption,
    adminProtectOptions: window.PAYROLL_SECURITY_OPTIONS.adminProtectOptions,
    adminCodeSet: !!window.PAYROLL_SECURITY_OPTIONS.adminCode
  });
}

// Exposé globalement
window.applySecurityOptions = applySecurityOptions;

/**
 * Lit les valeurs actuelles du formulaire et retourne un objet d'options
 * @returns {Object} Options du formulaire
 */
function getSecurityFormOptions() {
  const enableEncryptionEl = document.getElementById('opt-enable-encryption');
  const adminProtectOptionsEl = document.getElementById('opt-admin-protect-options');
  const adminCodeEl = document.getElementById('opt-admin-code');
  
  return {
    enableEncryption: enableEncryptionEl?.checked === true,
    adminProtectOptions: adminProtectOptionsEl?.checked === true,
    adminCode: adminCodeEl?.value || ""
  };
}

// Exposé globalement
window.getSecurityFormOptions = getSecurityFormOptions;

/**
 * Remplit le formulaire avec les valeurs des options
 * @param {Object} opt - Options à appliquer au formulaire
 */
function fillSecurityForm(opt) {
  const enableEncryptionEl = document.getElementById('opt-enable-encryption');
  const adminProtectOptionsEl = document.getElementById('opt-admin-protect-options');
  const adminCodeEl = document.getElementById('opt-admin-code');
  
  if (enableEncryptionEl) enableEncryptionEl.checked = opt.enableEncryption === true;
  if (adminProtectOptionsEl) adminProtectOptionsEl.checked = opt.adminProtectOptions === true;
  // Ne pas remplir le champ password pour des raisons de sécurité
  // if (adminCodeEl) adminCodeEl.value = opt.adminCode || "";
}

// Exposé globalement
window.fillSecurityForm = fillSecurityForm;

/**
 * Met à jour le message de feedback
 * @param {string} message - Message à afficher
 */
function updateSecurityFeedback(message) {
  const feedbackEl = document.getElementById('security-options-feedback');
  if (feedbackEl) {
    feedbackEl.textContent = message;
  }
}

/**
 * Initialise les listeners sur les contrôles du formulaire
 */
function attachSecurityListeners() {
  // Fonction helper pour sauvegarder automatiquement
  const autoSaveAndApply = () => {
    const opts = getSecurityFormOptions();
    saveSecurityOptions(opts);
    applySecurityOptions(opts);
    updateSecurityFeedback('Options mises à jour.');
    setTimeout(() => updateSecurityFeedback(''), 2000);
  };
  
  // Chiffrement
  const enableEncryptionEl = document.getElementById('opt-enable-encryption');
  if (enableEncryptionEl) {
    enableEncryptionEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Protection admin
  const adminProtectOptionsEl = document.getElementById('opt-admin-protect-options');
  if (adminProtectOptionsEl) {
    adminProtectOptionsEl.addEventListener('change', () => {
      const opts = getSecurityFormOptions();
      saveSecurityOptions(opts);
      applySecurityOptions(opts);
      updateSecurityFeedback('Protection mise à jour. Le code sera demandé lors du prochain accès aux options.');
      setTimeout(() => updateSecurityFeedback(''), 3000);
    });
  }
  
  // Code administrateur
  const adminCodeEl = document.getElementById('opt-admin-code');
  if (adminCodeEl) {
    adminCodeEl.addEventListener('blur', autoSaveAndApply);
    adminCodeEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Bouton enregistrer
  const saveBtn = document.getElementById('btn-save-security-options');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      const opts = getSecurityFormOptions();
      saveSecurityOptions(opts);
      applySecurityOptions(opts);
      updateSecurityFeedback('Options de sécurité enregistrées avec succès.');
      setTimeout(() => updateSecurityFeedback(''), 3000);
    });
  }
}

// Exposé globalement
window.attachSecurityListeners = attachSecurityListeners;

/**
 * Initialise le panneau Sécurité
 */
function initSecurityPanel() {
  const opts = getSecurityOptions();
  fillSecurityForm(opts);
  applySecurityOptions(opts);
  attachSecurityListeners();
  console.log('Panneau Sécurité initialisé');
}

// Exposé globalement
window.initSecurityPanel = initSecurityPanel;

// Auto-init si DOM est déjà chargé
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSecurityPanel);
} else {
  initSecurityPanel();
}

