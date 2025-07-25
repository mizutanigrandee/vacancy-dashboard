// ========== 設定 ==========
const DATA_PATH = "./vacancy_price_cache.json";
const PREV_DATA_PATH = "./vacancy_price_cache_previous.json";
const EVENT_PATH = "./event_data.json";
const HISTORICAL_PATH = "./historical_data.json";
const SPIKE_PATH = "./demand_spike_history.json";

// ========== グローバル状態 ==========
let calendarData = {};
let prevCalendarData = {};
let eventData = {};
let historicalData = {};
let spikeData = [];

let currentYearMonth = [];
let selectedDate = null;

// ========== 初期化 ==========
window.onload = async function() {
  await loadAllData();
  renderSpikeBanner();
  initMonth();
  renderCalendars();
  updateLastUpdate();
  setupMonthButtons();
}

// ========== データ読込 ==========
async function loadAllData() {
  calendarData = await fetchJson(DATA_PATH);
  prevCalendarData = await fetchJson(PREV_DATA_PATH);
  eventData = await fetchJson(EVENT_PATH);
  historicalData = await fetchJson(HISTORICAL_PATH);
  spikeData = await fetchJson(SPIKE_PATH);
}

async function fetchJson(path) {
  try {
    const res = await fetch(path + "?v=" + Date.now()); // キャッシュ対策
    if (!res.ok) return {};
    return await res.json();
  } catch(e) {
    return {};
  }
}

// ========== 需要急騰バナー ==========
function renderSpikeBanner() {
  const banner = document.getElementById("spike-banner");
  banner.innerHTML = "";
  if (!Array.isArray(spikeData) || spikeData.length === 0) {
    banner.style.display = "none";
    return;
  }
  banner.style.display = "flex";
  const maxSpikes = 10;
  spikeData.slice(0, maxSpikes).forEach(s => {
    const badge = document.createElement("span");
    badge.className = "spike-badge";
    badge.innerHTML = `🚀 <span class="spike-date">${s.date}</span> ${s.comment ? s.comment : ""}`;
    banner.appendChild(badge);
  });
}

// ========== 月初期設定 ==========
function initMonth() {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  currentYearMonth = [
    [year, month],
    month === 12 ? [year+1, 1] : [year, month+1]
  ];
}

// ========== カレンダー描画 ==========
function renderCalendars() {
  const container = document.getElementById("calendar-container");
  container.innerHTML = "";
  for (let ym of currentYearMonth) {
    const calElem = renderMonthCalendar(ym[0], ym[1]);
    container.appendChild(calElem);
  }
}

