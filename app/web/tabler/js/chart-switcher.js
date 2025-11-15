// Gestionnaire de sélection et sauvegarde des types de graphiques
// Utilise localStorage pour persister les choix utilisateur

(function(){
  const ChartSwitcher = {
    // Sauvegarder le choix pour une page/graphique
    saveChoice: function(pageId, chartId, variantId){
      const key = `chartType_${pageId}_${chartId}`;
      localStorage.setItem(key, variantId);
      console.log(`Chart type saved: ${key} = ${variantId}`);
    },
    
    // Récupérer le choix sauvegardé
    getChoice: function(pageId, chartId){
      const key = `chartType_${pageId}_${chartId}`;
      return localStorage.getItem(key);
    },
    
    // Créer un graphique avec le type sauvegardé ou par défaut
    createChart: function(selector, pageId, chartId, defaultVariantId, dataFetcher){
      const savedVariant = this.getChoice(pageId, chartId) || defaultVariantId;
      const variant = getChartVariant(savedVariant);
      
      if (!variant) {
        console.error(`Chart variant not found: ${savedVariant}`);
        return null;
      }
      
      // Créer le graphique avec la config du catalog
      const chartConfig = {
        ...variant.config,
        chart: {
          ...variant.config.chart,
          height: 350,
          toolbar: { show: true }
        }
      };
      
      // add custom Options icon to toolbar (merge with existing toolbar config)
      chartConfig.chart = chartConfig.chart || {};
      chartConfig.chart.toolbar = chartConfig.chart.toolbar || {};
      chartConfig.chart.toolbar.tools = chartConfig.chart.toolbar.tools || {};
      chartConfig.chart.toolbar.tools.customIcons = chartConfig.chart.toolbar.tools.customIcons || [];
      chartConfig.chart.toolbar.tools.customIcons.push({
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
      
      const chart = new ApexCharts(document.querySelector(selector), chartConfig);
      chart.render();
      
      // attach central ChartOptions module if present
      try {
        if (window.ChartOptions && typeof window.ChartOptions.attachChartOptions === 'function') {
          window.ChartOptions.attachChartOptions(selector, pageId, chartId, chart, dataFetcher);
        }
      } catch (e) {
        console.warn('ChartOptions attach failed', e);
      }
      
      // Charger les données réelles si dataFetcher fourni
      if (typeof dataFetcher === 'function') {
        Promise.resolve(dataFetcher())
          .then(realData => {
            if (!realData) return;
            if (realData.options) chart.updateOptions(realData.options);
            if (realData.xaxis) chart.updateOptions({ xaxis: realData.xaxis });
            if (realData.yaxis) chart.updateOptions({ yaxis: realData.yaxis });
            if (realData.labels) chart.updateOptions({ labels: realData.labels });
            if (realData.colors) chart.updateOptions({ colors: realData.colors });
            const type = variant.config.chart?.type;
            if (type === 'pie' || type === 'donut') {
              if (Array.isArray(realData.series) && typeof realData.series[0] === 'number') {
                chart.updateOptions({ series: realData.series, labels: realData.labels });
                return;
              }
              const sourceSeries = realData.series || [];
              const series = sourceSeries.map(s => {
                const lastPoint = (s.data || [])[s.data.length - 1];
                return lastPoint ? Math.abs(lastPoint.y) : 0;
              });
              const labels = sourceSeries.map(s => s.name);
              chart.updateOptions({ series, labels });
            } else if (type === 'radialBar') {
              if (Array.isArray(realData.series) && typeof realData.series[0] === 'number') {
                chart.updateSeries(realData.series);
                if (realData.labels) chart.updateOptions({ labels: realData.labels });
                return;
              }
              const sourceSeries = (realData.series || []).slice(0, 4);
              const series = sourceSeries.map(s => {
                const lastPoint = (s.data || [])[s.data.length - 1];
                if (!lastPoint) return 0;
                return Math.min(100, Math.abs(lastPoint.y / 1000));
              });
              const labels = sourceSeries.map(s => s.name);
              chart.updateOptions({ series, labels });
            } else {
              if (realData.series) chart.updateSeries(realData.series);
            }
          })
          .catch(err => console.error('Error loading chart data:', err));
      }
      
      return chart;
    },
    
    // Générer un aperçu miniature dans un élément
    renderPreview: function(selector, variantId){
      const variant = getChartVariant(variantId);
      if (!variant) return null;
      
      const previewConfig = {
        ...variant.config,
        ...variant.data,
        chart: {
          ...variant.config.chart,
          height: 120,
          toolbar: { show: false },
          sparkline: { enabled: false }
        }
      };
      
      const chart = new ApexCharts(document.querySelector(selector), previewConfig);
      chart.render();
      return chart;
    },
    
    // Obtenir le nom du type actuel
    getCurrentVariantName: function(pageId, chartId, defaultVariantId){
      const savedVariant = this.getChoice(pageId, chartId) || defaultVariantId;
      const variant = getChartVariant(savedVariant);
      return variant ? variant.name : 'Graphique';
    }
  };
  
  window.ChartSwitcher = ChartSwitcher;
})();




