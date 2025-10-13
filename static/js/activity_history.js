"use strict";

/* ===== 버전/패턴 로그 ===== */
console.info("activity_history.js loaded v10");
console.log("ajaxPattern =>", window.ACTIVITY_DETAIL_URL_PATTERN || window.ajaxPattern);

/* ===== 공통 유틸 ===== */
const DURATION = 280;
const baseH = new WeakMap();       // 카드 높이 저장
const busyRows = new WeakSet();    // 애니 중복 방지
const lockRow = (row, on) => (row.style.pointerEvents = on ? "none" : "");

const onTransitionEnd = (el, prop) =>
  new Promise((resolve) => {
    const h = (e) => {
      if (!prop || e.propertyName === prop) {
        el.removeEventListener("transitionend", h);
        resolve();
      }
    };
    el.addEventListener("transitionend", h);
  });

/* ===== URL 패턴 유틸 ===== */
function getDetailPattern() {
  return window.ACTIVITY_DETAIL_URL_PATTERN || window.ajaxPattern || "";
}
function makeDetailUrl(id) {
  const sid = String(id || "");
  if (!sid) return "";
  const p = getDetailPattern();
  if (!p) return "";
  if (p.includes("__ID__")) return p.replace("__ID__", sid);
  if (/\/0\/?$/.test(p)) return p.replace(/\/0\/?$/, `/${sid}/`);
  return p.replace("0", sid);
}

/* ===== 표시용 포매터 ===== */
const _nf = new Intl.NumberFormat("ko-KR");
const _int = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? Math.trunc(n) : 0;
};
const _flt1 = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? Math.round(n * 10) / 10 : 0;
};
const _fmt = (n, unit = "") => (unit ? `${_nf.format(n)} ${unit}` : _nf.format(n));
const _fmtPoint = (p) => `+ ${_nf.format(Math.max(0, _int(p)))} P`;

/* ===== 상세 패널 ===== */
function makeActivityPanel(name, dateText, data) {
  const d = data || {};
  const steps   = _int(d.steps);
  const minutes = _int(d.travel_minutes);
  const kcal    = _flt1(d.calories_kcal);
  const point   = _int(d.point_earned);
  const items   = Array.isArray(d.ingredients) ? d.ingredients : [];

  const panel = document.createElement("div");
  panel.className = "activity-detail-inline";
  Object.assign(panel.style, {
    flexBasis: "100%",
    width: "100%",
    marginTop: "10px",
    paddingTop: "10px",
    borderTop: "1px solid #e9e9e9",
    fontSize: "14px",
    lineHeight: "1.55",
    opacity: "0",
    transition: `opacity ${DURATION}ms ease`,
  });

  panel.innerHTML = `
    <div class="detail-body">
      <div style="display:flex; align-items:center; gap:8px; margin:0 0 10px;">
        <span style="font-size:16px">📝</span>
        <h4 style="margin:0; font-size:15px;">걷기 기록</h4>
      </div>

      <div style="display:grid; grid-template-columns:1fr auto; row-gap:8px; column-gap:12px; margin-bottom:12px;">
        <div style="color:#4b5563;">이동 시간</div>
        <div style="justify-self:end; color:#111827;">${_fmt(minutes, "분")}</div>

        <div style="color:#4b5563;">걸음 수</div>
        <div style="justify-self:end; color:#111827;">${_fmt(steps, "걸음")}</div>

        <div style="color:#4b5563;">소모 칼로리</div>
        <div style="justify-self:end; color:#111827;">${_fmt(kcal, "kcal")}</div>

        <div style="color:#4b5563;">획득 포인트</div>
        <div style="justify-self:end; color:#5b8f00; font-weight:700;">${_fmtPoint(point)}</div>
      </div>

      ${
        items.length
          ? `
            <div style="display:flex; align-items:center; gap:8px; margin:14px 0 8px;">
              <span style="font-size:16px">🍽️</span>
              <h4 style="margin:0; font-size:15px;">구매한 식재료</h4>
            </div>
            <ul style="list-style:none; padding:0; margin:0; border:1px solid #eee; border-radius:10px; overflow:hidden;">
              ${items.map((x) => `<li style="padding:10px 12px; border-bottom:1px solid #eee;">${x}</li>`).join("")}
            </ul>
          `
          : ""
      }
    </div>
  `;
  const lis = panel.querySelectorAll("ul > li");
  if (lis.length) lis[lis.length - 1].style.borderBottom = "0";
  return panel;
}

