let currentPage = 'dashboard';

function showPage(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const pageEl = document.getElementById('page-' + page);
    const navEl = document.querySelector(`[data-page="${page}"]`);

    if (pageEl) pageEl.classList.add('active');
    if (navEl) navEl.classList.add('active');

    currentPage = page;

    if (page === 'dashboard') loadSystemInfo();
}

async function loadSystemInfo() {
    try {
        const res = await fetch('/api/system-info');
        const data = await res.json();

        animateValue('cpuValue', data.cpu.percent, '%');
        animateValue('ramValue', data.memory.percent, '%');
        if (data.disk && data.disk.length) {
            animateValue('diskValue', data.disk[0].percent, '%');
            animateBar('diskBar', data.disk[0].percent);
        }
        animateBar('cpuBar', data.cpu.percent);
        animateBar('ramBar', data.memory.percent);

        if (data.os) {
            const badge = document.getElementById('osBadge');
            if (badge) badge.textContent = data.os.os_name + ' ' + data.os.release;
        }

        document.getElementById('netValue').textContent = formatBytes(data.network.bytes_recv) + ' recv';
    } catch (e) {
        console.error('System info failed:', e);
    }
}

function animateValue(id, target, suffix) {
    const el = document.getElementById(id);
    if (!el) return;
    let current = 0;
    const step = Math.max(1, Math.floor(target / 30));
    const interval = setInterval(() => {
        current += step;
        if (current >= target) {
            current = target;
            clearInterval(interval);
        }
        el.textContent = current + suffix;
    }, 20);
}

function animateBar(id, percent) {
    const el = document.getElementById(id);
    if (!el) return;
    setTimeout(() => { el.style.width = percent + '%'; }, 100);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

async function runOptimizer(category) {
    showLoading(`Optimizing ${category}...`);

    try {
        const res = await fetch(`/api/optimize/${category}`, { method: 'POST' });
        const data = await res.json();

        hideLoading();
        displayResults(category, data.results || data);
    } catch (e) {
        hideLoading();
        displayResults(category, [{ success: false, message: 'Error: ' + e.message }]);
    }
}

async function runAllOptimizations() {
    showLoading('Running all optimizers...');

    try {
        const res = await fetch('/api/optimize/all', { method: 'POST' });
        const data = await res.json();

        hideLoading();

        let allResults = [];
        Object.entries(data).forEach(([cat, results]) => {
            if (Array.isArray(results)) {
                results.forEach(r => {
                    allResults.push({ ...r, category: cat });
                });
            }
        });

        const container = document.getElementById('dashboardResultsList');
        const section = document.getElementById('dashboardResults');
        if (container && section) {
            section.style.display = 'block';
            container.innerHTML = allResults.map(r => {
                const cls = r.success ? 'result-ok' : 'result-fail';
                const icon = r.success ? '✓' : '✗';
                const prefix = r.category ? `[${r.category.toUpperCase()}] ` : '';
                return `<div class="result-item ${cls}">${icon} ${prefix}${r.message}</div>`;
            }).join('');
        }
    } catch (e) {
        hideLoading();
        displayResults('dashboard', [{ success: false, message: 'Error: ' + e.message }]);
    }
}

function displayResults(category, results) {
    const container = document.getElementById(category + 'ResultsList');
    const section = document.getElementById(category + 'Results');

    if (!container || !section) return;

    section.style.display = 'block';

    if (Array.isArray(results)) {
        container.innerHTML = results.map((r, i) => {
            const cls = r.success ? 'result-ok' : 'result-fail';
            const icon = r.success ? '✓' : '✗';
            return `<div class="result-item ${cls}" style="animation-delay:${i * 0.05}s">${icon} ${r.message}</div>`;
        }).join('');
    }
}

function showLoading(text) {
    const overlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    if (overlay) overlay.style.display = 'flex';
    if (loadingText) loadingText.textContent = text || 'Optimizing...';
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.style.display = 'none';
}

document.addEventListener('DOMContentLoaded', () => {
    loadSystemInfo();
    setInterval(loadSystemInfo, 5000);
});
