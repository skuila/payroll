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
      const chart = new ApexCharts(el, {
        chart: { type, ...defaultOptions.chart, ...(opts?.chart || {}) },
        ...defaultOptions,
        ...(opts || {}),
      });
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





