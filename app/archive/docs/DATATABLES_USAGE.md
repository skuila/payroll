# Utilisation DataTables (local, Tabler / Bootstrap 5)

## Fichiers requis (locaux)

Dans `web/tabler/dist/libs/datatables/` :
- CSS: `dataTables.bootstrap5.min.css`, `buttons.bootstrap5.min.css`, `responsive.bootstrap5.min.css`, `fixedHeader.bootstrap5.min.css`
- JS: `jquery.min.js`, `jquery.dataTables.min.js`, `dataTables.bootstrap5.min.js`,
  `dataTables.buttons.min.js`, `buttons.bootstrap5.min.js`, `buttons.html5.min.js`,
  `buttons.print.min.js`, `jszip.min.js`, `pdfmake.min.js`, `vfs_fonts.js`,
  `dataTables.responsive.min.js`, `responsive.bootstrap5.min.js`,
  `dataTables.fixedHeader.min.js`, `fixedHeader.bootstrap5.min.js`
- i18n: `i18n/fr-CA.json`

Téléchargez-les via:

```bash
python scripts/download_datatables.py
```

## Inclusion dans une page Tabler

Dans `<head>` :

```html
<link href="./dist/libs/datatables/css/dataTables.bootstrap5.min.css" rel="stylesheet"/>
<link href="./dist/libs/datatables/css/buttons.bootstrap5.min.css" rel="stylesheet"/>
<link href="./dist/libs/datatables/css/responsive.bootstrap5.min.css" rel="stylesheet"/>
<link href="./dist/libs/datatables/css/fixedHeader.bootstrap5.min.css" rel="stylesheet"/>
```

Avant `</body>` :

```html
<script src="./dist/libs/datatables/js/jquery.min.js"></script>
<script src="./dist/libs/datatables/js/jquery.dataTables.min.js"></script>
<script src="./dist/libs/datatables/js/dataTables.bootstrap5.min.js"></script>
<script src="./dist/libs/datatables/js/dataTables.buttons.min.js"></script>
<script src="./dist/libs/datatables/js/buttons.bootstrap5.min.js"></script>
<script src="./dist/libs/datatables/js/jszip.min.js"></script>
<script src="./dist/libs/datatables/js/pdfmake.min.js"></script>
<script src="./dist/libs/datatables/js/vfs_fonts.js"></script>
<script src="./dist/libs/datatables/js/buttons.html5.min.js"></script>
<script src="./dist/libs/datatables/js/buttons.print.min.js"></script>
<script src="./dist/libs/datatables/js/dataTables.responsive.min.js"></script>
<script src="./dist/libs/datatables/js/responsive.bootstrap5.min.js"></script>
<script src="./dist/libs/datatables/js/dataTables.fixedHeader.min.js"></script>
<script src="./dist/libs/datatables/js/fixedHeader.bootstrap5.min.js"></script>
<script src="./js/datatables-helper.js"></script>
```

## Initialisation via AppBridge (exemple)

HTML :

```html
<table id="tbl-demo" class="table table-striped w-100">
  <thead>
    <tr>
      <th>Nom</th>
      <th>Catégorie</th>
      <th>Titre</th>
      <th>Date</th>
      <th>Statut</th>
      <th class="text-end">Total ($)</th>
    </tr>
  </thead>
  <tbody><tr><td colspan="6">Chargement…</td></tr></tbody>
  </table>
```

JS :

```html
<script>
(function(){
  function buildSql(){
    const from = document.getElementById('startDate').value;
    const to = document.getElementById('endDate').value || from;
    return `SELECT
              COALESCE(e.nom_complet, e.nom_norm || COALESCE(' ' || e.prenom_norm, '')) AS nom_complet,
              COALESCE(p.categorie_emploi,'Non défini') AS categorie_emploi,
              COALESCE(p.titre_emploi,'Non défini')     AS titre_emploi,
              MAX(t.pay_date)                            AS pay_date,
              COALESCE(s.statut_calcule,'actif')         AS statut_calcule,
              SUM(t.amount_cents)::numeric/100.0         AS amount_paid
            FROM payroll.payroll_transactions t
            JOIN core.employees e ON e.employee_id=t.employee_id
            LEFT JOIN paie.v_employe_profil p ON p.employee_id=e.employee_id
            LEFT JOIN paie.v_employe_statut_calcule s ON s.employee_id=e.employee_id
            WHERE t.pay_date BETWEEN DATE '${from}' AND DATE '${to}'
            GROUP BY 1,2,3,5
            ORDER BY 1`;
  }

  window.DataTablesHelper.initWithAppBridge('#tbl-demo', buildSql, [
    { title: 'Nom', data: 0 },
    { title: 'Catégorie', data: 1 },
    { title: 'Titre', data: 2 },
    { title: 'Date', data: 3, render: DataTablesHelper.formatDate },
    { title: 'Statut', data: 4, render: s => `<span class="badge ${String(s||'').toLowerCase()==='actif'?'bg-success-lt':'bg-secondary-lt'}">${s||'-'}</span>` },
    { title: 'Total ($)', data: 5, className: 'text-end', render: DataTablesHelper.formatCurrency }
  ]);
})();
</script>
```

## Conseils
- Utilisez la locale `fr-CA.json` locale (offline)
- Mappez les colonnes par index si vos données sont des tableaux (`rows` de AppBridge)
- Pour les très gros volumes, prévoyez un mode server-side plus tard (FastAPI)

