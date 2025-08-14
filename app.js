// ========== データ & 祝日設定 ==========

// ファイルパス定義
const DATA_PATH  = "./vacancy_price_cache.json";
const PREV_PATH  = "./vacancy_price_cache_previous.json";
const EVENT_PATH = "./event_data.json";
const HIST_PATH  = "./historical_data.json";
const SPIKE_PATH = "./demand_spike_history.json";   // ←追加
const LASTUPDATED_PATH = "./last_updated.json";      // ←追加

// グローバル状態
let calendarData   = {},
    prevData       = {},
    eventData      = {},
    historicalData = {},
    spikeData      = {};   // ←追加
let currentYM = [], selectedDate = null;

// ========== 祝日判定（ローカルjs方式） ==========
function isHoliday(date) {
  if (!window.JapaneseHolidays) return null;
  return window.JapaneseHolidays.isHoliday(date);
}

// ========== ヘルパー ==========
const todayIso = () => new Date().toISOString().slice(0,10);
async function loadJson(path) {
  try {
    const res = await fetch(path);
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
  spikeData      = await loadJson(SPIKE_PATH);   // ←追加
}

// ========== 需要スパイク履歴バナー ==========
// サマリー：直近3日分×最大10件（※バナー表示は「当日〜3日先」を除外）
function renderSpikeBanner() {
  const bannerDiv = document.getElementById("spike-banner");
  if (!bannerDiv) return;

  if (!spikeData || Object.keys(spikeData).length === 0) {
    bannerDiv.innerHTML = "";
    return;
  }

  // ---- ここが今回のポイント（JSTで「当日0:00」を作る＆近すぎる日を除外） ----
  const EXCLUDE_NEAR_DAYS = 3; // 当日(0)〜3日先を除外 → 4日先以降を表示
  const MS_PER_DAY = 24 * 60 * 60 * 1000;

  // JSTの「今日 00:00」
  const now = new Date();
  const jstNow = new Date(now.getTime() + (9 - now.getTimezoneOffset() / 60) * 60 * 60 * 1000);
  const jstToday = new Date(Date.UTC(
    jstNow.getUTCFullYear(),
    jstNow.getUTCMonth(),
    jstNow.getUTCDate(), 0, 0, 0
  ));

  const parseYMD = (ymd) => {
    // "YYYY-MM-DD" → JST 00:00 の Date
    const [y, m, d] = String(ymd).split("-").map(Number);
    return new Date(Date.UTC(y, m - 1, d, 0, 0, 0));
  };
  // ---------------------------------------------------------------------

  // 直近3日の「検知日(up_date)」だけ拾う（ここは従来どおり）
  const sortedDates = Object.keys(spikeData)
    .sort((a, b) => b.localeCompare(a))  // 新しい検知日が先
    .slice(0, 3);

  let chips = [];

  for (const up_date of sortedDates) {
    for (const spike of spikeData[up_date]) {
      const spikeDate = spike.spike_date || "";   // 例: "2025-08-12"
      if (!spikeDate) continue;

      // 「当日〜3日先」を除外（過去日も除外されます）
      const target = parseYMD(spikeDate);
      const daysAhead = Math.floor((target - jstToday) / MS_PER_DAY);
      if (daysAhead <= EXCLUDE_NEAR_DAYS) continue;  // ← ここで除外！

      const priceDiff = spike.price_diff || 0;
      const priceRatio = spike.price_ratio ? (spike.price_ratio * 100).toFixed(1) : "0";
      const price = spike.price ? spike.price.toLocaleString() : "-";
      const vacancyDiff = spike.vacancy_diff || 0;
      const vacancyRatio = spike.vacancy_ratio ? (spike.vacancy_ratio * 100).toFixed(1) : "0";
      const vacancy = spike.vacancy ? spike.vacancy.toLocaleString() : "-";

      const priceTxt = `<span class='spike-price ${priceDiff > 0 ? "up" : "down"}'>単価${priceDiff > 0 ? "↑" : "↓"} ${Math.abs(priceDiff).toLocaleString()}円</span>（${priceRatio}%）`;
      const vacTxt   = `<span class='spike-vacancy ${vacancyDiff < 0 ? "dec" : "inc"}'>客室${vacancyDiff < 0 ? "減" : "増"} ${Math.abs(vacancyDiff)}</span>（${vacancyRatio}%）`;

      chips.push(
        `<div class="spike-chip">
          <span class="spike-date">[${up_date.replace(/^(\d{4})-(\d{2})-(\d{2})$/, "$2/$3 UP")}]</span>
          <span class="spike-main"><b>該当日 ${spikeDate}</b> ${priceTxt} ${vacTxt} <span class="spike-avg">平均￥${price}／残${vacancy}</span></span>
        </div>`
      );

      if (chips.length >= 10) break;
    }
    if (chips.length >= 10) break;
  }

  if (chips.length === 0) {
    bannerDiv.innerHTML = "";
    return;
  }

  bannerDiv.innerHTML =
    `<div class="spike-banner-box">
      <span class="spike-banner-header">🚀 需要急騰検知日</span>
      <span class="spike-banner-meta">（直近3日・最大10件）</span>
      <div class="spike-chip-row">${chips.join("")}</div>
    </div>`;
}


// ========== 月送りボタン設定 ==========
function setupMonthButtons() {
  const prevBtn = document.getElementById("prevMonthBtn");
  const curBtn  = document.getElementById("currentMonthBtn");
  const nextBtn = document.getElementById("nextMonthBtn");
  if (prevBtn) prevBtn.onclick = () => { shiftMonth(-1); renderPage(); };
  if (curBtn)  curBtn.onclick  = () => { initMonth();   renderPage(); };
  if (nextBtn) nextBtn.onclick = () => { shiftMonth(1);  renderPage(); };
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
  if (isMobile) {
    document.querySelector(".calendar-main").innerHTML =
      '<div class="main-flexbox">' +
        '<div class="calendar-container" id="calendar-container"></div>' +
        '<div class="graph-side" id="graph-container"></div>' +
      '</div>';
  } else {
    document.querySelector(".calendar-main").innerHTML =
      '<div class="main-flexbox">' +
        '<div class="graph-side" id="graph-container"></div>' +
        '<div class="calendar-container" id="calendar-container"></div>' +
      '</div>';
  }
  renderSpikeBanner(); // ←需要急騰バナー描画
  renderGraph(selectedDate);
  renderCalendars();
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
  wrap.innerHTML = `<div class="month-header">${y}年${m}月</div>`;

  const grid = document.createElement("div");
  grid.className = "calendar-grid";

  // 曜日ヘッダー
  ["日","月","火","水","木","金","土"].forEach(d => {
    const c = document.createElement("div");
    c.className = "calendar-dow";
    c.textContent = d;
    grid.appendChild(c);
  });

  // 空セル
  const firstDay = new Date(y,m-1,1).getDay(),
        lastDate = new Date(y,m,0).getDate();
  for (let i=0; i<firstDay; i++){
    const e = document.createElement("div");
    e.className = "calendar-cell";
    grid.appendChild(e);
  }

  // 各日セル
  for (let d=1; d<=lastDate; d++){
    const iso = y + '-' + String(m).padStart(2,"0") + '-' + String(d).padStart(2,"0");
    const cell = document.createElement("div");
    cell.className = "calendar-cell";
    cell.dataset.date = iso;

    // 祝日判定
    let holidayName = isHoliday(iso);

    // 土日祝色分け
    const idx = (grid.children.length) % 7;
    if      (holidayName) cell.classList.add("holiday-bg");
    else if (idx === 0)   cell.classList.add("sunday-bg");
    else if (idx === 6)   cell.classList.add("saturday-bg");

    // 過去日付グレーアウト
    if (iso < todayIso()) cell.classList.add("past-date");

    // データ取得＆差分
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

    // 括弧付き差分テキスト
    const dvText = dv > 0 ? `(+${dv})` : dv < 0 ? `(${dv})` : `(±0)`;

    // 需要シンボル
    let lvl = 0;
    if (cur.vacancy!=null && cur.avg_price!=null){
      if (cur.vacancy<=70  || cur.avg_price>=50000) lvl=5;
      else if (cur.vacancy<=100 || cur.avg_price>=40000) lvl=4;
      else if (cur.vacancy<=150 || cur.avg_price>=35000) lvl=3;
      else if (cur.vacancy<=200 || cur.avg_price>=30000) lvl=2;
      else if (cur.vacancy<=250 || cur.avg_price>=25000) lvl=1;
    }
    const badge = lvl ? `<div class="cell-demand-badge lv${lvl}">🔥${lvl}</div>` : "";

    // イベント
    const evs = (eventData[iso] || [])
      .map(ev => `<a href="https://www.google.com/search?q=${encodeURIComponent(ev.name)}" target="_blank" title="「${ev.name}」について調べる" class="event-link">
                    ${ev.icon} ${ev.name}
                  </a>`)
      .join("<br>");

    cell.innerHTML =
      `<div class="cell-date">${d}</div>` +
      `<div class="cell-main">
        <span class="cell-vacancy">${stock}</span>
        <span class="cell-vacancy-diff ${(dv>0?'plus':dv<0?'minus':'flat')}">${dvText}</span>
      </div>` +
      `<div class="cell-price">
        ￥${price}
        <span class="cell-price-diff ${(dp>0?'up':dp<0?'down':'flat')}">${dp>0?'↑':dp<0?'↓':'→'}</span>
      </div>` +
      badge +
      `<div class="cell-event-list">${evs}</div>`;

    cell.onclick = () => { selectedDate = iso; renderPage(); };
    grid.appendChild(cell);
  }

  wrap.appendChild(grid);
  return wrap;
}

// ========== グラフ描画 ==========
function renderGraph(dateStr){
  const gc = document.getElementById("graph-container");
  if (!gc) return;
  if (!dateStr) { gc.innerHTML=""; return; }

  const allDates = Object.keys(historicalData).sort(),
        idx = allDates.indexOf(dateStr);

  gc.innerHTML =
    '<div class="graph-btns">' +
      '<button onclick="closeGraph()"> 当日へ戻る</button>' +
      '<button onclick="nav(-1)">< 前日</button>' +
      '<button onclick="nav(1)">翌日 ></button>' +
    '</div>' +
    `<h3>${dateStr} の在庫・価格推移</h3>` +
    '<canvas id="stockChart" width="600" height="250"></canvas>' +
    '<canvas id="priceChart" width="600" height="250"></canvas>';

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

  // Chart.js描画
  const hist = historicalData[dateStr] || {}, labels = [], sv = [], pv = [];
  Object.keys(hist).sort().forEach(d => {
    labels.push(d);
    sv.push(hist[d].vacancy);
    pv.push(hist[d].avg_price);
  });

  if (window.sc) window.sc.destroy();
  if (window.pc) window.pc.destroy();

  if (labels.length) {
    // 在庫数グラフ
    window.sc = new Chart(
      document.getElementById("stockChart").getContext("2d"),
      {
        type: "line",
        data: { labels, datasets: [{ data: sv, fill: false, borderColor: "#2196f3", pointRadius: 2 }] },
        options: {
          plugins: { legend: { display: false } },
          responsive: false,
          animation: false,  
          scales: {
            y: { beginAtZero: true, min: 50, max: 350, title: { display: true, text: "在庫数" } },
            x: { title: { display: true, text: "日付" } }
          }
        }
      }
    );
    // 価格グラフ
    window.pc = new Chart(
      document.getElementById("priceChart").getContext("2d"),
      {
        type: "line",
        data: { labels, datasets: [{ data: pv, fill: false, borderColor: "#e91e63", pointRadius: 2 }] },
        options: {
          plugins: { legend: { display: false } },
          responsive: false,
          animation: false,  
          scales: {
            y: { beginAtZero: true, min: 10000, max: 40000, title: { display: true, text: "平均価格（円）" } },
            x: { title: { display: true, text: "日付" } }
          }
        }
      }
    );
  }
}

// ========== 最終更新日時（Actions完了時刻を表示） ==========
function updateLastUpdate(){
  const el = document.getElementById("last-update");
  if (!el) return;

  fetch(LASTUPDATED_PATH + "?cb=" + Date.now())
    .then(r => r.ok ? r.json() : Promise.reject("fetch failed"))
    .then(meta => {
      const jst = meta.last_updated_jst || meta.last_updated_iso || "—";
      el.textContent = `最終更新日時：${jst}`;
      const tips = [];
      if (meta.last_updated_iso) tips.push(`ISO: ${meta.last_updated_iso}`);
      if (meta.git_sha)          tips.push(`SHA: ${meta.git_sha}`);
      if (meta.source)           tips.push(`src: ${meta.source}`);
      el.title = tips.join("\n");
    })
    .catch(() => {
      el.textContent = "最終更新日時：—";
      el.title = "last_updated.json の取得に失敗しました";
    });
}

// ========== 起動時初期化 ==========
window.onload = async () => {
  await loadAll();
  initMonth();
  if (!selectedDate) selectedDate = todayIso();
  renderPage();
  updateLastUpdate();        // ← 閲覧時刻ではなく Actions 完了時刻を表示
  setupMonthButtons();
  window.addEventListener('resize', () => { renderPage(); });
};
