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

// ===================== EXPORT MODAL =====================
function setupExportModal() {
    const modal = document.getElementById('exportModal');
    const openBtn = document.getElementById('openExportBtn');
    const closeBtn = document.getElementById('closeExportBtn');
    const doBtn = document.getElementById('doExportBtn');
    const startInput = document.getElementById('exportStart');
    const endInput = document.getElementById('exportEnd');

    // Set default dates (Last 7 days to Today)
    const today = new Date();
    const lastWeek = new Date(today);
    lastWeek.setDate(today.getDate() - 7);

    startInput.value = lastWeek.toISOString().split('T')[0];
    endInput.value = today.toISOString().split('T')[0];

    openBtn.addEventListener('click', () => modal.classList.add('show'));
    closeBtn.addEventListener('click', () => modal.classList.remove('show'));
    
    // Close on outside click
    window.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('show');
    });

    doBtn.addEventListener('click', () => {
        const start = startInput.value;
        const end = endInput.value;
        const type = document.getElementById('exportType').value;
        
        if (!start || !end) {
            alert('Vui lòng chọn đầy đủ ngày bắt đầu và kết thúc!');
            return;
        }
        if (start > end) {
            alert('Ngày bắt đầu không được lớn hơn ngày kết thúc!');
            return;
        }
        
        // Trigger download via window.location
        if (type === 'ai') {
            window.location.href = `${API_BASE}/api/export_predictions?start=${start}&end=${end}`;
        } else {
            window.location.href = `${API_BASE}/api/export?start=${start}&end=${end}`;
        }
        modal.classList.remove('show');
    });
}

// ===================== DELETE MODAL =====================
function setupDeleteModal() {
    const modal = document.getElementById('deleteModal');
    const openBtn = document.getElementById('openDeleteBtn');
    const closeBtn = document.getElementById('closeDeleteBtn');
    const doBtn = document.getElementById('doDeleteBtn');

    if (!modal || !openBtn || !closeBtn || !doBtn) return;

    openBtn.addEventListener('click', () => modal.classList.add('show'));
    closeBtn.addEventListener('click', () => modal.classList.remove('show'));
    
    // Close on outside click
    window.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('show');
    });

    doBtn.addEventListener('click', async () => {
        const hours = document.getElementById('deleteRange').value;
        const confirmMsg = hours == 0 
            ? "BẠN CÓ CHẮC CHẮN MUỐN XÓA TẤT CẢ DỮ LIỆU? Hành động này không thể hoàn tác!" 
            : `Bạn có chắc chắn muốn xóa dữ liệu của ${hours} giờ qua không?`;

        if (confirm(confirmMsg)) {
            doBtn.textContent = "Đang xóa...";
            doBtn.disabled = true;
            try {
                const response = await fetch(`${API_BASE}/api/delete`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ hours: parseInt(hours) })
                });
                const data = await response.json();
                
                if (data.status === 'ok') {
                    alert(data.message);
                    modal.classList.remove('show');
                    // Refresh all data
                    refreshAll();
                    fetchPrediction();
                } else {
                    alert("Lỗi: " + data.message);
                }
            } catch (error) {
                console.error("Lỗi khi xóa:", error);
                alert("Đã xảy ra lỗi khi kết nối với máy chủ.");
            } finally {
                doBtn.textContent = "Xác Nhận Xóa";
                doBtn.disabled = false;
            }
        }
    });
}

// ===================== AI PREDICTION =====================
const WEATHER_ICONS = {
    'normal': '🌤️',
    'sunny': '☀️',
    'rainy': '🌧️',
};

async function fetchPrediction() {
    try {
        const res = await fetch(`${API_BASE}/api/predict`);
        const data = await res.json();
        updatePredictionUI(data);
    } catch (e) {
        console.error('Fetch prediction error:', e);
    }
}

function updatePredictionUI(data) {
    const badge = document.getElementById('aiBadge');
    const placeholder = document.getElementById('aiPlaceholder');
    const currentWeather = document.getElementById('currentWeather');
    const predGrid = document.getElementById('predictionGrid');
    const aiMethod = document.getElementById('aiMethod');

    if (!data || data.status !== 'ok') {
        // AI not ready
        badge.textContent = data?.status === 'not_ready' ? 'Chưa sẵn sàng' :
                           data?.status === 'insufficient_data' ? 'Thiếu dữ liệu' : 'Đang tải...';
        placeholder.style.display = '';
        currentWeather.style.display = 'none';
        predGrid.style.display = 'none';
        return;
    }

    // AI ready — show predictions
    badge.textContent = 'Hoạt động';
    badge.style.background = 'rgba(110,231,183,0.15)';
    badge.style.color = '#6ee7b7';
    badge.style.borderColor = 'rgba(110,231,183,0.3)';
    placeholder.style.display = 'none';
    currentWeather.style.display = 'flex';
    predGrid.style.display = 'grid';

    if (data.model_info?.method) {
        aiMethod.textContent = data.model_info.method;
    }

    // Current weather
    const cw = data.current_weather || 'normal';
    document.getElementById('currentWeatherIcon').textContent = WEATHER_ICONS[cw] || '🌤️';
    document.getElementById('currentWeatherText').textContent = data.current_weather_vi || cw;

    // 30 min prediction
    const p30 = data.predictions?.['30min'];
    if (p30) {
        document.getElementById('weatherIcon30').textContent = WEATHER_ICONS[p30.weather] || '🌤️';
        document.getElementById('weatherText30').textContent = p30.weather_vi || p30.weather;
        document.getElementById('predictTime30').textContent = p30.time || '--:--';
        document.getElementById('pred30-pm25').textContent = Math.round(p30.pm25);
        document.getElementById('pred30-temp').textContent = p30.temperature?.toFixed(1);
        document.getElementById('pred30-hum').textContent = p30.humidity?.toFixed(1);
        document.getElementById('pred30-pres').textContent = p30.pressure?.toFixed(1);
        document.getElementById('pred30-uv').textContent = p30.uv?.toFixed(2);
    }

    // 60 min prediction
    const p60 = data.predictions?.['60min'];
    if (p60) {
        document.getElementById('weatherIcon60').textContent = WEATHER_ICONS[p60.weather] || '🌤️';
        document.getElementById('weatherText60').textContent = p60.weather_vi || p60.weather;
        document.getElementById('predictTime60').textContent = p60.time || '--:--';
        document.getElementById('pred60-pm25').textContent = Math.round(p60.pm25);
        document.getElementById('pred60-temp').textContent = p60.temperature?.toFixed(1);
        document.getElementById('pred60-hum').textContent = p60.humidity?.toFixed(1);
        document.getElementById('pred60-pres').textContent = p60.pressure?.toFixed(1);
        document.getElementById('pred60-uv').textContent = p60.uv?.toFixed(2);
    }
}

// ===================== POLLING =====================
async function refreshAll() {
    await Promise.all([fetchLatest(), fetchHistory(), fetchStats()]);
}

// ===================== INIT =====================
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    setupTimeButtons();
    setupExportModal();
    setupDeleteModal();
    updateClock();
    setInterval(updateClock, 1000);

    // Initial fetch
    refreshAll();
    fetchPrediction();

    // Poll sensor data every 30s
    setInterval(refreshAll, POLL_INTERVAL);

    // Poll AI prediction every 60s
    setInterval(fetchPrediction, 60000);
});
