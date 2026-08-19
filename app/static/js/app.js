// AI Operations Copilot - Modern Vanilla Frontend Controller

const PRESETS = {
    database: {
        description: "Postgres Database connection saturation and lock timeouts causing API 500 spikes",
        logs: `[2026-08-19 14:02:11] WARN [pool-executor-4] Slow query: SELECT * FROM orders WHERE status='PENDING' duration=4210ms
[2026-08-19 14:02:15] ERROR [http-nio-8080-exec-12] Database connection timeout: Connection pool exhausted (active=100/100)
[2026-08-19 14:02:18] ERROR [http-nio-8080-exec-19] Deadlock detected in database transaction #9021; query canceled
[2026-08-19 14:02:22] ERROR [http-nio-8080-exec-24] 500 Internal Server Error - Failed to acquire database connection
[2026-08-19 14:02:28] ERROR [http-nio-8080-exec-31] 500 Internal Server Error - Transaction rollback failed`,
        metrics: JSON.stringify({
            cpu_usage: [45.2, 58.1, 91.4, 98.2],
            db_connections: [45, 80, 100, 100],
            latency_ms: [140, 220, 2800, 4100],
            error_rate: [0.001, 0.005, 0.18, 0.35]
        }, null, 2)
    },
    memory: {
        description: "Java heap space OutOfMemoryError and OOM killer termination on payment-worker-pod",
        logs: `[2026-08-19 14:15:02] WARN [GC-Monitor] High memory usage detected: 89% of max heap utilized
[2026-08-19 14:15:10] ERROR [batch-worker-2] java.lang.OutOfMemoryError: Java heap space
[2026-08-19 14:15:12] ERROR [batch-worker-3] OutOfMemoryError: GC overhead limit exceeded
[2026-08-19 14:15:15] CRITICAL [systemd] kernel: [19401.12] oom-killer: killed process 4123 (java) total-vm:8.4GB
[2026-08-19 14:15:20] ERROR [gateway] 502 Bad Gateway - upstream worker unreachable`,
        metrics: JSON.stringify({
            memory_usage: [65.0, 78.5, 94.2, 99.8],
            cpu_usage: [30.0, 45.0, 88.0, 92.0],
            latency_ms: [90, 110, 1500, 3200]
        }, null, 2)
    },
    network: {
        description: "Upstream payment gateway timeout causing connection drops and request backlog",
        logs: `[2026-08-19 14:30:01] WARN [checkout-service] Slow response from upstream gateway: https://pay.partner.com (1800ms)
[2026-08-19 14:30:05] ERROR [checkout-service] Connection timed out: ETIMEDOUT to 52.84.12.91:443
[2026-08-19 14:30:08] ERROR [checkout-service] 504 Gateway Timeout on /v2/charge
[2026-08-19 14:30:12] ERROR [checkout-service] Upstream request timeout after 10000ms`,
        metrics: JSON.stringify({
            latency_ms: [210, 520, 3800, 5200],
            network_drop_rate: [0.001, 0.01, 0.08, 0.15],
            error_rate: [0.00, 0.02, 0.22, 0.40]
        }, null, 2)
    }
};

let currentJobId = null;
let pollInterval = null;

// Navigation Tab Management
function showView(viewName) {
    document.getElementById('view-dashboard').style.display = viewName === 'dashboard' ? 'block' : 'none';
    document.getElementById('view-new').style.display = viewName === 'new' ? 'block' : 'none';
    document.getElementById('view-details').style.display = viewName === 'details' ? 'block' : 'none';

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === viewName);
    });

    if (viewName === 'dashboard') {
        loadIncidents();
        if (pollInterval) clearInterval(pollInterval);
    }
}

// Quick Preset Loader
function loadPreset(key) {
    const p = PRESETS[key];
    if (!p) return;
    document.getElementById('input-desc').value = p.description;
    document.getElementById('input-logs').value = p.logs;
    document.getElementById('input-metrics').value = p.metrics;
}

