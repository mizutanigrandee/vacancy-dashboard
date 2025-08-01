// ========== データ & 祝日設定 ==========

const DATA_PATH  = "./vacancy_price_cache.json";
const PREV_PATH  = "./vacancy_price_cache_previous.json";
const EVENT_PATH = "./event_data.json";
const HIST_PATH  = "./historical_data.json";
const SPIKE_PATH = "./demand_spike_history.json"; // スパイクバナー

let calendarData   = {},
    prevData       = {},
    eventData      = {},
    historicalData = {},
    spikeData      = {};
let currentYM = [], selectedDate = null;

// ========== 祝日判定 ==========

function isHoliday(date) {
  if (!window.JapaneseHolidays) return null;
  return window.JapaneseHolidays.isHoliday(date);
}

// ========== ヘルパー ==========

const todayIso = () => new Date().toISOString().slice(0,10);

async function loadJson(path) {
  try {
    const res = await fetch(path + '?t=' + (new Date().getTime()));
    if (!res.ok) return {};
    return await res.json();
  } catch {
    return {};
  }
}
async function loadAll() {
  calendarData   = await loadJson(DATA_PATH);
  prevData       = await loadJson(PREV_PATH);
  eventData      = await loadJson(EVENT_PATH);
  historicalData = await loadJson(HIST_PATH);
  spikeData      = await loadJson(SPIKE_PATH);
}

// ========== 月送りボタン設定 ==========

function setupMonthButtons() {
  document.getElementById("prevMonthBtn").onclick    = () => { shiftMonth(-1); renderPage(); };
  document.getElementById("currentMonthBtn").onclick = () => { initMonth();   renderPage(); };
  document.getElementById("nextMonthBtn").onclick    = () => { shiftMonth(1);  renderPage(); };
}
function initMonth() {
  const t = new Date(),
        y = t.getFullYear(),
        m = t.getMonth() + 1;
  currentYM = [[y, m], m === 12 ? [y+1,1] : [y, m+1]];
}
function shiftMonth(diff) {
  let [y,m] = currentYM[0];
  m += diff;
  if (m < 1)      { y--; m = 12; }
  else if (m > 12){ y++; m = 1;  }
  currentYM = [[y,m], m === 12 ? [y+1,1] : [y, m+1]];
}

// ========== ページ全体再描画 ==========

function renderPage() {
  let isMobile = window.innerWidth <= 700;
  document.querySelector(".calendar-main").innerHTML =
    '<div class="main-flexbox">' +
      '<div>' +
        '<div id="spike-banner"></div>' +
        '<div class="graph-side" id="graph-container"></div>' +
      '</div>' +
      '<div class="calendar-container" id="calendar-container"></div>' +
    '</div>';
  renderSpikeBanner();
  renderGraph(selectedDate);
  renderCalendars();
}

// ========== スパイクバナー描画 ==========

function renderSpikeBanner() {
  const el = document.getElementById("spike-banner");
  el.innerHTML = "";
  // 最新3日×10件
  if (!spikeData || Object.keys(spikeData).length === 0) return;

  const dates = Object.keys(spikeData).sort().reverse().slice(0,3);
  let chips = [];
  for (const up_date of dates) {
    for (const spike of spikeData[up_date]) {
      chips.push(
        `<div class="spike-chip">
          <span class="spike-up-date">【${up_date.slice(5).replace('-','/')} UP】</span>
          <span class="spike-main">該当日 <span class="spike-date">${spike.spike_date}</span></span>
          <span style="color:#d35400;">単価${spike.price_diff>0?'↑':'↓'} ${Math.abs(spike.price_diff).toLocaleString()}円</span>
          <span style="color:#2980b9;">客室${spike.vacancy_diff<0?'減':'増'} ${Math.abs(spike.vacancy_diff)}件</span>
          <span class="spike-summary">平均￥${spike.price.toLocaleString()}／残${spike.vacancy}</span>
        </div>`
      );
      if (chips.length >= 10) break;
    }
    if (chips.length >= 10) break;
  }
  if (chips.length) {
    el.innerHTML =
      `<div class="spike-banner-box">
        <div class="spike-banner-title">
          <span style="font-size:1.15em;color:#e67e22;margin-right:7px;">🚀</span>
          <span style="font-weight:800;color:#e67e22;font-size:1em;letter-spacing:0.5px;margin-right:7px;">
            需要急騰検知日
          </span>
          <span style="font-size:0.9em;color:#ae8d3a;">（直近3日分・最大10件）</span>
        </div>
        <div class="spike-banner-row">
          ${chips.join("")}
        </div>
      </div>`;
  }
}

