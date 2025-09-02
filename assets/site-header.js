// assets/site-header.js
(() => {
  const script = document.currentScript;
  const active = script?.dataset?.active || "";

  const CFG = {
    // ▼ ロゴ画像のファイル名に合わせてここを変更
    logo: "assets/バナー画像3.png",
    title: "めちゃいいツール",
    // ▼ メニューのリンク先（本家＝料金カレンダー、他2つは ota-bridge のページ）
    menu: [
      { id: "calendar",  label: "料金カレンダー", path: "https://mizutanigrandee.github.io/vacancy-dashboard/" },
      { id: "reviews",   label: "クチコミ比較",   path: "https://mizutanigrandee.github.io/ota-bridge/reviews.html" },
      { id: "compete",   label: "競合比較",       path: "https://mizutanigrandee.github.io/ota-bridge/daily_preview.html" }
    ]
  };

  const hdr = document.createElement("header");
  hdr.className = "site-header";
  hdr.innerHTML = `
    <div class="wrap">
      <a class="brand" href="${CFG.menu[0].path}">
        <img src="${CFG.logo}" alt="${CFG.title} logo" decoding="async" />
        <strong>${CFG.title}</strong>
      </a>

      <!-- ▼ ここが追加：ハンバーガーボタン -->
      <button class="menu-toggle" aria-label="メニュー">☰</button>

      <nav class="site-nav" role="navigation" aria-label="Main">
        ${CFG.menu.map(m => `<a href="${m.path}" data-mid="${m.id}">${m.label}</a>`).join("")}
      </nav>
    </div>
  `;


  const exist = document.querySelector("header.site-header");
  exist ? exist.replaceWith(hdr) : document.body.prepend(hdr);

    // ▼ ハンバーガー開閉（生成した要素に直接バインド）
  const toggle = hdr.querySelector(".menu-toggle");
  const navEl = hdr.querySelector(".site-nav");
  if (toggle && navEl) {
    toggle.addEventListener("click", () => {
      navEl.classList.toggle("open");
    });
  }


  const hereFile = (location.pathname.split("/").pop() || "").toLowerCase();
  document.querySelectorAll(".site-nav a").forEach(a => {
    const id = a.getAttribute("data-mid");
    const file = (a.getAttribute("href") || "").split("/").pop().toLowerCase();
    if (active === id || file === hereFile) {
      a.classList.add("is-active");
      a.setAttribute("aria-current","page");
    }
  });
})();

// === スマホ用ハンバーガーメニュー ===
document.addEventListener("DOMContentLoaded", ()=>{
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector(".site-nav");

  if(toggle && nav){
    toggle.addEventListener("click", ()=>{
      nav.classList.toggle("open");
    });
  }
});
