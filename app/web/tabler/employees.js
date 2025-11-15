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

  const HAS_TABLER_LITE_UI = typeof document !== 'undefined'
    && document.getElementById('tbl-employees')
    && document.getElementById('btn-apply-date');

  const HAS_LEGACY_EMPLOYEES_UI = typeof document !== 'undefined'
    && document.getElementById('sel-period');

  const tablerLiteState = {
    active: !!HAS_TABLER_LITE_UI,
    dt: null,
    rows: [],
    modalChart: null,
    lastDate: null
  };

  const tablerLiteSampleEmployees = [
    {
      employee_id: 1,
      nom: 'Amin Ajarar',
      matricule: 'A001',
      statut: 'actif',
      categorie_emploi: 'Comptabilité',
      titre_emploi: 'Agent de gestion comptable',
      salaire_net: 398464.35,
      salaire_prev: 370000,
      salary_trend: [
        { date: '2024-11-01', value: 360000 },
        { date: '2024-12-01', value: 370000 },
        { date: '2025-01-01', value: 398464.35 }
      ]
    },
    {
      employee_id: 2,
      nom: 'AMIN AJARAR',
      matricule: 'A001',
      statut: 'inactif',
      categorie_emploi: 'Comptabilité',
      titre_emploi: 'Ancien agent',
      salaire_net: 0,
      salaire_prev: 1200,
      salary_trend: [
        { date: '2024-11-01', value: 1200 },
        { date: '2024-12-01', value: 0 },
        { date: '2025-01-01', value: 0 }
      ]
    },
    {
      employee_id: 3,
      nom: 'Jean Allaaain',
      matricule: 'B220',
      statut: 'inactif',
      categorie_emploi: 'Technique',
      titre_emploi: 'Technicien',
      salaire_net: 800,
      salaire_prev: 1000,
      salary_trend: [
        { date: '2024-11-01', value: 950 },
        { date: '2024-12-01', value: 1000 },
        { date: '2025-01-01', value: 800 }
      ]
    },
    {
      employee_id: 4,
      nom: 'Marie Dupont',
      matricule: 'C333',
      statut: 'actif',
      categorie_emploi: 'Administration',
      titre_emploi: 'Chef bureau',
      salaire_net: 4200.5,
      salaire_prev: 4100,
      salary_trend: [
        { date: '2024-11-01', value: 3900 },
        { date: '2024-12-01', value: 4100 },
        { date: '2025-01-01', value: 4200.5 }
      ]
    }
  ];
  
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
    async getEmployeesByDate(dateIso) {
      return callBridge('getEmployees', dateIso);
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
  // TABLER LITE HELPERS (employees.html)
  // ========================================================================

  const tablerLiteIntl = new Intl.NumberFormat('fr-CA', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });

  function tablerLiteFmtMoney(value) {
    return tablerLiteIntl.format(Number(value || 0));
  }

  function tablerLiteComputeDelta(cur, prev) {
    const current = Number(cur || 0);
    const previous = Number(prev || 0);
    if (previous === 0) {
      if (current === 0) return { pct: 0, dir: 'neutral' };
      return { pct: 100, dir: 'up' };
    }
    const pct = ((current - previous) / Math.abs(previous)) * 100;
    return {
      pct,
      dir: pct > 0.1 ? 'up' : pct < -0.1 ? 'down' : 'neutral'
    };
  }

  function tablerLiteRenderDelta(cur, prev) {
    const result = tablerLiteComputeDelta(cur, prev);
    const pctStr = (Math.abs(result.pct) >= 1 || result.pct === 0)
      ? result.pct.toFixed(1) + '%'
      : result.pct.toFixed(2) + '%';

    if (result.dir === 'up') {
      return `<span class="arrow-up">▲ ${pctStr}</span>`;
    }
    if (result.dir === 'down') {
      return `<span class="arrow-down">▼ ${pctStr}</span>`;
    }
    return `<span class="arrow-neutral">— ${pctStr}</span>`;
  }

  function tablerLiteCreateSparkline(canvasId, trend) {
    if (!Array.isArray(trend) || !trend.length) return;
    const node = document.getElementById(canvasId);
    if (!node || typeof Chart === 'undefined') return;

    node.width = 140;
    node.height = 36;
    const ctx = node.getContext('2d');
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: trend.map(t => t.date),
        datasets: [{
          data: trend.map(t => t.value),
          borderColor: '#0b69ff',
          backgroundColor: 'rgba(11,105,255,0.08)',
          tension: 0.3,
          pointRadius: 0
        }]
      },
      options: {
        responsive: false,
        maintainAspectRatio: false,
        scales: { x: { display: false }, y: { display: false } },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => tablerLiteFmtMoney(ctx.parsed.y)
            }
          }
        }
      }
    });
  }

  function tablerLiteOpenModal(row) {
    const modalTitle = document.getElementById('modalTitle');
    const modalCanvas = document.getElementById('modalChart');
    const modalElement = document.getElementById('modalDetail');
    if (!modalElement || !modalCanvas) return;

    if (modalTitle) {
      modalTitle.textContent = `Historique salaire — ${row.nom || ''}`;
    }

    if (tablerLiteState.modalChart) {
      tablerLiteState.modalChart.destroy();
      tablerLiteState.modalChart = null;
    }

    if (typeof Chart !== 'undefined') {
      const ctx = modalCanvas.getContext('2d');
      tablerLiteState.modalChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: (row.salary_trend || []).map(t => t.date),
          datasets: [{
            label: 'Salaire net',
            data: (row.salary_trend || []).map(t => t.value),
            borderColor: '#16a34a',
            backgroundColor: 'rgba(22,163,74,0.08)',
            tension: 0.2
          }]
        },
        options: {
          plugins: {
            tooltip: {
              callbacks: {
                label: (ctx) => tablerLiteFmtMoney(ctx.parsed.y)
              }
            }
          }
        }
      });
    }

    if (window.tabler && tabler.Core && tabler.Core.Modal) {
      new tabler.Core.Modal(modalElement).show();
    } else if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
      const bsModal = new bootstrap.Modal(modalElement);
      bsModal.show();
    } else {
      modalElement.style.display = 'block';
      modalElement.classList.add('show');
    }
  }

  function tablerLitePrepareRows(rawRows) {
    const rows = Array.isArray(rawRows) ? rawRows : tablerLiteSampleEmployees;
    return rows.map((r, idx) => {
      const statut = (r.statut || '').toLowerCase() === 'actif' ? 'actif' : 'inactif';
      const prev = Number(r.salaire_prev || 0);
      const net = Number(r.salaire_net || 0);
      return {
        employee_id: r.employee_id || idx + 1,
        nom: r.nom || '',
        matricule: r.matricule || '',
        statut,
        categorie: r.categorie_emploi || r.categorie || '',
        titre: r.titre_emploi || r.titre || '',
        salaire_net: net,
        salaire_prev: prev,
        salary_trend: Array.isArray(r.salary_trend) ? r.salary_trend : [],
        deltaHtml: tablerLiteRenderDelta(net, prev)
      };
    });
  }

  function tablerLiteInitDataTable(rows) {
    const prepared = tablerLitePrepareRows(rows);
    const $ = window.jQuery;
    if (!$ || !$.fn || !$.fn.DataTable) {
      console.error('[Employees][Lite] DataTables non disponible');
      return;
    }

    const tableEl = document.getElementById('tbl-employees');
    if (!tableEl) return;

    const applyTrend = () => {
      prepared.forEach((row) => {
        const canvasId = `spark_${row.employee_id}`;
        setTimeout(() => tablerLiteCreateSparkline(canvasId, row.salary_trend), 40);
      });
    };

    const columns = [
      {
        data: 'nom',
        render: (d, _t, row) => `<a href="#" class="emp-link" data-id="${row.employee_id}">${d}</a>`
      },
      { data: 'matricule' },
      {
        data: 'statut',
        render: (value) => value === 'actif'
          ? '<span class="badge-actif">Actif</span>'
          : '<span class="badge-inactif">Ancien</span>'
      },
      { data: 'categorie' },
      { data: 'titre' },
      {
        data: 'salaire_net',
        className: 'text-end',
        render: (value) => tablerLiteFmtMoney(value)
      },
      {
        data: 'deltaHtml',
        className: 'text-center',
        orderable: false,
        searchable: false
      },
      {
        data: 'salary_trend',
        orderable: false,
        searchable: false,
        render: (_trend, _t, row) => `<canvas id="spark_${row.employee_id}" class="spark-canvas"></canvas>`
      },
      {
        data: null,
        orderable: false,
        searchable: false,
        render: (_d, _t, row) =>
          `<div class="btn-group"><button class="btn btn-sm btn-outline-primary btn-detail" data-id="${row.employee_id}">Détails</button></div>`
      }
    ];

    const drawCallback = function() {
      applyTrend();
    };

    const existingDt = window._employees_dt || tablerLiteState.dt;
    if (existingDt && $.fn.DataTable.isDataTable('#tbl-employees')) {
      existingDt.clear().rows.add(prepared).draw();
      applyTrend();
      window._employees_dt = existingDt;
      tablerLiteState.dt = existingDt;
    } else {
      const dtInstance = $('#tbl-employees').DataTable({
        data: prepared,
        columns,
        createdRow: (_row, data) => {
          if (data && data.statut && data.statut === data.statut.toUpperCase()) {
            // déjà géré via deltaHtml (pas nécessaire)
          }
        },
        dom: 'Bfrtip',
        buttons: ['excelHtml5', 'csvHtml5', 'pdfHtml5', 'print', 'pageLength'],
        pageLength: 10,
        responsive: true,
        drawCallback,
        footerCallback: function() {
          const api = this.api();
          const rowsData = api.rows({ search: 'applied' }).data().toArray();
          let total = 0;
          rowsData.forEach((r) => { total += Number(r.salaire_net || 0); });
          const fmt = window.DataTablesHelper?.formatCurrency
            ? window.DataTablesHelper.formatCurrency(total)
            : tablerLiteFmtMoney(total);
          $(api.column(5).footer()).html(`<strong>${fmt}</strong>`);
        }
      });

      window._employees_dt = dtInstance;
      tablerLiteState.dt = dtInstance;

      $('#tbl-employees tbody')
        .off('click.emp-detail')
        .on('click.emp-detail', '.btn-detail', function() {
          const id = Number(this.getAttribute('data-id'));
          const rowData = tablerLiteState.rows.find(r => r.employee_id == id);
          if (rowData) {
            tablerLiteOpenModal(rowData);
          }
        })
        .on('click.emp-link', function(e) {
          const anchor = e.target.closest('.emp-link');
          if (!anchor) return;
          e.preventDefault();
          const id = Number(anchor.getAttribute('data-id'));
          const rowData = tablerLiteState.rows.find(r => r.employee_id == id);
          if (rowData) {
            tablerLiteOpenModal(rowData);
          }
        });
    }

    tablerLiteState.rows = prepared;
  }

  function tablerLiteApplyStatusFilter(filterValue) {
    if (!tablerLiteState.dt) return;
    if (!filterValue || filterValue === 'all') {
      tablerLiteState.dt.column(2).search('').draw();
    } else {
      const term = filterValue === 'actif' ? 'Actif' : 'Ancien';
      tablerLiteState.dt.column(2).search(term).draw();
    }
  }

  async function tablerLiteRefresh(dateIso) {
    const targetDate = (dateIso || tablerLiteState.lastDate || '').trim() || new Date().toISOString().slice(0, 10);
    tablerLiteState.lastDate = targetDate;

    try {
      if (!state.bridge) {
        throw new Error('AppBridge non disponible');
      }

      const rows = await API.getEmployeesByDate(targetDate);
      if (Array.isArray(rows)) {
        tablerLiteInitDataTable(rows);
        console.log('[Employees][Lite] Table initialisée depuis AppBridge.getEmployees');
      } else if (rows && rows.error) {
        throw new Error(rows.error);
      } else {
        throw new Error('Réponse inattendue');
      }
    } catch (err) {
      console.error('[Employees][Lite] AppBridge.getEmployees failed:', err);
      console.warn('[Employees][Lite] Fallback sur les données exemples locales');
      tablerLiteInitDataTable(tablerLiteSampleEmployees);
    }

    const statusSelect = document.getElementById('filter-statut');
    if (statusSelect) {
      tablerLiteApplyStatusFilter(statusSelect.value);
    }
  }

  async function tablerLiteResolveActiveDate() {
    try {
      if (!state.bridge) {
        return null;
      }
      const raw = await callBridge('get_active_pay_date');
      const info = typeof raw === 'string' ? JSON.parse(raw) : raw;
      const payDate = info && info.pay_date ? info.pay_date : null;
      if (payDate) {
        console.log(`[Employees][Lite] Période active détectée: ${payDate} (source: ${info.source || 'unknown'})`);
      } else {
        console.warn('[Employees][Lite] Aucune période active retournée');
      }
      return payDate;
    } catch (err) {
      console.warn('[Employees][Lite] Impossible de récupérer la période active:', err);
      return null;
    }
  }

  function tablerLiteBindControls() {
    const dateInput = document.getElementById('pay-date');
    if (dateInput && !dateInput.value) {
      dateInput.value = tablerLiteState.lastDate || new Date().toISOString().slice(0, 10);
    }

    const applyBtn = document.getElementById('btn-apply-date');
    if (applyBtn) {
      applyBtn.addEventListener('click', async () => {
        const value = dateInput?.value || new Date().toISOString().slice(0, 10);
        try {
          await tablerLiteRefresh(value);
        } catch (err) {
          console.error('[Employees][Lite] Rafraîchissement manuel échoué, fallback local', err);
          tablerLiteInitDataTable(tablerLiteSampleEmployees);
        }
      });
    }

    const statusSelect = document.getElementById('filter-statut');
    if (statusSelect) {
      statusSelect.addEventListener('change', () => {
        tablerLiteApplyStatusFilter(statusSelect.value);
      });
    }

    const toggleBtn = document.getElementById('btn-toggle-borders');
    if (toggleBtn) {
      const tableEl = document.getElementById('tbl-employees');
      toggleBtn.addEventListener('click', () => {
        if (!tableEl) return;
        const hasNoBorders = tableEl.classList.toggle('table-no-borders');
        toggleBtn.textContent = hasNoBorders ? 'Afficher bordures' : 'Masquer bordures';
      });
    }
  }

  async function initTablerLiteUI() {
    tablerLiteBindControls();
    const dateInput = document.getElementById('pay-date');
    const activeDate = await tablerLiteResolveActiveDate();
    const initialDate = activeDate || dateInput?.value || new Date().toISOString().slice(0, 10);
    if (dateInput) {
      dateInput.value = initialDate;
    }
    await tablerLiteRefresh(initialDate);
  }
  
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
      const initializer = tablerLiteState.active ? initTablerLiteUI : init;
      initializer().catch(err => {
        console.error('[App] Erreur initialisation:', err);
        if (!tablerLiteState.active) {
          showToast('Erreur critique au démarrage', 'error');
        }
      });
    });
  } else if (tablerLiteState.active) {
    console.warn('[Bridge] QWebChannel non disponible - mode démo');
    initTablerLiteUI().catch(err => console.error('[Employees][Lite] init fallback:', err));
  } else {
    console.error('[Bridge] QWebChannel non disponible');
    const legacyBody = document.getElementById('tbody');
    if (legacyBody) {
      legacyBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center text-danger py-4">
            <i class="ti ti-plug-off icon me-2"></i>
            Application non connectée (QWebChannel manquant)
          </td>
        </tr>
      `;
    }
  }
  
})();