// ========== カレンダー描画 ==========

function renderCalendars() {
  const container = document.getElementById("calendar-container");
  container.innerHTML = "";
  for (const [y,m] of currentYM) {
    container.appendChild(renderMonth(y,m));
  }
}

function renderMonth(y,m) {
  const wrap = document.createElement("div");
  wrap.className = "month-calendar";
  wrap.innerHTML = '<div class="month-header">' + y + '年' + m + '月</div>';

  const grid = document.createElement("div");
  grid.className = "calendar-grid";

  ["日","月","火","水","木","金","土"].forEach(d => {
    const c = document.createElement("div");
    c.className = "calendar-dow";
    c.textContent = d;
    grid.appendChild(c);
  });

  const firstDay = new Date(y,m-1,1).getDay(),
        lastDate = new Date(y,m,0).getDate();
  for (let i=0; i<firstDay; i++){
    const e = document.createElement("div");
    e.className = "calendar-cell";
    grid.appendChild(e);
  }
  for (let d=1; d<=lastDate; d++){
    const iso = y + '-' + String(m).padStart(2,"0") + '-' + String(d).padStart(2,"0");
    const cell = document.createElement("div");
    cell.className = "calendar-cell";
    cell.dataset.date = iso;

    let holidayName = isHoliday(iso);
    const idx = (grid.children.length) % 7;
    if      (holidayName) cell.classList.add("holiday-bg");
    else if (idx === 0)   cell.classList.add("sunday-bg");
    else if (idx === 6)   cell.classList.add("saturday-bg");
    if (iso < todayIso()) cell.classList.add("past-date");

    const cur = calendarData[iso] || {},
          prv = prevData[iso]      || {};
    const dv  = typeof cur.vacancy_diff === "number"
                ? cur.vacancy_diff
                : (cur.vacancy||0) - (prv.vacancy||0);
    const dp  = typeof cur.avg_price_diff === "number"
                ? cur.avg_price_diff
                : Math.round((cur.avg_price||0) - (prv.avg_price||0));
    const stock = cur.vacancy != null ? `${cur.vacancy}件` : "-";
    const price = cur.avg_price != null ? cur.avg_price.toLocaleString() : "-";
    const dvText = dv > 0 ? `(+${dv})` : dv < 0 ? `(${dv})` : `(±0)`;

    let lvl = 0;
    if (cur.vacancy!=null && cur.avg_price!=null){
      if (cur.vacancy<=70  || cur.avg_price>=50000) lvl=5;
      else if (cur.vacancy<=100 || cur.avg_price>=40000) lvl=4;
      else if (cur.vacancy<=150 || cur.avg_price>=35000) lvl=3;
      else if (cur.vacancy<=200 || cur.avg_price>=30000) lvl=2;
      else if (cur.vacancy<=250 || cur.avg_price>=25000) lvl=1;
    }
    const badge = lvl ? `<div class="cell-demand-badge lv${lvl}">🔥${lvl}</div>` : "";
    const evs = (eventData[iso] || [])
      .map(ev => `<div class="cell-event" style="font-size:9px; color:#222; white-space:normal; line-height:1.1;">${ev.icon} <span style="color:#222;">${ev.name}</span></div>`)
      .join("");

    cell.innerHTML =
      '<div class="cell-date">' + d + '</div>' +
      '<div class="cell-main">' +
        '<span class="cell-vacancy">' + stock + '</span>' +
        '<span class="cell-vacancy-diff ' + (dv>0?'plus':dv<0?'minus':'flat') + '">' + dvText + '</span>' +
      '</div>' +
      '<div class="cell-price">' +
        '￥' + price +
        '<span class="cell-price-diff ' + (dp>0?'up':dp<0?'down':'flat') + '">' + (dp>0?'↑':dp<0?'↓':'→') + '</span>' +
      '</div>' +
      badge +
      '<div class="cell-event-list">' + evs + '</div>';

    cell.onclick = () => { selectedDate = iso; renderPage(); };
    grid.appendChild(cell);
  }

  wrap.appendChild(grid);
  return wrap;
}