/* ===== 하단 CTA ===== */
let fridgeCta = null;
function ensureCTA() {
  if (fridgeCta) return fridgeCta;
  const parent = document.querySelector(".box") || document.body;

  fridgeCta = document.createElement("div");
  fridgeCta.id = "fridgeCta";
  Object.assign(fridgeCta.style, {
    position: "sticky",
    bottom: "65px",
    width: "393px",
    height: "122px",
    zIndex: "45",
    padding: "14px",
    background: "#fff",
    boxShadow: "0 6px 22px rgba(0,0,0,.08)",
    display: "none",
  });

  const msg = document.createElement("p");
  msg.textContent = "아직 냉장고에 식재료가 남아있나요?";
  Object.assign(msg.style, {
    margin: "0 0 10px",
    textAlign: "center",
    color: "#545454",
    fontSize: "16px",
    fontWeight: "600",
  });

  const btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = "기존 식재료로 요리법 찾기";
  btn.className = "fridge-cta-btn";
  Object.assign(btn.style, {
    width: "271px",
    padding: "14px 16px",
    display: "block",
    margin: "0 auto",
    borderRadius: "12px",
    border: "0",
    background: "#cce7a3",
    fontWeight: "600",
    fontSize: "20px",
    color: "#fff",
    cursor: "pointer",
  });
  btn.addEventListener("click", () => {
    console.log("[CTA] 기존 식재료로 요리법 찾기");
  });

  fridgeCta.append(msg, btn);
  const bottomNav = document.querySelector(".bottom-nav");
  if (bottomNav && bottomNav.parentElement === parent) parent.insertBefore(fridgeCta, bottomNav);
  else parent.appendChild(fridgeCta);
  return fridgeCta;
}
function showCTA() { ensureCTA().style.display = "block"; }
function hideCTA() { if (fridgeCta) fridgeCta.style.display = "none"; }
function updateCTAVisibility() {
  document.querySelector(".recipes_list.open") ? showCTA() : hideCTA();
}

/* ===== 데이터 로딩 (views.py 스키마에 맞춤) ===== */
async function loadRowDataOnce(card) {
  if (card._detailData) return card._detailData;

  // ✔ data-id는 .history-row에 있음
  const host = card.closest(".history-row") || card;
  const id = host?.dataset?.id;

  // id 없으면 카드에 내려온 data-* 값으로라도 표시 (없으면 0)
  if (!id) {
    const ds = host.dataset || {};
    console.warn("[activity_history] shopping_list id 없음. 카드 데이터로 표시");
    card._detailData = {
      point_earned: _int(ds.point ?? 0),
      travel_minutes: ds.travel !== "" ? _int(ds.travel) : 0,
      steps: ds.steps !== "" ? _int(ds.steps) : 0,
      calories_kcal: ds.kcal !== "" ? _flt1(ds.kcal) : 0,
      ingredients: [],
    };
    return card._detailData;
  }

  const url = makeDetailUrl(id);
  try {
    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
      redirect: "follow",
    });
    const ct = res.headers.get("content-type") || "";
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    if (!ct.includes("application/json")) {
      const peek = (await res.text()).slice(0, 200);
      throw new Error("Non-JSON: " + peek);
    }
    const raw = await res.json();
    const data = {
      point_earned: _int(raw.point_earned),
      travel_minutes: _int(raw.travel_minutes),
      steps: _int(raw.steps),
      calories_kcal: _flt1(raw.calories_kcal),
      ingredients: Array.isArray(raw.ingredients) ? raw.ingredients : [],
    };
    card._detailData = data;
    return data;
  } catch (e) {
    console.error("[activity_history] fetch 실패:", e);
    card._detailData = { point_earned: 0, travel_minutes: 0, steps: 0, calories_kcal: 0, ingredients: [] };
    return card._detailData;
  }
}

