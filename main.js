const calendar1El = document.getElementById('calendar1');
const calendar2El = document.getElementById('calendar2');
const graphContainer = document.getElementById('graph-container');
const priceChartEl = document.getElementById('priceChart');
const lastUpdatedEl = document.getElementById('lastUpdated');
const graphDateEl = document.getElementById('graph-date');
let vacancyData = {};
let eventData = [];
let historicalData = {};
let currentMonth = moment().startOf('month');
let selectedDate = null;
let priceChart = null;

// ==== [1] ダミーデータ（本番はfetch可） ====
function loadData() {
  vacancyData = {
    "2025-07-22": { "vacancy": 310, "avg_price": 9458, "previous_vacancy": 320, "previous_avg_price": 9500 },
    "2025-07-23": { "vacancy": 300, "avg_price": 9300, "previous_vacancy": 310, "previous_avg_price": 9400 },
    "2025-07-24": { "vacancy": 290, "avg_price": 9200, "previous_vacancy": 300, "previous_avg_price": 9300 },
    "2025-07-25": { "vacancy": 280, "avg_price": 9100, "previous_vacancy": 290, "previous_avg_price": 9200 }
    // 必要に応じ増やす
  };
  eventData = [
    { date: "2025-07-22", icon: "🔴", name: "京セラ" },
    { date: "2025-07-23", icon: "🔵", name: "ヤンマー" },
    { date: "2025-07-24", icon: "⚫", name: "その他" }
  ];
  historicalData = {
    "2025-07-22": {
      "2025-07-01": { "vacancy": 300, "avg_price": 9000 },
      "2025-07-15": { "vacancy": 310, "avg_price": 9200 },
      "2025-07-22": { "vacancy": 310, "avg_price": 9458 }
    },
    "2025-07-23": {
      "2025-07-01": { "vacancy": 310, "avg_price": 9100 },
      "2025-07-15": { "vacancy": 305, "avg_price": 9250 },
      "2025-07-23": { "vacancy": 300, "avg_price": 9300 }
    }
    // 必要に応じ増やす
  };
  lastUpdatedEl.textContent = `最終更新: ${moment().format('YYYY-MM-DD HH:mm')} JST`;
  renderCalendars();
}

function calculateDemand(vacancy, avgPrice) {
  if (vacancy === '-' || avgPrice === '-') return 0;
  const v = parseInt(vacancy);
  const p = parseInt(avgPrice);
  if (v <= 70 || p >= 50000) return 5;
  if (v <= 100 || p >= 40000) return 4;
  if (v <= 150 || p >= 35000) return 3;
  if (v <= 200 || p >= 30000) return 2;
  if (v <= 250 || p >= 25000) return 1;
  return 0;
}

function getHolidayColor(date) {
  const day = moment(date).day();
  if (day === 0) return '#ffecec'; // 日曜
  if (day === 6) return '#e7f4ff'; // 土曜
  return '#fff';
}