// ========== 1か月分カレンダー描画 ==========
function renderMonthCalendar(year, month) {
  const wrapper = document.createElement("div");
  wrapper.className = "month-calendar";
  const header = document.createElement("div");
  header.className = "month-header";
  header.textContent = `${year}年${month}月`;
  wrapper.appendChild(header);

  // 曜日ヘッダー
  const daysOfWeek = ["日", "月", "火", "水", "木", "金", "土"];
  const grid = document.createElement("div");
  grid.className = "calendar-grid";
  for (let d of daysOfWeek) {
    const cell = document.createElement("div");
    cell.className = "calendar-cell";
    cell.style.fontWeight = "bold";
    cell.style.background = "#fff";
    cell.textContent = d;
    grid.appendChild(cell);
  }

  // 各日のセル
  const firstDay = new Date(year, month-1, 1).getDay();
  const lastDate = new Date(year, month, 0).getDate();
  let dayCount = 0;
  for (let i=0; i<firstDay; i++) {
    const emptyCell = document.createElement("div");
    emptyCell.className = "calendar-cell";
    grid.appendChild(emptyCell);
    dayCount++;
  }
  for (let date=1; date<=lastDate; date++) {
    const cellDate = `${year}-${String(month).padStart(2,"0")}-${String(date).padStart(2,"0")}`;
    const cell = document.createElement("div");
    cell.className = "calendar-cell";
    cell.dataset.date = cellDate;

    // 曜日色分け
    const dayOfWeek = (dayCount)%7;
    if (dayOfWeek === 0) cell.classList.add("sunday");
    if (dayOfWeek === 6) cell.classList.add("saturday");

    // データ取得
    const data = calendarData[cellDate] || {};
    const prevData = prevCalendarData[cellDate] || {};
    const eventArr = eventData[cellDate]?.events || [];
    let demandLv = data.demand || 0;

    // 祝日・イベント色分け
    let isHoliday = eventArr.some(e => e.type === "holiday" || (e.name && e.name.includes("祝日")));
    let isEvent = eventArr.some(e => e.type === "event" || e.type === "kyocera" || e.type === "yanmar" || e.type === "other");
    if (isHoliday) cell.classList.add("holiday");
    else if (isEvent) cell.classList.add("event");
    if (demandLv >= 3) cell.classList.add("strong-demand");

    // 前日比
    let diffHtml = "";
    if (typeof data.vacancy === "number" && typeof prevData.vacancy === "number") {
      let diff = data.vacancy - prevData.vacancy;
      if (diff > 0) {
        diffHtml = `<span class="cell-diff up">＋${diff}</span>`;
      } else if (diff < 0) {
        diffHtml = `<span class="cell-diff down">－${Math.abs(diff)}</span>`;
      } else {
        diffHtml = `<span class="cell-diff flat">±0</span>`;
      }
    }

    // 価格
    let priceStr = "-";
    if (typeof data.avg_price === "number") {
      priceStr = `¥${Math.round(data.avg_price).toLocaleString()}`;
      // 前日比アイコン
      if (typeof prevData.avg_price === "number" && prevData.avg_price !== 0) {
        let diff = data.avg_price - prevData.avg_price;
        if (diff > 0) {
          priceStr += ` <span class="cell-diff up">↑</span>`;
        } else if (diff < 0) {
          priceStr += ` <span class="cell-diff down">↓</span>`;
        } else {
          priceStr += ` <span class="cell-diff flat">→</span>`;
        }
      }
    }

    // イベント注記（複数行対応・種別アイコン）
    let eventHtml = "";
    if (eventArr.length > 0) {
      eventHtml = eventArr.map(ev => {
        let icon = "";
        if (ev.type === "kyocera") icon = "🔴";
        else if (ev.type === "yanmar") icon = "🔵";
        else if (ev.type === "other") icon = "★";
        else if (ev.type === "holiday") icon = "🎌";
        else icon = "🎫";
        return `<span class="cell-event">${icon} ${ev.name}</span>`;
      }).join("");
    }

    // 需要シンボル（🔥1～5段階）
    let demandHtml = "";
    if (demandLv >= 1) {
      let lv = Math.min(demandLv,5);
      demandHtml = `<span class="cell-demand lv${lv}">🔥${lv}</span>`;
    }

    // 本体
    let stock = (typeof data.vacancy === "number") ? `${data.vacancy}件` : "-";
    cell.innerHTML = `
      <div class="cell-main">${stock} (${date}日) ${diffHtml}</div>
      <div class="cell-price">${priceStr}</div>
      ${eventHtml}
      ${demandHtml}
    `;

    cell.onclick = function() {
      selectDate(cellDate);
    };

    grid.appendChild(cell);
    dayCount++;
  }
  wrapper.appendChild(grid);
  return wrapper;
}

// ========== 日付選択 ==========
function selectDate(dateStr) {
  selectedDate = dateStr;
  document.querySelectorAll('.calendar-cell').forEach(cell => {
    if (cell.dataset.date === dateStr) {
      cell.classList.add('selected');
    } else {
      cell.classList.remove('selected');
    }
  });
  renderGraph(dateStr);
}

