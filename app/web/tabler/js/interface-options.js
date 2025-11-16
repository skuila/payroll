/**
 * Interface Options Manager - Gestion des options d'affichage de l'interface
 * Utilise AppBridge (QWebChannel) pour la persistance avec fallback localStorage
 */

// Valeurs par défaut
const DEFAULT_INTERFACE_OPTIONS = {
  mode: "dark",
  primary: "#0d6efd",
  secondary: "#6c757d",
  accent: "#198754",
  fontSize: "14px",
  fontFamily: "Inter, system-ui, -apple-system",
  density: "standard",
  currency: "CAD",
  currencySymbol: "$",
  symbolPosition: "before",
  thousandSeparator: " ",
  decimalSeparator: ",",
  decimals: 2,
  negativeFormat: "-123",
  dateFormat: "DD/MM/YYYY",
  showTooltips: true,
  highContrast: false,
  borders: true,
  themePreset: "standard"
};

// Exposé globalement pour debug
window.DEFAULT_INTERFACE_OPTIONS = DEFAULT_INTERFACE_OPTIONS;

/**
 * Initialise AppBridge si disponible
 * @returns {Promise<Object|null>} AppBridge ou null
 */
function initAppBridge() {
  if (window.AppBridge) {
    return Promise.resolve(window.AppBridge);
  }
  if (typeof window.AppBridgeReady === 'function') {
    return window.AppBridgeReady();
  }
  if (window.qt?.webChannelTransport) {
    return new Promise((resolve, reject) => {
      new QWebChannel(qt.webChannelTransport, channel => {
        window.AppBridge = channel.objects.AppBridge || null;
        if (window.AppBridge) {
          resolve(window.AppBridge);
        } else {
          reject(new Error('AppBridge non disponible'));
        }
      });
    });
  }
  return Promise.resolve(null);
}

/**
 * Lit les options d'interface depuis AppBridge (avec fallback localStorage)
 * @returns {Promise<Object>} Options d'interface
 */
async function getInterfaceOptions() {
  try {
    // Essayer AppBridge d'abord
    const bridge = await initAppBridge();
    if (bridge && typeof bridge.get_options === 'function') {
      try {
        const raw = await Promise.resolve(bridge.get_options());
        const payload = typeof raw === 'string' ? JSON.parse(raw) : raw;
        const interfaceOpts = payload?.interface || {};
        if (Object.keys(interfaceOpts).length > 0) {
          const merged = { ...DEFAULT_INTERFACE_OPTIONS, ...interfaceOpts };
          // Sauvegarder en cache localStorage
          saveInterfaceOptionsToLocal(merged);
          return merged;
        }
      } catch (err) {
        console.warn('Erreur lecture AppBridge options interface:', err);
      }
    }
  } catch (err) {
    console.warn('AppBridge non disponible, utilisation localStorage:', err);
  }
  
  // Fallback localStorage
  try {
    const stored = localStorage.getItem('payroll_interface_options');
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_INTERFACE_OPTIONS, ...parsed };
    }
  } catch (err) {
    console.warn('Erreur lecture localStorage options interface:', err);
  }
  
  return { ...DEFAULT_INTERFACE_OPTIONS };
}

/**
 * Sauvegarde dans localStorage (cache)
 * @param {Object} opt - Options à sauvegarder
 */
function saveInterfaceOptionsToLocal(opt) {
  try {
    localStorage.setItem('payroll_interface_options', JSON.stringify(opt));
  } catch (err) {
    console.warn('Erreur sauvegarde localStorage:', err);
  }
}

// Exposé globalement
window.getInterfaceOptions = getInterfaceOptions;

/**
 * Enregistre les options d'interface (AppBridge + localStorage cache)
 * @param {Object} opt - Options à enregistrer
 * @returns {Promise<boolean>} Succès
 */
async function saveInterfaceOptions(opt) {
  // Sauvegarder dans localStorage immédiatement (cache)
  saveInterfaceOptionsToLocal(opt);
  
  // Essayer AppBridge
  try {
    const bridge = await initAppBridge();
    if (bridge && typeof bridge.update_options === 'function') {
      const payload = {
        interface: opt
      };
      const response = await Promise.resolve(bridge.update_options(JSON.stringify(payload)));
      const result = typeof response === 'string' ? JSON.parse(response) : response;
      if (result?.status === 'ok') {
        console.log('Options interface sauvegardées via AppBridge:', opt);
        return true;
      } else {
        console.warn('Erreur sauvegarde AppBridge:', result?.message);
      }
    }
  } catch (err) {
    console.warn('AppBridge non disponible, sauvegarde localStorage uniquement:', err);
  }
  
  console.log('Options interface sauvegardées (localStorage):', opt);
  return false;
}

