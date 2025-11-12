// web/tabler/js/analytics-helpers.js
// Fonctions d'agrégation côté client: sum, sumIf, groupBy, build timeseries
(function(){
  if (window.Analytics) return;

  function safeNum(v) {
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
  }

  const Analytics = {
    sum: function(arr, getter) {
      let s = 0;
      for (const it of arr || []) s += safeNum(getter ? getter(it) : it);
      return s;
    },
    sumIf: function(arr, pred, getter) {
      let s = 0;
      for (const it of arr || []) if (!pred || pred(it)) s += safeNum(getter ? getter(it) : it);
      return s;
    },
    countDistinct: function(arr, getter) {
      const set = new Set();
      for (const it of arr || []) set.add(getter ? getter(it) : it);
      return set.size;
    },
    groupBy: function(arr, keyFn) {
      const map = new Map();
      for (const it of arr || []) {
        const k = keyFn(it);
        if (!map.has(k)) map.set(k, []);
        map.get(k).push(it);
      }
      return map;
    },
    toSeriesXY: function(groupMap, xKeyFn, yAggFn) {
      // groupMap: Map<seriesName, rows[]>
      const out = {};
      for (const [name, rows] of groupMap.entries()) {
        const byX = Analytics.groupBy(rows, xKeyFn);
        const pts = [];
        for (const [x, subset] of byX.entries()) {
          pts.push({ x, y: yAggFn(subset) });
        }
        pts.sort((a,b) => (a.x > b.x ? 1 : a.x < b.x ? -1 : 0));
        out[name] = pts;
      }
      return out;
    },
  };

  window.Analytics = Analytics;
})();





