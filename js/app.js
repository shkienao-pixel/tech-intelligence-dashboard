/**
 * Tech Intelligence Dashboard — Frontend Logic
 * Connects to the FastAPI backend (localhost:8000) when available.
 * Falls back to static demo mode when backend is offline.
 */

const API = "http://localhost:8000/api";
const html = document.documentElement;

// ── Theme ─────────────────────────────────────────────────────────────────────
function applyTheme(dark) {
  html.classList.toggle("dark", dark);
}
function toggleTheme() {
  const dark = !html.classList.contains("dark");
  applyTheme(dark);
  localStorage.setItem("theme", dark ? "dark" : "light");
  updateThemeIcons();
}
function updateThemeIcons() {
  const dark = html.classList.contains("dark");
  document.querySelectorAll("[data-theme-icon]").forEach(el => {
    el.textContent = dark ? "light_mode" : "dark_mode";
  });
}
;(function initTheme() {
  const saved = localStorage.getItem("theme");
  const sys   = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(saved === "dark" || (!saved && sys));
})();

// ── Animated Counters ─────────────────────────────────────────────────────────
function animateCounter(el, target, duration = 1400) {
  const end = parseInt(String(target).replace(/,/g, ""), 10);
  if (isNaN(end)) return;
  const t0 = performance.now();
  const step = now => {
    const p = Math.min((now - t0) / duration, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(end * eased).toLocaleString();
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
function initCounters() {
  document.querySelectorAll("[data-counter]").forEach(el => {
    const target = el.dataset.counter;
    const obs = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) { animateCounter(el, target); obs.disconnect(); }
    }, { threshold: 0.5 });
    obs.observe(el);
  });
}

// ── Progress Bars ─────────────────────────────────────────────────────────────
function initProgressBars() {
  document.querySelectorAll("[data-progress]").forEach(bar => {
    setTimeout(() => { bar.style.width = bar.dataset.progress + "%"; }, 300);
  });
}

// ── Trend Tag Filter ──────────────────────────────────────────────────────────
function initTrendTags() {
  document.querySelectorAll("[data-trend]").forEach(tag => {
    tag.addEventListener("click", () => {
      const active = tag.classList.contains("border-primary");
      document.querySelectorAll("[data-trend]").forEach(t => {
        t.classList.remove("border-primary", "bg-primary/10");
      });
      if (!active) tag.classList.add("border-primary", "bg-primary/10");
    });
  });
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = "info") {
  const colors = { info: "bg-primary text-white", success: "bg-green-500 text-white", error: "bg-red-500 text-white" };
  const icons  = { info: "info", success: "check_circle", error: "error" };
  const el = document.createElement("div");
  el.className = `fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl shadow-xl text-sm font-bold
    flex items-center gap-2 transition-all duration-300 translate-y-10 opacity-0 ${colors[type] || colors.info}`;
  el.innerHTML = `<span class="material-symbols-outlined text-sm">${icons[type] || "info"}</span>${msg}`;
  document.body.appendChild(el);
  requestAnimationFrame(() => el.classList.remove("translate-y-10", "opacity-0"));
  setTimeout(() => { el.classList.add("translate-y-10", "opacity-0"); setTimeout(() => el.remove(), 300); }, 4000);
}