// Exposé globalement
window.saveInterfaceOptions = saveInterfaceOptions;

/**
 * Applique les options d'interface à la page courante
 * @param {Object} opt - Options à appliquer
 */
function applyInterfaceOptions(opt) {
  const root = document.documentElement;
  
  // Couleurs CSS variables (Bootstrap/Tabler)
  root.style.setProperty('--bs-primary', opt.primary);
  root.style.setProperty('--bs-secondary', opt.secondary);
  root.style.setProperty('--primary', opt.primary);
  root.style.setProperty('--secondary', opt.secondary);
  root.style.setProperty('--accent', opt.accent);
  
  // Mode sombre/clair (via data-bs-theme)
  if (opt.mode === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.setAttribute('data-bs-theme', prefersDark ? 'dark' : 'light');
  } else {
    root.setAttribute('data-bs-theme', opt.mode);
  }
  
  // Taille de police
  root.style.fontSize = opt.fontSize;
  
  // Famille de police
  root.style.fontFamily = opt.fontFamily;
  
  // Densité (classes sur body)
  document.body.classList.remove('density-compact', 'density-standard', 'density-comfortable');
  document.body.classList.add(`density-${opt.density}`);
  
  // Contraste élevé
  if (opt.highContrast) {
    document.body.classList.add('high-contrast');
  } else {
    document.body.classList.remove('high-contrast');
  }
  
  // Bordures
  if (opt.borders) {
    document.body.classList.add('show-borders');
  } else {
    document.body.classList.remove('show-borders');
  }
  
  // Format monétaire global (exposé via window)
  window.PAYROLL_FORMAT = {
    currency: opt.currency,
    currencySymbol: opt.currencySymbol,
    symbolPosition: opt.symbolPosition,
    thousandSeparator: opt.thousandSeparator,
    decimalSeparator: opt.decimalSeparator,
    decimals: opt.decimals,
    negativeFormat: opt.negativeFormat
  };
  
  // Format de date global
  window.PAYROLL_DATE_FORMAT = opt.dateFormat;
  
  // Tooltips
  window.PAYROLL_SHOW_TOOLTIPS = opt.showTooltips;
  
  console.log('Options interface appliquées:', opt);
}

// Exposé globalement
window.applyInterfaceOptions = applyInterfaceOptions;

/**
 * Lit les valeurs actuelles du formulaire et retourne un objet d'options
 * @returns {Object} Options du formulaire
 */
function getFormOptions() {
  const modeEl = document.getElementById('opt-mode');
  const primaryEl = document.getElementById('opt-color-primary');
  const secondaryEl = document.getElementById('opt-color-secondary');
  const accentEl = document.getElementById('opt-color-accent');
  const highContrastEl = document.getElementById('opt-high-contrast');
  const fontSizeEl = document.getElementById('opt-font-size');
  const fontFamilyEl = document.getElementById('opt-font-family');
  const densityEls = document.querySelectorAll('input[name="opt-density"]');
  const bordersEl = document.getElementById('opt-borders');
  const currencyEl = document.getElementById('opt-currency');
  const currencyPosEls = document.querySelectorAll('input[name="opt-currency-pos"]');
  const thousandSepEl = document.getElementById('opt-thousand-sep');
  const decimalSepEl = document.getElementById('opt-decimal-sep');
  const decimalsEl = document.getElementById('opt-decimals');
  const negativeFormatEl = document.getElementById('opt-negative-format');
  const dateFormatEl = document.getElementById('opt-date-format');
  const tooltipsEl = document.getElementById('opt-tooltips');
  const themePresetEls = document.querySelectorAll('input[name="opt-theme-preset"]');
  
  const density = Array.from(densityEls).find(r => r.checked)?.value || 'standard';
  const currencyPos = Array.from(currencyPosEls).find(r => r.checked)?.value || 'before';
  const themePreset = Array.from(themePresetEls).find(r => r.checked)?.value || 'standard';
  
  // Mapping symboles
  const currencySymbolMap = {
    'CAD': '$',
    'USD': '$',
    'EUR': '€',
    'None': ''
  };
  
  // Mapping séparateurs
  const separatorMap = {
    'space': ' ',
    'thin-space': '\u2009',
    'comma': ',',
    'dot': '.',
    'none': ''
  };
  
  return {
    mode: modeEl?.value || 'dark',
    primary: primaryEl?.value || '#0d6efd',
    secondary: secondaryEl?.value || '#6c757d',
    accent: accentEl?.value || '#198754',
    fontSize: fontSizeEl?.value ? `${fontSizeEl.value}px` : '14px',
    fontFamily: fontFamilyEl?.value || 'Inter, system-ui, -apple-system',
    density: density,
    currency: currencyEl?.value || 'CAD',
    currencySymbol: currencySymbolMap[currencyEl?.value] || '$',
    symbolPosition: currencyPos,
    thousandSeparator: separatorMap[thousandSepEl?.value] || ' ',
    decimalSeparator: decimalSepEl?.value === 'comma' ? ',' : '.',
    decimals: parseInt(decimalsEl?.value || '2', 10),
    negativeFormat: negativeFormatEl?.value || '-123',
    dateFormat: dateFormatEl?.value || 'DD/MM/YYYY',
    showTooltips: tooltipsEl?.checked !== false,
    highContrast: highContrastEl?.checked === true,
    borders: bordersEl?.checked !== false,
    themePreset: themePreset
  };
}

