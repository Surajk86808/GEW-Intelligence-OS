const DATA_URL = "../phase_4_knowledge_memory/memory/inputs/transcripts/gew_dashboard_insights.json";

const chartRegistry = {};
const filterState = {
    searchTerm: "",
    centerSort: "enrollment_rate_pct",
};

const iconMap = {
    total_leads: "users",
    total_calls: "phone-call",
    enrollment_rate: "badge-dollar-sign",
    disqualification_rate: "shield-alert",
    top_performer: "crown",
    best_campaign: "rocket",
    top_centre: "map-pinned",
};

const kpiConfig = [
    {
        key: "total_leads",
        title: "Total Leads",
        icon: iconMap.total_leads,
        value: data => data.overall_funnel?.total_leads ?? 0,
        format: formatInteger,
        foot: data => `${formatInteger(data.report_metadata?.total_leads_analyzed ?? 0)} analyzed in this reporting window`,
    },
    {
        key: "total_calls",
        title: "Total Calls",
        icon: iconMap.total_calls,
        value: data => data.report_metadata?.total_calls_analyzed ?? 0,
        format: formatInteger,
        foot: data => `${data.report_metadata?.data_period ?? "Current dataset"} monitored across inbound operations`,
    },
    {
        key: "enrollment_rate",
        title: "Enrollment Rate",
        icon: iconMap.enrollment_rate,
        value: data => data.overall_funnel?.enrollment_rate_pct ?? 0,
        format: value => `${Number(value).toFixed(1)}%`,
        foot: () => "Primary conversion efficiency across all aggregated leads",
    },
    {
        key: "disqualification_rate",
        title: "Disqualification Rate",
        icon: iconMap.disqualification_rate,
        value: data => data.overall_funnel?.disqualification_rate_pct ?? 0,
        format: value => `${Number(value).toFixed(1)}%`,
        foot: () => "Critical signal for routing quality and audience fit",
    },
    {
        key: "top_performer",
        title: "Top Performer",
        icon: iconMap.top_performer,
        value: data => data.top_3_performers?.[0]?.name ?? "N/A",
        format: value => value,
        foot: data => `${formatInteger(data.top_3_performers?.[0]?.enrolled ?? 0)} enrollments with ${Number(data.top_3_performers?.[0]?.performance_score ?? 0).toFixed(2)} score`,
    },
    {
        key: "best_campaign",
        title: "Best Campaign",
        icon: iconMap.best_campaign,
        value: data => getBestCampaign(data)?.campaign ?? "N/A",
        format: shortenLabel,
        foot: data => `${Number(getBestCampaign(data)?.enrollment_rate_pct ?? 0).toFixed(1)}% enrollment rate`,
    },
    {
        key: "top_centre",
        title: "Top Centre",
        icon: iconMap.top_centre,
        value: data => getTopCentre(data)?.centre ?? "N/A",
        format: value => value,
        foot: data => `${Number(getTopCentre(data)?.enrollment_rate_pct ?? 0).toFixed(1)}% enrollment rate`,
    },
];

document.addEventListener("DOMContentLoaded", () => {
    bindFilters();
    loadDashboard();
});

function bindFilters() {
    const searchInput = document.getElementById("entity-search");
    const centerSort = document.getElementById("center-sort");

    searchInput?.addEventListener("input", event => {
        filterState.searchTerm = event.target.value.trim().toLowerCase();
        if (window.__dashboardData) {
            renderFilteredCollections(window.__dashboardData);
        }
    });

    centerSort?.addEventListener("change", event => {
        filterState.centerSort = event.target.value;
        if (window.__dashboardData) {
            renderCentreTable(window.__dashboardData);
        }
    });
}

