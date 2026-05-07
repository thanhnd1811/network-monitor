/**
 * Dashboard renderer for network monitor.
 * Fetches data/status.json + data/history.json and re-renders every 30s.
 */

const REFRESH_INTERVAL_MS = 30 * 1000;
const STATUS_URL = "data/status.json";
const HISTORY_URL = "data/history.json";

const $ = (sel) => document.querySelector(sel);

let refreshTimer = null;

function timeAgo(iso) {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  const now = Date.now();
  const sec = Math.max(0, Math.floor((now - then) / 1000));
  if (sec < 60) return `${sec} giây trước`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} phút trước`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} giờ trước`;
  const day = Math.floor(hr / 24);
  return `${day} ngày trước`;
}

function fmtTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())} ${pad(d.getDate())}/${pad(d.getMonth() + 1)}`;
}

function locationInitials(name) {
  // Cơ sở Hà Nội -> HN; TP Hồ Chí Minh -> HCM; Quảng Ninh -> QN
  if (name.includes("Hà Nội")) return "HN";
  if (name.includes("Hồ Chí Minh")) return "HCM";
  if (name.includes("Quảng Ninh")) return "QN";
  return name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 3);
}

function renderSummary(status) {
  const s = status.summary || { total: 0, up: 0, down: 0 };
  $("#num-up").textContent = s.up;
  $("#num-down").textContent = s.down;
  $("#num-total").textContent = s.total;
  const downCard = $("#card-down");
  downCard.classList.toggle("alert", s.down > 0);

  // Tab title with badge
  document.title = s.down > 0
    ? `(${s.down} mất) Giám sát mạng — ĐH Ngoại thương`
    : `Giám sát mạng — ĐH Ngoại thương`;
}

function renderLocations(status) {
  const container = $("#locations-container");
  const html = (status.locations || []).map((loc) => {
    const linesHtml = loc.lines.map((line) => {
      const stateCls = line.up ? "up" : "down";
      const stateText = line.up ? "Hoạt động" : "Mất";
      const ipDisplay = line.ip_range || line.ip;
      const methodHint = line.up ? `${line.method} · ${line.latency_ms}ms` : "không phản hồi";
      return `
        <div class="line">
          <span class="status-dot ${stateCls}"></span>
          <div class="line-info">
            <div class="line-name">
              <span class="isp-badge">${escapeHtml(line.isp)}</span>${escapeHtml(line.name)}
            </div>
            <div class="line-meta">${escapeHtml(ipDisplay)} · ${escapeHtml(methodHint)}</div>
          </div>
          <span class="line-status ${stateCls}">${stateText}</span>
        </div>
      `;
    }).join("");

    const okCount = loc.total_count - loc.down_count;
    const downHtml = loc.down_count > 0
      ? `<span class="down-count">${loc.down_count} mất</span> · <span class="ok">${okCount} hoạt động</span>`
      : `<span class="ok">Tất cả ${loc.total_count} đường đều OK</span>`;

    return `
      <section class="location">
        <header class="location-header">
          <div class="location-title">
            <span class="location-icon">${locationInitials(loc.name)}</span>
            ${escapeHtml(loc.name)}
          </div>
          <div class="location-stats">${downHtml}</div>
        </header>
        <div class="lines">${linesHtml}</div>
      </section>
    `;
  }).join("");
  container.innerHTML = html;
}

function renderHistory(history) {
  const list = $("#history-list");
  const events = (history.events || []).slice().reverse().slice(0, 20);
  if (events.length === 0) {
    list.innerHTML = '<div class="empty">Chưa có sự cố nào được ghi nhận.</div>';
    return;
  }
  list.innerHTML = events.map((e) => {
    const cls = e.to_up ? "up-event" : "down-event";
    const verb = e.to_up
      ? `<strong style="color: var(--green)">đã hoạt động trở lại</strong>`
      : `<strong style="color: var(--red)">bị mất kết nối</strong>`;
    return `
      <div class="history-item ${cls}">
        <span class="status-dot ${e.to_up ? "up" : "down"}"></span>
        <div>${escapeHtml(e.name)} ${verb}</div>
        <span class="time">${fmtTime(e.at)}</span>
      </div>
    `;
  }).join("");
}

function escapeHtml(s) {
  if (s == null) return "";
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

async function loadAndRender() {
  const refreshBtn = $("#refresh-btn");
  refreshBtn.classList.add("spinning");
  try {
    const [statusRes, historyRes] = await Promise.all([
      fetch(STATUS_URL + "?t=" + Date.now()),
      fetch(HISTORY_URL + "?t=" + Date.now()).catch(() => null),
    ]);
    if (!statusRes.ok) throw new Error("Không tải được status.json");
    const status = await statusRes.json();
    renderSummary(status);
    renderLocations(status);
    $("#last-updated").textContent = `Cập nhật: ${timeAgo(status.generated_at)}`;

    if (historyRes && historyRes.ok) {
      const history = await historyRes.json();
      renderHistory(history);
    }
  } catch (err) {
    $("#last-updated").textContent = "Lỗi tải dữ liệu — sẽ thử lại sau";
    console.error(err);
  } finally {
    setTimeout(() => refreshBtn.classList.remove("spinning"), 400);
  }
}

function scheduleRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(loadAndRender, REFRESH_INTERVAL_MS);
}

document.addEventListener("DOMContentLoaded", () => {
  $("#refresh-btn").addEventListener("click", loadAndRender);
  loadAndRender();
  scheduleRefresh();

  // Re-fetch when tab becomes visible again
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) loadAndRender();
  });
});
