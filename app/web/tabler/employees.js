/**
 * employees.js - Gestion des employés avec AppBridge (QWebChannel)
 * PayrollAnalyzer v2 - Production ready
 */

(function() {
  'use strict';
  
  let listenersBound = false;
  
  // ========================================================================
  // CONFIGURATION & CONSTANTES
  // ========================================================================
  
  const CONFIG = {
    TIMEOUT: 8000,              // Timeout API (ms)
    DEBOUNCE_DELAY: 250,        // Debounce recherche (ms)
    PAGE_SIZE: 10,              // Lignes par page
    MAX_NEW_DISPLAY: 50,        // Max nouveaux affichés
    STORAGE_KEY: 'employees_state' // LocalStorage key
  };
  
  // ========================================================================
  // STATE MANAGEMENT
  // ========================================================================
  
  const state = {
    bridge: null,
    currentAbortController: null,
    filters: {
      period: null,
      q: '',
      status: '',
      type: '',
      dept: ''
    },
    pagination: {
      page: 1,
      total: 0
    },
    cache: {
      departments: new Set()
    },
    drawer: null
  };
  
  // ========================================================================
  // API BRIDGE (QWebChannel)
  // ========================================================================
  
  /**
   * Appel sécurisé à AppBridge avec timeout
   */
  async function callBridge(methodName, ...args) {
    if (!state.bridge) {
      throw new Error('AppBridge non disponible');
    }
    
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`Timeout: ${methodName} a dépassé ${CONFIG.TIMEOUT}ms`));
      }, CONFIG.TIMEOUT);
      
      try {
        const result = state.bridge[methodName](...args);
        
        // Gérer Promise ou résultat direct
        Promise.resolve(result).then(data => {
          clearTimeout(timeout);
          const parsed = typeof data === 'string' ? JSON.parse(data) : data;
          resolve(parsed);
        }).catch(err => {
          clearTimeout(timeout);
          reject(err);
        });
      } catch (err) {
        clearTimeout(timeout);
        reject(err);
      }
    });
  }
  
  /**
   * API Endpoints (mode desktop uniquement: AppBridge sans HTTP)
   */

  const API = {
    async getPeriods() {
      const periodsStr = await callBridge('get_periods', '');
      const periods = typeof periodsStr === 'string' ? JSON.parse(periodsStr) : periodsStr;
      if (Array.isArray(periods)) {
        return periods.map(p => ({ 
          id: p.id || p.period_id || p.date || p.pay_date || '', 
          label: p.label || p.date || p.pay_date || '' 
        }));
      }
      return Array.isArray(periods) ? periods : [];
    },
    async getKPI(periodId) {
      const kpiStr = await callBridge('get_kpi', periodId);
      return typeof kpiStr === 'string' ? JSON.parse(kpiStr) : kpiStr;
    },
    async listEmployees(_periodId, filters, page, pageSize) {
      return callBridge('list_employees', _periodId, JSON.stringify(filters||{}), page, pageSize);
    },
    async getEmployeeDetail(employeeId) {
      return callBridge('get_employee_detail', employeeId);
    },
    export(type, payload) {
      return callBridge('export', type, payload);
    },
    async getFacets() {
      // Non disponible en mode desktop → retourner valeurs vides
      return { categories: [], titles: [] };
    },
    async getGrouping(limit = 50) {
      // Non disponible en mode desktop → retourner valeurs vides
      return [];
    }
  };
  
  // ========================================================================
  // PERSISTENCE (LocalStorage)
  // ========================================================================
  
  function saveState() {
    try {
      const toSave = {
        period: state.filters.period,
        filters: {
          q: state.filters.q,
          status: state.filters.status,
          type: state.filters.type,
          dept: state.filters.dept
        }
      };
      localStorage.setItem(CONFIG.STORAGE_KEY, JSON.stringify(toSave));
      console.log('[Storage] État sauvegardé:', toSave);
    } catch (e) {
      console.warn('[Storage] Échec sauvegarde:', e);
    }
  }
  
  function loadState() {
    try {
      const saved = localStorage.getItem(CONFIG.STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        console.log('[Storage] État restauré:', parsed);
        return parsed;
      }
    } catch (e) {
      console.warn('[Storage] Échec chargement:', e);
    }
    return null;
  }
  
  // ========================================================================
  // UI HELPERS
  // ========================================================================
  
  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const id = 'toast-' + Date.now();
    
    const colors = {
      success: 'bg-success',
      error: 'bg-danger',
      warning: 'bg-warning',
      info: 'bg-info'
    };
    
    const toast = document.createElement('div');
    toast.id = id;
    toast.className = `toast align-items-center text-white ${colors[type] || colors.info} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">${escapeHtml(message)}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fermer"></button>
      </div>
    `;
    
    container.appendChild(toast);
    
    // Utiliser Bootstrap si disponible, sinon setTimeout simple
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
      const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
      bsToast.show();
      toast.addEventListener('hidden.bs.toast', () => toast.remove());
    } else {
      toast.style.display = 'block';
      setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
      }, 5000);
    }
  }
  
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  function formatNumber(num) {
    return new Intl.NumberFormat('fr-CA').format(num);
  }
  
  function formatPercent(num) {
    return new Intl.NumberFormat('fr-CA', { 
      style: 'percent', 
      minimumFractionDigits: 1,
      maximumFractionDigits: 1
    }).format(num / 100);
  }
  
  // ========================================================================
  // TÉLÉMÉTRIE (hook no-op)
  // ========================================================================
  
  function track(eventName, payload) {
    console.log('[Track]', eventName, payload);
    // Hook pour intégration future (Google Analytics, Mixpanel, etc.)
  }
  
  // ========================================================================
  // CHARGEMENT DONNÉES
  // ========================================================================
  
  async function loadPeriods() {
    try {
      const periods = await API.getPeriods();
      const select = document.getElementById('sel-period');
      
      if (!periods || periods.length === 0) {
        select.innerHTML = '<option value="">Aucune période disponible</option>';
        return;
      }
      
      select.innerHTML = periods.map(p => 
        `<option value="${escapeHtml(p.id)}">${escapeHtml(p.label)}</option>`
      ).join('');
      
      // Restaurer période sauvegardée ou dernière
      const saved = loadState();
      if (saved && saved.period && periods.find(p => p.id === saved.period)) {
        select.value = saved.period;
        state.filters.period = saved.period;
      } else {
        state.filters.period = periods[0].id;
        select.value = periods[0].id;
      }
      
      console.log('[API] Périodes chargées:', periods.length);
    } catch (err) {
      console.error('[API] Erreur chargement périodes:', err);
      showToast('Impossible de charger les périodes', 'error');
    }
  }
  
  async function loadKPI(periodId) {
    try {
      const kpi = await API.getKPI(periodId);
      
      document.getElementById('k-total').textContent = formatNumber(kpi.total || 0);
      document.getElementById('k-new').textContent = formatNumber(kpi.nouveaux || 0);
      document.getElementById('k-left').textContent = formatNumber(kpi.sorties || 0);
      document.getElementById('k-churn').textContent = formatPercent(kpi.churn || 0);
      
      if (kpi.prev) {
        document.getElementById('hint-prev').textContent = `Période précédente: ${kpi.prev}`;
      } else {
        document.getElementById('hint-prev').textContent = 'Première période';
      }
      
      // Carte nouveaux (conditionnelle)
      const cardNew = document.getElementById('card-new');
      if (kpi.nouveaux > 0) {
        cardNew.style.display = 'block';
        document.getElementById('b-new').textContent = kpi.nouveaux;
        // La liste sera chargée avec les employés
      } else {
        cardNew.style.display = 'none';
      }
      
      console.log('[API] KPI chargés:', kpi);
    } catch (err) {
      console.error('[API] Erreur chargement KPI:', err);
      showToast('Impossible de charger les indicateurs', 'error');
    }
  }
  
  async function loadEmployees(resetPage = false) {
    if (resetPage) {
      state.pagination.page = 1;
    }
    
    // Annuler requête précédente si en cours
    if (state.currentAbortController) {
      state.currentAbortController.abort();
    }
    state.currentAbortController = new AbortController();
    
    const tbody = document.getElementById('tbody');
    
    // Skeleton loader
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-muted" role="status"></div>
          <span class="text-muted ms-2">Chargement...</span>
        </td>
      </tr>
    `;
    
    try {
      // Si pas de bridge → HTTP direct
      if (!state.bridge) {
        const res = await API.listEmployees(state.filters.period, state.filters, state.pagination.page, CONFIG.PAGE_SIZE);
        state.pagination.total = res.total || 0;
        renderTable(res.items || []);
        updatePagination();
        renderNewEmployees(res.items || []);
        return;
      }

      // Construit un WHERE SQL sécurisé (lecture seule)
      const where = [];
      function sqlSafe(v){
        return (v||'').toString().replace(/'/g, "''");
      }
      if (state.filters.q) {
        const q = sqlSafe(state.filters.q.trim().toLowerCase());
        where.push(`(LOWER(COALESCE(e.nom,'')) LIKE '%${q}%' OR LOWER(COALESCE(e.prenom,'')) LIKE '%${q}%' OR LOWER(COALESCE(e.matricule,'')) LIKE '%${q}%')`);
      }
      if (state.filters.status) {
        const s = sqlSafe(state.filters.status);
        where.push(`e.statut = '${s}'`);
      }
      if (state.filters.dept) {
        const d = sqlSafe(state.filters.dept);
        // Si vous avez un champ dept, adaptez ici. Placeholder:
        where.push(`COALESCE(e.dept,'') = '${d}'`);
      }
      const selCat = document.getElementById('f-cat')?.value || '';
      const selTitle = document.getElementById('f-title')?.value || '';
      if (selCat) {
        where.push(`COALESCE(p.categorie_emploi,'') = '${sqlSafe(selCat)}'`);
      }
      if (selTitle) {
        where.push(`COALESCE(p.titre_emploi,'') = '${sqlSafe(selTitle)}'`);
      }
      const whereSql = where.length ? ('WHERE ' + where.join(' AND ')) : '';

      const offset = (state.pagination.page - 1) * CONFIG.PAGE_SIZE;
      const limit = CONFIG.PAGE_SIZE;

      const sqlData = `
        SELECT e.employee_id, e.matricule, COALESCE(e.nom,'') AS nom, COALESCE(e.prenom,'') AS prenom,
               COALESCE(e.statut,'') AS statut,
               COALESCE(p.categorie_emploi,'') AS categorie_emploi,
               COALESCE(p.titre_emploi,'') AS titre_emploi
        FROM core.employees e
        LEFT JOIN paie.v_employe_profil p ON p.employee_id = e.employee_id
        ${whereSql}
        ORDER BY e.nom, e.prenom
        LIMIT ${limit} OFFSET ${offset}
      `;

      const sqlCount = `
        SELECT COUNT(1)
        FROM core.employees e
        LEFT JOIN paie.v_employe_profil p ON p.employee_id = e.employee_id
        ${whereSql}
      `;

      const dataResStr = await callBridge('execute_sql', sqlData);
      const countResStr = await callBridge('execute_sql', sqlCount);

      if (state.currentAbortController.signal.aborted) return;

      // Parser les résultats JSON
      const dataRes = typeof dataResStr === 'string' ? JSON.parse(dataResStr) : dataResStr;
      const countRes = typeof countResStr === 'string' ? JSON.parse(countResStr) : countResStr;

      const items = Array.isArray(dataRes.rows) ? dataRes.rows.map(r => ({
        employee_id: r[0], matricule: r[1], nom: (r[2] || '') + (r[3] ? (' ' + r[3]) : ''), statut: r[4] || '',
        categorie_emploi: r[5] || '', titre_emploi: r[6] || ''
      })) : [];
      const total = (Array.isArray(countRes.rows) && countRes.rows[0] && countRes.rows[0][0]) ? Number(countRes.rows[0][0]) : 0;

      state.pagination.total = total;

      renderTable(items);
      updatePagination();
      renderNewEmployees(items);

      console.log('[DB] Employés chargés:', items.length, '/', total);

    } catch (err) {
      if (err.name === 'AbortError' || state.currentAbortController?.signal.aborted) {
        console.log('[API] Requête annulée');
        return;
      }
      console.error('[API] Erreur chargement employés:', err);
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="text-center text-danger py-4">
            <i class="ti ti-alert-circle icon me-2"></i>
            Erreur de chargement. <a href="#" onclick="location.reload()">Réessayer</a>
          </td>
        </tr>
      `;
      showToast('Impossible de charger la liste des employés', 'error');
    } finally {
      state.currentAbortController = null;
    }
  }

  // Chargement des groupes (catégorie / titre) via AppBridge (execute_sql)
  async function loadGrouping() {
    const tbody = document.getElementById('tbody-grouping');
    const chartEl = document.getElementById('chart-grouping');
    if (!tbody) return; // section absente

    tbody.innerHTML = `
      <tr>
        <td colspan="3" class="text-center py-4 text-muted">
          <div class="spinner-border spinner-border-sm text-muted" role="status"></div>
          <span class="ms-2">Chargement des groupes…</span>
        </td>
      </tr>
    `;

    const sql = `
      SELECT categorie_emploi, titre_emploi, nb_employes
      FROM paie.v_employes_groupes
      ORDER BY titre_emploi, nb_employes DESC, categorie_emploi
      LIMIT 50
    `;

    try {
      let rows;
      if (!state.bridge) {
        rows = await API.getGrouping(50);
        // Adapter en tableau de positions comme execute_sql
        rows = rows.map(r => [r.categorie_emploi, r.titre_emploi, r.nb_employes]);
      } else {
        const resultStr = await callBridge('execute_sql', sql);
        const result = typeof resultStr === 'string' ? JSON.parse(resultStr) : resultStr;
        rows = Array.isArray(result.rows) ? result.rows.slice(0, 8) : [];
      }
      if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-3">Aucun groupe</td></tr>';
      } else {
        tbody.innerHTML = rows.map(r => {
          const cat = (r[0] ?? '').toString();
          const titre = (r[1] ?? '').toString();
          const n = Number(r[2] ?? 0);
          const nfmt = (window.formatNumberFr ? formatNumberFr(n, 0) : new Intl.NumberFormat('fr-CA').format(n));
          return `<tr><td>${escapeHtml(cat)}</td><td>${escapeHtml(titre)}</td><td class="text-end">${nfmt}</td></tr>`;
        }).join('');

        // Bar chart si ApexCharts dispo
        if (window.ApexCharts && chartEl) {
          const labels = rows.map(r => `${r[0] ?? ''} — ${r[1] ?? ''}`);
          const data = rows.map(r => Number(r[2] ?? 0));
          const opts = {
            chart: { type: 'bar', height: 260, toolbar: { show: false } },
            series: [{ name: 'Employés', data }],
            xaxis: { categories: labels, labels: { show: false } },
            plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
            dataLabels: { enabled: true, formatter: (v) => (window.formatNumberFr ? formatNumberFr(v, 0) : v) },
            colors: ['#2fb344']
          };
          const chart = new ApexCharts(chartEl, opts);
          chart.render();
        }
      }
    } catch (e) {
      console.error('[Grouping] Erreur:', e);
      tbody.innerHTML = '<tr><td colspan="3" class="text-center text-danger py-3">Erreur de chargement</td></tr>';
    }
  }
  
  function renderTable(items) {
    const tbody = document.getElementById('tbody');
    
    if (!items || items.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="text-center text-muted py-4">
            <i class="ti ti-database-off icon me-2"></i>
            Aucun employé trouvé
          </td>
        </tr>
      `;
      document.getElementById('table-meta').textContent = '0 résultat';
      return;
    }
    
    tbody.innerHTML = items.map(emp => {
      const typeBadge = {
        new: '<span class="badge bg-success">Nouveau</span>',
        old: '<span class="badge bg-secondary">Ancien</span>',
        left: '<span class="badge bg-danger">Sorti</span>'
      }[emp.type] || '<span class="badge">-</span>';
      
      const statusBadge = emp.statut === 'actif' 
        ? '<span class="badge bg-success-lt">Actif</span>'
        : '<span class="badge bg-secondary-lt">Inactif</span>';
      
      return `
        <tr>
          <td>${typeBadge}</td>
          <td><code>${escapeHtml(emp.matricule || '-')}</code></td>
          <td>
            <a href="#" class="text-reset employee-link" data-id="${emp.employee_id}">
              ${escapeHtml(emp.nom || 'Sans nom')}
            </a>
          </td>
          <td>${escapeHtml(emp.categorie_emploi || '-')}</td>
          <td>${escapeHtml(emp.titre_emploi || '-')}</td>
          <td>${escapeHtml(emp.dept || '-')}</td>
          <td>${statusBadge}</td>
        </tr>
      `;
    }).join('');
    
    // Attacher événements clic nom
    tbody.querySelectorAll('.employee-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const employeeId = e.target.getAttribute('data-id');
        openDrawer(employeeId);
      });
    });
    
    const start = (state.pagination.page - 1) * CONFIG.PAGE_SIZE + 1;
    const end = Math.min(state.pagination.page * CONFIG.PAGE_SIZE, state.pagination.total);
    document.getElementById('table-meta').textContent = 
      `Affichage ${start}-${end} sur ${formatNumber(state.pagination.total)} résultats`;
  }
  
  function renderNewEmployees(items) {
    const newEmployees = items.filter(e => e.type === 'new');
    const listNew = document.getElementById('list-new');
    
    if (newEmployees.length === 0) {
      return;
    }
    
    const toDisplay = newEmployees.slice(0, CONFIG.MAX_NEW_DISPLAY);
    const remaining = newEmployees.length - toDisplay.length;
    
    listNew.innerHTML = toDisplay.map(emp => 
      `<span class="badge bg-success-lt" style="font-size:0.875rem;">
        ${escapeHtml(emp.matricule)} — ${escapeHtml(emp.nom)}
      </span>`
    ).join('') + (remaining > 0 
      ? `<span class="badge bg-muted">+${remaining} de plus…</span>`
      : '');
  }
  
  function updatePagination() {
    const totalPages = Math.ceil(state.pagination.total / CONFIG.PAGE_SIZE);
    const currentPage = state.pagination.page;
    
    document.getElementById('pager-info').textContent = 
      `Page ${currentPage} / ${totalPages || 1}`;
    
    const prevBtn = document.getElementById('prev');
    const nextBtn = document.getElementById('next');
    
    if (currentPage <= 1) {
      prevBtn.classList.add('disabled');
      prevBtn.querySelector('a').setAttribute('tabindex', '-1');
    } else {
      prevBtn.classList.remove('disabled');
      prevBtn.querySelector('a').removeAttribute('tabindex');
    }
    
    if (currentPage >= totalPages) {
      nextBtn.classList.add('disabled');
      nextBtn.querySelector('a').setAttribute('tabindex', '-1');
    } else {
      nextBtn.classList.remove('disabled');
      nextBtn.querySelector('a').removeAttribute('tabindex');
    }
  }
  
  function updateDepartmentFilter() {
    const select = document.getElementById('f-dept');
    const currentValue = select.value;
    
    const depts = Array.from(state.cache.departments).sort();
    
    select.innerHTML = '<option value="">Tous</option>' + 
      depts.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join('');
    
    if (currentValue && depts.includes(currentValue)) {
      select.value = currentValue;
    }
  }

  // Charger facettes Catégorie / Titre depuis la base
  async function loadFacets() {
    const selCat = document.getElementById('f-cat');
    const selTitle = document.getElementById('f-title');
    if (!selCat || !selTitle) {
      console.warn('[Facets] Éléments de sélection non trouvés');
      return;
    }

    try {
      // Afficher l'état de chargement
      selCat.innerHTML = '<option value="">Chargement...</option>';
      selTitle.innerHTML = '<option value="">Chargement...</option>';
      console.log('[Facets] Chargement des facettes...');
      if (!state.bridge) {
        const data = await API.getFacets();
        const cats = (data.categories || []).map(v => String(v));
        const titles = (data.titles || []).map(v => String(v));
        selCat.innerHTML = '<option value="">Toutes</option>' + cats.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
        selTitle.innerHTML = '<option value="">Tous</option>' + titles.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');
        return;
      }

      // Bridge: requêtes SQL directes
      const sqlCat = `SELECT DISTINCT categorie_emploi FROM paie.stg_paie_transactions WHERE categorie_emploi IS NOT NULL AND TRIM(categorie_emploi) != '' ORDER BY categorie_emploi`;
      const sqlTitle = `SELECT DISTINCT titre_emploi FROM paie.stg_paie_transactions WHERE titre_emploi IS NOT NULL AND TRIM(titre_emploi) != '' ORDER BY titre_emploi`;
      const [resCat, resTitle] = await Promise.all([
        callBridge('execute_sql', sqlCat),
        callBridge('execute_sql', sqlTitle)
      ]);

      console.log('[Facets] Résultats catégories:', resCat);
      console.log('[Facets] Résultats titres:', resTitle);

      // Gérer le format de retour (execute_sql retourne un JSON stringifié)
      let cats = [];
      let titles = [];
      
      // Parser resCat
      let parsedCat = resCat;
      if (typeof resCat === 'string') {
        try {
          parsedCat = JSON.parse(resCat);
        } catch (e) {
          console.error('[Facets] Erreur parsing JSON catégories:', e);
          parsedCat = null;
        }
      }
      
      if (parsedCat && parsedCat.rows && Array.isArray(parsedCat.rows)) {
        cats = parsedCat.rows.map(r => {
          const val = Array.isArray(r) ? r[0] : r;
          return (val || '').toString().trim();
        }).filter(v => v && v !== '');
      } else if (Array.isArray(parsedCat)) {
        cats = parsedCat.map(r => {
          const val = Array.isArray(r) ? r[0] : r;
          return (val || '').toString().trim();
        }).filter(v => v && v !== '');
      }
      
      // Parser resTitle
      let parsedTitle = resTitle;
      if (typeof resTitle === 'string') {
        try {
          parsedTitle = JSON.parse(resTitle);
        } catch (e) {
          console.error('[Facets] Erreur parsing JSON titres:', e);
          parsedTitle = null;
        }
      }
      
      if (parsedTitle && parsedTitle.rows && Array.isArray(parsedTitle.rows)) {
        titles = parsedTitle.rows.map(r => {
          const val = Array.isArray(r) ? r[0] : r;
          return (val || '').toString().trim();
        }).filter(v => v && v !== '');
      } else if (Array.isArray(parsedTitle)) {
        titles = parsedTitle.map(r => {
          const val = Array.isArray(r) ? r[0] : r;
          return (val || '').toString().trim();
        }).filter(v => v && v !== '');
      }

      console.log('[Facets] Catégories extraites:', cats);
      console.log('[Facets] Titres extraits:', titles);

      if (cats.length > 0) {
        selCat.innerHTML = '<option value="">Toutes</option>' + cats.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
      } else {
        selCat.innerHTML = '<option value="">Aucune catégorie</option>';
      }

      if (titles.length > 0) {
        selTitle.innerHTML = '<option value="">Tous</option>' + titles.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('');
      } else {
        selTitle.innerHTML = '<option value="">Aucun titre</option>';
      }

      console.log('[Facets] Facettes chargées avec succès');
    } catch (e) {
      console.error('[Facets] Erreur chargement facettes:', e);
      selCat.innerHTML = '<option value="">Erreur de chargement</option>';
      selTitle.innerHTML = '<option value="">Erreur de chargement</option>';
      showToast('Erreur lors du chargement des filtres', 'error');
    }
  }
  
  // ========================================================================
  // DRAWER - FICHE EMPLOYÉ
  // ========================================================================
  
  async function openDrawer(employeeId) {
    if (!state.drawer) {
      console.warn('[Drawer] Instance Bootstrap non initialisée');
      return;
    }
    
    track('open_drawer', { employee_id: employeeId });
    
    const drawerBody = document.getElementById('drawer-body');
    drawerBody.innerHTML = `
      <div class="text-center py-5">
        <div class="spinner-border text-muted" role="status"></div>
        <div class="mt-2 text-muted">Chargement...</div>
      </div>
    `;
    
    state.drawer.show();
    
    try {
      const detail = await API.getEmployeeDetail(employeeId);
      
      const statusBadge = detail.statut === 'actif'
        ? '<span class="badge bg-success">Actif</span>'
        : '<span class="badge bg-secondary">Inactif</span>';
      
      const typeBadge = {
        new: '<span class="badge bg-success">Nouveau</span>',
        old: '<span class="badge bg-secondary">Ancien</span>',
        left: '<span class="badge bg-danger">Sorti</span>'
      }[detail.type] || '<span class="badge">-</span>';
      
      drawerBody.innerHTML = `
        <div class="card mb-3">
          <div class="card-body">
            <h3>${escapeHtml(detail.nom || 'Sans nom')}</h3>
            <dl class="row mt-3">
              <dt class="col-5">Matricule</dt>
              <dd class="col-7"><code>${escapeHtml(detail.matricule || '-')}</code></dd>
              
              <dt class="col-5">Statut</dt>
              <dd class="col-7">${statusBadge}</dd>
              
              <dt class="col-5">Type</dt>
              <dd class="col-7">${typeBadge}</dd>
              
              <dt class="col-5">Département</dt>
              <dd class="col-7">${escapeHtml(detail.dept || '-')}</dd>
            </dl>
          </div>
        </div>
        
        ${detail.historique && detail.historique.length > 0 ? `
          <div class="card mb-3">
            <div class="card-header">
              <h4 class="card-title">Historique</h4>
            </div>
            <div class="list-group list-group-flush">
              ${detail.historique.map(h => `
                <div class="list-group-item">
                  <div class="row align-items-center">
                    <div class="col-auto">
                      <span class="badge bg-blue-lt">${escapeHtml(h.periode || '-')}</span>
                    </div>
                    <div class="col">
                      <div class="text-truncate">
                        ${escapeHtml(h.changements || 'Aucun changement')}
                      </div>
                    </div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}
        
        <div class="btn-list">
          <button class="btn btn-outline-primary" id="exp-pdf-emp">
            <i class="ti ti-file-type-pdf icon me-2"></i>
            Exporter PDF
          </button>
          <button class="btn btn-outline-primary" id="exp-excel-emp">
            <i class="ti ti-file-spreadsheet icon me-2"></i>
            Exporter Excel
          </button>
        </div>
      `;
      
      // Attacher événements export
      document.getElementById('exp-pdf-emp').addEventListener('click', () => 
        exportFile('pdf_employee', { employee_id: employeeId })
      );
      document.getElementById('exp-excel-emp').addEventListener('click', () => 
        exportFile('excel_employee', { employee_id: employeeId })
      );
      
    } catch (err) {
      console.error('[Drawer] Erreur chargement détails:', err);
      drawerBody.innerHTML = `
        <div class="alert alert-danger">
          <i class="ti ti-alert-circle icon me-2"></i>
          Impossible de charger les détails de l'employé
        </div>
      `;
      showToast('Erreur chargement fiche employé', 'error');
    }
  }
  
  // ========================================================================
  // EXPORTS
  // ========================================================================
  
  async function exportFile(type, payload = {}) {
    track('export', { type, ...payload });
    
    try {
      const enrichedPayload = {
        ...payload,
        period: state.filters.period,
        filters: state.filters
      };
      
      const result = await API.export(type, enrichedPayload);
      
      if (result.path) {
        showToast(`Export réussi: ${result.path}`, 'success');
        console.log('[Export] Fichier créé:', result.path);
      } else {
        showToast('Export terminé mais chemin non retourné', 'warning');
      }
    } catch (err) {
      console.error('[Export] Erreur:', err);
      showToast('Export impossible, réessayez', 'error');
    }
  }
  
  // ========================================================================
  // FILTRES & ÉVÉNEMENTS
  // ========================================================================
  
  let searchDebounceTimeout = null;
  
  function applyFilters() {
    if (searchDebounceTimeout) {
      clearTimeout(searchDebounceTimeout);
    }
    
    searchDebounceTimeout = setTimeout(() => {
      loadEmployees(true); // Reset page
      saveState();
      track('apply_filters', state.filters);
    }, CONFIG.DEBOUNCE_DELAY);
  }
  
  function setupEventListeners() {
    if (listenersBound) {
      return;
    }
    listenersBound = true;
    console.log('[Employees] bind listeners');
    
    // Période
    document.getElementById('sel-period').addEventListener('change', (e) => {
      state.filters.period = e.target.value;
      state.cache.departments.clear(); // Reset cache
      loadKPI(state.filters.period);
      loadEmployees(true);
      saveState();
      track('change_period', { period: state.filters.period });
    });
    
    // Recherche (debounced)
    document.getElementById('q').addEventListener('input', (e) => {
      state.filters.q = e.target.value;
      applyFilters();
    });
    
    // Statut
    document.getElementById('f-status').addEventListener('change', (e) => {
      state.filters.status = e.target.value;
      loadEmployees(true);
      saveState();
    });
    
    // Type
    document.getElementById('f-type').addEventListener('change', (e) => {
      state.filters.type = e.target.value;
      loadEmployees(true);
      saveState();
    });
    
    // Département
    document.getElementById('f-dept').addEventListener('change', (e) => {
      state.filters.dept = e.target.value;
      loadEmployees(true);
      saveState();
    });
    // Catégorie
    const fCat = document.getElementById('f-cat');
    if (fCat) {
      fCat.addEventListener('change', () => {
        loadEmployees(true);
      });
    }
    // Titre
    const fTitle = document.getElementById('f-title');
    if (fTitle) {
      fTitle.addEventListener('change', () => {
        loadEmployees(true);
      });
    }
    
    // Pagination
    document.getElementById('prev').addEventListener('click', (e) => {
      e.preventDefault();
      if (state.pagination.page > 1) {
        state.pagination.page--;
        loadEmployees();
      }
    });
    
    document.getElementById('next').addEventListener('click', (e) => {
      e.preventDefault();
      const totalPages = Math.ceil(state.pagination.total / CONFIG.PAGE_SIZE);
      if (state.pagination.page < totalPages) {
        state.pagination.page++;
        loadEmployees();
      }
    });
    
    // Rafraîchir
    document.getElementById('btn-refresh').addEventListener('click', () => {
      loadKPI(state.filters.period);
      loadEmployees(true);
      track('refresh', {});
    });
    
    // Exports
    document.getElementById('exp-excel-view').addEventListener('click', (e) => {
      e.preventDefault();
      exportFile('excel_view');
    });
    
    document.getElementById('exp-excel-pack').addEventListener('click', (e) => {
      e.preventDefault();
      exportFile('excel_pack');
    });
    
    document.getElementById('exp-pdf-period').addEventListener('click', (e) => {
      e.preventDefault();
      exportFile('pdf_period');
    });
    
    // Drawer close
    document.getElementById('close-drawer').addEventListener('click', () => {
      if (state.drawer) state.drawer.hide();
    });
    
    // ESC pour fermer drawer
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && state.drawer) {
        const drawerEl = document.getElementById('drawer');
        if (drawerEl.classList.contains('show')) {
          state.drawer.hide();
        }
      }
    });
  }
  
  function restoreFilters() {
    const saved = loadState();
    if (!saved) return;
    
    if (saved.filters) {
      if (saved.filters.q) {
        document.getElementById('q').value = saved.filters.q;
        state.filters.q = saved.filters.q;
      }
      if (saved.filters.status) {
        document.getElementById('f-status').value = saved.filters.status;
        state.filters.status = saved.filters.status;
      }
      if (saved.filters.type) {
        document.getElementById('f-type').value = saved.filters.type;
        state.filters.type = saved.filters.type;
      }
      if (saved.filters.dept) {
        state.filters.dept = saved.filters.dept;
        // Le select sera restauré après chargement des départements
      }
    }
  }
  
  // ========================================================================
  // INITIALISATION
  // ========================================================================
  
  async function init() {
    console.log('[Employees] init');
    console.log('[App] Initialisation...');
    console.log('[Storage] Clé localStorage:', CONFIG.STORAGE_KEY);
    
    // Initialiser drawer Bootstrap (si disponible)
    const drawerEl = document.getElementById('drawer');
    if (typeof bootstrap !== 'undefined' && bootstrap.Offcanvas) {
      state.drawer = new bootstrap.Offcanvas(drawerEl);
    } else {
      // Fallback manuel si Bootstrap non disponible
      state.drawer = {
        show: () => {
          drawerEl.classList.add('show');
          drawerEl.style.visibility = 'visible';
        },
        hide: () => {
          drawerEl.classList.remove('show');
          drawerEl.style.visibility = 'hidden';
        }
      };
    }
    
    // Setup événements
    setupEventListeners();
    
    // Charger périodes
    await loadPeriods();
    
    if (!state.filters.period) {
      showToast('Aucune période disponible', 'warning');
      return;
    }
    
    // Restaurer filtres
    restoreFilters();
    
    // Charger données initiales
    await Promise.all([
      loadKPI(state.filters.period),
      loadFacets(),
      loadEmployees(),
      loadGrouping()
    ]);
    
    console.log('[App] Initialisé avec succès');
    console.log('[API] Endpoints utilisés: get_periods, get_kpi, list_employees, execute_sql');
    console.log('[Storage] Clés persistées:', CONFIG.STORAGE_KEY);
  }
  
  // ========================================================================
  // BOOTSTRAP (QWebChannel)
  // ========================================================================
  
  if (typeof qt !== 'undefined' && qt.webChannelTransport) {
    new QWebChannel(qt.webChannelTransport, (channel) => {
      state.bridge = channel.objects.AppBridge;
      console.log('[Bridge] QWebChannel connecté');
      init().catch(err => {
        console.error('[App] Erreur initialisation:', err);
        showToast('Erreur critique au démarrage', 'error');
      });
    });
  } else {
    console.error('[Bridge] QWebChannel non disponible');
    document.getElementById('tbody').innerHTML = `
      <tr>
        <td colspan="5" class="text-center text-danger py-4">
          <i class="ti ti-plug-off icon me-2"></i>
          Application non connectée (QWebChannel manquant)
        </td>
      </tr>
    `;
  }
  
})();

