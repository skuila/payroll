/**
 * Options Employés & RH - Gestion des paramètres liés aux employés
 * Utilise localStorage pour la persistance
 */

// Valeurs par défaut
const DEFAULT_EMPLOYES_OPTIONS = {
  anonymizeNames: true,
  employeeIdFormat: "Matricule + Nom",
  showMatricule: true,
  alertUppercaseNames: true,
  alertNetNegative: true,
  alertShowSummary: true,
  salaryVariationThreshold: "20"
};

// Exposé globalement pour debug
window.DEFAULT_EMPLOYES_OPTIONS = DEFAULT_EMPLOYES_OPTIONS;

/**
 * Lit les options employés depuis localStorage
 * @returns {Object} Options employés
 */
function getEmployesOptions() {
  try {
    const stored = localStorage.getItem('payroll_employes_options');
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_EMPLOYES_OPTIONS, ...parsed };
    }
  } catch (err) {
    console.warn('Erreur lecture options employés:', err);
  }
  return { ...DEFAULT_EMPLOYES_OPTIONS };
}

// Exposé globalement
window.getEmployesOptions = getEmployesOptions;

/**
 * Enregistre les options employés dans localStorage
 * @param {Object} opt - Options à enregistrer
 */
function saveEmployesOptions(opt) {
  try {
    localStorage.setItem('payroll_employes_options', JSON.stringify(opt));
    console.log('Options employés sauvegardées:', opt);
  } catch (err) {
    console.error('Erreur sauvegarde options employés:', err);
  }
}

// Exposé globalement
window.saveEmployesOptions = saveEmployesOptions;

/**
 * Applique les options employés (expose via window)
 * @param {Object} opt - Options à appliquer
 */
function applyEmployesOptions(opt) {
  // Expose les options globalement pour utilisation dans l'application
  window.PAYROLL_EMPLOYES_OPTIONS = {
    anonymizeNames: opt.anonymizeNames,
    employeeIdFormat: opt.employeeIdFormat,
    showMatricule: opt.showMatricule,
    alertUppercaseNames: opt.alertUppercaseNames,
    alertNetNegative: opt.alertNetNegative,
    alertShowSummary: opt.alertShowSummary,
    salaryVariationThreshold: opt.salaryVariationThreshold
  };
  
  console.log('Options employés appliquées:', opt);
}

// Exposé globalement
window.applyEmployesOptions = applyEmployesOptions;

/**
 * Lit les valeurs actuelles du formulaire et retourne un objet d'options
 * @returns {Object} Options du formulaire
 */
function getEmployesFormOptions() {
  const anonymizeNamesEl = document.getElementById('opt-anonymize-names');
  const employeeIdFormatEl = document.getElementById('opt-employee-id-format');
  const showMatriculeEl = document.getElementById('opt-show-matricule');
  const alertUppercaseNamesEl = document.getElementById('opt-alert-uppercase-names');
  const alertNetNegativeEl = document.getElementById('opt-alert-net-negative');
  const alertShowSummaryEl = document.getElementById('opt-alert-show-summary');
  const salaryVariationThresholdEl = document.getElementById('opt-salary-variation-threshold');
  
  return {
    anonymizeNames: anonymizeNamesEl?.checked !== false,
    employeeIdFormat: employeeIdFormatEl?.value || 'Matricule + Nom',
    showMatricule: showMatriculeEl?.checked !== false,
    alertUppercaseNames: alertUppercaseNamesEl?.checked !== false,
    alertNetNegative: alertNetNegativeEl?.checked !== false,
    alertShowSummary: alertShowSummaryEl?.checked !== false,
    salaryVariationThreshold: salaryVariationThresholdEl?.value || '20'
  };
}

// Exposé globalement
window.getEmployesFormOptions = getEmployesFormOptions;

/**
 * Remplit le formulaire avec les valeurs des options
 * @param {Object} opt - Options à appliquer au formulaire
 */