// ========== グラフ描画 ==========
function renderGraph(dateStr) {
  const graphContainer = document.getElementById("graph-container");
  graphContainer.style.display = "block";

  // 履歴データ取得
  const history = historicalData[dateStr];
  const stockHistory = history?.stock_history || [];
  const priceHistory = history?.price_history || [];
  const labels = history?.date_list || [];

  // 現在インデックス
  let idx = Object.keys(historicalData).indexOf(dateStr);

  // グラフ操作ボタン
  let keys = Object.keys(historicalData);
  function goTo(offset) {
    let i = idx + offset;
    if (i >= 0 && i < keys.length) selectDate(keys[i]);
  }

  graphContainer.innerHTML = `
    <div class="graph-btns">
      <button onclick="closeGraph()">✗ グラフを閉じる</button>
      <button onclick="goGraphDay(-1)">＜前日</button>
      <button onclick="goGraphDay(1)">翌日＞</button>
    </div>
    <h3>${dateStr} の在庫・価格推移</h3>
    <div style="margin-bottom:18px;">
      <canvas id="stockChart" width="420" height="180"></canvas>
    </div>
    <div>
      <canvas id="priceChart" width="420" height="180"></canvas>
    </div>
  `;

  // グラフ移動関数をグローバル化
  window.goGraphDay = function(diff) {
    let keys = Object.keys(historicalData);
    let idx = keys.indexOf(selectedDate);
    let nextIdx = idx + diff;
    if (nextIdx >= 0 && nextIdx < keys.length) {
      selectDate(keys[nextIdx]);
    }
  };

  // メモリリーク防止
  if(window.stockChartInstance) window.stockChartInstance.destroy();
  if(window.priceChartInstance) window.priceChartInstance.destroy();

  // 在庫推移グラフ
  if (labels.length && stockHistory.length) {
    window.stockChartInstance = new Chart(document.getElementById('stockChart').getContext('2d'), {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: '在庫数',
          data: stockHistory,
          fill: false,
          borderColor: '#2196f3',
          backgroundColor: '#90caf9',
          tension: 0.2,
          pointRadius: 2,
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: "在庫数" } },
          x: { title: { display: true, text: "日付" } }
        }
      }
    });
  }
  // 価格推移グラフ
  if (labels.length && priceHistory.length) {
    window.priceChartInstance = new Chart(document.getElementById('priceChart').getContext('2d'), {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: '平均価格',
          data: priceHistory,
          fill: false,
          borderColor: '#e91e63',
          backgroundColor: '#f8bbd0',
          tension: 0.2,
          pointRadius: 2,
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: false,
            title: { display: true, text: "平均価格（円）" }
          },
          x: { title: { display: true, text: "日付" } }
        }
      }
    });
  }
}

// ========== グラフを閉じる ==========
function closeGraph() {
  document.getElementById("graph-container").style.display = "none";
  document.querySelectorAll('.calendar-cell.selected').forEach(cell => {
    cell.classList.remove('selected');
  });
  selectedDate = null;
  if(window.stockChartInstance) {
    window.stockChartInstance.destroy();
    window.stockChartInstance = null;
  }
  if(window.priceChartInstance) {
    window.priceChartInstance.destroy();
    window.priceChartInstance = null;
  }
}

// ========== 月切替ボタン ==========
function setupMonthButtons() {
  document.getElementById("prevMonthBtn").onclick = function() {
    shiftMonth(-1);
  };
  document.getElementById("currentMonthBtn").onclick = function() {
    initMonth();
    renderCalendars();
  };
  document.getElementById("nextMonthBtn").onclick = function() {
    shiftMonth(1);
  };
}
function shiftMonth(diff) {
  let [y,m] = currentYearMonth[0];
  m += diff;
  if (m < 1) { y--; m = 12; }
  if (m > 12) { y++; m = 1; }
  currentYearMonth = [
    [y,m],
    m === 12 ? [y+1,1] : [y,m+1]
  ];
  renderCalendars();
}

// ========== 最終更新日時 ==========
function updateLastUpdate() {
  document.getElementById("last-update").textContent = "最終更新日時：" + formatDate(new Date());
}
function formatDate(dt) {
  return `${dt.getFullYear()}-${String(dt.getMonth()+1).padStart(2,"0")}-${String(dt.getDate()).padStart(2,"0")} ${String(dt.getHours()).padStart(2,"0")}:${String(dt.getMinutes()).padStart(2,"0")}:${String(dt.getSeconds()).padStart(2,"0")}`;
}
