## Panneau d'options Apex natif

- Inclure `./js/chart-options.js` après `apex-chart-catalog.js` et `chart-switcher.js` (déjà fait dans chaque page `analytics_*.html`).
- Après création d'un graphique ApexCharts (via `ChartSwitcher` ou `ChartsHelper`), appeler :
  ```js
  if (window.ChartOptions && chartInstance) {
    window.ChartOptions.attachChartOptions('#chart-id','page','chart', chartInstance, dataFetcherFacultatif);
  }
  ```
- Le bouton ⚙ intégré à la toolbar Apex ouvre le panneau flottant (sources, regroupement, agrégation, couleurs).
- `ChartSwitcher` et `ChartsHelper` injectent automatiquement l'icône personnalisée via la toolbar Apex.

### AppBridge (Qt/Python)
```python
class AppBridge(QObject):
    @pyqtSlot(str, str, result=str)
    def get_chart_settings(self, page_id, chart_id):
        return self.repo.load_chart_settings(page_id, chart_id) or ''

    @pyqtSlot(str, str, str)
    def save_chart_settings(self, page_id, chart_id, settings_json):
        self.repo.save_chart_settings(page_id, chart_id, settings_json)
```

### Table PostgreSQL minimale
```sql
CREATE TABLE chart_settings (
  id SERIAL PRIMARY KEY,
  page_id TEXT NOT NULL,
  chart_id TEXT NOT NULL,
  user_id TEXT,
  settings JSONB NOT NULL,
  updated_at TIMESTAMP DEFAULT now()
);
```

### Vérification manuelle
1. Ouvrir une page `analytics_*.html` (ex: `analytics_masse.html`).
2. Cliquer sur l’icône Options dans la toolbar Apex.
3. Modifier source / regroupement / agrégation / couleurs puis **Appliquer**.
4. Cliquer sur **Appliquer** ou **Fermer** et vérifier la persistance (localStorage + `save_chart_settings` si bridge actif).

