// web/tabler/app_bridge.js
// ========================================
// UNIFIED APP BRIDGE - Tabler Dashboard
// ========================================
// API JavaScript centralisée pour communiquer avec Python via QWebChannel
// RÈGLE: Zéro CSS custom, zéro composant custom - injection contenu uniquement dans composants Tabler officiels

console.log('✓ App Bridge chargé (Tabler-only policy)');

// ========== API PUBLIQUE ==========

/**
 * Mise à jour des KPI du dashboard (index.html)
 * @param {Object} kpiMap - Map {id: value} des KPI à mettre à jour
 * 
 * Exemple:
 *   window.AppBridge.updateKPI({
 *     'kpi-masse': '125 000,50 $',
 *     'kpi-net': '2 777,78 $',
 *     'kpi-deductions': '25 000,00 $',
 *     'kpi-employes': '45'
 *   });
 * 
 * IDs disponibles (index.html):
 *   - kpi-masse : Masse salariale brute
 *   - kpi-net : Net moyen
 *   - kpi-deductions : Déductions totales
 *   - kpi-employes : Nombre d'employés actifs
 *   - kpi-masse-trend : Tendance masse (ex: "+5%")
 *   - kpi-net-trend : Tendance net
 *   - kpi-deductions-trend : Tendance déductions
 *   - kpi-employes-trend : Tendance employés
 *   - kpi-masse-progress : Progress bar (style width)
 *   - kpi-deductions-progress : Progress bar déductions
 */
window.AppBridge = window.AppBridge || {};

window.AppBridge.updateKPI = function(kpiMap) {
  if (!kpiMap || typeof kpiMap !== 'object') {
    console.error('❌ updateKPI: argument invalide (objet requis)');
    return;
  }
  
  let updatedCount = 0;
  
  for (const [id, value] of Object.entries(kpiMap)) {
    const element = document.getElementById(id);
    
    if (element) {
      // Distinction: progress bar vs texte
      if (id.includes('-progress')) {
        // Progress bar: mettre à jour style.width
        if (typeof value === 'number') {
          element.style.width = `${Math.min(100, Math.max(0, value))}%`;
          updatedCount++;
        } else {
          console.warn(`⚠️ updateKPI: valeur progress invalide pour ${id} (number requis)`);
        }
      } else {
        // Texte: injecter via textContent (pas d'HTML brut pour sécurité)
        element.textContent = String(value);
        updatedCount++;
      }
    } else {
      console.warn(`⚠️ updateKPI: élément introuvable - ${id}`);
    }
  }
  
  if (updatedCount > 0) {
    console.log(`✓ updateKPI: ${updatedCount} KPI mis à jour`);
  }
};

/**
 * Formatage monétaire CAD canadien (fr-CA)
 * Utilise Intl.NumberFormat avec fallback robuste
 * 
 * @param {number} value - Montant à formater
 * @returns {string} - Montant formaté (ex: "1 234,56 $")
 */
window.AppBridge.formatCAD = function(value) {
  try {
    return new Intl.NumberFormat('fr-CA', {
      style: 'currency',
      currency: 'CAD',
      currencyDisplay: 'narrowSymbol',  // Force "$" uniquement
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  } catch (e) {
    // Fallback si Intl échoue
    return String(value).replace('.', ',') + ' $';
  }
};

/**
 * Formatage date fr-CA
 * 
 * @param {string|Date} dateStr - Date à formater
 * @returns {string} - Date formatée
 */
window.AppBridge.formatDate = function(dateStr) {
  try {
    return new Intl.DateTimeFormat('fr-CA', { 
      dateStyle: 'medium' 
    }).format(new Date(dateStr));
  } catch (e) {
    return String(dateStr);
  }
};

/**
 * Afficher/masquer un élément par ID
 * 
 * @param {string} elementId - ID de l'élément
 * @param {boolean} visible - true pour afficher, false pour masquer
 */
window.AppBridge.toggleElement = function(elementId, visible) {
  const element = document.getElementById(elementId);
  if (element) {
    element.style.display = visible ? '' : 'none';
  } else {
    console.warn(`⚠️ toggleElement: élément introuvable - ${elementId}`);
  }
};

/**
 * Injecter du HTML dans un conteneur (avec sanitization basique)
 * ATTENTION: Utiliser uniquement pour contenu contrôlé (pas d'input utilisateur)
 * 
 * @param {string} containerId - ID du conteneur
 * @param {string} htmlContent - Contenu HTML à injecter
 */
window.AppBridge.injectHTML = function(containerId, htmlContent) {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = htmlContent;
    console.log(`✓ injectHTML: contenu injecté dans ${containerId}`);
  } else {
    console.warn(`⚠️ injectHTML: conteneur introuvable - ${containerId}`);
  }
};

/**
 * Afficher un toast Tabler (notification temporaire)
 * 
 * @param {string} message - Message à afficher
 * @param {string} type - Type: 'success', 'danger', 'warning', 'info'
 */
window.AppBridge.showToast = function(message, type = 'info') {
  // TODO: Implémenter toast Tabler natif
  // Pour l'instant: fallback console
  const emoji = {
    'success': '✅',
    'danger': '❌',
    'warning': '⚠️',
    'info': 'ℹ️'
  };
  
  console.log(`${emoji[type] || 'ℹ️'} Toast [${type}]: ${message}`);
  
  // Si Bootstrap Toast disponible (Tabler l'inclut)
  // Créer dynamiquement un toast DOM si nécessaire
};

// ========== COMPATIBILITÉ ==========

// Alias pour rétrocompatibilité (si ancien code utilise window.fmtCad)
window.fmtCad = window.AppBridge.formatCAD;
window.fmtDate = window.AppBridge.formatDate;

// ========== INITIALISATION ==========

document.addEventListener('DOMContentLoaded', function() {
  console.log('✓ App Bridge prêt (DOM loaded)');
  
  // Si QWebChannel disponible, logger pour debug
  if (typeof QWebChannel !== 'undefined') {
    console.log('✓ QWebChannel détecté (PyQt6 bridge disponible)');
  } else {
    console.warn('⚠️ QWebChannel non détecté (mode standalone HTML)');
  }
});

// ========== EXPORT ==========

// Export pour modules ES6 si nécessaire
if (typeof module !== 'undefined' && module.exports) {
  module.exports = window.AppBridge;
}
