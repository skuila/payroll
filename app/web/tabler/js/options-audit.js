/**
 * Options Audit & Contrôles - Gestion des paramètres d'audit
 * Utilise localStorage pour la persistance
 */

// Valeurs par défaut pour les options d'audit
const DEFAULT_AUDIT_OPTIONS = {
  auditNetNegative: true,
  auditUppercase: true,
  auditSensitiveCodes: true,
  auditMissingPeriods: true,
  auditOpenAfterImport: true
};

// Exposé globalement pour debug
window.DEFAULT_AUDIT_OPTIONS = DEFAULT_AUDIT_OPTIONS;

/**
 * Lit les options d'audit depuis localStorage
 * @returns {Object} Options d'audit
 */
function getAuditOptions() {
  try {
    const stored = localStorage.getItem('payroll_audit_options');
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_AUDIT_OPTIONS, ...parsed };
    }
  } catch (err) {
    console.warn('Erreur lecture options audit:', err);
  }
  return { ...DEFAULT_AUDIT_OPTIONS };
}

// Exposé globalement
window.getAuditOptions = getAuditOptions;

/**
 * Enregistre les options d'audit dans localStorage
 * @param {Object} opt - Options à enregistrer
 */
function saveAuditOptions(opt) {
  try {
    localStorage.setItem('payroll_audit_options', JSON.stringify(opt));
    console.log('Options audit sauvegardées:', opt);
  } catch (err) {
    console.error('Erreur sauvegarde options audit:', err);
  }
}

// Exposé globalement
window.saveAuditOptions = saveAuditOptions;

/**
 * Applique les options d'audit (expose via window)
 * @param {Object} opt - Options à appliquer
 */
function applyAuditOptions(opt) {
  // Expose les options globalement pour utilisation dans l'application
  window.PAYROLL_AUDIT_OPTIONS = {
    auditNetNegative: opt.auditNetNegative,
    auditUppercase: opt.auditUppercase,
    auditSensitiveCodes: opt.auditSensitiveCodes,
    auditMissingPeriods: opt.auditMissingPeriods,
    auditOpenAfterImport: opt.auditOpenAfterImport
  };
  
  console.log('Options audit appliquées:', opt);
}

// Exposé globalement
window.applyAuditOptions = applyAuditOptions;

/**
 * Lit les valeurs actuelles du formulaire et retourne un objet d'options
 * @returns {Object} Options du formulaire
 */
function getAuditFormOptions() {
  const auditNetNegativeEl = document.getElementById('opt-audit-net-negative');
  const auditUppercaseEl = document.getElementById('opt-audit-uppercase');
  const auditSensitiveCodesEl = document.getElementById('opt-audit-sensitive-codes');
  const auditMissingPeriodsEl = document.getElementById('opt-audit-missing-periods');
  const auditOpenAfterImportEl = document.getElementById('opt-audit-open-after-import');
  
  return {
    auditNetNegative: auditNetNegativeEl?.checked !== false,
    auditUppercase: auditUppercaseEl?.checked !== false,
    auditSensitiveCodes: auditSensitiveCodesEl?.checked !== false,
    auditMissingPeriods: auditMissingPeriodsEl?.checked !== false,
    auditOpenAfterImport: auditOpenAfterImportEl?.checked !== false
  };
}

// Exposé globalement
window.getAuditFormOptions = getAuditFormOptions;

/**
 * Remplit le formulaire avec les valeurs des options
 * @param {Object} opt - Options à appliquer au formulaire
 */
function fillAuditForm(opt) {
  const auditNetNegativeEl = document.getElementById('opt-audit-net-negative');
  const auditUppercaseEl = document.getElementById('opt-audit-uppercase');
  const auditSensitiveCodesEl = document.getElementById('opt-audit-sensitive-codes');
  const auditMissingPeriodsEl = document.getElementById('opt-audit-missing-periods');
  const auditOpenAfterImportEl = document.getElementById('opt-audit-open-after-import');
  
  if (auditNetNegativeEl) auditNetNegativeEl.checked = opt.auditNetNegative !== false;
  if (auditUppercaseEl) auditUppercaseEl.checked = opt.auditUppercase !== false;
  if (auditSensitiveCodesEl) auditSensitiveCodesEl.checked = opt.auditSensitiveCodes !== false;
  if (auditMissingPeriodsEl) auditMissingPeriodsEl.checked = opt.auditMissingPeriods !== false;
  if (auditOpenAfterImportEl) auditOpenAfterImportEl.checked = opt.auditOpenAfterImport !== false;
}

