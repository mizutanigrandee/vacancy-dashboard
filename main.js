const calendarEl = document.getElementById('calendar');
let vacancyData = [];
let eventData = [];
let historicalData = [];

async function loadData() {
  try {
    // JSONデータの読み込み
    const vacancyResponse = await fetch('vacancy_price_cache.json');
    vacancyData = await vacancyResponse.json();

    const historicalResponse = await fetch('historical_data.json');
    historicalData = await historicalResponse.json();

    // Excelデータの読み込み
    const eventResponse = await fetch('event_data.xlsx');
    const arrayBuffer = await eventResponse.arrayBuffer();
    const workbook = XLSX.read(new Uint8Array(arrayBuffer), { type: 'array' });
    eventData = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]]);
  } catch (error) {
    console.error('データ読み込みエラー:', error);
  }
  renderCalendar();
  renderGraph();
}

function renderCalendar() {
  const today = moment();
  let html = '<div class="grid grid-cols-7 gap-1 text-center">';
  html += '<div class="col-span-7 flex justify-between mb-2">';
  html += `<button onclick="changeMonth(-1)" class="px-4 py-2 bg-blue-500 text-white rounded">&lt;</button>`;
  html += `<h2 class="text-xl">${today.format('YYYY年MM月')}</h2>`;
  html += `<button onclick="changeMonth(1)" class="px-4 py-2 bg-blue-500 text-white rounded">&gt;</button>`;
  html += '</div>';

  // 曜日ヘッダ
  const days = ['日', '月', '火', '水', '木', '金', '土'];
  days.forEach(day => {
    html += `<div class="font-bold">${day}</div>`;
  });

  // カレンダー生成
  const startOfMonth = today.clone().startOf('month');
  const endOfMonth = today.clone().endOf('month');
  const startWeek = startOfMonth.day();
  const daysInMonth = endOfMonth.date();

  // 空白セル
  for (let i = 0; i < startWeek; i++) {
    html += '<div></div>';
  }

  // 日付セル
  for (let day = 1; day <= daysInMonth; day++) {
    const date = today.clone().date(day).format('YYYY-MM-DD');
    const data = vacancyData.find(d => d.date === date) || { vacancy: '-', avg_price: '-' };
    const prevData = vacancyData.find(d => d.date === moment(date).subtract(1, 'day').format('YYYY-MM-DD')) || {};
    const priceDiff = data.avg_price !== '-' && prevData.avg_price ? data.avg_price - prevData.avg_price : null;
    const event = eventData.find(e => e.date === date);
    
    html += `
      <div class="p-2 border rounded relative hover:bg-gray-100">
        <div class="text-right">${day}</div>
        <div>空室: ${data.vacancy}</div>
        <div>価格: ${data.avg_price}円</div>
        ${priceDiff !== null ? `<div class="${priceDiff >= 0 ? 'text-red-500' : 'text-green-500'}">
          ${priceDiff >= 0 ? '+' : ''}${priceDiff}円</div>` : ''}
        ${event ? `<div class="text-xs text-blue-500">${event.event_name}</div>` : ''}
      </div>`;
  }
  html += '</div>';
  calendarEl.innerHTML = html;
}

function changeMonth(offset) {
  moment().add(offset, 'months');
  renderCalendar();
}

function renderGraph() {
  const ctx = document.getElementById('priceChart').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: historicalData.map(d => d.date),
      datasets: [
        {
          label: '平均価格',
          data: historicalData.map(d => d.avg_price),
          borderColor: 'blue',
          fill: false
        },
        {
          label: '空室数',
          data: historicalData.map(d => d.vacancy),
          borderColor: 'green',
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      scales: {
        x: { title: { display: true, text: '日付' } },
        y: { title: { display: true, text: '値' } }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', loadData);