// ========== グラフ描画 ==========

function renderGraph(dateStr){
  const gc = document.getElementById("graph-container");
  if (!dateStr) { gc.innerHTML=""; return; }

  const allDates = Object.keys(historicalData).sort(),
        idx = allDates.indexOf(dateStr);

  gc.innerHTML =
    '<div class="graph-btns">' +
      '<button onclick="closeGraph()">✗ 当日へ戻る</button>' +
      '<button onclick="nav(-1)">< 前日</button>' +
      '<button onclick="nav(1)">翌日 ></button>' +
    '</div>' +
    `<h3 style="font-size:1rem;">${dateStr} の在庫・価格推移</h3>` +
    '<canvas id="stockChart" width="350" height="120"></canvas>' +
    '<canvas id="priceChart" width="350" height="120"></canvas>';

  window.nav = diff => {
    const ni = idx + diff;
    if (ni >= 0 && ni < allDates.length) {
      selectedDate = allDates[ni];
      renderPage();
    }
  };
  window.closeGraph = () => {
    selectedDate = todayIso();
    renderPage();
  };

  const hist = historicalData[dateStr] || {}, labels = [], sv = [], pv = [];
  Object.keys(hist).sort().forEach(d => {
    labels.push(d);
    sv.push(hist[d].vacancy);
    pv.push(hist[d].avg_price);
  });

  if (window.sc) window.sc.destroy();
  if (window.pc) window.pc.destroy();

  if (labels.length) {
    window.sc = new Chart(
      document.getElementById("stockChart").getContext("2d"),
      {
        type: "line",
        data: { labels, datasets: [{ data: sv, fill: false, borderColor: "#2196f3", pointRadius: 1 }] },
        options: {
          plugins: { legend: { display: false } },
          responsive: false,
          animation: false,  
          scales: {
            y: { beginAtZero: true, min: 0, max: 400, title: { display: true, text: "在庫数" } },
            x: { title: { display: true, text: "日付" } }
          }
        }
      }
    );
    window.pc = new Chart(
      document.getElementById("priceChart").getContext("2d"),
      {
        type: "line",
        data: { labels, datasets: [{ data: pv, fill: false, borderColor: "#e91e63", pointRadius: 1 }] },
        options: {
          plugins: { legend: { display: false } },
          responsive: false,
          animation: false,  
          scales: {
            y: { beginAtZero: true, min: 0, max: 40000, title: { display: true, text: "平均価格（円）" } },
            x: { title: { display: true, text: "日付" } }
          }
        }
      }
    );
  }
}

// ========== 最終更新日時 ==========

function updateLastUpdate(){
  const el = document.getElementById("last-update");
  let dtStr = "";
  if (calendarData && calendarData.last_update) {
    dtStr = calendarData.last_update;
  } else {
    const d  = new Date(),
          z  = n => String(n).padStart(2,"0");
    dtStr = `${d.getFullYear()}-${z(d.getMonth()+1)}-${z(d.getDate())} ${z(d.getHours())}:${z(d.getMinutes())}:${z(d.getSeconds())}`;
  }
  el.textContent = `最終更新日時：${dtStr}`;
}

// ========== 起動時初期化 ==========

window.onload = async () => {
  await loadAll();
  initMonth();
  if (!selectedDate) selectedDate = todayIso();
  renderPage();
  updateLastUpdate();
  setupMonthButtons();
  window.addEventListener('resize', () => { renderPage(); });
};
