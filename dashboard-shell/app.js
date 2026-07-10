// app.js — DARPAN Dashboard Shell Logic

// 1. Dynamic Hostname Resolution for Browser-Facing Integrations
const HOSTNAME = window.location.hostname;
const FLASK_API_BASE = `http://${HOSTNAME}:5000`;
const GRAFANA_BASE = `http://${HOSTNAME}:3000`;
const TOPOLOGY_BASE = `http://${HOSTNAME}:8000`;

// 2. Grafana Dashboard UID and Panel IDs Configuration
// Edit these values in one place to match your actual Grafana setup
const GRAFANA_DASHBOARD_UID = "68c20f8d-78cc-4366-8e7e-ddeeea51b77b";

const GRAFANA_PANELS = {
    // RAN Section  (IDs extracted from 5G_SMO_Dashboard_Provisioned.json)
    "ran-1": 3,   // Active gNBs            (stat)
    "ran-2": 11,  // RAN Connection Status   (timeseries — rrc_success_rate + handover)
    "ran-3": 10,  // Fault Summary           (table — packet_loss, bler, latency)

    // Core Section
    "core-1": 2,  // Active Subscribers      (stat)
    "core-2": 4,  // Active Sessions         (stat)
    "core-3": 15, // Core Cluster Stats      (state-timeline — subscribers + sessions)

    // Traffic & UE Section
    "traffic-1": 9,  // Uplink & Downlink Traffic  (timeseries)
    "traffic-2": 8,  // Traffic Utilization         (gauge)
    "traffic-3": 14  // Top UE Throughput           (table)
};

// State Variables
let lastTelemeteryTimestamp = null;
let freshnessIntervalId = null;

// DOM Elements
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');
const navItems = document.querySelectorAll('.nav-item');
const contentSections = document.querySelectorAll('.content-section');
const backendStatusDot = document.getElementById('backend-status-dot');
const backendStatusText = document.getElementById('backend-status-text');
const freshnessText = document.getElementById('freshness-text');
const alertBar = document.getElementById('alert-bar');
const alertMessage = document.getElementById('alert-message');
const anomalyContainer = document.getElementById('anomaly-cards-container');
const injectorStatusMsg = document.getElementById('injector-status-msg');

// 3. COLLAPSIBLE SIDEBAR
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
});

// 4. SIDEBAR NAVIGATION CONTROLS (With Lazy Loading of Iframes)
navItems.forEach(item => {
    item.addEventListener('click', () => {
        const targetSection = item.getAttribute('data-section');
        
        // Update nav items
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
        
        // Update visible section
        contentSections.forEach(sec => sec.classList.remove('active'));
        const activeSection = document.getElementById(`section-${targetSection}`);
        if (activeSection) {
            activeSection.classList.add('active');
            // Lazy load iframes inside the activated section
            loadSectionIframes(targetSection);
        }
    });
});

// Lazy loader for iframe panels
function loadSectionIframes(sectionId) {
    if (sectionId === 'overview') return;
    
    if (sectionId === 'topology') {
        const iframe = document.getElementById('iframe-topology');
        const skeleton = document.getElementById('skeleton-topology');
        if (iframe && iframe.src === '') {
            iframe.src = TOPOLOGY_BASE;
            setupIframeLoadingListener(iframe, skeleton);
        }
        return;
    }
    
    if (sectionId === 'predictions') {
        // Predictions section uses custom API fetching, no iframes
        fetchPredictionsData();
        return;
    }
    
    // Grafana embeds for RAN, Core, Traffic
    const iframeIds = {
        'ran': ['ran-1', 'ran-2', 'ran-3'],
        'core': ['core-1', 'core-2', 'core-3'],
        'traffic': ['traffic-1', 'traffic-2', 'traffic-3']
    };
    
    const ids = iframeIds[sectionId] || [];
    ids.forEach((panelKey, index) => {
        const iframeNum = index + 1;
        const iframe = document.getElementById(`iframe-${sectionId}-${iframeNum}`);
        const skeleton = document.getElementById(`skeleton-${sectionId}-${iframeNum}`);
        
        if (iframe && iframe.src === '') {
            const panelId = GRAFANA_PANELS[panelKey];
            // Format for Grafana single panel embeds (d-solo)
            const embedUrl = `${GRAFANA_BASE}/d-solo/${GRAFANA_DASHBOARD_UID}/5g-smo-dashboard?orgId=1&panelId=${panelId}&theme=dark&refresh=5s`;
            
            iframe.src = embedUrl;
            setupIframeLoadingListener(iframe, skeleton);
        }
    });
}

