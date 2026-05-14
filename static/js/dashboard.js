/**
 * dashboard.js - Air Quality Monitoring Dashboard
 * Handles data fetching, chart rendering, and UI updates.
 */

// ===================== CONFIG =====================
const API_BASE = window.location.origin;
const POLL_INTERVAL = 30000; // 30 seconds
let currentHours = 24;

// ===================== CHARTS =====================
const chartConfigs = {
    'pm25':  { color: '#fbbf24', label: 'PM2.5', borderColor: '#fbbf24', bgColor: 'rgba(251,191,36,0.08)' },
    'temp':  { color: '#f87171', label: 'Nhiệt độ', borderColor: '#f87171', bgColor: 'rgba(248,113,113,0.08)' },
    'hum':   { color: '#22d3ee', label: 'Độ ẩm', borderColor: '#22d3ee', bgColor: 'rgba(34,211,238,0.08)' },
    'pres':  { color: '#a78bfa', label: 'Áp suất', borderColor: '#a78bfa', bgColor: 'rgba(167,139,250,0.08)' },
    'uv':    { color: '#f59e0b', label: 'UV', borderColor: '#f59e0b', bgColor: 'rgba(245,158,11,0.08)' },
};

const charts = {};

// Chart.js global defaults
Chart.defaults.color = '#64748b';
Chart.defaults.borderColor = '#2a2f45';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 11;

function createChart(canvasId, key) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const cfg = chartConfigs[key];
    charts[key] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: cfg.label,
                data: [],
                borderColor: cfg.borderColor,
                backgroundColor: cfg.bgColor,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointHoverBackgroundColor: cfg.color,
                pointHoverBorderColor: '#fff',
                fill: true,
                tension: 0.35,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1e2235',
                    titleColor: '#e2e8f0',
                    bodyColor: '#94a3b8',
                    borderColor: '#2a2f45',
                    borderWidth: 1,
                    padding: 10,
                    displayColors: false,
                    callbacks: {
                        title: function(items) {
                            if (!items.length) return '';
                            const d = new Date(items[0].parsed.x);
                            return d.toLocaleString('vi-VN');
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        tooltipFormat: 'HH:mm:ss dd/MM',
                        displayFormats: {
                            minute: 'HH:mm',
                            hour: 'HH:mm',
                            day: 'dd/MM'
                        }
                    },
                    grid: {
                        display: false,
                    },
                    ticks: {
                        maxTicksLimit: 8,
                        font: { size: 10 },
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(42, 47, 69, 0.5)',
                    },
                    ticks: {
                        font: { size: 10 },
                        maxTicksLimit: 5,
                    }
                }
            },
            animation: {
                duration: 500,
                easing: 'easeOutQuart',
            }
        }
    });
}

function initCharts() {
    createChart('chart-pm25', 'pm25');
    createChart('chart-temp', 'temp');
    createChart('chart-hum', 'hum');
    createChart('chart-pres', 'pres');
    createChart('chart-uv', 'uv');
}

// ===================== DATA FETCHING =====================

async function fetchLatest() {
    try {
        const res = await fetch(`${API_BASE}/api/latest`);
        const data = await res.json();
        if (data && data.pm25 !== undefined) {
            updateCards(data);
            setConnectionStatus(true);
        }
    } catch (e) {
        console.error('Fetch latest error:', e);
        setConnectionStatus(false);
    }
}

async function fetchHistory() {
    try {
        const res = await fetch(`${API_BASE}/api/history?hours=${currentHours}`);
        const data = await res.json();
        if (Array.isArray(data)) {
            updateCharts(data);
            document.getElementById('dataCount').textContent = data.length;
        }
    } catch (e) {
        console.error('Fetch history error:', e);
    }
}

async function fetchStats() {
    try {
        const res = await fetch(`${API_BASE}/api/stats?hours=${currentHours}`);
        const data = await res.json();
        if (data) {
            updateStats(data);
        }
    } catch (e) {
        console.error('Fetch stats error:', e);
    }
}

// ===================== UI UPDATES =====================

