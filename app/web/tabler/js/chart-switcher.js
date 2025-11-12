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
      
      const chart = new ApexCharts(document.querySelector(selector), chartConfig);
      chart.render();
      
      // Charger les données réelles si dataFetcher fourni
      if (typeof dataFetcher === 'function') {
        dataFetcher().then(realData => {
          if (realData) {
            // Adapter les données selon le type
            if (variant.config.chart.type === 'pie' || variant.config.chart.type === 'donut') {
              // Pour pie/donut: extraire dernière valeur de chaque série
              const series = realData.series.map(s => {
                const lastPoint = s.data[s.data.length - 1];
                return Math.abs(lastPoint.y);
              });
              const labels = realData.series.map(s => s.name);
              chart.updateOptions({series, labels});
            } else if (variant.config.chart.type === 'radialBar') {
              // Pour radialBar: extraire pourcentages
              const series = realData.series.slice(0, 4).map(s => {
                const lastPoint = s.data[s.data.length - 1];
                return Math.min(100, Math.abs(lastPoint.y / 1000));
              });
              const labels = realData.series.slice(0, 4).map(s => s.name);
              chart.updateOptions({series, labels});
            } else {
              // Pour line/bar/area: utiliser tel quel
              chart.updateSeries(realData.series);
            }
          }
        }).catch(err => console.error('Error loading chart data:', err));
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




