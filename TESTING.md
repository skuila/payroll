# Validation chart-options native

1. Ouvrir une page analytics (ex. `analytics_masse.html`) dans l'app Qt ou via navigateur.
2. Vérifier la présence de l'icône ⚙ dans la toolbar Apex de chaque graphique.
3. Cliquer deux fois sur **Options** :
   - Changer Source / Groupement / Agrégation puis cliquer sur **Appliquer** → `chart.updateSeries(...)` doit rafraîchir les données.
   - Modifier une ou plusieurs couleurs (color pickers) → `chart.updateOptions({ colors })` applique immédiatement la palette.
4. Cliquer sur **Appliquer** (bouton principal) puis **Fermer**.
5. Rafraîchir la page : les choix doivent persister (localStorage `chartSettings_*` et logs `save_chart_settings` si AppBridge actif).

