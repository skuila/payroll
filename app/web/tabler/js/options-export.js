/**
 * Options Export & Rapports - Gestion des paramètres d'export
 * Utilise localStorage pour la persistance
 */

// Valeurs par défaut
const DEFAULT_EXPORT_OPTIONS = {
  exportCols: {
    codepaie: true,
    description: true,
    categorie: true,
    poste: true,
    statut: true
  },
  filenamePattern: "Paie_{date_paie}_{type_rapport}.xlsx",
  exportFolder: "",
  pdfOrientation: "Portrait",
  pdfLegend: true
};

// Exposé globalement pour debug
window.DEFAULT_EXPORT_OPTIONS = DEFAULT_EXPORT_OPTIONS;

/**
 * Lit les options d'export depuis localStorage
 * @returns {Object} Options d'export
 */
function getExportOptions() {
  try {
    const stored = localStorage.getItem('payroll_export_options');
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_EXPORT_OPTIONS, ...parsed };
    }
  } catch (err) {
    console.warn('Erreur lecture options export:', err);
  }
  return { ...DEFAULT_EXPORT_OPTIONS };
}

// Exposé globalement
window.getExportOptions = getExportOptions;

/**
 * Enregistre les options d'export dans localStorage
 * @param {Object} opt - Options à enregistrer
 */
function saveExportOptions(opt) {
  try {
    localStorage.setItem('payroll_export_options', JSON.stringify(opt));
    console.log('Options export sauvegardées:', opt);
  } catch (err) {
    console.error('Erreur sauvegarde options export:', err);
  }
}

// Exposé globalement
window.saveExportOptions = saveExportOptions;

/**
 * Applique les options d'export (expose via window)
 * @param {Object} opt - Options à appliquer
 */
function applyExportOptions(opt) {
  // Expose les options globalement pour utilisation dans l'application
  window.PAYROLL_EXPORT_OPTIONS = {
    exportCols: opt.exportCols || DEFAULT_EXPORT_OPTIONS.exportCols,
    filenamePattern: opt.filenamePattern || DEFAULT_EXPORT_OPTIONS.filenamePattern,
    exportFolder: opt.exportFolder || DEFAULT_EXPORT_OPTIONS.exportFolder,
    pdfOrientation: opt.pdfOrientation || DEFAULT_EXPORT_OPTIONS.pdfOrientation,
    pdfLegend: opt.pdfLegend !== false
  };
  
  console.log('Options export appliquées:', opt);
}

// Exposé globalement
window.applyExportOptions = applyExportOptions;

/**
 * Lit les valeurs actuelles du formulaire et retourne un objet d'options
 * @returns {Object} Options du formulaire
 */
function getExportFormOptions() {
  const codepaieEl = document.getElementById('opt-export-col-codepaie');
  const descriptionEl = document.getElementById('opt-export-col-description');
  const categorieEl = document.getElementById('opt-export-col-categorie');
  const posteEl = document.getElementById('opt-export-col-poste');
  const statutEl = document.getElementById('opt-export-col-statut');
  const filenamePatternEl = document.getElementById('opt-export-filename-pattern');
  const exportFolderEl = document.getElementById('opt-export-folder');
  const pdfOrientationEl = document.getElementById('opt-export-pdf-orientation');
  const pdfLegendEl = document.getElementById('opt-export-pdf-legend');
  
  return {
    exportCols: {
      codepaie: codepaieEl?.checked !== false,
      description: descriptionEl?.checked !== false,
      categorie: categorieEl?.checked !== false,
      poste: posteEl?.checked !== false,
      statut: statutEl?.checked !== false
    },
    filenamePattern: filenamePatternEl?.value || DEFAULT_EXPORT_OPTIONS.filenamePattern,
    exportFolder: exportFolderEl?.value || '',
    pdfOrientation: pdfOrientationEl?.value || 'Portrait',
    pdfLegend: pdfLegendEl?.checked !== false
  };
}

// Exposé globalement
window.getExportFormOptions = getExportFormOptions;

/**
 * Remplit le formulaire avec les valeurs des options
 * @param {Object} opt - Options à appliquer au formulaire
 */
function fillExportForm(opt) {
  const codepaieEl = document.getElementById('opt-export-col-codepaie');
  const descriptionEl = document.getElementById('opt-export-col-description');
  const categorieEl = document.getElementById('opt-export-col-categorie');
  const posteEl = document.getElementById('opt-export-col-poste');
  const statutEl = document.getElementById('opt-export-col-statut');
  const filenamePatternEl = document.getElementById('opt-export-filename-pattern');
  const exportFolderEl = document.getElementById('opt-export-folder');
  const pdfOrientationEl = document.getElementById('opt-export-pdf-orientation');
  const pdfLegendEl = document.getElementById('opt-export-pdf-legend');
  
  const cols = opt.exportCols || DEFAULT_EXPORT_OPTIONS.exportCols;
  
  if (codepaieEl) codepaieEl.checked = cols.codepaie !== false;
  if (descriptionEl) descriptionEl.checked = cols.description !== false;
  if (categorieEl) categorieEl.checked = cols.categorie !== false;
  if (posteEl) posteEl.checked = cols.poste !== false;
  if (statutEl) statutEl.checked = cols.statut !== false;
  if (filenamePatternEl) filenamePatternEl.value = opt.filenamePattern || DEFAULT_EXPORT_OPTIONS.filenamePattern;
  if (exportFolderEl) exportFolderEl.value = opt.exportFolder || '';
  if (pdfOrientationEl) pdfOrientationEl.value = opt.pdfOrientation || 'Portrait';
  if (pdfLegendEl) pdfLegendEl.checked = opt.pdfLegend !== false;
}

