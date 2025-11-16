/**
 * Options Fiscalité / DAS - Gestion des paramètres fiscaux
 * Utilise localStorage pour la persistance
 */

// Valeurs par défaut
const DEFAULT_FISCALITE_OPTIONS = {
  countryProvince: "Canada - QC",
  fiscalYearDas: "2025",
  enableDasControl: true,
  dasRoundingMode: "Arrondi traditionnel",
  dasProfile: "Profil générique",
  dasSeparator: "Tabulation"
};

// Exposé globalement pour debug
window.DEFAULT_FISCALITE_OPTIONS = DEFAULT_FISCALITE_OPTIONS;

/**
 * Lit les options fiscales depuis localStorage
 * @returns {Object} Options fiscales
 */
function getFiscaliteOptions() {
  try {
    const stored = localStorage.getItem('payroll_fiscalite_options');
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_FISCALITE_OPTIONS, ...parsed };
    }
  } catch (err) {
    console.warn('Erreur lecture options fiscales:', err);
  }
  return { ...DEFAULT_FISCALITE_OPTIONS };
}

// Exposé globalement
window.getFiscaliteOptions = getFiscaliteOptions;

/**
 * Enregistre les options fiscales dans localStorage
 * @param {Object} opt - Options à enregistrer
 */
function saveFiscaliteOptions(opt) {
  try {
    localStorage.setItem('payroll_fiscalite_options', JSON.stringify(opt));
    console.log('Options fiscales sauvegardées:', opt);
  } catch (err) {
    console.error('Erreur sauvegarde options fiscales:', err);
  }
}

// Exposé globalement
window.saveFiscaliteOptions = saveFiscaliteOptions;

/**
 * Applique les options fiscales (expose via window)
 * @param {Object} opt - Options à appliquer
 */
function applyFiscaliteOptions(opt) {
  // Expose les options globalement pour utilisation dans l'application
  window.PAYROLL_FISCALITE_OPTIONS = {
    countryProvince: opt.countryProvince,
    fiscalYearDas: opt.fiscalYearDas,
    enableDasControl: opt.enableDasControl,
    dasRoundingMode: opt.dasRoundingMode,
    dasProfile: opt.dasProfile,
    dasSeparator: opt.dasSeparator
  };
  
  console.log('Options fiscales appliquées:', opt);
}

// Exposé globalement
window.applyFiscaliteOptions = applyFiscaliteOptions;

/**
 * Lit les valeurs actuelles du formulaire et retourne un objet d'options
 * @returns {Object} Options du formulaire
 */
function getFiscaliteFormOptions() {
  const countryProvinceEl = document.getElementById('opt-country-province');
  const fiscalYearDasEl = document.getElementById('opt-fiscal-year-das');
  const enableDasControlEl = document.getElementById('opt-enable-das-control');
  const dasRoundingModeEl = document.getElementById('opt-das-rounding-mode');
  const dasProfileEl = document.getElementById('opt-das-profile');
  const dasSeparatorEl = document.getElementById('opt-das-separator');
  
  return {
    countryProvince: countryProvinceEl?.value || 'Canada - QC',
    fiscalYearDas: fiscalYearDasEl?.value || '2025',
    enableDasControl: enableDasControlEl?.checked !== false,
    dasRoundingMode: dasRoundingModeEl?.value || 'Arrondi traditionnel',
    dasProfile: dasProfileEl?.value || 'Profil générique',
    dasSeparator: dasSeparatorEl?.value || 'Tabulation'
  };
}

// Exposé globalement
window.getFiscaliteFormOptions = getFiscaliteFormOptions;

/**
 * Remplit le formulaire avec les valeurs des options
 * @param {Object} opt - Options à appliquer au formulaire
 */
function fillFiscaliteForm(opt) {
  const countryProvinceEl = document.getElementById('opt-country-province');
  const fiscalYearDasEl = document.getElementById('opt-fiscal-year-das');
  const enableDasControlEl = document.getElementById('opt-enable-das-control');
  const dasRoundingModeEl = document.getElementById('opt-das-rounding-mode');
  const dasProfileEl = document.getElementById('opt-das-profile');
  const dasSeparatorEl = document.getElementById('opt-das-separator');
  
  if (countryProvinceEl) countryProvinceEl.value = opt.countryProvince || 'Canada - QC';
  if (fiscalYearDasEl) fiscalYearDasEl.value = opt.fiscalYearDas || '2025';
  if (enableDasControlEl) enableDasControlEl.checked = opt.enableDasControl !== false;
  if (dasRoundingModeEl) dasRoundingModeEl.value = opt.dasRoundingMode || 'Arrondi traditionnel';
  if (dasProfileEl) dasProfileEl.value = opt.dasProfile || 'Profil générique';
  if (dasSeparatorEl) dasSeparatorEl.value = opt.dasSeparator || 'Tabulation';
}

// Exposé globalement
window.fillFiscaliteForm = fillFiscaliteForm;

/**
 * Met à jour le message de feedback
 * @param {string} message - Message à afficher
 */
function updateFiscaliteFeedback(message) {
  const feedbackEl = document.getElementById('fiscalite-options-feedback');
  if (feedbackEl) {
    feedbackEl.textContent = message;
  }
}

/**
 * Initialise les listeners sur les contrôles du formulaire
 */
function attachFiscaliteListeners() {
  // Fonction helper pour sauvegarder automatiquement
  const autoSaveAndApply = () => {
    const opts = getFiscaliteFormOptions();
    saveFiscaliteOptions(opts);
    applyFiscaliteOptions(opts);
    updateFiscaliteFeedback('Options mises à jour.');
    setTimeout(() => updateFiscaliteFeedback(''), 2000);
  };
  
  // Pays / Province
  const countryProvinceEl = document.getElementById('opt-country-province');
  if (countryProvinceEl) {
    countryProvinceEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Année fiscale
  const fiscalYearDasEl = document.getElementById('opt-fiscal-year-das');
  if (fiscalYearDasEl) {
    fiscalYearDasEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Contrôle DAS
  const enableDasControlEl = document.getElementById('opt-enable-das-control');
  if (enableDasControlEl) {
    enableDasControlEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Arrondi DAS
  const dasRoundingModeEl = document.getElementById('opt-das-rounding-mode');
  if (dasRoundingModeEl) {
    dasRoundingModeEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Profil DAS
  const dasProfileEl = document.getElementById('opt-das-profile');
  if (dasProfileEl) {
    dasProfileEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Séparateur DAS
  const dasSeparatorEl = document.getElementById('opt-das-separator');
  if (dasSeparatorEl) {
    dasSeparatorEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Bouton enregistrer
  const saveBtn = document.getElementById('btn-save-fiscalite-options');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      const opts = getFiscaliteFormOptions();
      saveFiscaliteOptions(opts);
      applyFiscaliteOptions(opts);
      updateFiscaliteFeedback('Options fiscales enregistrées avec succès.');
      setTimeout(() => updateFiscaliteFeedback(''), 3000);
    });
  }
}

// Exposé globalement
window.attachFiscaliteListeners = attachFiscaliteListeners;

/**
 * Initialise le panneau Fiscalité
 */
function initFiscalitePanel() {
  const opts = getFiscaliteOptions();
  fillFiscaliteForm(opts);
  applyFiscaliteOptions(opts);
  attachFiscaliteListeners();
  console.log('Panneau Fiscalité initialisé');
}

// Exposé globalement
window.initFiscalitePanel = initFiscalitePanel;

// Auto-init si DOM est déjà chargé
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initFiscalitePanel);
} else {
  initFiscalitePanel();
}