// Fetch Incidents List
async function loadIncidents() {
    const listBody = document.getElementById('incidents-tbody');
    try {
        const res = await fetch('/api/v1/incidents/');
        const data = await res.json();
        
        if (!data || data.length === 0) {
            listBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-dim); padding: 3rem;">No incidents analyzed yet. Click "Analyze New Incident" to start.</td></tr>`;
            return;
        }

        listBody.innerHTML = data.map(inc => {
            const statusClass = inc.status === 'completed' ? 'status-completed' : inc.status === 'failed' ? 'status-failed' : 'status-processing';
            const shortId = inc.job_id.substring(0, 8);
            const desc = inc.description || (inc.result ? inc.result.root_cause.cause : 'Incident Analysis');
            const step = inc.step || inc.status;
            const date = new Date(inc.created_at || Date.now()).toLocaleTimeString();

            return `
                <tr class="incident-row" onclick="viewIncidentDetails('${inc.job_id}')">
                    <td style="font-family: var(--font-mono); color: #60a5fa; font-weight: 600;">#${shortId}</td>
                    <td style="font-weight: 500;">${escapeHtml(desc)}</td>
                    <td><span class="status-badge ${statusClass}">${inc.status}</span></td>
                    <td style="font-size: 0.85rem; color: var(--text-muted); font-family: var(--font-mono);">${step}</td>
                    <td style="color: var(--text-dim); font-size: 0.85rem;">${date}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.error("Failed to load incidents:", e);
        listBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--danger); padding: 2rem;">Failed to connect to API server.</td></tr>`;
    }
}

// Submit Incident Form
async function submitIncident(event) {
    event.preventDefault();
    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.innerHTML = 'Submitting & Analyzing...';

    const desc = document.getElementById('input-desc').value.trim();
    const logsRaw = document.getElementById('input-logs').value.trim();
    const metricsRaw = document.getElementById('input-metrics').value.trim();

    let metricsObj = {};
    if (metricsRaw) {
        try {
            metricsObj = JSON.parse(metricsRaw);
        } catch (e) {
            alert("Invalid JSON format in Metrics field. Please provide valid JSON.");
            btn.disabled = false;
            btn.innerHTML = '🚀 Run Incident Analysis';
            return;
        }
    }

    const logLines = logsRaw.split('\n').filter(l => l.trim().length > 0);

    try {
        const res = await fetch('/api/v1/incidents/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                description: desc,
                logs: logLines,
                metrics: metricsObj
            })
        });

        if (!res.ok) throw new Error('Submission failed');
        const data = await res.json();
        
        btn.disabled = false;
        btn.innerHTML = '🚀 Run Incident Analysis';
        viewIncidentDetails(data.job_id);

    } catch (e) {
        alert("Error creating incident: " + e.message);
        btn.disabled = false;
        btn.innerHTML = '🚀 Run Incident Analysis';
    }
}

// View Incident Details & Live Polling
function viewIncidentDetails(jobId) {
    currentJobId = jobId;
    showView('details');
    document.getElementById('details-job-id').innerText = '#' + jobId.substring(0, 8);

    if (pollInterval) clearInterval(pollInterval);
    
    fetchIncidentStatus(jobId);
    pollInterval = setInterval(() => {
        fetchIncidentStatus(jobId);
    }, 800);
}

async function fetchIncidentStatus(jobId) {
    try {
        const res = await fetch(`/api/v1/incidents/${jobId}`);
        if (!res.ok) return;
        const data = await res.json();

        updateDetailsUI(data);

        if (data.status === 'completed' || data.status === 'failed') {
            if (pollInterval) clearInterval(pollInterval);
        }
    } catch (e) {
        console.error("Polling error:", e);
    }
}

function updateDetailsUI(data) {
    // Update Badge
    const badge = document.getElementById('details-status-badge');
    badge.className = `status-badge ${data.status === 'completed' ? 'status-completed' : data.status === 'failed' ? 'status-failed' : 'status-processing'}`;
    badge.innerText = data.status.toUpperCase();

    // Update Stepper
    const stepOrder = ['analyzing_logs', 'analyzing_metrics', 'inferring_root_cause', 'generating_recommendations', 'finalizing_report'];
    const currentIdx = stepOrder.indexOf(data.step);

    stepOrder.forEach((stepKey, idx) => {
        const el = document.getElementById(`step-${stepKey}`);
        if (!el) return;

        if (data.status === 'completed') {
            el.className = 'step-item done';
        } else if (data.status === 'failed') {
            el.className = idx <= currentIdx ? 'step-item done' : 'step-item';
        } else {
            if (idx < currentIdx) el.className = 'step-item done';
            else if (idx === currentIdx) el.className = 'step-item active';
            else el.className = 'step-item';
        }
    });

    // Update Report / Debug
    const reportBox = document.getElementById('report-content-box');
    const debugBox = document.getElementById('debug-content-box');

    debugBox.innerText = JSON.stringify(data, null, 2);

    if (data.result && data.result.summary) {
        if (window.marked) {
            reportBox.innerHTML = window.marked.parse(data.result.summary);
        } else {
            reportBox.innerText = data.result.summary;
        }
    } else {
        reportBox.innerHTML = `<div style="text-align:center; padding: 4rem; color: var(--text-dim);"><div class="spinner"></div><p style="margin-top: 1rem;">C++ and Python agents are analyzing telemetry...</p></div>`;
    }
}

function switchDetailTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    document.getElementById('tab-report').style.display = tabName === 'report' ? 'block' : 'none';
    document.getElementById('tab-debug').style.display = tabName === 'debug' ? 'block' : 'none';
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    loadPreset('database');
    loadIncidents();
});