function updateCards(d) {
    updateValue('val-pm25', Math.round(d.pm25));
    updateValue('val-temp', d.temperature?.toFixed(1));
    updateValue('val-hum', d.humidity?.toFixed(1));
    updateValue('val-pres', d.pressure?.toFixed(1));
    updateValue('val-uv', d.uv?.toFixed(2));

    // PM2.5 quality indicator
    const pm = d.pm25;
    const qEl = document.getElementById('quality-pm25');
    if (pm <= 50) {
        qEl.textContent = 'Tốt';
        qEl.className = 'card-quality quality-good';
    } else if (pm <= 100) {
        qEl.textContent = 'Trung bình';
        qEl.className = 'card-quality quality-moderate';
    } else if (pm <= 150) {
        qEl.textContent = 'Kém';
        qEl.className = 'card-quality quality-bad';
    } else {
        qEl.textContent = 'Nguy hại';
        qEl.className = 'card-quality quality-danger';
    }

    // UV quality
    const uv = d.uv;
    const uvEl = document.getElementById('quality-uv');
    if (uv <= 2) {
        uvEl.textContent = 'Thấp';
        uvEl.className = 'card-quality quality-good';
    } else if (uv <= 5) {
        uvEl.textContent = 'Trung bình';
        uvEl.className = 'card-quality quality-moderate';
    } else if (uv <= 7) {
        uvEl.textContent = 'Cao';
        uvEl.className = 'card-quality quality-bad';
    } else {
        uvEl.textContent = 'Rất cao';
        uvEl.className = 'card-quality quality-danger';
    }

    // Update timestamp
    const now = new Date();
    document.getElementById('lastUpdate').textContent = now.toLocaleTimeString('vi-VN');
}

function updateValue(id, val) {
    const el = document.getElementById(id);
    if (!el) return;
    if (el.textContent !== String(val)) {
        el.textContent = val;
        el.classList.remove('flash');
        void el.offsetWidth; // reflow
        el.classList.add('flash');
    }
}

function updateStats(s) {
    setText('min-temp', s.min_temp?.toFixed(1) ?? '--');
    setText('max-temp', s.max_temp?.toFixed(1) ?? '--');
    setText('min-hum', s.min_hum?.toFixed(1) ?? '--');
    setText('max-hum', s.max_hum?.toFixed(1) ?? '--');
    setText('min-pres', s.min_pres?.toFixed(0) ?? '--');
    setText('max-pres', s.max_pres?.toFixed(0) ?? '--');
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function updateCharts(data) {
    const keyMap = {
        'pm25': 'pm25',
        'temp': 'temperature',
        'hum': 'humidity',
        'pres': 'pressure',
        'uv': 'uv'
    };

    for (const [chartKey, dataKey] of Object.entries(keyMap)) {
        if (!charts[chartKey]) continue;

        const timestamps = data.map(d => new Date(d.timestamp));
        const values = data.map(d => d[dataKey]);

        charts[chartKey].data.labels = timestamps;
        charts[chartKey].data.datasets[0].data = values;
        charts[chartKey].update('none');
    }
}

function setConnectionStatus(connected) {
    const badge = document.getElementById('connectionStatus');
    const text = badge.querySelector('.status-text');
    if (connected) {
        badge.className = 'status-badge connected';
        text.textContent = 'Đang hoạt động';
    } else {
        badge.className = 'status-badge disconnected';
        text.textContent = 'Mất kết nối';
    }
}

// ===================== CLOCK =====================
function updateClock() {
    const now = new Date();
    document.getElementById('headerTime').textContent = now.toLocaleTimeString('vi-VN');
}

// ===================== TIME RANGE BUTTONS =====================
function setupTimeButtons() {
    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentHours = parseInt(btn.dataset.hours);
            fetchHistory();
            fetchStats();
        });
    });
}

// ===================== POLLING =====================
async function refreshAll() {
    await Promise.all([fetchLatest(), fetchHistory(), fetchStats()]);
}

// ===================== INIT =====================
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    setupTimeButtons();
    updateClock();
    setInterval(updateClock, 1000);

    // Initial fetch
    refreshAll();

    // Poll every 30s
    setInterval(refreshAll, POLL_INTERVAL);
});