// ── API helpers ───────────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const method = (opts.method || "GET").toUpperCase();
  // Only set Content-Type for requests that carry a body
  const needsContentType = opts.body !== undefined && opts.body !== null;
  const headers = needsContentType
    ? { "Content-Type": "application/json", ...(opts.headers || {}) }
    : { ...(opts.headers || {}) };
  const res = await fetch(API + path, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status} ${res.statusText}` }));
    throw new Error(err.detail || `HTTP ${res.status} ${res.statusText}`);
  }
  // 204 No Content has no body
  if (res.status === 204) return null;
  return res.json();
}

// ── Status Banner ─────────────────────────────────────────────────────────────
let backendOnline = false;
let _dashboardData = null;

async function checkBackendStatus() {
  const banner = document.getElementById("backend-banner");
  const dot    = document.getElementById("status-dot");
  const label  = document.getElementById("status-label");
  const genBtn = document.getElementById("generate-btn");

  try {
    const s = await apiFetch("/status");
    backendOnline = true;

    if (banner) banner.classList.add("hidden");
    if (dot)    { dot.classList.remove("bg-slate-400"); dot.classList.add("bg-green-500"); }
    if (label)  label.textContent = s.ready ? "Status: Ready" : "Status: Setup Required";
    if (genBtn) genBtn.disabled = !s.ready;

    if (!s.x_configured || !s.claude_configured) {
      showToast("⚙️ Fill in server/.env with your credentials to enable report generation.", "info");
    }

  } catch {
    backendOnline = false;
    if (banner)  banner.classList.remove("hidden");
    if (dot)     { dot.classList.remove("bg-green-500"); dot.classList.add("bg-slate-400"); }
    if (label)   label.textContent = "Status: Offline (Demo Mode)";
    if (genBtn)  genBtn.disabled = true;
  }
}

// ── Dashboard Data ────────────────────────────────────────────────────────────
async function loadDashboard() {
  if (!backendOnline) return;
  try {
    const data = await apiFetch("/dashboard");
    _dashboardData = data;
    renderDashboard(data);
  } catch (e) {
    if (e.message.includes("No report yet")) {
      _dashboardData = null;
      renderReportsTable([]);
    }
  }
}

function renderDashboard(data) {
  const { stats, trending_topics, recent_reports } = data;

  // Stats
  setCounter("stat-influencers", stats.influencers);
  setCounter("stat-posts",       stats.posts);
  setCounter("stat-trends",      stats.trends);
  if (stats.last_updated) {
    const el = document.getElementById("dashboard-subtitle");
    if (el) {
      const d = new Date(stats.last_updated);
      el.textContent = `${d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })} · Live X signal analysis · ${stats.influencers} influencers monitored`;
    }
  }

  // Trending topics
  if (trending_topics?.length) renderTrendingTopics(trending_topics);

  // Reports table
  renderReportsTable(recent_reports || []);
}

function setCounter(id, value) {
  const el = document.getElementById(id);
  if (el) animateCounter(el, value);
}

function renderTrendingTopics(topics) {
  const wrap = document.getElementById("trending-topics");
  if (!wrap) return;
  wrap.innerHTML = topics.map(t => `
    <button data-trend class="px-3 py-1.5 bg-slate-100 dark:bg-slate-700 rounded-lg text-sm font-bold
      border border-slate-200 dark:border-slate-600 hover:border-primary transition-all cursor-pointer flex items-center gap-1.5">
      ${t.tag}
      <span class="text-[10px] font-black ${t.is_new ? 'text-primary' : parseFloat(t.change) < 0 ? 'text-slate-400' : 'text-green-500'}">${t.change}</span>
    </button>`).join("");
  initTrendTags();

  // Velocity bars
  const barsWrap = document.getElementById("velocity-bars");
  if (!barsWrap) return;
  const top3 = topics.slice(0, 3);
  barsWrap.innerHTML = top3.map(t => `
    <div>
      <div class="flex justify-between mb-1.5">
        <span class="text-xs font-bold text-primary uppercase">${t.tag}</span>
        <span class="text-xs font-bold text-primary">${t.velocity}%</span>
      </div>
      <div class="h-2 rounded-full bg-primary/10 overflow-hidden">
        <div class="progress-bar h-full rounded-full bg-primary" data-progress="${t.velocity}"></div>
      </div>
    </div>`).join("");
  initProgressBars();
}

const SCORE_STYLES = {
  "HIGH INTEL": "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 border-green-200 dark:border-green-800",
  "CRITICAL":   "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800",
  "STABLE":     "bg-slate-100 dark:bg-slate-700 text-slate-500 border-slate-200 dark:border-slate-600",
};

function renderReportsTable(reports) {
  const tbody = document.getElementById("reports-tbody");
  if (!tbody) return;
  if (!reports.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-10 text-center text-slate-400 text-sm" data-i18n="reports.waiting">
      ${typeof t === "function" ? t("reports.waiting") : "No reports yet — click Generate Daily Report to fetch live data."}</td></tr>`;
    return;
  }
  tbody.innerHTML = reports.map(r => {
    const scoreClass = SCORE_STYLES[r.score] || SCORE_STYLES["STABLE"];
    return `
    <tr class="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors" id="report-row-${r.id}">
      <td class="px-6 py-5">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined text-slate-400">picture_as_pdf</span>
          <div>
            <p class="text-sm font-bold text-slate-900 dark:text-white">${escHtml(_pick(r, "title"))}</p>
            <p class="text-[10px] text-slate-500">${escHtml(_pick(r, "subtitle") || "")}</p>
          </div>
        </div>
      </td>
      <td class="px-6 py-5 text-sm font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">${r.date}</td>
      <td class="px-6 py-5">
        <div class="flex justify-center">
          <span class="px-2 py-1 text-[10px] font-black rounded border ${scoreClass}">${r.score}</span>
        </div>
      </td>
      <td class="px-6 py-5 text-right">
        <div class="flex justify-end gap-2">
          <button onclick="viewReport('${r.id}')" class="p-2 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-lg transition-colors" title="View">
            <span class="material-symbols-outlined text-slate-500 text-lg">visibility</span>
          </button>
          <button onclick="downloadReport('${r.id}')" class="p-2 hover:bg-primary/10 text-primary rounded-lg transition-colors" title="Download">
            <span class="material-symbols-outlined text-lg">download</span>
          </button>
          <button onclick="deleteReport('${r.id}')" class="p-2 hover:bg-red-100 dark:hover:bg-red-900/30 text-red-400 hover:text-red-600 rounded-lg transition-colors" title="Delete">
            <span class="material-symbols-outlined text-lg">delete</span>
          </button>
        </div>
      </td>
    </tr>`;
  }).join("");
}