function fillEmployesForm(opt) {
  const anonymizeNamesEl = document.getElementById('opt-anonymize-names');
  const employeeIdFormatEl = document.getElementById('opt-employee-id-format');
  const showMatriculeEl = document.getElementById('opt-show-matricule');
  const alertUppercaseNamesEl = document.getElementById('opt-alert-uppercase-names');
  const alertNetNegativeEl = document.getElementById('opt-alert-net-negative');
  const alertShowSummaryEl = document.getElementById('opt-alert-show-summary');
  const salaryVariationThresholdEl = document.getElementById('opt-salary-variation-threshold');
  
  if (anonymizeNamesEl) anonymizeNamesEl.checked = opt.anonymizeNames !== false;
  if (employeeIdFormatEl) employeeIdFormatEl.value = opt.employeeIdFormat || 'Matricule + Nom';
  if (showMatriculeEl) showMatriculeEl.checked = opt.showMatricule !== false;
  if (alertUppercaseNamesEl) alertUppercaseNamesEl.checked = opt.alertUppercaseNames !== false;
  if (alertNetNegativeEl) alertNetNegativeEl.checked = opt.alertNetNegative !== false;
  if (alertShowSummaryEl) alertShowSummaryEl.checked = opt.alertShowSummary !== false;
  if (salaryVariationThresholdEl) salaryVariationThresholdEl.value = opt.salaryVariationThreshold || '20';
}

// Exposé globalement
window.fillEmployesForm = fillEmployesForm;

/**
 * Met à jour le message de feedback
 * @param {string} message - Message à afficher
 */
function updateEmployesFeedback(message) {
  const feedbackEl = document.getElementById('employes-options-feedback');
  if (feedbackEl) {
    feedbackEl.textContent = message;
  }
}

/**
 * Initialise les listeners sur les contrôles du formulaire
 */
function attachEmployesListeners() {
  // Fonction helper pour sauvegarder automatiquement
  const autoSaveAndApply = () => {
    const opts = getEmployesFormOptions();
    saveEmployesOptions(opts);
    applyEmployesOptions(opts);
    updateEmployesFeedback('Options mises à jour.');
    setTimeout(() => updateEmployesFeedback(''), 2000);
  };
  
  // Anonymisation
  const anonymizeNamesEl = document.getElementById('opt-anonymize-names');
  if (anonymizeNamesEl) {
    anonymizeNamesEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Format d'identification
  const employeeIdFormatEl = document.getElementById('opt-employee-id-format');
  if (employeeIdFormatEl) {
    employeeIdFormatEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Afficher matricule
  const showMatriculeEl = document.getElementById('opt-show-matricule');
  if (showMatriculeEl) {
    showMatriculeEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Alerte majuscules
  const alertUppercaseNamesEl = document.getElementById('opt-alert-uppercase-names');
  if (alertUppercaseNamesEl) {
    alertUppercaseNamesEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Alerte net négatif
  const alertNetNegativeEl = document.getElementById('opt-alert-net-negative');
  if (alertNetNegativeEl) {
    alertNetNegativeEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Alerte résumé
  const alertShowSummaryEl = document.getElementById('opt-alert-show-summary');
  if (alertShowSummaryEl) {
    alertShowSummaryEl.addEventListener('change', autoSaveAndApply);
  }
  
  // Seuil de variation
  const salaryVariationThresholdEl = document.getElementById('opt-salary-variation-threshold');
  if (salaryVariationThresholdEl) {
    salaryVariationThresholdEl.addEventListener('input', autoSaveAndApply);
  }
  
  // Bouton enregistrer
  const saveBtn = document.getElementById('btn-save-employes-options');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      const opts = getEmployesFormOptions();
      saveEmployesOptions(opts);
      applyEmployesOptions(opts);
      updateEmployesFeedback('Options employés enregistrées avec succès.');
      setTimeout(() => updateEmployesFeedback(''), 3000);
    });
  }
}

// Exposé globalement
window.attachEmployesListeners = attachEmployesListeners;

/**
 * Initialise le panneau Employés
 */
function initEmployesPanel() {
  const opts = getEmployesOptions();
  fillEmployesForm(opts);
  applyEmployesOptions(opts);
  attachEmployesListeners();
  console.log('Panneau Employés initialisé');
}

// Exposé globalement
window.initEmployesPanel = initEmployesPanel;

// Auto-init si DOM est déjà chargé
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initEmployesPanel);
} else {
  initEmployesPanel();
}

