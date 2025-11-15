// web/tabler/js/charts-helper.js
// Mince couche pour initialiser ApexCharts avec options par défaut Tabler
(function(){
  if (window.ChartsHelper) return;

  function ensureApex() {
    if (!window.ApexCharts) throw new Error('ApexCharts non chargé');
  }

  const defaultOptions = {
    chart: { fontFamily: 'inherit', foreColor: '#1e293b' },
    stroke: { width: 2 },
    dataLabels: { enabled: false },
    legend: { position: 'top' },
    tooltip: { theme: 'light' },
    noData: { text: 'Aucune donnée' },
  };

  const ChartsHelper = {
    mount: function (elSelector, type, opts) {
      ensureApex();
      const el = document.querySelector(elSelector);
      if (!el) throw new Error(`Élément introuvable: ${elSelector}`);
      const config = {
        ...defaultOptions,
        ...(opts || {}),
      };
      config.chart = {
        type,
        ...defaultOptions.chart,
        ...(opts?.chart || {}),
      };
      config.chart.toolbar = config.chart.toolbar || {};
      config.chart.toolbar.tools = config.chart.toolbar.tools || {};
      config.chart.toolbar.tools.customIcons = config.chart.toolbar.tools.customIcons || [];
      config.chart.toolbar.tools.customIcons.push({
        icon: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v2"/><path d="M12 17v2"/><path d="M5 12h2"/><path d="M17 12h2"/><circle cx="12" cy="12" r="3"/></svg>',
        index: -1,
        title: 'Options',
        class: 'apx-custom-options',
        click: function(chartRef){
          if (window.ChartOptions && typeof window.ChartOptions.showOptionsPanel === 'function') {
            window.ChartOptions.showOptionsPanel(chartRef);
          } else {
            console.warn('ChartOptions not available');
          }
        }
      });
      const chart = new ApexCharts(el, config);
      chart.render();
      return chart;
    },
    seriesXY: function (pointsArray, name = 'Series') {
      // pointsArray: [{x: <cat/date>, y: <number>}, ...]
      return [{ name, data: pointsArray || [] }];
    },
    seriesFromGroups: function (groupKeyToPoints) {
      // { key: [{x,y}, ...], ... } -> [{name, data}, ...]
      return Object.keys(groupKeyToPoints || {}).map(k => ({
        name: k,
        data: groupKeyToPoints[k] || [],
      }));
    },
  };

  window.ChartsHelper = ChartsHelper;
})();