// Hides loading skeleton when iframe finishes loading
function setupIframeLoadingListener(iframe, skeleton) {
    iframe.onload = () => {
        if (skeleton) {
            skeleton.style.opacity = '0';
            setTimeout(() => {
                skeleton.style.display = 'none';
            }, 500); // Fade out transition matching CSS
        }
        iframe.classList.add('loaded');
    };
}

// 5. DATA FRESHNESS POLLING (poll /api/kpis every 5s)
function pollTelemetryFreshness() {
    fetch(`${FLASK_API_BASE}/api/kpis`)
        .then(response => {
            if (!response.ok) throw new Error('Backend responding with error');
            return response.json();
        })
        .then(data => {
            // Update backend status dot to Online
            backendStatusDot.className = "status-dot online";
            backendStatusText.textContent = "Backend: Connected";
            
            if (data && data.timestamp) {
                lastTelemeteryTimestamp = data.timestamp;
                updateFreshnessDisplay();
            }
        })
        .catch(err => {
            // Graceful degradation when unreachable
            backendStatusDot.className = "status-dot offline";
            backendStatusText.textContent = "Backend: Unreachable";
            freshnessText.textContent = "No live telemetry feed";
            lastTelemeteryTimestamp = null;
        });
}

function updateFreshnessDisplay() {
    if (!lastTelemeteryTimestamp) return;
    
    const now = Date.now();
    const diffSeconds = Math.max(0, Math.floor((now - lastTelemeteryTimestamp) / 1000));
    
    if (diffSeconds < 2) {
        freshnessText.textContent = "Last update: Just now";
    } else {
        freshnessText.textContent = `Last update: ${diffSeconds}s ago`;
    }
}

// 6. ANOMALY DETECTION POLLING (poll /api/predict/anomaly every 10s)
function pollAnomalyPredictions() {
    fetch(`${FLASK_API_BASE}/api/predict/anomaly`)
        .then(response => {
            if (!response.ok) throw new Error('Anomaly endpoint unreachable');
            return response.json();
        })
        .then(data => {
            if (data.status === 'warming_up') {
                alertBar.className = "alert-bar normal";
                alertMessage.textContent = `AI engine warming up (collected ${data.points}/${data.needed} ticks)...`;
                return;
            }
            
            // Check if there are any active anomalies
            const anomalies = [];
            for (const [kpi, stats] of Object.entries(data)) {
                if (stats.is_anomaly) {
                    anomalies.push({
                        kpi: kpi.replace(/_/g, ' '),
                        zScore: stats.z_score,
                        value: stats.value
                    });
                }
            }
            
            if (anomalies.length > 0) {
                // Anomaly state
                alertBar.className = "alert-bar anomaly";
                const anomalyList = anomalies.map(a => `${a.kpi} (Z: ${a.zScore > 0 ? '+' : ''}${a.zScore})`).join(', ');
                alertMessage.textContent = `⚠️ ANOMALY DETECTED: ${anomalyList}. Check Predictions or RAN/Core tabs.`;
            } else {
                // Normal state
                alertBar.className = "alert-bar normal";
                alertMessage.textContent = "💚 All systems normal. Closed-loop AI models monitoring active.";
            }
            
            // If currently on predictions tab, update container
            const predictionsSec = document.getElementById('section-predictions');
            if (predictionsSec && predictionsSec.classList.contains('active')) {
                renderAnomalyCards(data);
            }
        })
        .catch(err => {
            // Graceful degradation when unreachable
            alertBar.className = "alert-bar normal";
            alertMessage.textContent = "⚠️ Prediction Engine: Unreachable. Telemetry models suspended.";
            
            const predictionsSec = document.getElementById('section-predictions');
            if (predictionsSec && predictionsSec.classList.contains('active')) {
                anomalyContainer.innerHTML = `<div class="loading-placeholder">Prediction models unavailable. Flask API offline.</div>`;
            }
        });
}