/* ===== 아코디언 닫기 ===== */
async function closeRow(card) {
  if (busyRows.has(card)) return;
  busyRows.add(card);
  lockRow(card, true);

  try {
    const arrow = card.querySelector(".see-detail");
    const panel = card.querySelector(".activity-detail-inline");
    card.style.overflow = "hidden";

    if (panel) {
      panel.style.transition = `opacity ${DURATION}ms ease`;
      panel.style.opacity = "0";
    }

    const base = baseH.get(card) ?? card.offsetHeight;
    card.style.transition = `height ${DURATION}ms ease`;
    card.style.height = `${base}px`;

    if (arrow) {
      arrow.style.transition = "transform .2s ease, filter .2s ease, opacity .2s ease";
      arrow.style.transform = "none";
      arrow.style.filter = "";
      arrow.style.opacity = "0.45";
    }

    await Promise.all([
      onTransitionEnd(card, "height"),
      panel ? onTransitionEnd(panel, "opacity") : Promise.resolve(),
    ]);

    panel?.remove();
    card.style.flexWrap = "";
    card.style.overflow = "";
    card.classList.remove("open");
  } finally {
    busyRows.delete(card);
    lockRow(card, false);
    updateCTAVisibility();
  }
}

/* ===== 아코디언 열기 ===== */
async function openRowWithDetail(card) {
  if (busyRows.has(card)) return;
  busyRows.add(card);
  lockRow(card, true);

  try {
    card.querySelectorAll(".activity-detail-inline").forEach((n) => n.remove());

    if (!baseH.has(card)) baseH.set(card, card.offsetHeight);
    const start = baseH.get(card) ?? card.offsetHeight;

    card.style.height = `${start}px`;
    card.style.overflow = "hidden";
    card.style.flexWrap = "wrap";
    card.style.transition = `height ${DURATION}ms ease`;

    const name = card.querySelector(".menu_name")?.textContent.trim() || "";
    const dateText = card.querySelector(".menu_date")?.textContent.trim() || "";
    const data = await loadRowDataOnce(card);
    const panel = makeActivityPanel(name, dateText, data);
    card.appendChild(panel);

    const arrow = card.querySelector(".see-detail");
    if (arrow) {
      arrow.style.transition = "transform .2s ease, filter .2s ease, opacity .2s ease";
      arrow.style.transform = "rotate(90deg)";
      arrow.style.filter = "brightness(0)";
      arrow.style.opacity = "1";
    }

    requestAnimationFrame(() => {
      const extra = panel.scrollHeight + 10;
      card.style.height = `${start + extra}px`;
      panel.style.opacity = "1";
    });

    card.classList.add("open");

    setTimeout(() => {
      panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
      setTimeout(() => {
        if (card.classList.contains("open")) card.style.overflow = "";
      });
    }, 0);
  } finally {
    busyRows.delete(card);
    lockRow(card, false);
    updateCTAVisibility();
  }
}