// Exposé globalement
window.getFormOptions = getFormOptions;

/**
 * Remplit le formulaire avec les valeurs des options
 * @param {Object} opt - Options à appliquer au formulaire
 */
function fillForm(opt) {
  const modeEl = document.getElementById('opt-mode');
  const primaryEl = document.getElementById('opt-color-primary');
  const secondaryEl = document.getElementById('opt-color-secondary');
  const accentEl = document.getElementById('opt-color-accent');
  const highContrastEl = document.getElementById('opt-high-contrast');
  const fontSizeEl = document.getElementById('opt-font-size');
  const fontSizeValueEl = document.getElementById('opt-font-size-value');
  const fontFamilyEl = document.getElementById('opt-font-family');
  const bordersEl = document.getElementById('opt-borders');
  const currencyEl = document.getElementById('opt-currency');
  const thousandSepEl = document.getElementById('opt-thousand-sep');
  const decimalSepEl = document.getElementById('opt-decimal-sep');
  const decimalsEl = document.getElementById('opt-decimals');
  const negativeFormatEl = document.getElementById('opt-negative-format');
  const dateFormatEl = document.getElementById('opt-date-format');
  const tooltipsEl = document.getElementById('opt-tooltips');
  
  if (modeEl) modeEl.value = opt.mode || 'dark';
  if (primaryEl) primaryEl.value = opt.primary || '#0d6efd';
  if (secondaryEl) secondaryEl.value = opt.secondary || '#6c757d';
  if (accentEl) accentEl.value = opt.accent || '#198754';
  if (highContrastEl) highContrastEl.checked = opt.highContrast === true;
  if (fontSizeEl) {
    const size = parseInt(opt.fontSize || '14px', 10);
    fontSizeEl.value = size;
    if (fontSizeValueEl) fontSizeValueEl.textContent = size;
  }
  if (fontFamilyEl) fontFamilyEl.value = opt.fontFamily || 'Inter, system-ui, -apple-system';
  if (bordersEl) bordersEl.checked = opt.borders !== false;
  if (currencyEl) currencyEl.value = opt.currency || 'CAD';
  if (tooltipsEl) tooltipsEl.checked = opt.showTooltips !== false;
  
  // Densité
  const densityEls = document.querySelectorAll(`input[name="opt-density"][value="${opt.density || 'standard'}"]`);
  densityEls.forEach(el => el.checked = true);
  
  // Position symbole devise
  const currencyPosEls = document.querySelectorAll(`input[name="opt-currency-pos"][value="${opt.symbolPosition || 'before'}"]`);
  currencyPosEls.forEach(el => el.checked = true);
  
  // Thème prédéfini
  const themePresetEls = document.querySelectorAll(`input[name="opt-theme-preset"][value="${opt.themePreset || 'standard'}"]`);
  themePresetEls.forEach(el => el.checked = true);
  
  // Mapping séparateurs (inverse)
  const separatorReverseMap = {
    ' ': 'space',
    '\u2009': 'thin-space',
    ',': 'comma',
    '.': 'dot',
    '': 'none'
  };
  if (thousandSepEl) thousandSepEl.value = separatorReverseMap[opt.thousandSeparator] || 'space';
  if (decimalSepEl) decimalSepEl.value = opt.decimalSeparator === ',' ? 'comma' : 'dot';
  if (decimalsEl) decimalsEl.value = String(opt.decimals || 2);
  if (negativeFormatEl) negativeFormatEl.value = opt.negativeFormat || '-123';
  if (dateFormatEl) dateFormatEl.value = opt.dateFormat || 'DD/MM/YYYY';
}

