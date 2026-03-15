// Weather & Fit — main.js

let currentUnit = 'F';
let chart = null;

// ── Unit toggle ──────────────────────────────────────────────────────────────

function setUnit(unit) {
  currentUnit = unit;

  // Toggle button active state
  document.getElementById('btnF').classList.toggle('active', unit === 'F');
  document.getElementById('btnC').classList.toggle('active', unit === 'C');

  // Show/hide all val-f / val-c spans
  document.querySelectorAll('.val-f').forEach(el => {
    el.style.display = unit === 'F' ? 'inline' : 'none';
  });
  document.querySelectorAll('.val-c').forEach(el => {
    el.style.display = unit === 'C' ? 'inline' : 'none';
  });

  // Update all unit labels (°F / °C)
  document.querySelectorAll('.unit-label').forEach(el => {
    el.textContent = unit;
  });

  // Update chart if it exists
  if (chart) updateChart(unit);
}


// ── Hourly chart ─────────────────────────────────────────────────────────────

function initChart(labels, dataF, dataC) {
  const ctx = document.getElementById('hourlyChart');
  if (!ctx) return;

  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Temp °F',
        data: dataF,
        borderColor: '#0197F6',
        backgroundColor: 'rgba(1,151,246,0.12)',
        borderWidth: 2.5,
        pointBackgroundColor: '#0197F6',
        pointBorderColor: '#0F2E1A',
        pointBorderWidth: 2,
        pointRadius: 5,
        tension: 0.4,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15,46,26,0.95)',
          borderColor: 'rgba(201,255,226,0.15)',
          borderWidth: 1,
          titleColor: '#C9FFE2',
          bodyColor: '#D4E9ED',
          padding: 10,
          callbacks: {
            label: ctx => ` ${ctx.parsed.y}°${currentUnit}`
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(201,255,226,0.05)' },
          ticks: {
            color: 'rgba(212,233,237,0.5)',
            font: { family: "'Barlow Condensed'", size: 12, weight: '600' }
          }
        },
        y: {
          grid: { color: 'rgba(201,255,226,0.05)' },
          ticks: {
            color: 'rgba(212,233,237,0.5)',
            font: { family: "'Barlow Condensed'", size: 12, weight: '600' },
            callback: val => `${val}°`
          }
        }
      }
    }
  });

  // Store both datasets so we can switch units
  chart._dataF = dataF;
  chart._dataC = dataC;
}

function updateChart(unit) {
  if (!chart) return;
  chart.data.datasets[0].data = unit === 'F' ? chart._dataF : chart._dataC;
  chart.data.datasets[0].label = `Temp °${unit}`;
  chart.update();
}


// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {

  // Auto-focus search only on empty state
  const input   = document.querySelector('.search-input');
  const results = document.querySelector('.results');
  if (input && !results) input.focus();

  // Stagger outfit items
  document.querySelectorAll('.outfit-item').forEach((el, i) => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(-10px)';
    el.style.transition = `opacity .3s ease ${.25 + i * .06}s, transform .3s ease ${.25 + i * .06}s`;
    requestAnimationFrame(() => setTimeout(() => {
      el.style.opacity = '1';
      el.style.transform = 'translateX(0)';
    }, 30));
  });

});