// Exposé globalement
window.fillAuditForm = fillAuditForm;

/**
 * Met à jour le message de feedback
 * @param {string} message - Message à afficher
 */
function updateAuditFeedback(message) {
  const feedbackEl = document.getElementById('audit-options-feedback');
  if (feedbackEl) {
    feedbackEl.textContent = message;
  }
}

// ========== GESTION DES CODES SENSIBLES ==========

/**
 * Lit la liste des codes sensibles depuis localStorage
 * @returns {Array} Liste des codes sensibles [{ code, description, risk }, ...]
 */
function getSensitiveCodes() {
  try {
    const stored = localStorage.getItem('payroll_sensitive_codes');
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (err) {
    console.warn('Erreur lecture codes sensibles:', err);
  }
  return [];
}

// Exposé globalement
window.getSensitiveCodes = getSensitiveCodes;

/**
 * Enregistre la liste des codes sensibles dans localStorage
 * @param {Array} list - Liste des codes sensibles
 */
function saveSensitiveCodes(list) {
  try {
    localStorage.setItem('payroll_sensitive_codes', JSON.stringify(list));
    console.log('Codes sensibles sauvegardés:', list);
  } catch (err) {
    console.error('Erreur sauvegarde codes sensibles:', err);
  }
}

// Exposé globalement
window.saveSensitiveCodes = saveSensitiveCodes;

/**
 * Récupère les données du tableau des codes sensibles
 * @returns {Array} Liste des codes sensibles depuis le tableau
 */
function getSensitiveCodesFromTable() {
  const tbody = document.getElementById('sensitive-codes-tbody');
  if (!tbody) return [];
  
  const rows = tbody.querySelectorAll('tr[data-code-row]');
  const codes = [];
  
  rows.forEach((row, index) => {
    const codeInput = row.querySelector('input[name="sensitive-code"]');
    const descInput = row.querySelector('input[name="sensitive-description"]');
    const riskSelect = row.querySelector('select[name="sensitive-risk"]');
    
    const code = codeInput?.value?.trim();
    const description = descInput?.value?.trim();
    const risk = riskSelect?.value || 'faible';
    
    if (code) {
      codes.push({ code, description: description || '', risk });
    }
  });
  
  return codes;
}

/**
 * Rend le tableau des codes sensibles avec les données
 */
function renderSensitiveCodesTable() {
  const tbody = document.getElementById('sensitive-codes-tbody');
  if (!tbody) return;
  
  const codes = getSensitiveCodes();
  tbody.innerHTML = '';
  
  if (codes.length === 0) {
    // Afficher une ligne vide par défaut
    addSensitiveCodeRow();
  } else {
    codes.forEach((item, index) => {
      addSensitiveCodeRow(item.code, item.description, item.risk);
    });
  }
}

/**
 * Ajoute une nouvelle ligne dans le tableau des codes sensibles
 * @param {string} code - Code initial (optionnel)
 * @param {string} description - Description initiale (optionnel)
 * @param {string} risk - Niveau de risque initial (optionnel)
 */
function addSensitiveCodeRow(code = '', description = '', risk = 'faible') {
  const tbody = document.getElementById('sensitive-codes-tbody');
  if (!tbody) return;
  
  const rowIndex = tbody.querySelectorAll('tr[data-code-row]').length;
  const row = document.createElement('tr');
  row.setAttribute('data-code-row', rowIndex);
  
  row.innerHTML = `
    <td>
      <input type="text" class="form-control form-control-sm" name="sensitive-code" value="${code}" placeholder="Ex: 001, 002, etc.">
    </td>
    <td>
      <input type="text" class="form-control form-control-sm" name="sensitive-description" value="${description}" placeholder="Description du code">
    </td>
    <td>
      <select class="form-select form-select-sm" name="sensitive-risk">
        <option value="faible" ${risk === 'faible' ? 'selected' : ''}>Faible</option>
        <option value="moyen" ${risk === 'moyen' ? 'selected' : ''}>Moyen</option>
        <option value="élevé" ${risk === 'élevé' ? 'selected' : ''}>Élevé</option>
      </select>
    </td>
    <td>
      <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeSensitiveCodeRow(this)">
        <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="16" height="16" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M4 7l16 0" /><path d="M10 11l0 6" /><path d="M14 11l0 6" /><path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12" /><path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3" /></svg>
      </button>
    </td>
  `;
  
  tbody.appendChild(row);
}

// Exposé globalement
window.addSensitiveCodeRow = addSensitiveCodeRow;

/**
 * Supprime une ligne du tableau des codes sensibles
 * @param {HTMLElement} button - Bouton de suppression
 */
function removeSensitiveCodeRow(button) {
  const row = button.closest('tr[data-code-row]');
  if (row) {
    row.remove();
    // Re-indexer les lignes restantes
    const tbody = document.getElementById('sensitive-codes-tbody');
    if (tbody) {
      const rows = tbody.querySelectorAll('tr[data-code-row]');
      rows.forEach((r, index) => {
        r.setAttribute('data-code-row', index);
      });
    }
  }
}

// Exposé globalement
window.removeSensitiveCodeRow = removeSensitiveCodeRow;

/**
 * Initialise les listeners sur les contrôles du formulaire
 */
function attachAuditListeners() {
  // Fonction helper pour sauvegarder automatiquement
  const autoSaveAndApply = () => {
    const opts = getAuditFormOptions();
    saveAuditOptions(opts);
    applyAuditOptions(opts);
    updateAuditFeedback('Options mises à jour.');
    setTimeout(() => updateAuditFeedback(''), 2000);
  };
  
  // Listeners pour les checkboxes d'audit
  const checkboxes = [
    'opt-audit-net-negative',
    'opt-audit-uppercase',
    'opt-audit-sensitive-codes',
    'opt-audit-missing-periods',
    'opt-audit-open-after-import'
  ];
  
  checkboxes.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', autoSaveAndApply);
    }
  });
  
  // Bouton enregistrer options audit
  const saveBtn = document.getElementById('btn-save-audit-options');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      const opts = getAuditFormOptions();
      saveAuditOptions(opts);
      applyAuditOptions(opts);
      updateAuditFeedback('Options d\'audit enregistrées avec succès.');
      setTimeout(() => updateAuditFeedback(''), 3000);
    });
  }
  
  // Bouton gérer codes sensibles (ouvre le modal)
  const manageCodesBtn = document.getElementById('btn-manage-sensitive-codes');
  if (manageCodesBtn) {
    manageCodesBtn.addEventListener('click', () => {
      renderSensitiveCodesTable();
    });
  }
  
  // Bouton ajouter ligne codes sensibles
  const addCodeBtn = document.getElementById('btn-add-sensitive-code');
  if (addCodeBtn) {
    addCodeBtn.addEventListener('click', () => {
      addSensitiveCodeRow();
    });
  }
  
  // Bouton sauvegarder codes sensibles
  const saveCodesBtn = document.getElementById('btn-save-sensitive-codes');
  if (saveCodesBtn) {
    saveCodesBtn.addEventListener('click', () => {
      const codes = getSensitiveCodesFromTable();
      saveSensitiveCodes(codes);
      console.log('Codes sensibles sauvegardés:', codes);
      
      // Fermer le modal
      const modal = bootstrap.Modal.getInstance(document.getElementById('modal-sensitive-codes'));
      if (modal) {
        modal.hide();
      }
      
      // Afficher un message de succès
      updateAuditFeedback('Liste des codes sensibles enregistrée.');
      setTimeout(() => updateAuditFeedback(''), 3000);
    });
  }
}

// Exposé globalement
window.attachAuditListeners = attachAuditListeners;

/**
 * Initialise le panneau Audit
 */
function initAuditPanel() {
  const opts = getAuditOptions();
  fillAuditForm(opts);
  applyAuditOptions(opts);
  attachAuditListeners();
  console.log('Panneau Audit initialisé');
}

// Exposé globalement
window.initAuditPanel = initAuditPanel;

// Auto-init si DOM est déjà chargé
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAuditPanel);
} else {
  initAuditPanel();
}