async function loadDashboard() {
    const overlay = document.getElementById("loading-overlay");
    const status = document.getElementById("data-status");

    try {
        const response = await fetch(DATA_URL, { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status} while loading dashboard data`);
        }

        const data = await response.json();
        window.__dashboardData = data;

        renderDashboard(data);
        setStatus(status, "success", "Live intelligence feed loaded");
    } catch (error) {
        console.error("Dashboard load failed:", error);
        setStatus(status, "error", "Dashboard data unavailable");
        renderError(error);
    } finally {
        overlay?.classList.add("hidden");
    }
}

function renderDashboard(data) {
    renderReportMeta(data);
    renderExecutiveOverview(data);
    renderLeaderboard(data);
    renderFunnel(data);
    renderCampaignSection(data);
    renderCentreTable(data);
    renderRiskPanel(data);
    renderInsights(data);
    renderActions(data);
    renderCallAnalytics(data);

    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function renderReportMeta(data) {
    const metaGrid = document.getElementById("report-meta");
    const metadata = [
        ["Source", data.report_metadata?.source_file ?? "N/A"],
        ["Reporting Period", data.report_metadata?.data_period ?? "N/A"],
        ["Leads Analyzed", formatInteger(data.report_metadata?.total_leads_analyzed ?? 0)],
        ["Calls Analyzed", formatInteger(data.report_metadata?.total_calls_analyzed ?? 0)],
    ];

    metaGrid.innerHTML = metadata.map(([label, value]) => `
        <article class="meta-card">
            <span class="meta-label">${escapeHtml(label)}</span>
            <span class="meta-value">${escapeHtml(String(value))}</span>
        </article>
    `).join("");
}

function renderExecutiveOverview(data) {
    const grid = document.getElementById("kpi-grid");
    grid.innerHTML = kpiConfig.map((item, index) => {
        const rawValue = item.value(data);
        const animationTarget = typeof rawValue === "number" ? rawValue : 0;
        const formatted = item.format(rawValue);
        return `
            <article class="kpi-card reveal" style="animation-delay:${120 + index * 70}ms">
                <div class="kpi-head">
                    <div class="kpi-title">${escapeHtml(item.title)}</div>
                    <div class="kpi-icon"><i data-lucide="${item.icon}"></i></div>
                </div>
                <h4 class="kpi-value counter" data-target="${animationTarget}" data-format="${escapeHtml(item.key)}">${escapeHtml(String(formatted))}</h4>
                <p class="kpi-foot">${escapeHtml(item.foot(data))}</p>
            </article>
        `;
    }).join("");

    animateCounters(grid);
}

function renderLeaderboard(data) {
    const container = document.getElementById("leaderboard");
    const performers = applySearchFilter(data.top_3_performers ?? [], item => [item.name]);

    container.innerHTML = performers.map((performer, index) => `
        <article class="leader-card ${index === 0 ? "rank-1" : ""}">
            <div class="leader-top">
                <div>
                    <span class="leader-rank">Rank #${index + 1}</span>
                    <h4 class="leader-name">${escapeHtml(performer.name)}</h4>
                </div>
                <div class="leader-score">${Number(performer.performance_score ?? 0).toFixed(2)}</div>
            </div>
            <div class="leader-metrics">
                <div class="metric-chip">
                    <span class="label">Enrollments</span>
                    <span class="value">${formatInteger(performer.enrolled ?? 0)}</span>
                </div>
                <div class="metric-chip">
                    <span class="label">Walk-in Rate</span>
                    <span class="value">${Number(performer.walkin_rate_pct ?? 0).toFixed(1)}%</span>
                </div>
                <div class="metric-chip">
                    <span class="label">Disqualification Rate</span>
                    <span class="value">${Number(performer.disqualification_rate_pct ?? 0).toFixed(1)}%</span>
                </div>
                <div class="metric-chip">
                    <span class="label">Centres Covered</span>
                    <span class="value">${formatInteger(performer.centres_covered ?? 0)}</span>
                </div>
            </div>
        </article>
    `).join("") || emptyState("No performer records match the active search.");
}

function renderFunnel(data) {
    const board = document.getElementById("funnel-board");
    const funnel = [
        { label: "Total Leads", value: data.overall_funnel?.total_leads ?? 0 },
        { label: "Follow Up", value: data.overall_funnel?.follow_up_pipeline ?? 0 },
        { label: "Walk-in", value: data.overall_funnel?.walked_in ?? 0 },
        { label: "Enrolled", value: data.overall_funnel?.enrolled ?? 0 },
        { label: "Disqualified", value: data.overall_funnel?.disqualified ?? 0 },
    ];
    const max = Math.max(...funnel.map(item => item.value), 1);

    board.innerHTML = funnel.map((step, index) => `
        <div class="funnel-step">
            <div class="funnel-meta">
                <span>${escapeHtml(step.label)}</span>
                <strong>${formatInteger(step.value)}</strong>
            </div>
            <div class="funnel-bar">
                <div class="funnel-fill" style="width:${Math.max((step.value / max) * 100, 18)}%; animation-delay:${index * 80}ms">
                    ${formatInteger(step.value)}
                </div>
            </div>
        </div>
    `).join("");
}

function renderCampaignSection(data) {
    const campaigns = applySearchFilter(data.campaign_performance ?? [], item => [item.campaign]);
    renderCampaignHighlights(campaigns);
    renderCampaignList(campaigns);
    renderCampaignChart(campaigns);
}

function renderCampaignHighlights(campaigns) {
    const container = document.getElementById("campaign-highlights");
    const best = [...campaigns].sort((left, right) => (right.enrollment_rate_pct ?? 0) - (left.enrollment_rate_pct ?? 0))[0];
    const worst = [...campaigns].sort((left, right) => (right.disqualified ?? 0) - (left.disqualified ?? 0))[0];

    container.innerHTML = `
        <div class="panel-header">
            <div>
                <p class="eyebrow">Performance Signals</p>
                <h3>Best vs Worst</h3>
            </div>
        </div>
        <div class="campaign-highlight-grid">
            ${best ? `
                <article class="highlight-card good">
                    <div class="highlight-label">Best Campaign</div>
                    <div class="highlight-title">${escapeHtml(best.campaign)}</div>
                    <div class="highlight-metric">${Number(best.enrollment_rate_pct ?? 0).toFixed(1)}% enrollment rate</div>
                </article>
            ` : ""}
            ${worst ? `
                <article class="highlight-card bad">
                    <div class="highlight-label">Highest Disqualification Pressure</div>
                    <div class="highlight-title">${escapeHtml(worst.campaign)}</div>
                    <div class="highlight-metric">${formatInteger(worst.disqualified ?? 0)} disqualified leads</div>
                </article>
            ` : ""}
        </div>
    `;
}

function renderCampaignList(campaigns) {
    const container = document.getElementById("campaign-list");
    container.innerHTML = `
        <div class="panel-header">
            <div>
                <p class="eyebrow">Campaign Cards</p>
                <h3>ROI Comparison</h3>
            </div>
        </div>
        <div class="campaign-list">
            ${
                campaigns.map(campaign => `
                    <article class="campaign-item">
                        <div class="campaign-item-header">
                            <div class="campaign-name">${escapeHtml(campaign.campaign)}</div>
                            <span class="campaign-badge">${Number(campaign.enrollment_rate_pct ?? 0).toFixed(1)}%</span>
                        </div>
                        <div class="campaign-stats">
                            <span class="campaign-stat">Walk-in ${Number(campaign.walkin_rate_pct ?? 0).toFixed(1)}%</span>
                            <span class="campaign-stat">Disqualified ${formatInteger(campaign.disqualified ?? 0)}</span>
                            <span class="campaign-stat">Enrolled ${formatInteger(campaign.enrolled ?? 0)}</span>
                        </div>
                    </article>
                `).join("") || emptyState("No campaign records match the active search.")
            }
        </div>
    `;
}

function renderCentreTable(data) {
    const body = document.getElementById("centre-table-body");
    const centers = applySearchFilter(data.centre_performance ?? [], item => [item.centre]);
    const sorted = [...centers].sort((left, right) => {
        const sortKey = filterState.centerSort;
        return Number(right?.[sortKey] ?? 0) - Number(left?.[sortKey] ?? 0);
    });

    body.innerHTML = sorted.map((centre, index) => `
        <tr>
            <td>
                <span class="centre-badge">
                    <span class="badge-dot" style="background:${index < 3 ? "var(--accent-emerald)" : "var(--accent-cyan)"}"></span>
                    ${escapeHtml(centre.centre)}
                </span>
            </td>
            <td>${formatInteger(centre.total_leads ?? 0)}</td>
            <td>${formatInteger(centre.enrolled ?? 0)}</td>
            <td>${formatInteger(centre.walkin ?? 0)}</td>
            <td><span class="rate-pill ${getRateClass(centre.enrollment_rate_pct ?? 0)}">${Number(centre.enrollment_rate_pct ?? 0).toFixed(1)}%</span></td>
        </tr>
    `).join("") || `<tr><td colspan="5">${emptyState("No centre rows match the active search.")}</td></tr>`;
}

function renderRiskPanel(data) {
    const riskGrid = document.getElementById("risk-grid");
    const risks = [
        {
            title: "Online Preference Leakage",
            value: data.risk_signals?.online_preference_over_offline ?? 0,
            description: "Leads seeking online products are entering the offline sales path.",
            severity: "high",
            tone: "warning",
        },
        {
            title: "Support Query Misrouting",
            value: data.risk_signals?.support_queries_misrouted ?? 0,
            description: "Inbound sales resources are absorbing support traffic instead of monetizable leads.",
            severity: "critical",
            tone: "critical",
        },
        {
            title: "Wrong Audience Leads",
            value: data.risk_signals?.wrong_channel_leads ?? 0,
            description: "IVR acquisition is attracting out-of-scope or low-fit audiences.",
            severity: "critical",
            tone: "critical",
        },
        {
            title: "Price Objections",
            value: data.risk_signals?.price_objections ?? 0,
            description: "Explicit pricing resistance detected in the business intelligence layer.",
            severity: "high",
            tone: "warning",
        },
    ];

    riskGrid.innerHTML = risks.map(risk => `
        <article class="risk-card ${risk.tone === "warning" ? "warning" : ""}">
            <div class="risk-top">
                <div>
                    <div class="risk-title">${escapeHtml(risk.title)}</div>
                    <div class="risk-value">${formatInteger(risk.value)}</div>
                </div>
                <span class="severity-badge ${risk.severity}">${escapeHtml(risk.severity)}</span>
            </div>
            <p>${escapeHtml(risk.description)}</p>
        </article>
    `).join("");
}

function renderInsights(data) {
    const container = document.getElementById("insight-stream");
    const insights = data.business_insights ?? [];

    container.innerHTML = insights.map(insight => {
        const tone = classifyInsightTone(insight);
        return `
            <article class="insight-card">
                <div class="insight-head">
                    <div class="insight-icon"><i data-lucide="${tone.icon}"></i></div>
                    <span class="insight-tone ${tone.className}">${escapeHtml(tone.label)}</span>
                </div>
                <div class="insight-body">${escapeHtml(insight)}</div>
            </article>
        `;
    }).join("") || emptyState("No business insights found in the current JSON payload.");
}

function renderActions(data) {
    const container = document.getElementById("action-stream");
    const actions = data.recommended_actions ?? [];

    container.innerHTML = actions.map(action => {
        const priority = classifyActionPriority(action);
        return `
            <article class="action-card">
                <div class="action-head">
                    <div class="action-check"><i data-lucide="badge-check"></i></div>
                    <span class="action-priority ${priority.className}">${escapeHtml(priority.label)}</span>
                </div>
                <div class="action-body">${escapeHtml(action)}</div>
            </article>
        `;
    }).join("") || emptyState("No recommended actions found in the current JSON payload.");
}

function renderCallAnalytics(data) {
    renderDurationChart(data.call_duration_distribution ?? {});
    renderCounselorVolumeChart(data.june_inbound_volume_by_counselor ?? {});
    renderDailyTrendChart(data.call_volume_by_day ?? {});
}

function renderDurationChart(distribution) {
    const labels = Object.keys(distribution).map(formatDurationBucket);
    const values = Object.values(distribution);
    mountChart("duration-chart", "doughnut", {
        labels,
        datasets: [{
            data: values,
            backgroundColor: ["#38bdf8", "#60a5fa", "#a78bfa", "#34d399", "#fbbf24"],
            borderColor: "rgba(7, 12, 22, 0.9)",
            borderWidth: 3,
            hoverOffset: 8,
        }],
    }, {
        plugins: {
            legend: { labels: { color: "#cbd5e1" } },
        },
    });
}

function renderCounselorVolumeChart(volumeByCounselor) {
    mountChart("counselor-volume-chart", "bar", {
        labels: Object.keys(volumeByCounselor),
        datasets: [{
            label: "Inbound Calls",
            data: Object.values(volumeByCounselor),
            borderRadius: 14,
            backgroundColor: ["rgba(56, 189, 248, 0.85)", "rgba(96, 165, 250, 0.8)", "rgba(167, 139, 250, 0.82)"],
        }],
    }, axisOptions(false));
}

function renderDailyTrendChart(volumeByDay) {
    mountChart("daily-trend-chart", "line", {
        labels: Object.keys(volumeByDay),
        datasets: [{
            label: "Daily Inbound Calls",
            data: Object.values(volumeByDay),
            tension: 0.35,
            borderColor: "#38bdf8",
            backgroundColor: "rgba(56, 189, 248, 0.18)",
            fill: true,
            pointRadius: 4,
            pointHoverRadius: 6,
        }],
    }, axisOptions(true));
}

function renderCampaignChart(campaigns) {
    mountChart("campaign-chart", "bar", {
        labels: campaigns.map(item => shortenLabel(item.campaign, 18)),
        datasets: [
            {
                label: "Enrollment Rate %",
                data: campaigns.map(item => item.enrollment_rate_pct ?? 0),
                backgroundColor: "rgba(52, 211, 153, 0.82)",
                borderRadius: 10,
            },
            {
                label: "Walk-in Rate %",
                data: campaigns.map(item => item.walkin_rate_pct ?? 0),
                backgroundColor: "rgba(56, 189, 248, 0.78)",
                borderRadius: 10,
            },
        ],
    }, {
        ...axisOptions(false),
        plugins: {
            legend: {
                labels: { color: "#cbd5e1" },
            },
        },
    });
}

function renderFilteredCollections(data) {
    renderLeaderboard(data);
    renderCampaignSection(data);
    renderCentreTable(data);
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function animateCounters(root) {
    const counters = root.querySelectorAll(".counter");
    counters.forEach(counter => {
        const target = Number(counter.dataset.target || 0);
        const formatKey = counter.dataset.format;
        if (!Number.isFinite(target) || target === 0) {
            return;
        }

        const duration = 1000;
        const startedAt = performance.now();
        const formatter = resolveCounterFormatter(formatKey);

        const tick = now => {
            const progress = Math.min((now - startedAt) / duration, 1);
            const current = target * easeOutCubic(progress);
            counter.textContent = formatter(current, progress === 1, target);
            if (progress < 1) {
                requestAnimationFrame(tick);
            }
        };

        requestAnimationFrame(tick);
    });
}

function resolveCounterFormatter(formatKey) {
    if (formatKey === "enrollment_rate" || formatKey === "disqualification_rate") {
        return value => `${value.toFixed(1)}%`;
    }
    if (formatKey === "best_campaign" || formatKey === "top_performer" || formatKey === "top_centre") {
        return (_value, done, target) => done ? String(target) : "";
    }
    return value => formatInteger(Math.round(value));
}

function mountChart(canvasId, type, data, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) {
        return;
    }

    if (chartRegistry[canvasId]) {
        chartRegistry[canvasId].destroy();
    }

    chartRegistry[canvasId] = new Chart(canvas, {
        type,
        data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 900,
                easing: "easeOutQuart",
            },
            scales: type === "doughnut" ? {} : {
                x: {
                    grid: { color: "rgba(148, 163, 184, 0.08)" },
                    ticks: { color: "#94a3b8" },
                },
                y: {
                    grid: { color: "rgba(148, 163, 184, 0.08)" },
                    ticks: { color: "#94a3b8" },
                },
            },
            plugins: {
                legend: { labels: { color: "#cbd5e1" } },
                tooltip: {
                    backgroundColor: "rgba(7, 12, 22, 0.96)",
                    titleColor: "#f8fafc",
                    bodyColor: "#cbd5e1",
                    borderColor: "rgba(56, 189, 248, 0.18)",
                    borderWidth: 1,
                    padding: 12,
                },
            },
            ...options,
        },
    });
}

function axisOptions(showXAxisBorder) {
    return {
        scales: {
            x: {
                grid: { display: false },
                border: { display: showXAxisBorder },
                ticks: { color: "#94a3b8" },
            },
            y: {
                grid: { color: "rgba(148, 163, 184, 0.08)" },
                ticks: { color: "#94a3b8" },
                beginAtZero: true,
            },
        },
    };
}

function renderError(error) {
    const template = document.getElementById("error-template");
    const fragment = template.content.cloneNode(true);
    const messageNode = fragment.querySelector("#error-message");
    if (messageNode) {
        messageNode.textContent = `${error.message}. Confirm the JSON file exists and that your local server can access paths outside frontend/.`;
    }
    document.querySelector(".dashboard-main")?.replaceWith(fragment);
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function setStatus(node, status, text) {
    if (!node) {
        return;
    }
    node.classList.remove("success", "error");
    if (status) {
        node.classList.add(status);
    }
    const label = node.querySelector("span:last-child");
    if (label) {
        label.textContent = text;
    }
}

function applySearchFilter(items, accessor) {
    if (!filterState.searchTerm) {
        return items;
    }

    return items.filter(item => accessor(item).some(value =>
        String(value ?? "").toLowerCase().includes(filterState.searchTerm)
    ));
}

function getBestCampaign(data) {
    return [...(data.campaign_performance ?? [])].sort((left, right) => (right.enrollment_rate_pct ?? 0) - (left.enrollment_rate_pct ?? 0))[0];
}

function getTopCentre(data) {
    return [...(data.centre_performance ?? [])].sort((left, right) => (right.enrollment_rate_pct ?? 0) - (left.enrollment_rate_pct ?? 0))[0];
}

function classifyInsightTone(text) {
    const normalized = text.toUpperCase();
    if (normalized.includes("CRITICAL") || normalized.includes("MISROUTED") || normalized.includes("WRONG CHANNEL")) {
        return { label: "Critical", className: "critical", icon: "siren" };
    }
    if (normalized.includes("BEST") || normalized.includes("TOP PERFORMER") || normalized.includes("TOP CENTRE")) {
        return { label: "Positive", className: "positive", icon: "sparkles" };
    }
    return { label: "Opportunity", className: "opportunity", icon: "lightbulb" };
}

function classifyActionPriority(text) {
    const normalized = text.toUpperCase();
    if (normalized.includes("URGENT")) {
        return { label: "Critical", className: "critical" };
    }
    return { label: "High Priority", className: "high" };
}

function getRateClass(rate) {
    if (Number(rate) >= 15) {
        return "top";
    }
    if (Number(rate) >= 5) {
        return "mid";
    }
    return "low";
}

function easeOutCubic(value) {
    return 1 - Math.pow(1 - value, 3);
}

function formatInteger(value) {
    return Number(value || 0).toLocaleString("en-IN");
}

function formatDurationBucket(key) {
    return key
        .replace("under_", "Under ")
        .replace("over_", "Over ")
        .replace("_", "-")
        .replace("min", " min");
}

function shortenLabel(value, maxLength = 28) {
    const text = String(value ?? "");
    return text.length > maxLength ? `${text.slice(0, maxLength - 3)}...` : text;
}

function emptyState(text) {
    return `<div class="meta-card">${escapeHtml(text)}</div>`;
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}
