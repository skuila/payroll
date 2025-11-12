// web/tabler/js/datatables-helper.js
// Helper léger pour initialiser DataTables avec ou sans AppBridge (QWebChannel)
// Fournit : DataTablesHelper.init(selector, data, columns, options)
//           DataTablesHelper.initWithAppBridge(selector, buildSqlFn, columns, options)
//           DataTablesHelper.formatCurrency / formatDate

(function () {
  if (window.DataTablesHelper) return;
  if (!window.__DT_INSTANCES__) {
    window.__DT_INSTANCES__ = {};
  }

  function ensureDeps() {
    if (!window.jQuery) throw new Error('jQuery manquant pour DataTables');
    if (!window.jQuery.fn || !window.jQuery.fn.DataTable) {
      throw new Error('DataTables non chargé');
    }
  }

  const NF_CAD = new Intl.NumberFormat('fr-CA', {
    style: 'currency',
    currency: 'CAD',
    currencyDisplay: 'narrowSymbol',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const DF_FR = new Intl.DateTimeFormat('fr-CA', { dateStyle: 'medium' });

  const DataTablesHelper = {
    formatCurrency: function (value) {
      try { return NF_CAD.format(Number(value || 0)); } catch { return String(value ?? ''); }
    },
    formatDate: function (value) {
      try { return DF_FR.format(new Date(value)); } catch { return String(value ?? ''); }
    },
    init: async function (selector, rows, columns, options) {
      ensureDeps();
      const $ = window.jQuery;
      const tableEl = $(selector);
      if (!tableEl.length) throw new Error(`Table introuvable: ${selector}`);

      // Réutiliser instance si déjà initialisée
      const key = String(selector);
      if ($.fn.DataTable.isDataTable(tableEl)) {
        const existing = window.__DT_INSTANCES__[key] || tableEl.DataTable();
        if (Array.isArray(rows)) {
          existing.clear();
          existing.rows.add(rows);
          existing.draw(false);
        } else {
          existing.draw(false);
        }
        return existing;
      }

      const dt = tableEl.DataTable({
        data: rows || [],
        columns: columns || [],
        responsive: true,
        deferRender: true,
        stateSave: false,
        dom: 'Bfrtip',
        buttons: ['excelHtml5', 'csvHtml5', 'pdfHtml5', 'print', 'pageLength'],
        language: {
          url: './dist/libs/datatables/i18n/fr-CA.json',
        },
        ...options,
      });
      window.__DT_INSTANCES__[key] = dt;
      return dt;
    },
    initWithAppBridge: async function (selector, buildSqlFn, columns, options) {
      ensureDeps();
      const $ = window.jQuery;
      const tableEl = $(selector);
      if (!tableEl.length) throw new Error(`Table introuvable: ${selector}`);

      const key = String(selector);

      // Si déjà initialisée → recharger via ajax (pas de re-init)
      if ($.fn.DataTable.isDataTable(tableEl) && window.__DT_INSTANCES__[key]) {
        const instance = window.__DT_INSTANCES__[key];
        instance.ajax && instance.ajax.reload(null, false);
        return instance;
      }

      const dt = tableEl.DataTable({
        destroy: true,
        processing: true,
        serverSide: false,
        ajax: function(_req, callback, settings) {
          // DataTables attend un objet type jqXHR avec abort()
          const ctrl = { aborted: false };
          const jqXHR = { abort: function() { ctrl.aborted = true; } };
          settings.jqXHR = jqXHR;

          try {
            if (window.appBridge && typeof window.appBridge.execute_sql === 'function') {
              const sql = typeof buildSqlFn === 'function' ? buildSqlFn() : String(buildSqlFn || '');
              DataTablesHelper.lastSql = sql;
              console.debug('[DataTablesHelper] SQL exécutée:', sql);
              Promise.resolve(window.appBridge.execute_sql(sql))
                .then(raw => {
                  if (ctrl.aborted) { callback({ data: [] }); return; }
                  const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
                  const rows = parsed && parsed.rows ? parsed.rows : (Array.isArray(parsed) ? parsed : []);
                  try { console.debug('[DataTablesHelper] rows reçues:', Array.isArray(rows) ? rows.length : 0); } catch {}
                  callback({ data: rows });
                })
                .catch(e => {
                  console.error('Erreur ajax DataTables:', e);
                  callback({ data: [] });
                });
            } else {
              DataTablesHelper.lastSql = null;
              console.warn('AppBridge.execute_sql indisponible.');
              callback({ data: [] });
            }
          } catch (e) {
            console.error('Erreur ajax DataTables:', e);
            callback({ data: [] });
          }

          return jqXHR;
        },
        data: [],
        columns: columns || [],
        responsive: true,
        deferRender: true,
        stateSave: false,
        dom: 'Bfrtip',
        buttons: ['excelHtml5', 'csvHtml5', 'pdfHtml5', 'print', 'pageLength'],
        language: {
          url: './dist/libs/datatables/i18n/fr-CA.json',
        },
        ...options,
      });
      window.__DT_INSTANCES__[key] = dt;
      return dt;
    },
  };

  window.DataTablesHelper = DataTablesHelper;
})();
