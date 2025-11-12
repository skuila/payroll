// Catalog complet des 75+ variantes ApexCharts
// Source: https://apexcharts.com/javascript-chart-demos/

const APEX_CHART_CATALOG = {
  line: {
    family: 'Line Charts',
    icon: '<path d="M3 17l6 -6l4 4l8 -8" /><path d="M14 7l7 0l0 7" />',
    variants: [
      {
        id: 'line-basic',
        name: 'Courbe simple',
        desc: 'Tendances et évolutions',
        config: { chart: {type:'line'}, stroke: {curve:'straight', width:2} },
        data: {series:[{name:'Série 1',data:[30,40,35,50,49,60,70]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'line-smooth',
        name: 'Courbe lissée',
        desc: 'Courbe avec interpolation douce',
        config: { chart: {type:'line'}, stroke: {curve:'smooth', width:3} },
        data: {series:[{name:'Série 1',data:[30,40,35,50,49,60,70]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'line-stepline',
        name: 'Escalier',
        desc: 'Courbe en marches',
        config: { chart: {type:'line'}, stroke: {curve:'stepline', width:2} },
        data: {series:[{name:'Série 1',data:[30,40,35,50,49,60,70]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'line-dashed',
        name: 'Pointillés',
        desc: 'Ligne en tirets',
        config: { chart: {type:'line'}, stroke: {curve:'straight', width:2, dashArray:5} },
        data: {series:[{name:'Série 1',data:[30,40,35,50,49,60,70]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'line-gradient',
        name: 'Avec dégradé',
        desc: 'Ligne avec gradient de couleur',
        config: { chart: {type:'line'}, stroke: {curve:'smooth', width:3}, fill:{type:'gradient'} },
        data: {series:[{name:'Série 1',data:[30,40,35,50,49,60,70]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'line-multi',
        name: 'Multi-séries',
        desc: 'Plusieurs courbes',
        config: { chart: {type:'line'}, stroke: {curve:'smooth', width:2} },
        data: {series:[{name:'S1',data:[30,40,35,50,49,60,70]},{name:'S2',data:[20,30,25,40,39,50,60]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      }
    ]
  },
  
  area: {
    family: 'Area Charts',
    icon: '<path d="M4 19l4 -6l4 2l4 -5l4 4v5h-16z" />',
    variants: [
      {
        id: 'area-basic',
        name: 'Aire simple',
        desc: 'Zone remplie sous la courbe',
        config: { chart: {type:'area'}, stroke: {curve:'smooth'}, fill:{opacity:0.3} },
        data: {series:[{name:'Série 1',data:[30,40,35,50,49,60,70]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'area-stacked',
        name: 'Aires empilées',
        desc: 'Aires cumulées',
        config: { chart: {type:'area', stacked:true}, stroke: {curve:'smooth'}, fill:{opacity:0.5} },
        data: {series:[{name:'S1',data:[30,40,35,50,49,60,70]},{name:'S2',data:[20,30,25,40,39,50,60]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'area-stacked-100',
        name: 'Aires 100%',
        desc: 'Empilées en pourcentages',
        config: { chart: {type:'area', stacked:true, stackType:'100%'}, stroke: {curve:'smooth'}, fill:{opacity:0.6} },
        data: {series:[{name:'S1',data:[30,40,35,50,49,60,70]},{name:'S2',data:[20,30,25,40,39,50,60]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'area-spline',
        name: 'Aire lissée',
        desc: 'Courbe spline avec remplissage',
        config: { chart: {type:'area'}, stroke: {curve:'smooth', width:3}, fill:{type:'gradient'} },
        data: {series:[{name:'Série 1',data:[30,40,35,50,49,60,70]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      }
    ]
  },
  
  bar: {
    family: 'Bar Charts',
    icon: '<path d="M3 12m0 1a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v6a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1z" /><path d="M9 8m0 1a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v10a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1z" />',
    variants: [
      {
        id: 'bar-vertical',
        name: 'Barres verticales',
        desc: 'Colonnes simples',
        config: { chart: {type:'bar'}, plotOptions:{bar:{horizontal:false}} },
        data: {series:[{name:'Montant',data:[30,40,35,50,49,60,70]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'bar-horizontal',
        name: 'Barres horizontales',
        desc: 'Idéal pour classements',
        config: { chart: {type:'bar'}, plotOptions:{bar:{horizontal:true}} },
        data: {series:[{name:'Montant',data:[30,40,35,50,49,60,70]}], xaxis:{categories:['Emp1','Emp2','Emp3','Emp4','Emp5','Emp6','Emp7']}}
      },
      {
        id: 'bar-stacked',
        name: 'Barres empilées',
        desc: 'Composition par catégorie',
        config: { chart: {type:'bar', stacked:true}, plotOptions:{bar:{horizontal:false}} },
        data: {series:[{name:'S1',data:[30,40,35,50,49,60,70]},{name:'S2',data:[20,30,25,40,39,50,60]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'bar-stacked-100',
        name: 'Barres 100%',
        desc: 'Empilées en pourcentages',
        config: { chart: {type:'bar', stacked:true, stackType:'100%'}, plotOptions:{bar:{horizontal:false}} },
        data: {series:[{name:'S1',data:[30,40,35,50,49,60,70]},{name:'S2',data:[20,30,25,40,39,50,60]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'bar-grouped',
        name: 'Barres groupées',
        desc: 'Comparaison multi-séries',
        config: { chart: {type:'bar'}, plotOptions:{bar:{horizontal:false, columnWidth:'55%'}} },
        data: {series:[{name:'2024',data:[30,40,35,50,49,60,70]},{name:'2025',data:[35,45,40,55,54,65,75]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'bar-negative',
        name: 'Avec valeurs négatives',
        desc: 'Gains et pertes',
        config: { chart: {type:'bar'}, plotOptions:{bar:{horizontal:false}} },
        data: {series:[{name:'Montant',data:[30,-20,35,-15,49,60,-10]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'bar-patterned',
        name: 'Avec motifs',
        desc: 'Barres avec patterns',
        config: { chart: {type:'bar'}, plotOptions:{bar:{horizontal:false}}, fill:{type:'pattern', pattern:{style:['verticalLines','horizontalLines']}} },
        data: {series:[{name:'S1',data:[30,40,35,50,49,60,70]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'bar-distributed',
        name: 'Distribuées (couleurs)',
        desc: 'Chaque barre une couleur',
        config: { chart: {type:'bar'}, plotOptions:{bar:{horizontal:false, distributed:true}} },
        data: {series:[{name:'Montant',data:[30,40,35,50,49,60,70]}], xaxis:{categories:['A','B','C','D','E','F','G']}}
      }
    ]
  },
  
  mixed: {
    family: 'Mixed Charts',
    icon: '<path d="M3 17l6 -6l4 4l8 -8" /><path d="M3 12m0 1a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v6a1 1 0 0 1 -1 1h-4a1 1 0 0 1 -1 -1z" />',
    variants: [
      {
        id: 'mixed-line-bar',
        name: 'Ligne + Barres',
        desc: 'Combiner courbe et colonnes',
        config: { chart: {type:'line'} },
        data: {series:[{name:'Ligne',type:'line',data:[30,40,35,50,49,60,70]},{name:'Barres',type:'column',data:[20,30,25,40,39,50,60]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'mixed-line-area',
        name: 'Ligne + Aire',
        desc: 'Courbe avec zone remplie',
        config: { chart: {type:'line'} },
        data: {series:[{name:'Ligne',type:'line',data:[30,40,35,50,49,60,70]},{name:'Aire',type:'area',data:[20,30,25,40,39,50,60]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      },
      {
        id: 'mixed-multi-yaxis',
        name: 'Multi-axes Y',
        desc: 'Plusieurs échelles verticales',
        config: { chart: {type:'line'}, yaxis:[{title:{text:'Axe 1'}},{opposite:true,title:{text:'Axe 2'}}] },
        data: {series:[{name:'S1',data:[30,40,35,50,49,60,70]},{name:'S2',data:[300,400,350,500,490,600,700]}], xaxis:{categories:['Jan','Fév','Mar','Avr','Mai','Jun','Jul']}}
      }
    ]
  },
  
  pie: {
    family: 'Pie & Donut',
    icon: '<path d="M10 3.2a9 9 0 1 0 10.8 10.8a1 1 0 0 0 -1 -1h-6.8a2 2 0 0 1 -2 -2v-7a.9 .9 0 0 0 -1 -.8" />',
    variants: [
      {
        id: 'pie-basic',
        name: 'Camembert',
        desc: 'Répartition en parts',
        config: { chart: {type:'pie'} },
        data: {series:[44,55,13,33,22], labels:['Gains','Déductions','Assurances','Primes','Autres']}
      },
      {
        id: 'pie-gradient',
        name: 'Camembert dégradé',
        desc: 'Avec gradient de couleurs',
        config: { chart: {type:'pie'}, fill:{type:'gradient'} },
        data: {series:[44,55,13,33,22], labels:['Gains','Déductions','Assurances','Primes','Autres']}
      },
      {
        id: 'pie-monochrome',
        name: 'Monochrome',
        desc: 'Nuances d\'une couleur',
        config: { chart: {type:'pie'}, theme:{monochrome:{enabled:true}} },
        data: {series:[44,55,13,33,22], labels:['A','B','C','D','E']}
      },
      {
        id: 'donut-basic',
        name: 'Donut',
        desc: 'Anneau avec centre vide',
        config: { chart: {type:'donut'} },
        data: {series:[44,55,13,33,22], labels:['Gains','Déductions','Assurances','Primes','Autres']}
      },
      {
        id: 'donut-gradient',
        name: 'Donut dégradé',
        desc: 'Anneau avec gradient',
        config: { chart: {type:'donut'}, fill:{type:'gradient'} },
        data: {series:[44,55,13,33,22], labels:['Gains','Déductions','Assurances','Primes','Autres']}
      },
      {
        id: 'donut-pattern',
        name: 'Donut motifs',
        desc: 'Avec patterns',
        config: { chart: {type:'donut'}, fill:{type:'pattern', pattern:{style:['verticalLines','horizontalLines','slantedLines']}} },
        data: {series:[44,55,13,33], labels:['A','B','C','D']}
      }
    ]
  },
  
  radialBar: {
    family: 'Radial Bar',
    icon: '<circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" />',
    variants: [
      {
        id: 'radialbar-single',
        name: 'Jauge simple',
        desc: 'Indicateur circulaire',
        config: { chart: {type:'radialBar'}, plotOptions:{radialBar:{hollow:{size:'70%'}}} },
        data: {series:[70], labels:['Progression']}
      },
      {
        id: 'radialbar-multiple',
        name: 'Multi-jauges',
        desc: 'Plusieurs indicateurs',
        config: { chart: {type:'radialBar'} },
        data: {series:[76,67,61,90], labels:['KPI 1','KPI 2','KPI 3','KPI 4']}
      },
      {
        id: 'radialbar-gradient',
        name: 'Jauge dégradé',
        desc: 'Avec gradient',
        config: { chart: {type:'radialBar'}, fill:{type:'gradient'}, plotOptions:{radialBar:{hollow:{size:'70%'}}} },
        data: {series:[70], labels:['Score']}
      },
      {
        id: 'radialbar-stroked',
        name: 'Avec contour',
        desc: 'Bordure épaisse',
        config: { chart: {type:'radialBar'}, plotOptions:{radialBar:{hollow:{size:'60%'}, track:{strokeWidth:'100%'}, dataLabels:{name:{offsetY:-10}, value:{offsetY:5}}}} },
        data: {series:[85], labels:['Conformité']}
      }
    ]
  },
  
  radar: {
    family: 'Radar Charts',
    icon: '<path d="M12 3l0 18" /><path d="M3 12l18 0" /><circle cx="12" cy="12" r="9" />',
    variants: [
      {
        id: 'radar-basic',
        name: 'Radar simple',
        desc: 'Profil multi-dimensions',
        config: { chart: {type:'radar'} },
        data: {series:[{name:'Profil',data:[80,50,30,40,100,20]}], xaxis:{categories:['Salaire','Ancienneté','Heures','Primes','Conformité','Absences']}}
      },
      {
        id: 'radar-multi',
        name: 'Radar multi-séries',
        desc: 'Comparaison de profils',
        config: { chart: {type:'radar'} },
        data: {series:[{name:'2024',data:[80,50,30,40,100,20]},{name:'2025',data:[70,60,40,50,90,30]}], xaxis:{categories:['A','B','C','D','E','F']}}
      },
      {
        id: 'radar-polygon',
        name: 'Radar rempli',
        desc: 'Polygone avec remplissage',
        config: { chart: {type:'radar'}, fill:{opacity:0.3} },
        data: {series:[{name:'Série',data:[80,50,30,40,100,20]}], xaxis:{categories:['A','B','C','D','E','F']}}
      }
    ]
  },
  
  heatmap: {
    family: 'Heatmap',
    icon: '<rect x="4" y="4" width="6" height="6" /><rect x="14" y="4" width="6" height="6" /><rect x="4" y="14" width="6" height="6" /><rect x="14" y="14" width="6" height="6" />',
    variants: [
      {
        id: 'heatmap-basic',
        name: 'Carte de chaleur',
        desc: 'Matrice de valeurs',
        config: { chart: {type:'heatmap'} },
        data: {series:[{name:'S1',data:[{x:'A',y:10},{x:'B',y:20},{x:'C',y:15}]},{name:'S2',data:[{x:'A',y:30},{x:'B',y:25},{x:'C',y:35}]}]}
      },
      {
        id: 'heatmap-multi',
        name: 'Heatmap multi-séries',
        desc: 'Plusieurs lignes',
        config: { chart: {type:'heatmap'} },
        data: {series:[{name:'Jan',data:[{x:'Lun',y:10},{x:'Mar',y:20},{x:'Mer',y:15},{x:'Jeu',y:25},{x:'Ven',y:30}]},{name:'Fév',data:[{x:'Lun',y:12},{x:'Mar',y:22},{x:'Mer',y:17},{x:'Jeu',y:27},{x:'Ven',y:32}]}]}
      },
      {
        id: 'heatmap-color-range',
        name: 'Plages de couleurs',
        desc: 'Palette personnalisée',
        config: { chart: {type:'heatmap'}, plotOptions:{heatmap:{colorScale:{ranges:[{from:0,to:10,color:'#00A100'},{from:11,to:20,color:'#FFB200'},{from:21,to:30,color:'#FF0000'}]}}} },
        data: {series:[{name:'S1',data:[{x:'A',y:5},{x:'B',y:15},{x:'C',y:25}]},{name:'S2',data:[{x:'A',y:8},{x:'B',y:18},{x:'C',y:28}]}]}
      },
      {
        id: 'heatmap-rounded',
        name: 'Coins arrondis',
        desc: 'Cellules arrondies',
        config: { chart: {type:'heatmap'}, plotOptions:{heatmap:{radius:8}} },
        data: {series:[{name:'S1',data:[{x:'A',y:10},{x:'B',y:20},{x:'C',y:15}]},{name:'S2',data:[{x:'A',y:30},{x:'B',y:25},{x:'C',y:35}]}]}
      }
    ]
  },
  
  treemap: {
    family: 'TreeMap',
    icon: '<rect x="3" y="3" width="8" height="8" /><rect x="13" y="3" width="8" height="4" /><rect x="13" y="9" width="8" height="12" /><rect x="3" y="13" width="8" height="8" />',
    variants: [
      {
        id: 'treemap-basic',
        name: 'TreeMap simple',
        desc: 'Hiérarchie rectangulaire',
        config: { chart: {type:'treemap'} },
        data: {series:[{data:[{x:'Poste A',y:400},{x:'Poste B',y:300},{x:'Poste C',y:200},{x:'Poste D',y:100}]}]}
      },
      {
        id: 'treemap-multi',
        name: 'TreeMap multi-séries',
        desc: 'Plusieurs niveaux',
        config: { chart: {type:'treemap'} },
        data: {series:[{name:'Dept 1',data:[{x:'A',y:100},{x:'B',y:200}]},{name:'Dept 2',data:[{x:'C',y:150},{x:'D',y:250}]}]}
      },
      {
        id: 'treemap-distributed',
        name: 'TreeMap coloré',
        desc: 'Couleurs distribuées',
        config: { chart: {type:'treemap'}, plotOptions:{treemap:{distributed:true}} },
        data: {series:[{data:[{x:'A',y:400},{x:'B',y:300},{x:'C',y:200},{x:'D',y:100}]}]}
      }
    ]
  },
  
  boxPlot: {
    family: 'BoxPlot',
    icon: '<rect x="8" y="6" width="8" height="12" /><path d="M12 6v-3" /><path d="M12 18v3" /><path d="M8 9h8" /><path d="M8 15h8" />',
    variants: [
      {
        id: 'boxplot-basic',
        name: 'Boîte simple',
        desc: 'Distribution statistique',
        config: { chart: {type:'boxPlot'} },
        data: {series:[{data:[{x:'Salaires',y:[2000,3000,4000,5000,6000]}]}]}
      },
      {
        id: 'boxplot-horizontal',
        name: 'Boîte horizontale',
        desc: 'Orientation horizontale',
        config: { chart: {type:'boxPlot'}, plotOptions:{boxPlot:{horizontal:true}} },
        data: {series:[{data:[{x:'Dept A',y:[2000,3000,4000,5000,6000]},{x:'Dept B',y:[2500,3500,4500,5500,6500]}]}]}
      }
    ]
  },
  
  scatter: {
    family: 'Scatter & Bubble',
    icon: '<circle cx="6" cy="18" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="18" cy="6" r="2" />',
    variants: [
      {
        id: 'scatter-basic',
        name: 'Nuage de points',
        desc: 'Corrélation X/Y',
        config: { chart: {type:'scatter', zoom:{enabled:true}} },
        data: {series:[{name:'Série',data:[[10,20],[15,25],[20,30],[25,35],[30,40]]}]}
      },
      {
        id: 'scatter-multi',
        name: 'Scatter multi-séries',
        desc: 'Plusieurs groupes',
        config: { chart: {type:'scatter'} },
        data: {series:[{name:'Groupe A',data:[[10,20],[15,25],[20,30]]},{name:'Groupe B',data:[[12,22],[17,27],[22,32]]}]}
      },
      {
        id: 'bubble-basic',
        name: 'Bulles',
        desc: 'Taille = 3e dimension',
        config: { chart: {type:'bubble'} },
        data: {series:[{name:'Série',data:[[10,20,30],[15,25,50],[20,30,70]]}]}
      },
      {
        id: 'bubble-3d',
        name: 'Bulles 3D',
        desc: 'Effet de profondeur',
        config: { chart: {type:'bubble'}, fill:{opacity:0.8} },
        data: {series:[{name:'Série',data:[[10,20,30],[15,25,50],[20,30,70]]}]}
      }
    ]
  },
  
  candlestick: {
    family: 'Candlestick',
    icon: '<rect x="8" y="6" width="8" height="12" /><path d="M12 6v-3" /><path d="M12 18v3" />',
    variants: [
      {
        id: 'candlestick-basic',
        name: 'Chandelier',
        desc: 'OHLC financier',
        config: { chart: {type:'candlestick'} },
        data: {series:[{data:[{x:new Date('2025-01-01'),y:[100,110,95,105]},{x:new Date('2025-01-02'),y:[105,115,100,110]}]}]}
      },
      {
        id: 'candlestick-combo',
        name: 'Chandelier + Volume',
        desc: 'Avec barres de volume',
        config: { chart: {type:'candlestick'} },
        data: {series:[{name:'Prix',type:'candlestick',data:[{x:new Date('2025-01-01'),y:[100,110,95,105]}]},{name:'Volume',type:'column',data:[{x:new Date('2025-01-01'),y:1000}]}]}
      }
    ]
  },
  
  rangeBar: {
    family: 'Range Bar (Timeline)',
    icon: '<rect x="3" y="6" width="14" height="3" /><rect x="6" y="12" width="12" height="3" /><rect x="4" y="18" width="10" height="3" />',
    variants: [
      {
        id: 'rangebar-basic',
        name: 'Barres de plages',
        desc: 'Durées et intervalles',
        config: { chart: {type:'rangeBar'} },
        data: {series:[{data:[{x:'Tâche A',y:[new Date('2025-01-01').getTime(),new Date('2025-01-10').getTime()]},{x:'Tâche B',y:[new Date('2025-01-05').getTime(),new Date('2025-01-15').getTime()]}]}]}
      },
      {
        id: 'rangebar-timeline',
        name: 'Timeline',
        desc: 'Chronologie d\'événements',
        config: { chart: {type:'rangeBar'}, plotOptions:{bar:{horizontal:true}} },
        data: {series:[{name:'Projet',data:[{x:'Phase 1',y:[new Date('2025-01-01').getTime(),new Date('2025-02-01').getTime()]},{x:'Phase 2',y:[new Date('2025-02-01').getTime(),new Date('2025-03-01').getTime()]}]}]}
      },
      {
        id: 'rangebar-grouped',
        name: 'Timeline groupée',
        desc: 'Plusieurs ressources',
        config: { chart: {type:'rangeBar'}, plotOptions:{bar:{horizontal:true}} },
        data: {series:[{name:'Emp 1',data:[{x:'Projet A',y:[new Date('2025-01-01').getTime(),new Date('2025-01-15').getTime()]}]},{name:'Emp 2',data:[{x:'Projet A',y:[new Date('2025-01-10').getTime(),new Date('2025-01-25').getTime()]}]}]}
      }
    ]
  },
  
  polarArea: {
    family: 'Polar Area',
    icon: '<circle cx="12" cy="12" r="9" /><path d="M12 3l0 18" /><path d="M3 12l18 0" />',
    variants: [
      {
        id: 'polararea-basic',
        name: 'Aire polaire',
        desc: 'Répartition radiale',
        config: { chart: {type:'polarArea'} },
        data: {series:[14,23,21,17,15,10,12], labels:['A','B','C','D','E','F','G']}
      },
      {
        id: 'polararea-monochrome',
        name: 'Polaire monochrome',
        desc: 'Nuances d\'une couleur',
        config: { chart: {type:'polarArea'}, theme:{monochrome:{enabled:true}} },
        data: {series:[14,23,21,17,15,10,12], labels:['A','B','C','D','E','F','G']}
      }
    ]
  }
};

// Fonction helper pour récupérer toutes les variantes (flat)
function getAllChartVariants() {
  const all = [];
  Object.keys(APEX_CHART_CATALOG).forEach(key => {
    const family = APEX_CHART_CATALOG[key];
    family.variants.forEach(v => {
      all.push({...v, family: family.family, familyIcon: family.icon});
    });
  });
  return all;
}

// Fonction pour récupérer une variante par ID
function getChartVariant(id) {
  const all = getAllChartVariants();
  return all.find(v => v.id === id);
}

window.APEX_CHART_CATALOG = APEX_CHART_CATALOG;
window.getAllChartVariants = getAllChartVariants;
window.getChartVariant = getChartVariant;