async function deleteReport(id) {
  const msg = typeof t === "function"
    ? t("reports.delete_confirm")
    : "Delete this report? This action cannot be undone.";
  if (!confirm(msg)) return;

  try {
    const url = `${API}/report/${id}`;
    console.log("[deleteReport] DELETE", url);
    const res = await fetch(url, { method: "DELETE" });
    console.log("[deleteReport] response status:", res.status);
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({ detail: `HTTP ${res.status} ${res.statusText}` }));
      console.error("[deleteReport] error body:", errBody);
      throw new Error(errBody.detail || `HTTP ${res.status}`);
    }
    // Fade out the row for smooth UX
    const row = document.getElementById(`report-row-${id}`);
    if (row) {
      row.style.transition = "opacity 0.3s";
      row.style.opacity = "0";
      await new Promise(r => setTimeout(r, 300));
    }
    showToast(typeof t === "function" ? t("reports.deleted") : "Report deleted.", "success");
    await loadDashboard();
  } catch (e) {
    console.error("[deleteReport] caught:", e);
    showToast(`${typeof t === "function" ? t("reports.delete_failed") : "Delete failed"}: ${e.message}`, "error");
  }
}

function viewReport(id) {
  window.location.href = `report.html?id=${id}`;
}

function downloadReport(id) {
  const win = window.open(`report.html?id=${id}&download=1`, "_blank");
  if (!win) showToast("Please allow popups to download PDF.", "error");
}
function escHtml(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

// ── Generate Report ───────────────────────────────────────────────────────────
let activeJobId = null;
let pollTimer   = null;

async function startGenerate() {
  const btn = document.getElementById("generate-btn");
  if (!btn || btn.disabled) return;

  try {
    btn.disabled = true;
    btn.innerHTML = `<span class="material-symbols-outlined text-sm animate-spin">refresh</span> Connecting to X…`;

    const { job_id } = await apiFetch("/generate", { method: "POST" });
    activeJobId = job_id;
    pollJobStatus(job_id, btn);

  } catch (e) {
    showToast(`Error: ${e.message}`, "error");
    btn.disabled = false;
    btn.innerHTML = `<span class="material-symbols-outlined text-sm">auto_awesome</span> Generate Daily Report`;
  }
}

function pollJobStatus(jobId, btn) {
  const progressBar = document.getElementById("job-progress-bar");
  const progressWrap = document.getElementById("job-progress");

  if (progressWrap) progressWrap.classList.remove("hidden");

  pollTimer = setInterval(async () => {
    try {
      const job = await apiFetch(`/job/${jobId}`);

      if (btn) btn.innerHTML = `<span class="material-symbols-outlined text-sm animate-spin">refresh</span> ${job.message}`;
      if (progressBar) progressBar.style.width = job.progress + "%";

      if (job.status === "completed") {
        clearInterval(pollTimer);
        if (progressWrap) progressWrap.classList.add("hidden");
        btn.disabled = false;
        btn.innerHTML = `<span class="material-symbols-outlined text-sm">auto_awesome</span> Generate Daily Report`;
        showToast("✅ Report generated successfully!", "success");
        await loadDashboard();

      } else if (job.status === "failed") {
        clearInterval(pollTimer);
        if (progressWrap) progressWrap.classList.add("hidden");
        btn.disabled = false;
        btn.innerHTML = `<span class="material-symbols-outlined text-sm">auto_awesome</span> Generate Daily Report`;
        showToast(`❌ Failed: ${job.message}`, "error");
      }
    } catch (e) {
      clearInterval(pollTimer);
      showToast("Lost connection to server.", "error");
    }
  }, 2500);
}

// ── Report Page ───────────────────────────────────────────────────────────────
let _currentReport = null;

async function loadReportPage() {
  if (!backendOnline) return;

  const params   = new URLSearchParams(window.location.search);
  const reportId = params.get("id");
  const endpoint = reportId && reportId !== "latest" ? `/report/${reportId}` : "/report/latest";

  try {
    const report = await apiFetch(endpoint);
    _currentReport = report;
    renderReportPage(report);
    if (params.get("download") === "1") {
      setTimeout(() => window.print(), 800);
    }
  } catch (e) {
    if (e.message.includes("No reports yet")) {
      showToast("No reports yet. Go to Dashboard and click Generate.", "info");
    }
  }
}

// Pick zh_ field when Chinese is active, fall back to English field
function _pick(obj, key) {
  const isZh = document.documentElement.lang === "zh-CN";
  return (isZh && obj?.["zh_" + key]) || obj?.[key] || "";
}

function renderReportPage(r) {
  const isZh = document.documentElement.lang === "zh-CN";
  const dateLocale = isZh ? "zh-CN" : "en-US";
  const dateOpts = { month: "long", day: "numeric", year: "numeric" };
  setText("report-date", new Date(r.generated_at).toLocaleDateString(dateLocale, dateOpts));
  const meta = isZh
    ? `AI 情报分析 · ${(r.total_influencers || 0)} 位博主 · ${(r.total_posts || 0).toLocaleString()} 条帖子`
    : `AI-Synthesized Research · ${(r.total_influencers || 0)} Influencers · ${(r.total_posts || 0).toLocaleString()} Posts Scanned`;
  setText("report-subtitle", meta);
  setText("exec-para-1", _pick(r.executive_summary, "paragraph1"));
  setText("exec-para-2", _pick(r.executive_summary, "paragraph2"));
  setText("vi-title", _pick(r.visual_insight, "title"));
  setText("vi-desc",  _pick(r.visual_insight, "description"));

  renderTrendsGrid(r.strategic_trends || []);
  renderInfluencers(r.influencer_highlights || []);
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function renderTrendsGrid(trends) {
  const grid = document.getElementById("trends-grid");
  if (!grid || !trends.length) return;

  const velColors = {
    "High Velocity": "bg-primary/10 text-primary",
    "Critical":      "bg-primary/10 text-primary",
    "Emerging":      "bg-slate-100 dark:bg-slate-800 text-slate-500",
    "Stable":        "bg-slate-100 dark:bg-slate-800 text-slate-500",
  };
  const arrows = { up: "arrow_upward", down: "arrow_downward", steady: "horizontal_rule" };
  const arrowColor = { up: "text-emerald-500", down: "text-red-400", steady: "text-amber-500" };

  grid.innerHTML = trends.map(t => {
    const vc  = velColors[t.velocity_label] || velColors.Stable;
    const dir = t.direction || "up";
    return `
    <div class="bg-white dark:bg-slate-900/50 p-6 rounded-xl border border-slate-200 dark:border-slate-800
                hover:border-primary/50 hover:shadow-md transition-all group">
      <div class="flex justify-between items-start mb-4">
        <span class="text-xs font-black px-2 py-1 rounded uppercase ${vc}">${t.velocity_label}</span>
        <span class="${arrowColor[dir]} font-bold flex items-center text-sm">
          <span class="material-symbols-outlined text-sm">${arrows[dir]}</span> ${t.change}
        </span>
      </div>
      <h4 class="text-xl font-bold mb-3 group-hover:text-primary transition-colors">${escHtml(_pick(t, "name"))}</h4>
      <div class="h-16 w-full flex items-end gap-1 mb-4">
        ${[30,45,40,65,85,100].map(h => `<div class="bar-anim bg-primary/20 w-full rounded-t-sm" style="height:${h}%"></div>`).join("")}
      </div>
      <p class="text-sm text-slate-600 dark:text-slate-400">${escHtml(_pick(t, "description"))}</p>
    </div>`;
  }).join("");
}

const AVATAR_COLORS = [
  "from-orange-400 to-primary",
  "from-blue-500 to-blue-700",
  "from-green-500 to-emerald-700",
  "from-purple-500 to-purple-700",
];

function renderInfluencers(highlights) {
  const grid = document.getElementById("influencer-grid");
  if (!grid || !highlights.length) return;

  grid.innerHTML = highlights.map((h, i) => {
    const initials = (h.display_name || h.username || "?").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
    return `
    <div class="bg-white dark:bg-slate-900/50 p-5 rounded-xl border border-slate-200 dark:border-slate-800
                flex flex-col h-full hover:border-primary/40 hover:shadow-md transition-all">
      <div class="flex items-center gap-3 mb-4">
        <div class="size-10 rounded-full bg-gradient-to-br ${AVATAR_COLORS[i % AVATAR_COLORS.length]}
                    flex items-center justify-center text-white font-bold text-sm ring-2 ring-primary/20 flex-shrink-0">
          ${initials}
        </div>
        <div class="flex flex-col min-w-0">
          <div class="flex items-center gap-1">
            <span class="font-bold text-sm truncate">@${escHtml(h.username)}</span>
            <span class="material-symbols-outlined text-blue-400 text-[14px] flex-shrink-0">verified</span>
          </div>
          <span class="text-[10px] text-slate-500 uppercase font-bold tracking-tight">${escHtml(_pick(h, "role"))}</span>
        </div>
      </div>
      <p class="text-sm text-slate-700 dark:text-slate-300 italic mb-4 flex-grow">"${escHtml(_pick(h, "quote"))}"</p>
      <div class="pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-between
                  text-[10px] font-bold text-slate-400 uppercase tracking-widest">
        <span>${Number(h.likes || 0).toLocaleString()} Likes</span>
        <span>${Number(h.shares || 0).toLocaleString()} Shares</span>
      </div>
    </div>`;
  }).join("");
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  updateThemeIcons();
  document.querySelectorAll("[data-toggle-theme]").forEach(el => el.addEventListener("click", toggleTheme));

  initCounters();
  initProgressBars();
  initTrendTags();

  // Generate button (dashboard page)
  const genBtn = document.getElementById("generate-btn");
  if (genBtn) genBtn.addEventListener("click", startGenerate);

  // Download buttons (report.html page)
  document.querySelectorAll("[data-action='download']").forEach(btn => {
    btn.addEventListener("click", () => window.print());
  });

  // Check backend
  await checkBackendStatus();

  // Dashboard page
  if (document.getElementById("reports-tbody")) {
    await loadDashboard();
    // Re-render report list when language is toggled
    const _origToggleLangDash = window.toggleLang;
    window.toggleLang = function() {
      _origToggleLangDash();
      if (_dashboardData) renderDashboard(_dashboardData);
    };
  }

  // Report page
  if (document.getElementById("exec-para-1")) {
    await loadReportPage();
    // Re-render report content when language is toggled
    const _origToggleLang = window.toggleLang;
    window.toggleLang = function() {
      _origToggleLang();
      if (_currentReport) renderReportPage(_currentReport);
    };
  }
});
