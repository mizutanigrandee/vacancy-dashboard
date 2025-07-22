document.addEventListener('DOMContentLoaded', async () => {
  let vacancyData = [], eventData = [], historicalData = [];
  try {
    vacancyData = await fetch('vacancy_price_cache.json').then(res => res.ok ? res.json() : []);
  } catch { vacancyData = []; }
  try {
    eventData = await fetch('event_data.json').then(res => res.ok ? res.json() : []);
  } catch { eventData = []; }
  try {
    historicalData = await fetch('historical_data.json').then(res => res.ok ? res.json() : []);
  } catch { historicalData = []; }

  // データが不正な場合でも必ず配列に
  if (!Array.isArray(eventData)) eventData = [];
  if (!Array.isArray(vacancyData)) vacancyData = [];
  if (!Array.isArray(historicalData)) historicalData = [];

  // カレンダー領域があれば「（データがありません）」と表示
  const cal = document.getElementById('calendar');
  if (cal) {
    cal.innerHTML = `<div style="color:#888; text-align:center; padding:40px 0;">
      （現在表示できるデータがありません）
    </div>`;
  }
});
