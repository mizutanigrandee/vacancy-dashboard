document.addEventListener('DOMContentLoaded', async () => {
  // Load JSON data
  const [vacancyData, eventData, historicalData] = await Promise.all([
    fetch('vacancy_price_cache.json').then(res => res.json()),
    fetch('event_data.json').then(res => res.json()),
    fetch('historical_data.json').then(res => res.json())
  ]);

  // ========== FullCalendarの初期化 ==========
  const calendarEl = document.getElementById('calendar');
  const calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridMonth',
    locale: 'ja',
    events: eventData.map(event => ({
      title: event.title,
      start: event.date,
      className: 'bg-blue-100 border-blue-500'
    })),
    dateClick: function(info) {
      const dateStr = info.dateStr;
      const historical = historicalData.find(h => h.date === dateStr) || { price_history: [] };

      // グラフ描画
      document.getElementById('graphTitle').textContent = `${dateStr} の価格推移`;
      const ctx = document.getElementById('priceChart').getContext('2d');
      // Chart.jsは毎回destroyしなくても複数上書きできるが、必要ならグローバルで管理してdestroyしても良い
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: historical.price_history.map((_, i) => `時点${i + 1}`),
          datasets: [{
            label: '平均価格',
            data: historical.price_history,
            borderColor: '#2563eb',
            fill: false
          }]
        },
        options: {
          responsive: true,
          scales: { y: { beginAtZero: false } }
        }
      });
      document.getElementById('graphModal').classList.remove('hidden');
    },
    eventContent: function(arg) {
      // 日ごとのセル表示カスタム
      const dateStr = arg.event.start.toISOString().split('T')[0];
      const dayData = vacancyData.find(d => d.date === dateStr) || {};
      const flame = dayData.flame ? '🔥' : '';
      // 前日比（必要に応じて追加で表示）
      let diff = '';
      if (dayData.diff && typeof dayData.diff === 'number') {
        diff = dayData.diff > 0 ? `<span style="color:#2196f3;">＋${dayData.diff}</span>` : 
               dayData.diff < 0 ? `<span style="color:#e14040;">－${Math.abs(dayData.diff)}</span>` : '';
      }
      return {
        html: `
          <div class="p-1">
            <div>${arg.event.title || ''}</div>
            <div>空室: ${dayData.vacancy ?? '-'}</div>
            <div>価格: ${dayData.price ?? '-'}</div>
            <div>${flame}</div>
            <div>${diff}</div>
          </div>
        `
      };
    }
  });
  calendar.render();

  // ========== 月切替用セレクタ ==========
  const monthFilter = document.getElementById('monthFilter');
  const months = [...new Set(vacancyData.map(d => d.date.slice(0, 7)))];
  months.forEach(month => {
    const option = document.createElement('option');
    option.value = month;
    option.textContent = month;
    monthFilter.appendChild(option);
  });

  // 月フィルター（ジャンプ）
  monthFilter.addEventListener('change', () => {
    const selectedMonth = monthFilter.value;
    if (selectedMonth) {
      calendar.gotoDate(`${selectedMonth}-01`);
    }
  });

  // リセットボタン
  document.getElementById('resetButton').addEventListener('click', () => {
    monthFilter.value = '';
    calendar.gotoDate(new Date());
  });

  // モーダル閉じる
  document.getElementById('closeModal').addEventListener('click', () => {
    document.getElementById('graphModal').classList.add('hidden');
    const ctx = document.getElementById('priceChart').getContext('2d');
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  });
});
