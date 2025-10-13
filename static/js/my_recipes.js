// 최신순/가나다순
document.addEventListener("DOMContentLoaded", () => {
  const latestTab = document.querySelector(".search-filter .lately");
  const alphaTab  = document.querySelector(".search-filter .abc");
  const list      = document.querySelector(".list-set");
  if (!latestTab || !alphaTab || !list) return;

  const items = Array.from(list.querySelectorAll(".recipes_list"));
  items.forEach((el, i) => (el._idx = i));

  const getTitle = (el) => el.querySelector(".menu_name")?.textContent.trim() || "";
  const getDate  = (el) => {
    const raw = el.querySelector(".menu_date")?.textContent.trim() || "";
    const m = raw.match(/(\d{4})[.\-/](\d{2})[.\-/](\d{2})/);
    return m ? new Date(`${m[1]}-${m[2]}-${m[3]}`).getTime() : 0;
  };

  // ★ 활성 표시: .is-active 뿐 아니라 .on 도 함께 토글
  const setActive = (activeEl) => {
    [latestTab, alphaTab].forEach((el) => {
      const on = el === activeEl;
      el.classList.toggle("is-active", on);
      el.classList.toggle("on", on);                 // ← 핵심
      el.setAttribute("aria-selected", on ? "true" : "false");
      el.setAttribute("role", "tab");
    });
    latestTab.parentElement?.setAttribute("role", "tablist");
  };

  const sortList = (mode) => {
    const sorted = items.slice().sort((a, b) => {
      return mode === "alpha"
        ? getTitle(a).localeCompare(getTitle(b), "ko", { sensitivity: "base", numeric: true })
        : getDate(b) - getDate(a);
    });
    sorted.forEach((el) => list.appendChild(el));
  };

  // ★ 초기 모드: URL ?sort= 또는 기존 클래스(on/is-active)에서 결정
  const getInitialMode = () => {
    const s = new URLSearchParams(location.search).get("sort");
    if (s === "alpha" || s === "latest") return s;
    if (alphaTab.classList.contains("on") || alphaTab.classList.contains("is-active")) return "alpha";
    return "latest";
  };

  const applySort = (mode) => {
    setActive(mode === "alpha" ? alphaTab : latestTab);
    sortList(mode);
  };

  latestTab.addEventListener("click", (e) => {
    // e.preventDefault(); // JS만으로 동작시키고 싶으면 주석 해제
    applySort("latest");
  });
  alphaTab.addEventListener("click", (e) => {
    // e.preventDefault();
    applySort("alpha");
  });

  applySort(getInitialMode()); // 초기 표시/정렬
});


// 요리법 상세 내용
// ★ 하드코딩 제거: recipesData, fetchRecipeDataForRow 전부 삭제 ★

const DURATION = 280;
const baseH = new WeakMap();
const busyRows = new WeakSet();
const lockRow = (row, on) => (row.style.pointerEvents = on ? "none" : "");

const onTransitionEnd = (el, prop) =>
  new Promise((resolve) => {
    const h = (e) => { if (!prop || e.propertyName === prop) { el.removeEventListener("transitionend", h); resolve(); } };
    el.addEventListener("transitionend", h);
  });

function makeInlinePanelFromAjax(data) {
  const title = data?.title ?? "";
  const desc  = data?.description ?? "";
  const panel = document.createElement("div");
  panel.className = "recipe-detail-inline";
  Object.assign(panel.style, {
    flexBasis: "100%", width: "100%",
    marginTop: "10px", paddingTop: "10px",
    borderTop: "1px solid #e9e9e9",
    fontSize: "14px", lineHeight: "1.55",
    opacity: "0", transition: `opacity ${DURATION}ms ease`,
  });
  panel.innerHTML = `
    <div class="detail-body">
      ${title ? `<p style="margin:0 0 10px;font-weight:700">🍳 ${title}</p>` : ""}
      ${desc ? `<pre style="white-space:pre-wrap;margin:0">${desc}</pre>` : "<p style='margin:0;color:#6b7280'>상세 내용이 없습니다.</p>"}
    </div>
  `;
  return panel;
}

async function closeRow(row) {
  if (busyRows.has(row)) return;
  busyRows.add(row); lockRow(row, true);
  try {
    const arrow = row.querySelector(".see-detail");
    const panel = row.querySelector(".recipe-detail-inline");
    row.style.overflow = "hidden";
    if (panel) { panel.style.transition = `opacity ${DURATION}ms ease`; panel.style.opacity = "0"; }
    const base = baseH.get(row) ?? row.offsetHeight;
    row.style.transition = `height ${DURATION}ms ease`;
    row.style.height = `${base}px`;
    if (arrow) { arrow.style.transition = "transform .2s, filter .2s, opacity .2s"; arrow.style.transform = "none"; arrow.style.filter = ""; arrow.style.opacity = "0.45"; }
    await Promise.all([ onTransitionEnd(row, "height"), panel ? onTransitionEnd(panel, "opacity") : Promise.resolve() ]);
    panel?.remove();
    row.style.flexWrap = ""; row.style.overflow = ""; row.classList.remove("open");
  } finally { busyRows.delete(row); lockRow(row, false); }
}

async function openRowWithDetail(row) {
  if (busyRows.has(row)) return;
  busyRows.add(row); lockRow(row, true);
  try {
    row.querySelectorAll(".recipe-detail-inline").forEach((n) => n.remove());
    if (!baseH.has(row)) baseH.set(row, row.offsetHeight);
    const start = baseH.get(row) ?? row.offsetHeight;

    row.style.height = `${start}px`;
    row.style.overflow = "hidden";
    row.style.flexWrap = "wrap";
    row.style.transition = `height ${DURATION}ms ease`;

    // ★ 백엔드에서만 데이터 로드
    const url = row.dataset.ajax || (row.dataset.id ? `/accounts/recipes/${row.dataset.id}/ajax/` : "");
    let data = {};
    if (url) {
      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      data = await res.json();
    }

    const panel = makeInlinePanelFromAjax(data);
    row.appendChild(panel);

    const arrow = row.querySelector(".see-detail");
    if (arrow) { arrow.style.transition = "transform .2s, filter .2s, opacity .2s"; arrow.style.transform = "rotate(90deg)"; arrow.style.filter = "brightness(0)"; arrow.style.opacity = "1"; }

    requestAnimationFrame(() => {
      const extra = panel.scrollHeight + 10;
      row.style.height = `${start + extra}px`;
      panel.style.opacity = "1";
    });

    row.classList.add("open");

    setTimeout(() => {
      panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
      setTimeout(() => { if (row.classList.contains("open")) row.style.overflow = ""; });
    }, 0);
  } finally { busyRows.delete(row); lockRow(row, false); }
}

// 이벤트 바인딩: 이동 방지 필수
const listSet = document.querySelector(".list-set");
if (listSet) {
  listSet.addEventListener("click", (e) => {
    const row = e.target.closest(".recipes_list");
    if (!row) return;
    e.preventDefault();                       // ★ JSON 페이지로 튕김 방지
    if (row.classList.contains("open")) closeRow(row);
    else openRowWithDetail(row);
  });

  listSet.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const row = e.target.closest(".recipes_list");
    if (!row) return;
    e.preventDefault();
    if (row.classList.contains("open")) closeRow(row);
    else openRowWithDetail(row);
  });
}

document.querySelector(".top-back")?.addEventListener("click", () => {
  document.querySelectorAll(".recipes_list.open").forEach((row) => closeRow(row));
});