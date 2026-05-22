// charts.js — Chart.js visualisasi untuk BaldGuard
// Exposed via window.BaldGuardCharts so analyze.html can call .init(withGenetic)

(function () {
  'use strict';

  let radarInst = null;
  let barInst   = null;
  let snpInst   = null;

  function destroy(inst) {
    if (inst && typeof inst.destroy === 'function') inst.destroy();
  }

  // Render gauge marker on the gradient track
  function renderGauge(score, color) {
    const marker = document.getElementById('gaugeMarker');
    if (marker) {
      marker.style.left   = Math.min(Math.max(score, 0), 100) + '%';
      marker.style.borderTopColor = color;
    }
    const scoreEl = document.getElementById('riskScore');
    if (scoreEl) {
      scoreEl.textContent = (typeof score === 'number' ? score.toFixed(1) : score);
      scoreEl.style.color = color;
    }
  }

  // Radar: 4 components
  function renderRadar(scores) {
    destroy(radarInst);
    const ctx = document.getElementById('radarChart');
    if (!ctx || typeof Chart === 'undefined') return;

    const hasGenetic = scores.genetic_score > 0;
    const labels = hasGenetic
      ? ['Genetik', 'Klinis', 'Keluarga', 'Gaya Hidup']
      : ['Klinis', 'Keluarga', 'Gaya Hidup'];
    const data = hasGenetic
      ? [scores.genetic_score, scores.clinical_score, scores.family_score, scores.lifestyle_score]
      : [scores.clinical_score, scores.family_score, scores.lifestyle_score];

    radarInst = new Chart(ctx, {
      type: 'radar',
      data: {
        labels,
        datasets: [{
          label: 'Skor Risiko',
          data,
          fill: true,
          backgroundColor: 'rgba(231,76,60,0.15)',
          borderColor: '#e74c3c',
          borderWidth: 2,
          pointBackgroundColor: '#e74c3c',
          pointRadius: 5,
          pointHoverRadius: 7,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        scales: {
          r: {
            min: 0,
            max: 100,
            ticks: { stepSize: 25, font: { size: 10 }, backdropColor: 'transparent' },
            grid: { color: 'rgba(0,0,0,0.08)' },
            pointLabels: { font: { size: 13, weight: '600' }, color: '#34495e' },
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => `${ctx.raw.toFixed(1)} / 100` } }
        }
      }
    });
    ctx._chart = radarInst;
  }

  // Bar: component contribution breakdown
  function renderBar(contributions) {
    destroy(barInst);
    const ctx = document.getElementById('barChart');
    if (!ctx || typeof Chart === 'undefined') return;

    const labels = Object.keys(contributions);
    const data   = Object.values(contributions);
    const palette = ['#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#e74c3c'];
    const colors  = labels.map((_, i) => palette[i % palette.length]);

    barInst = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Kontribusi Skor',
          data,
          backgroundColor: colors,
          borderRadius: 8,
          borderSkipped: false,
        }]
      },
      options: {
        responsive: true,
        indexAxis: 'y',
        scales: {
          x: { beginAtZero: true, max: 55, title: { display: true, text: 'Poin kontribusi' } }
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => `Kontribusi: ${ctx.raw.toFixed(1)} poin` } }
        }
      }
    });
    ctx._chart = barInst;
  }

  // SNP bar chart (horizontal, risk vs normal coloring)
  function renderSNP(snpResults) {
    if (!snpResults || !snpResults.length) return;
    const card = document.getElementById('snpHeatmapCard');
    if (card) card.style.display = 'block';

    destroy(snpInst);
    const ctx = document.getElementById('snpHeatmap');
    if (!ctx || typeof Chart === 'undefined') return;

    const known  = snpResults.filter(s => s.status !== 'UNKNOWN');
    if (!known.length) return;

    const labels = known.map(s => s.rs_id);
    const data   = known.map(s => s.odds_ratio);
    const colors = known.map(s => s.status === 'RISK' ? '#e74c3c' : '#2ecc71');

    snpInst = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Odds Ratio',
          data,
          backgroundColor: colors,
          borderRadius: 5,
        }]
      },
      options: {
        responsive: true,
        indexAxis: 'y',
        scales: {
          x: { beginAtZero: true, title: { display: true, text: 'Odds Ratio' } }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => {
                const s = known[ctx.dataIndex];
                return [
                  `Status: ${s.status === 'RISK' ? '⚠ Alel Risiko' : '✓ Normal'}`,
                  `OR: ${s.odds_ratio}×`,
                  `Alel: ${s.user_allele || '?'}`,
                ];
              }
            }
          }
        }
      }
    });
    ctx._chart = snpInst;
  }

  // Called from analyze.html's confirmAndShowResults flow
  function init(withGenetic) {
    const result = window._baldguardResult;
    if (!result) {
      // No real result yet — charts were already drawn by analyze.html's inline fallback
      return;
    }

    const scores = result.scores;
    renderGauge(scores.hybrid_score, result.risk_color || '#e74c3c');
    renderRadar(scores);
    renderBar(result.component_contributions);
    if (withGenetic && result.genetic_details && result.genetic_details.snp_results) {
      renderSNP(result.genetic_details.snp_results);
    }
  }

  // Expose globally
  window.BaldGuardCharts = { init, renderGauge, renderRadar, renderBar, renderSNP };
})();