/**
 * Applique un thème prédéfini
 * @param {string} preset - Nom du preset ('standard', 'dark-professional', 'high-contrast', 'blue')
 */
function applyThemePreset(preset) {
  const presets = {
    'standard': {
      mode: 'dark',
      primary: '#0d6efd',
      secondary: '#6c757d',
      accent: '#198754',
      highContrast: false
    },
    'dark-professional': {
      mode: 'dark',
      primary: '#2c3e50',
      secondary: '#34495e',
      accent: '#3498db',
      highContrast: false
    },
    'high-contrast': {
      mode: 'light',
      primary: '#000000',
      secondary: '#333333',
      accent: '#000000',
      highContrast: true
    },
    'blue': {
      mode: 'dark',
      primary: '#0066cc',
      secondary: '#0052a3',
      accent: '#00a3e0',
      highContrast: false
    }
  };
  
  const presetOpts = presets[preset];
  if (!presetOpts) return;
  
  const currentOpts = getFormOptions();
  const newOpts = { ...currentOpts, ...presetOpts };
  
  // Mettre à jour les champs du formulaire
  const primaryEl = document.getElementById('opt-color-primary');
  const secondaryEl = document.getElementById('opt-color-secondary');
  const accentEl = document.getElementById('opt-color-accent');
  const modeEl = document.getElementById('opt-mode');
  const highContrastEl = document.getElementById('opt-high-contrast');
  const themePresetEls = document.querySelectorAll(`input[name="opt-theme-preset"][value="${preset}"]`);
  
  if (primaryEl) primaryEl.value = newOpts.primary;
  if (secondaryEl) secondaryEl.value = newOpts.secondary;
  if (accentEl) accentEl.value = newOpts.accent;
  if (modeEl) modeEl.value = newOpts.mode;
  if (highContrastEl) highContrastEl.checked = newOpts.highContrast === true;
  themePresetEls.forEach(el => el.checked = true);
  
  // Sauvegarder et appliquer (localStorage uniquement, en temps réel)
  saveInterfaceOptionsToLocal(newOpts);
  applyInterfaceOptions(newOpts);
}

/**
 * Initialise les listeners sur les contrôles du formulaire
 */
