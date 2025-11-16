/*
  chart-options.js
  Centralise un panneau d'options natif pour ApexCharts :
  - Source (net/gross/employer_part)
  - Groupement (all/employee/poste)
  - Agrégation (day/month/year)
  - Color pickers par série
  Usage : window.ChartOptions.attachChartOptions(selector, pageId, chartId, chartInstance, dataFetcher?)
*/

(function () {
  'use strict';

  const ChartOptions = {
    _panelId: 'chart-options-panel',
    _attached: new WeakMap(),
    _lastAttachedChart: null,

    attachChartOptions(selector, pageId, chartId, chartInstance, dataFetcher) {
      if (!chartInstance) return;
      this._ensurePanel();
      this._ensureToolbarStyles();
      this._attached.set(chartInstance, { selector, pageId, chartId, dataFetcher });
      const series = (chartInstance.w && chartInstance.w.config && chartInstance.w.config.series) || [];
      this._renderColorPickers(series, chartInstance);
      this._lastAttachedChart = chartInstance;
      window.ChartOptions = window.ChartOptions || this;
    },

    showOptionsPanel(chartInstance) {
      if (!chartInstance) chartInstance = this._lastAttachedChart;
      if (!chartInstance) return;
      this._ensurePanel();
      const meta = this._attached.get(chartInstance) || {};
      const panel = document.getElementById(this._panelId);
      panel.querySelector('#fieldSelect').value = (meta.lastSettings && meta.lastSettings.field) || 'net';
      panel.querySelector('#groupSelect').value = (meta.lastSettings && meta.lastSettings.group) || 'all';
      panel.querySelector('#aggSelect').value = (meta.lastSettings && meta.lastSettings.agg) || 'month';
      const series = (chartInstance.w && chartInstance.w.config && chartInstance.w.config.series) || [];
      this._renderColorPickers(series, chartInstance, meta.lastSettings && meta.lastSettings.colors);
      panel.style.display = 'block';
      panel.dataset.attachedChart = this._getChartId(chartInstance);
      this._lastAttachedChart = chartInstance;
    },

    async applyOptionsToChart(chartInstance) {
      if (!chartInstance) chartInstance = this._lastAttachedChart;
      if (!chartInstance) return;
      const panel = document.getElementById(this._panelId);
      const field = panel.querySelector('#fieldSelect').value;
      const group = panel.querySelector('#groupSelect').value;
      const agg = panel.querySelector('#aggSelect').value;
      const colors = Array.from(panel.querySelectorAll('.co-picker')).map(i => i.value);

      const meta = this._attached.get(chartInstance) || {};
      const rows = await this._getRows(meta.dataFetcher);

      const type = (chartInstance.w?.config?.chart?.type || '').toLowerCase();
      const baseSeries = this._buildSeriesFromRows(rows, (group === 'all') ? 'all' : (group === 'employee' ? 'employee' : 'poste'), field);
      const aggregated = this._aggregateSeriesByPeriod(baseSeries, agg);

      const palette = ['#0b69ff','#7c3aed','#16a34a','#f97316','#ef4444','#06b6d4','#f59e0b','#ef9a9a'];
      const finalColors = [];
      for (let i=0;i<aggregated.length;i++) finalColors.push(colors[i] || palette[i % palette.length]);

      const isCircular = type === 'pie' || type === 'donut' || type === 'radialbar';
      try {
        if (!isCircular) {
          chartInstance.updateSeries(aggregated, true);
        }
        chartInstance.updateOptions({ colors: finalColors }, false, true);
      } catch (e) {
        console.warn('ChartOptions.applyOptionsToChart update failed', e);
      }

      meta.lastSettings = { field, group, agg, colors: finalColors };
      this._attached.set(chartInstance, meta);
      panel.style.display = 'none';
    },

    /* Internal helpers */
    _ensurePanel() {
      if (document.getElementById(this._panelId)) return;
      const panel = document.createElement('div');
      panel.id = this._panelId;
      panel.style.position = 'fixed';
      panel.style.right = '20px';
      panel.style.top = '80px';
      panel.style.width = '360px';
      panel.style.zIndex = '1200';
      panel.style.background = '#fff';
      panel.style.border = '1px solid #e6e9ee';
      panel.style.borderRadius = '10px';
      panel.style.boxShadow = '0 10px 30px rgba(2,6,23,0.12)';
      panel.style.padding = '14px';
      panel.style.display = 'none';
      panel.innerHTML = `
        <h3 style="margin:0 0 10px 0;font-size:16px">Options du graphique</h3>
        <div style="margin-bottom:8px"><label style="font-size:13px;display:block;margin-bottom:4px">Source de données</label>
          <select id="fieldSelect" style="width:100%;padding:8px;border-radius:6px;border:1px solid #d1d5db">
            <option value="net">Net</option>
            <option value="gross">Brut (gross)</option>
            <option value="employer_part">Part employeur</option>
          </select>
        </div>
        <div style="margin-bottom:8px"><label style="font-size:13px;display:block;margin-bottom:4px">Regrouper par</label>
          <select id="groupSelect" style="width:100%;padding:8px;border-radius:6px;border:1px solid #d1d5db">
            <option value="all">Toutes séries (Totaux)</option>
            <option value="employee">Employé</option>
            <option value="poste">Poste budgétaire</option>
          </select>
        </div>
        <div style="margin-bottom:8px"><label style="font-size:13px;display:block;margin-bottom:4px">Agrégation</label>
          <select id="aggSelect" style="width:100%;padding:8px;border-radius:6px;border:1px solid #d1d5db">
            <option value="day">Jour</option>
            <option value="month" selected>Mois</option>
            <option value="year">Année</option>
          </select>
        </div>
        <div style="margin-bottom:8px"><label style="font-size:13px;display:block;margin-bottom:4px">Couleurs (par série)</label>
          <div id="colorsContainer" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:6px"></div>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px">
          <button id="applyOptionsBtn" style="flex:1;padding:8px;border-radius:6px;border:1px solid #d1d5db">Appliquer</button>
          <button id="closeOptionsBtn" style="flex:1;padding:8px;border-radius:6px;border:1px solid #d1d5db">Fermer</button>
        </div>
      `;
      document.body.appendChild(panel);

      panel.querySelector('#closeOptionsBtn').addEventListener('click', ()=> panel.style.display='none');
      panel.querySelector('#applyOptionsBtn').addEventListener('click', ()=> {
        const chartInstance = this._lastAttachedChart;
        if (chartInstance) this.applyOptionsToChart(chartInstance);
      });
    },

    _renderColorPickers(series, chartInstance, colors) {
      const cont = document.getElementById('colorsContainer');
      if (!cont) return;
      cont.innerHTML = '';
      const palette = ['#0b69ff','#7c3aed','#16a34a','#f97316','#ef4444','#06b6d4','#f59e0b','#ef9a9a'];
      const cols = colors && colors.length ? colors.slice() : series.map((s,i)=> palette[i % palette.length]);
      series.forEach((s,i)=>{
        const inp = document.createElement('input');
        inp.type = 'color';
        inp.className = 'co-picker';
        inp.value = cols[i] || palette[i % palette.length];
        inp.title = s.name || `Série ${i+1}`;
        inp.dataset.idx = i;
        inp.addEventListener('input', ()=> {
          const c = Array.from(cont.querySelectorAll('.co-picker')).map(el=>el.value);
          try { chartInstance.updateOptions({ colors: c }, false, true); } catch(e) {}
        });
        cont.appendChild(inp);
      });
      this._lastAttachedChart = chartInstance;
    },

    _getRows(dataFetcher) {
      if (typeof dataFetcher === 'function') {
        try {
          const res = dataFetcher();
          if (res && typeof res.then === 'function') return res;
          return Promise.resolve(res);
        } catch (e) {
          return Promise.resolve([]);
        }
      }
      return Promise.resolve(window._rawRows || []);
    },

    _buildSeriesFromRows(rows, groupBy='all', valueField='net') {
      if (!Array.isArray(rows)) return [];
      if (groupBy === 'all') {
        return [{ name: 'Total', data: rows.map(r => ({ x: r.date, y: Number(r[valueField] || 0) })) }];
      }
      const groups = {};
      rows.forEach(r => {
        const key = r[groupBy] || 'INCONNU';
        groups[key] = groups[key] || [];
        groups[key].push(r);
      });
      return Object.keys(groups).map(k => ({ name: k, data: groups[k].map(r => ({ x: r.date, y: Number(r[valueField] || 0) })) }));
    },

    _aggregateSeriesByPeriod(seriesArray, period='month') {
      return seriesArray.map(s => {
        const map = new Map();
        s.data.forEach(pt => {
          const d = new Date(pt.x);
          let key;
          if (isNaN(d.getTime())) key = pt.x;
          else if (period === 'year') key = `${d.getFullYear()}`;
          else if (period === 'month') key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
          else key = d.toISOString().slice(0,10);
          map.set(key, (map.get(key) || 0) + (Number(pt.y) || 0));
        });
        const data = Array.from(map.entries()).sort((a,b)=> a[0] < b[0] ? -1 : 1).map(([k,v]) => ({ x: k, y: Math.round(v*100)/100 }));
        return { name: s.name, data };
      });
    },

    _getChartId(chartInstance) {
      if (!chartInstance) return null;
      return chartInstance.w && chartInstance.w.globals && chartInstance.w.globals.domID ? chartInstance.w.globals.domID : String(Math.random());
    },

    _ensureToolbarStyles() {
      if (document.getElementById('chart-options-toolbar-style')) return;
      const style = document.createElement('style');
      style.id = 'chart-options-toolbar-style';
      style.textContent = `
        .apexcharts-toolbar {
          opacity: 0;
          pointer-events: none;
          transition: opacity 0.2s ease;
        }
        .apexcharts-canvas:hover .apexcharts-toolbar,
        .apexcharts-toolbar:focus-within {
          opacity: 1 !important;
          pointer-events: auto;
        }
      `;
      document.head.appendChild(style);
    }
  };

  window.ChartOptions = window.ChartOptions || ChartOptions;
  ChartOptions._ensureToolbarStyles();
})();