function renderCalendar(el, month) {
  const cal = [];
  cal.push('<div class="calendar-wrapper"><table>');
  cal.push('<thead><tr>');
  for (const d of "日月火水木金土") cal.push(`<th>${d}</th>`);
  cal.push('</tr></thead><tbody>');
  const daysInMonth = month.daysInMonth();
  const startDay = month.startOf('month').day();
  const today = moment().startOf('day');

  for (let w = 0; w < 6; w++) {
    cal.push('<tr>');
    for (let d = 0; d < 7; d++) {
      const day = w * 7 + d - startDay + 1;
      if (day <= 0 || day > daysInMonth) {
        cal.push('<td></td>');
        continue;
      }
      const date = month.date(day).format('YYYY-MM-DD');
      const data = vacancyData[date] || { vacancy: '-', avg_price: '-', previous_vacancy: '-', previous_avg_price: '-' };
      const vacDiff = (data.vacancy !== '-' && data.previous_vacancy !== '-') ? (parseInt(data.vacancy) - parseInt(data.previous_vacancy)) : null;
      const priceDiff = (data.avg_price !== '-' && data.previous_avg_price !== '-') ? Math.round(parseInt(data.avg_price) - parseInt(data.previous_avg_price)) : null;
      const events = eventData.filter(e => e.date === date);
      const demand = calculateDemand(data.vacancy, data.avg_price);
      const bgColor = getHolidayColor(date);
      const isPast = moment(date).isBefore(today);

      cal.push(`
        <td style="background:${bgColor};" onclick="showGraph('${date}')">
          <div class="date-num">${day}</div>
          <div class="cell-vacancy">${data.vacancy === '-' ? '-' : `${data.vacancy}件`}
            ${vacDiff !== null ? `<span class="cell-diff ${vacDiff>=0?'pos':'neg'}">(${vacDiff>=0?'+':''}${vacDiff}件)</span>` : ''}
          </div>
          <div class="cell-price">¥${data.avg_price === '-' ? '-' : parseInt(data.avg_price).toLocaleString()}円
            ${priceDiff !== null ? `<span class="cell-diff ${priceDiff>=0?'pos':'neg'}">${priceDiff>=0?'↑':'↓'}</span>` : ''}
          </div>
          <div class="cell-event">${events.map(e =>
            `<span class="event-icon ${e.icon==='🔴'?'red':e.icon==='🔵'?'blue':'black'}"></span> ${e.name}`).join('<br>')}
          </div>
          ${!isPast && demand > 0 ? `<div class="cell-flame">🔥${'★'.repeat(demand)}</div>` : ''}
        </td>`);
    }
    cal.push('</tr>');
  }
  cal.push('</tbody></table></div>');
  el.innerHTML = cal.join('');
}

function renderCalendars() {
  const month1 = currentMonth.clone();
  const month2 = currentMonth.clone().add(1, 'month');
  renderCalendar(calendar1El, month1);
  renderCalendar(calendar2El, month2);
}

// --- ナビボタン制御 ---
document.getElementById('prevMonth').onclick = () => { currentMonth.add(-1, 'month'); renderCalendars(); };
document.getElementById('currentMonth').onclick = () => { currentMonth = moment().startOf('month'); renderCalendars(); };
document.getElementById('nextMonth').onclick = () => { currentMonth.add(1, 'month'); renderCalendars(); };

// --- グラフ表示 ---
window.showGraph = function(date) {
  selectedDate = date;
  graphContainer.classList.remove('hidden');
  if (priceChart) priceChart.destroy();
  graphDateEl.textContent = `${moment(date).format('YYYY年M月D日')} の推移グラフ`;
  const data = historicalData[date] || {};
  const dates = Object.keys(data).sort();
  const graphData = dates.map(d => ({
    date: d,
    vacancy: data[d].vacancy || 0,
    avg_price: data[d].avg_price || 0
  }));
  priceChart = new Chart(priceChartEl, {
    type: 'line',
    data: {
      labels: graphData.map(d => moment(d.date).format('MM/DD')),
      datasets: [
        { label: '平均価格', data: graphData.map(d => d.avg_price), borderColor: '#e53939', yAxisID: 'y1', fill: false, tension: 0.17, pointRadius: 4 },
        { label: '空室数', data: graphData.map(d => d.vacancy), borderColor: '#488cff', yAxisID: 'y2', fill: false, tension: 0.17, pointRadius: 4 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { title: { display: true, text: '日付' } },
        y1: { type: 'linear', position: 'left', title: { display: true, text: '平均価格(円)' }, ticks: { callback: v => `¥${v.toLocaleString()}` }, beginAtZero: true },
        y2: { type: 'linear', position: 'right', title: { display: true, text: '空室数' }, grid: { drawOnChartArea: false }, beginAtZero: true }
      },
      plugins: { legend: { position: 'top' } }
    }
  });
};

document.getElementById('closeGraph').onclick = () => graphContainer.classList.add('hidden');
document.getElementById('prevDay').onclick = () => {
  if (selectedDate) showGraph(moment(selectedDate).subtract(1, 'day').format('YYYY-MM-DD'));
};
document.getElementById('nextDay').onclick = () => {
  if (selectedDate) showGraph(moment(selectedDate).add(1, 'day').format('YYYY-MM-DD'));
};

document.addEventListener('DOMContentLoaded', loadData);