function attachInterfaceListeners() {
  // Fonction helper pour sauvegarder automatiquement (localStorage uniquement, en temps réel)
  const autoSaveLocal = (opts) => {
    saveInterfaceOptionsToLocal(opts);
    applyInterfaceOptions(opts);
  };
  
  // Mode global
  const modeEl = document.getElementById('opt-mode');
  if (modeEl) {
    modeEl.addEventListener('change', () => {
      const opts = getFormOptions();
      autoSaveLocal(opts);
    });
  }
  
  // Couleurs
  ['opt-color-primary', 'opt-color-secondary', 'opt-color-accent'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => {
        const opts = getFormOptions();
        autoSaveLocal(opts);
      });
    }
  });
  
  // Thèmes prédéfinis
  document.querySelectorAll('input[name="opt-theme-preset"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
      if (e.target.checked) {
        applyThemePreset(e.target.value);
      }
    });
  });
  
  // Contraste élevé
  const highContrastEl = document.getElementById('opt-high-contrast');
  if (highContrastEl) {
    highContrastEl.addEventListener('change', () => {
      const opts = getFormOptions();
      autoSaveLocal(opts);
    });
  }
  
  // Taille de police (range)
  const fontSizeEl = document.getElementById('opt-font-size');
  const fontSizeValueEl = document.getElementById('opt-font-size-value');
  if (fontSizeEl) {
    fontSizeEl.addEventListener('input', () => {
      if (fontSizeValueEl) fontSizeValueEl.textContent = fontSizeEl.value;
      const opts = getFormOptions();
      autoSaveLocal(opts);
    });
  }
  
  // Famille de police
  const fontFamilyEl = document.getElementById('opt-font-family');
  if (fontFamilyEl) {
    fontFamilyEl.addEventListener('change', () => {
      const opts = getFormOptions();
      autoSaveLocal(opts);
    });
  }
  
  // Densité
  document.querySelectorAll('input[name="opt-density"]').forEach(radio => {
    radio.addEventListener('change', () => {
      const opts = getFormOptions();
      autoSaveLocal(opts);
    });
  });
  
  // Bordures
  const bordersEl = document.getElementById('opt-borders');
  if (bordersEl) {
    bordersEl.addEventListener('change', () => {
      const opts = getFormOptions();
      autoSaveLocal(opts);
    });
  }
  
  // Format monétaire (devise, position, séparateurs, etc.)
  ['opt-currency', 'opt-thousand-sep', 'opt-decimal-sep', 'opt-decimals', 'opt-negative-format'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => {
        const opts = getFormOptions();
        autoSaveLocal(opts);
      });
    }
  });
  
  // Position symbole devise
  document.querySelectorAll('input[name="opt-currency-pos"]').forEach(radio => {
    radio.addEventListener('change', () => {
      const opts = getFormOptions();
      autoSaveLocal(opts);
    });
  });
  
  // Format de date
  const dateFormatEl = document.getElementById('opt-date-format');
  if (dateFormatEl) {
    dateFormatEl.addEventListener('change', () => {
      const opts = getFormOptions();
      autoSaveLocal(opts);
    });
  }
  
  // Tooltips
  const tooltipsEl = document.getElementById('opt-tooltips');
  if (tooltipsEl) {
    tooltipsEl.addEventListener('change', () => {
      const opts = getFormOptions();
      autoSaveLocal(opts);
    });
  }
  
  // Bouton reset
  const resetBtn = document.getElementById('btn-reset-interface');
  if (resetBtn) {
    resetBtn.addEventListener('click', async () => {
      if (confirm('Réinitialiser toutes les options aux valeurs par défaut ?')) {
        const defaults = { ...DEFAULT_INTERFACE_OPTIONS };
        fillForm(defaults);
        await saveInterfaceOptions(defaults);
        applyInterfaceOptions(defaults);
        showToast('Options réinitialisées aux valeurs par défaut', 'success');
      }
    });
  }
  
  // Bouton sauvegarder profil d'interface (AppBridge)
  const saveGlobalBtn = document.getElementById('btn-save-interface-global');
  if (saveGlobalBtn) {
    saveGlobalBtn.addEventListener('click', async () => {
      const feedbackEl = document.getElementById('interface-feedback');
      if (feedbackEl) feedbackEl.textContent = 'Enregistrement...';
      
      try {
        const opts = getFormOptions();
        const success = await saveInterfaceOptions(opts);
        if (success) {
          if (feedbackEl) feedbackEl.textContent = 'Profil d\'interface enregistré avec succès.';
          showToast('Profil d\'interface enregistré avec succès', 'success');
        } else {
          if (feedbackEl) feedbackEl.textContent = 'Profil enregistré sur cet appareil (localStorage).';
          showToast('Profil d\'interface enregistré sur cet appareil (localStorage)', 'info');
        }
      } catch (err) {
        console.error('Erreur sauvegarde:', err);
        if (feedbackEl) feedbackEl.textContent = 'Erreur lors de l\'enregistrement.';
        showToast('Erreur lors de l\'enregistrement', 'error');
      }
    });
  }
  
  // Bouton choisir colonnes
  const columnsBtn = document.querySelector('[data-bs-target="#modal-columns"]');
  if (columnsBtn) {
    columnsBtn.addEventListener('click', () => {
      // Charger les colonnes sélectionnées depuis localStorage
      loadColumnChoices();
    });
  }
  
  // Sauvegarder choix colonnes dans le modal
  const saveColumnsBtn = document.getElementById('btn-save-columns');
  if (saveColumnsBtn) {
    saveColumnsBtn.addEventListener('click', () => {
      saveColumnChoices();
      const modal = bootstrap.Modal.getInstance(document.getElementById('modal-columns'));
      if (modal) modal.hide();
    });
  }
}

/**
 * Charge les choix de colonnes depuis localStorage
 */
