/**
 * AlgoTrader — Chart.js Wrappers
 * P&L equity curve + monthly bar chart helpers.
 */

const CHART_COLORS = {
  algo1: '#388bfd',
  algo2: '#e3b341',
  algo3: '#3fb950',
  combined: '#bc8cff',
};

const CHART_DEFAULTS = {
  font:     { family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", size: 11 },
  color:    '#7d8590',
  gridColor: 'rgba(48,54,61,0.6)',
};

Chart.defaults.color            = CHART_DEFAULTS.color;
Chart.defaults.font.family      = CHART_DEFAULTS.font.family;
Chart.defaults.font.size        = CHART_DEFAULTS.font.size;

/**
 * Render equity curve (line chart, multiple algos)
 * @param {string} canvasId
 * @param {Object} datasets  { algo_id: [{date, cumulative_pnl}] }
 * @param {Object} algoNames { algo_id: "Name" }
 */
function renderEquityCurve(canvasId, datasets, algoNames) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  if (canvas._chartInstance) canvas._chartInstance.destroy();

  // Build union of all dates
  const allDates = new Set();
  for (const points of Object.values(datasets)) {
    points.forEach(p => allDates.add(p.date));
  }
  const labels = Array.from(allDates).sort();

  const chartDatasets = Object.entries(datasets).map(([algoId, points]) => {
    const pnlMap = {};
    points.forEach(p => pnlMap[p.date] = p.cumulative_pnl);
    return {
      label:       algoNames[algoId] || algoId,
      data:        labels.map(d => pnlMap[d] ?? null),
      borderColor: CHART_COLORS[algoId] || '#888',
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      tension: 0.2,
      spanGaps: true,
    };
  });

  canvas._chartInstance = new Chart(canvas, {
    type: 'line',
    data: { labels, datasets: chartDatasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          display: chartDatasets.length > 1,
          position: 'top',
          labels: { boxWidth: 12, padding: 12 },
        },
        tooltip: {
          callbacks: {
            label: ctx => {
              const v = ctx.parsed.y;
              if (v === null) return '';
              const sign = v >= 0 ? '+' : '';
              return ` ${ctx.dataset.label}: ${sign}₹${v.toLocaleString('en-IN')}`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: CHART_DEFAULTS.gridColor },
          ticks: { maxTicksLimit: 8, maxRotation: 0 },
        },
        y: {
          grid: { color: CHART_DEFAULTS.gridColor },
          ticks: {
            callback: v => {
              if (Math.abs(v) >= 100000) return (v/100000).toFixed(1) + 'L';
              if (Math.abs(v) >= 1000)   return (v/1000).toFixed(0) + 'K';
              return v;
            },
          },
        },
      },
    },
  });
  return canvas._chartInstance;
}

/**
 * Render monthly bar chart (single algo)
 * @param {string} canvasId
 * @param {Object} monthlyData  { "YYYY-MM": pnl }
 * @param {string} color
 */
function renderMonthlyBar(canvasId, monthlyData, color) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  if (canvas._chartInstance) canvas._chartInstance.destroy();

  const months = Object.keys(monthlyData).sort();
  const values = months.map(m => monthlyData[m]);

  canvas._chartInstance = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: months.map(m => {
        const [y, mo] = m.split('-');
        return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][parseInt(mo)-1];
      }),
      datasets: [{
        label: 'Monthly P&L',
        data: values,
        backgroundColor: values.map(v => v >= 0
          ? 'rgba(46,160,67,0.5)' : 'rgba(218,54,51,0.5)'),
        borderColor: values.map(v => v >= 0 ? '#3fb950' : '#f85149'),
        borderWidth: 1,
        borderRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const v = ctx.parsed.y;
              const sign = v >= 0 ? '+' : '';
              return ` ${sign}₹${v.toLocaleString('en-IN')}`;
            },
          },
        },
      },
      scales: {
        x: { grid: { color: CHART_DEFAULTS.gridColor } },
        y: {
          grid: { color: CHART_DEFAULTS.gridColor },
          ticks: {
            callback: v => {
              if (Math.abs(v) >= 1000) return (v/1000).toFixed(0) + 'K';
              return v;
            },
          },
        },
      },
    },
  });
  return canvas._chartInstance;
}

/**
 * Format P&L for display
 */
function fmtPnl(v, showSign = true) {
  if (v === null || v === undefined) return '₹0';
  const abs = Math.abs(v);
  const sign = showSign ? (v >= 0 ? '+' : '-') : (v < 0 ? '-' : '');
  if (abs >= 100000) return `${sign}₹${(abs/100000).toFixed(2)}L`;
  if (abs >= 1000)   return `${sign}₹${(abs/1000).toFixed(1)}K`;
  return `${sign}₹${Math.round(abs).toLocaleString('en-IN')}`;
}

function fmtPct(v) {
  if (v === null || v === undefined) return '0%';
  const sign = v >= 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}%`;
}

function pnlClass(v) {
  if (v > 0) return 'text-green';
  if (v < 0) return 'text-red';
  return 'text-muted';
}