// Fetch helper specifically for Predictions section tab
function fetchPredictionsData() {
    anomalyContainer.innerHTML = `<div class="loading-placeholder">Evaluating historical vectors...</div>`;
    fetch(`${FLASK_API_BASE}/api/predict/anomaly`)
        .then(response => response.json())
        .then(data => {
            renderAnomalyCards(data);
            document.getElementById('update-predictions').textContent = 'Updated: ' + new Date().toLocaleTimeString();
        })
        .catch(() => {
            anomalyContainer.innerHTML = `<div class="loading-placeholder">Unable to fetch prediction metadata from Flask server.</div>`;
            document.getElementById('update-predictions').textContent = 'Waiting for backend...';
        });
}

// Render dynamic anomaly metric cards
function renderAnomalyCards(data) {
    if (data.status === 'warming_up') {
        anomalyContainer.innerHTML = `
            <div class="loading-placeholder">
                Model training in progress. Telemetry data count: ${data.points}/${data.needed} ticks.
            </div>`;
        return;
    }
    
    let html = '';
    for (const [kpi, stats] of Object.entries(data)) {
        const isAnomaly = stats.is_anomaly;
        const displayName = kpi.replace(/_/g, ' ');
        const cardClass = isAnomaly ? 'anomaly-card danger' : 'anomaly-card';
        const badgeClass = isAnomaly ? 'anomaly-badge anomaly' : 'anomaly-badge normal';
        const badgeText = isAnomaly ? 'ANOMALY' : 'NORMAL';
        
        html += `
            <div class="${cardClass}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h4>${displayName}</h4>
                    <span class="${badgeClass}">${badgeText}</span>
                </div>
                <div class="stat-row" style="margin-top: 10px;">
                    <span class="stat-label">Value:</span>
                    <span class="stat-val">${stats.value}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">EWMA Baseline:</span>
                    <span class="stat-val">${stats.baseline}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Z-Score:</span>
                    <span class="stat-val" style="color: ${isAnomaly ? 'var(--red)' : 'var(--cyan)'};">
                        ${stats.z_score > 0 ? '+' : ''}${stats.z_score}
                    </span>
                </div>
            </div>
        `;
    }
    anomalyContainer.innerHTML = html;
}

// 7. DEMO ANOMALY INJECTION CONTROL
const injectButtons = document.querySelectorAll('.inject-btn');
injectButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const nodeType = btn.getAttribute('data-node');
        let port;
        let nodeLabel;
        
        if (nodeType === 'ru') {
            port = 6001;
            nodeLabel = "O-RU Simulator";
        } else if (nodeType === 'gnb') {
            port = 6002;
            nodeLabel = "gNB Simulator";
        } else if (nodeType === 'core') {
            port = 6003;
            nodeLabel = "5G Core Simulator";
        }
        
        const injectUrl = `http://${HOSTNAME}:${port}/api/inject_anomaly?seconds=30`;
        
        injectorStatusMsg.style.color = 'var(--cyan)';
        injectorStatusMsg.textContent = `Injecting anomaly trigger to ${nodeLabel}...`;
        
        fetch(injectUrl, { method: 'POST' })
            .then(res => {
                if (!res.ok) throw new Error('Injection HTTP error');
                return res.json();
            })
            .then(data => {
                injectorStatusMsg.style.color = 'var(--green)';
                injectorStatusMsg.textContent = `✅ Outage injected into ${nodeLabel} for ${data.duration_s}s! Closed-loop anomaly should flag shortly.`;
                // Trigger immediate telemetry refresh
                setTimeout(pollTelemetryFreshness, 1000);
                setTimeout(pollAnomalyPredictions, 2000);
            })
            .catch(err => {
                injectorStatusMsg.style.color = 'var(--red)';
                injectorStatusMsg.textContent = `❌ Failed to inject anomaly. Check if simulator is running on port ${port}.`;
            });
    });
});

// Initialization
window.addEventListener('load', () => {
    // Initial fetches
    pollTelemetryFreshness();
    pollAnomalyPredictions();
    
    // Set polling timers
    setInterval(pollTelemetryFreshness, 5000);
    setInterval(pollAnomalyPredictions, 10000);
    
    // Secondary freshness ticking every second for sub-second smooth counters
    freshnessIntervalId = setInterval(updateFreshnessDisplay, 1000);
});