/* ===== DOMContentLoaded: rows(래퍼) 기준 정렬/필터/토글 ===== */
document.addEventListener("DOMContentLoaded", () => {
  const rangeBtn  = document.getElementById("rangeBtn");
  const rangeMenu = document.getElementById("rangeMenu");
  const rangeItems = Array.from(rangeMenu?.querySelectorAll(".range-item") || []);
  const listWrap  = document.querySelector(".list-set");

  // ✅ 카드(.recipes_list)가 아니라 래퍼(.history-row) 기준
  const rows = Array.from(listWrap?.querySelectorAll(".history-row") || []);

  const latestTab = document.querySelector(".search-filter .lately");
  const alphaTab  = document.querySelector(".search-filter .abc");
  if (!rangeBtn || !rangeMenu || !rows.length || !latestTab || !alphaTab) return;

  // 날짜 파서
  const parseDate = (str) => {
    const m = String(str || "")
      .trim()
      .match(/(\d{4})[.\-\/](\d{2})[.\-\/](\d{2})\s+(\d{2}):(\d{2})/);
    if (!m) return 0;
    const [, y, M, d, h, min] = m;
    return new Date(`${y}-${M}-${d}T${h}:${min}:00`).getTime();
  };

  const cardOf  = (row) => row.querySelector(".recipes_list");
  const getTitle = (row) => cardOf(row)?.querySelector(".menu_name")?.textContent.trim() || "";
  const getTime  = (row) => {
    let ts = row.dataset.ts ? Number(row.dataset.ts) : NaN;
    if (Number.isNaN(ts)) {
      ts = parseDate(cardOf(row)?.querySelector(".menu_date")?.textContent);
      row.dataset.ts = String(ts);
    }
    return ts;
  };

  // 원래 순서 기억(숨김 복원용)
  rows.forEach((row, i) => (row._idx = i));

  // === 범위 드롭다운 ===
  const onDocClick = (e) => { if (!e.target.closest(".range-dropdown")) closeMenu(); };
  const onEscClose = (e) => { if (e.key === "Escape") closeMenu(); };
  const openMenu = () => {
    rangeMenu.hidden = false;
    rangeBtn.setAttribute("aria-expanded", "true");
    document.addEventListener("click", onDocClick);
    document.addEventListener("keydown", onEscClose);
  };
  const closeMenu = () => {
    rangeMenu.hidden = true;
    rangeBtn.setAttribute("aria-expanded", "false");
    document.removeEventListener("click", onDocClick);
    document.removeEventListener("keydown", onEscClose);
  };
  const toggleMenu = () => (rangeMenu.hidden ? openMenu() : closeMenu());
  rangeBtn.addEventListener("click", toggleMenu);

  const calcSince = (value) => {
    const now = new Date();
    const since = new Date(now);
    switch (value) {
      case "1m": since.setMonth(now.getMonth() - 1); break;
      case "3m": since.setMonth(now.getMonth() - 3); break;
      case "6m": since.setMonth(now.getMonth() - 6); break;
      case "1y": since.setFullYear(now.getFullYear() - 1); break;
      case "all": return 0;
      default: return 0;
    }
    return since.getTime();
  };

  const applyRangeFilter = (value) => {
    const sinceTs = calcSince(value);
    rows.forEach((row) => {
      const ts = getTime(row);
      const visible = value === "all" ? true : ts >= sinceTs;
      row.style.display = visible ? "" : "none";
    });
  };

  const selectRange = (li) => {
    rangeItems.forEach((el) => {
      const on = el === li;
      el.classList.toggle("is-selected", on);
      el.setAttribute("aria-selected", on ? "true" : "false");
    });
    rangeBtn.childNodes[0].nodeValue = (li.textContent || "").trim() + " ";
    rangeBtn.dataset.value = li.dataset.value || "";
    applyRangeFilter(li.dataset.value || "all");
    closeMenu();
  };

  rangeItems.forEach((li) => li.addEventListener("click", () => selectRange(li)));
  const initialRange = rangeItems.find((el) => el.classList.contains("is-selected")) || rangeItems[0];
  if (initialRange) selectRange(initialRange);

  // === 최신순/가나다순 정렬 ===
  const setActiveTab = (btn) => {
    [latestTab, alphaTab].forEach((el) => {
      const on = el === btn;
      el.classList.toggle("is-active", on);
      el.classList.toggle("on", on);
      el.setAttribute("aria-selected", on ? "true" : "false");
    });
  };

  const sortList = (mode) => {
    const visible = rows.filter((r) => r.style.display !== "none");
    const hidden  = rows.filter((r) => r.style.display === "none");

    const sorted = visible.slice().sort((a, b) => {
      if (mode === "alpha") {
        return getTitle(a).localeCompare(getTitle(b), "ko", {
          sensitivity: "base",
          numeric: true,
        });
      }
      return getTime(b) - getTime(a); // 최신순
    });

    // 래퍼(.history-row)를 다시 붙임 (dataset 유지)
    sorted.forEach((row) => listWrap.appendChild(row));
    hidden.sort((a, b) => a._idx - b._idx).forEach((row) => listWrap.appendChild(row));
  };

  setActiveTab(latestTab);
  sortList("latest");
  latestTab.addEventListener("click", () => { setActiveTab(latestTab); sortList("latest"); });
  alphaTab.addEventListener("click", () => { setActiveTab(alphaTab); sortList("alpha"); });

  // === 리스트 토글(열기/닫기) ===
  if (listWrap) {
    listWrap.addEventListener("click", (e) => {
      const card = e.target.closest(".recipes_list");
      if (!card) return;
      card.classList.contains("open") ? closeRow(card) : openRowWithDetail(card);
    });

    listWrap.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      const card = e.target.closest(".recipes_list");
      if (!card) return;
      e.preventDefault();
      card.classList.contains("open") ? closeRow(card) : openRowWithDetail(card);
    });
  }

  document.querySelector(".top-back")?.addEventListener("click", () => {
    document.querySelectorAll(".recipes_list.open").forEach((card) => closeRow(card));
  });

  if (typeof initRangeDropdown === "function") initRangeDropdown();
});

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