function loadColumnChoices() {
  try {
    const stored = localStorage.getItem('payroll_default_columns');
    const columns = stored ? JSON.parse(stored) : ['Matricule', 'Nom', 'Poste', 'Catégorie', 'Salaire Net', 'Statut'];
    
    const checkboxes = document.querySelectorAll('#opt-columns-chooser input[type="checkbox"]');
    checkboxes.forEach(cb => {
      cb.checked = columns.includes(cb.value);
    });
  } catch (err) {
    console.warn('Erreur chargement colonnes:', err);
  }
}

/**
 * Sauvegarde les choix de colonnes dans localStorage
 */
function saveColumnChoices() {
  try {
    const checkboxes = document.querySelectorAll('#opt-columns-chooser input[type="checkbox"]:checked');
    const columns = Array.from(checkboxes).map(cb => cb.value);
    localStorage.setItem('payroll_default_columns', JSON.stringify(columns));
    showToast('Colonnes sauvegardées', 'success');
  } catch (err) {
    console.error('Erreur sauvegarde colonnes:', err);
  }
}

/**
 * Affiche un toast simple
 * @param {string} message - Message à afficher
 * @param {string} type - Type (success, warning, error)
 */
function showToast(message, type = 'info') {
  const toastContainer = document.getElementById('toast-container') || createToastContainer();
  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'danger'} border-0`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>
  `;
  toastContainer.appendChild(toast);
  const bsToast = new bootstrap.Toast(toast);
  bsToast.show();
  toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

/**
 * Crée le conteneur de toasts s'il n'existe pas
 */
function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
  container.style.zIndex = '9999';
  document.body.appendChild(container);
  return container;
}

/**
 * Initialise le panneau Interface
 */
async function initInterfacePanel() {
  try {
    const opts = await getInterfaceOptions();
    fillForm(opts);
    applyInterfaceOptions(opts);
    attachInterfaceListeners();
    console.log('Panneau Interface initialisé');
  } catch (err) {
    console.error('Erreur initialisation panneau Interface:', err);
    // Utiliser valeurs par défaut en cas d'erreur
    fillForm(DEFAULT_INTERFACE_OPTIONS);
    applyInterfaceOptions(DEFAULT_INTERFACE_OPTIONS);
    attachInterfaceListeners();
  }
}

// Exposé globalement
window.initInterfacePanel = initInterfacePanel;

/**
 * Injecte les styles CSS pour les densités et autres effets
 */
function injectInterfaceStyles() {
  if (document.getElementById('interface-options-styles')) return;
  
  const style = document.createElement('style');
  style.id = 'interface-options-styles';
  style.textContent = `
    /* Densité compacte */
    body.density-compact .table td,
    body.density-compact .table th {
      padding: 0.25rem 0.5rem;
    }
    body.density-compact .card-body {
      padding: 0.75rem;
    }
    body.density-compact .btn {
      padding: 0.25rem 0.75rem;
      font-size: 0.875rem;
    }
    
    /* Densité standard (défaut) */
    body.density-standard .table td,
    body.density-standard .table th {
      padding: 0.5rem 0.75rem;
    }
    
    /* Densité confortable */
    body.density-comfortable .table td,
    body.density-comfortable .table th {
      padding: 0.75rem 1rem;
    }
    body.density-comfortable .card-body {
      padding: 1.5rem;
    }
    body.density-comfortable .btn {
      padding: 0.5rem 1rem;
    }
    
    /* Contraste élevé */
    body.high-contrast {
      --bs-body-bg: #ffffff;
      --bs-body-color: #000000;
      --bs-border-color: #000000;
    }
    body[data-bs-theme="dark"].high-contrast {
      --bs-body-bg: #000000;
      --bs-body-color: #ffffff;
      --bs-border-color: #ffffff;
    }
    body.high-contrast .card,
    body.high-contrast .table {
      border: 2px solid var(--bs-border-color);
    }
    
    /* Bordures conditionnelles */
    body:not(.show-borders) .table td,
    body:not(.show-borders) .table th {
      border: none;
    }
    body:not(.show-borders) .card {
      border: none;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
  `;
  document.head.appendChild(style);
}

// Injecter les styles au chargement
injectInterfaceStyles();

// Auto-init si DOM est déjà chargé
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initInterfacePanel);
} else {
  initInterfacePanel();
}