// Exposé globalement
window.fillExportForm = fillExportForm;

/**
 * Met à jour le message de feedback Excel
 * @param {string} message - Message à afficher
 */
function updateExportExcelFeedback(message) {
  const feedbackEl = document.getElementById('export-excel-feedback');
  if (feedbackEl) {
    feedbackEl.textContent = message;
  }
}

/**
 * Met à jour le message de feedback PDF
 * @param {string} message - Message à afficher
 */
function updateExportPdfFeedback(message) {
  const feedbackEl = document.getElementById('export-pdf-feedback');
  if (feedbackEl) {
    feedbackEl.textContent = message;
  }
}

/**
 * Initialise les listeners sur les contrôles du formulaire
 */
function attachExportListeners() {
  // Fonction helper pour sauvegarder automatiquement (Excel)
  const autoSaveExcel = () => {
    const opts = getExportFormOptions();
    const excelOpts = {
      ...opts,
      pdfOrientation: getExportOptions().pdfOrientation,
      pdfLegend: getExportOptions().pdfLegend
    };
    saveExportOptions(excelOpts);
    applyExportOptions(excelOpts);
    updateExportExcelFeedback('Options mises à jour.');
    setTimeout(() => updateExportExcelFeedback(''), 2000);
  };
  
  // Fonction helper pour sauvegarder automatiquement (PDF)
  const autoSavePdf = () => {
    const opts = getExportFormOptions();
    const pdfOpts = {
      exportCols: getExportOptions().exportCols,
      filenamePattern: getExportOptions().filenamePattern,
      exportFolder: getExportOptions().exportFolder,
      ...opts
    };
    saveExportOptions(pdfOpts);
    applyExportOptions(pdfOpts);
    updateExportPdfFeedback('Options mises à jour.');
    setTimeout(() => updateExportPdfFeedback(''), 2000);
  };
  
  // Listeners pour les checkboxes Excel (colonnes)
  const excelCheckboxes = [
    'opt-export-col-codepaie',
    'opt-export-col-description',
    'opt-export-col-categorie',
    'opt-export-col-poste',
    'opt-export-col-statut'
  ];
  
  excelCheckboxes.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', autoSaveExcel);
    }
  });
  
  // Listener pour le modèle de nom de fichier
  const filenamePatternEl = document.getElementById('opt-export-filename-pattern');
  if (filenamePatternEl) {
    filenamePatternEl.addEventListener('change', autoSaveExcel);
    filenamePatternEl.addEventListener('blur', autoSaveExcel);
  }
  
  // Listener pour le dossier d'export
  const exportFolderEl = document.getElementById('opt-export-folder');
  if (exportFolderEl) {
    exportFolderEl.addEventListener('change', autoSaveExcel);
    exportFolderEl.addEventListener('blur', autoSaveExcel);
  }
  
  // Listeners pour les options PDF
  const pdfOrientationEl = document.getElementById('opt-export-pdf-orientation');
  if (pdfOrientationEl) {
    pdfOrientationEl.addEventListener('change', autoSavePdf);
  }
  
  const pdfLegendEl = document.getElementById('opt-export-pdf-legend');
  if (pdfLegendEl) {
    pdfLegendEl.addEventListener('change', autoSavePdf);
  }
  
  // Bouton enregistrer options Excel
  const saveExcelBtn = document.getElementById('btn-save-export-excel');
  if (saveExcelBtn) {
    saveExcelBtn.addEventListener('click', () => {
      const opts = getExportFormOptions();
      const excelOpts = {
        ...opts,
        pdfOrientation: getExportOptions().pdfOrientation,
        pdfLegend: getExportOptions().pdfLegend
      };
      saveExportOptions(excelOpts);
      applyExportOptions(excelOpts);
      updateExportExcelFeedback('Options Excel enregistrées avec succès.');
      setTimeout(() => updateExportExcelFeedback(''), 3000);
    });
  }
  
  // Bouton enregistrer options PDF
  const savePdfBtn = document.getElementById('btn-save-export-pdf');
  if (savePdfBtn) {
    savePdfBtn.addEventListener('click', () => {
      const opts = getExportFormOptions();
      const pdfOpts = {
        exportCols: getExportOptions().exportCols,
        filenamePattern: getExportOptions().filenamePattern,
        exportFolder: getExportOptions().exportFolder,
        pdfOrientation: opts.pdfOrientation,
        pdfLegend: opts.pdfLegend
      };
      saveExportOptions(pdfOpts);
      applyExportOptions(pdfOpts);
      updateExportPdfFeedback('Options PDF enregistrées avec succès.');
      setTimeout(() => updateExportPdfFeedback(''), 3000);
    });
  }
}

// Exposé globalement
window.attachExportListeners = attachExportListeners;

/**
 * Initialise le panneau Export
 */
function initExportPanel() {
  const opts = getExportOptions();
  fillExportForm(opts);
  applyExportOptions(opts);
  attachExportListeners();
  console.log('Panneau Export initialisé');
}

// Exposé globalement
window.initExportPanel = initExportPanel;

// Auto-init si DOM est déjà chargé
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initExportPanel);
} else {
  initExportPanel();
}

