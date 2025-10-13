document.addEventListener("DOMContentLoaded", () => {
  // ▼ 드롭다운 완전 비활성화: 항상 펼쳐진 상태로 고정
  // 1) "입구 사진 확인하기" 섹션 고정 펼침
  document.querySelectorAll(".section-title").forEach((section) => {
    section.classList.add("open"); // 항상 펼침
    // 토글 화살표가 버튼처럼 작동하지 않도록 정리
    const arrow = section.querySelector(".center-arrow");
    if (arrow) {
      arrow.removeAttribute("role");
      arrow.removeAttribute("tabindex");
      arrow.style.transform = ""; // 회전 제거
      arrow.style.filter = "";    // 색상 보정 제거
      // 혹시 CSS에서 커서가 pointer면 기본으로 돌리고 싶다면:
      arrow.style.cursor = "default";
      // 기존에 걸린 핸들러가 있을 수도 있으니 안전하게 교체
      const clean = arrow.cloneNode(true);
      arrow.replaceWith(clean);
    }
  });

  // 2) "장바구니 체크리스트" 섹션 고정 펼침
  document.querySelectorAll("h4.section-title2").forEach((heading) => {
    heading.classList.add("open"); // 항상 펼침
    const arrow = heading.querySelector(".center-arrow");
    if (arrow) {
      arrow.removeAttribute("role");
      arrow.removeAttribute("tabindex");
      arrow.style.transform = "";
      arrow.style.filter = "";
      arrow.style.cursor = "default";
      const clean = arrow.cloneNode(true);
      arrow.replaceWith(clean);
    }

    // 연결된 패널도 항상 열림 상태로
    let panel = heading.nextElementSibling;
    if (!panel || !panel.classList.contains("checklist-card")) {
      panel = heading.parentElement?.querySelector(".checklist-card");
    }
    if (panel) {
      panel.classList.add("open");
      // transition 등으로 높이가 0이 되지 않도록 강제
      panel.style.maxHeight = "none";
      panel.style.opacity = "";
      panel.style.overflow = "visible";
    }
  });
});

// ===== 모달 열기/닫기 (유지) =====
document.addEventListener("DOMContentLoaded", () => {
  const scroller = document.querySelector(".app-body"); // 내부 스크롤 컨테이너
  const trigger = document.querySelector(".not-this-mart"); // "사진과 도착지가 다르다면?"
  const modal = document.querySelector(".re-start-modal"); // 오버레이
  const content = modal?.querySelector(".modal-content"); // 모달 카드
  const closeBtn = modal?.querySelector(".closeBtn");
  const callBtn = modal?.querySelector(".callBtn");
  const reNavBtn = modal?.querySelector(".renavigationBtn");

  if (!trigger || !modal || !content) return;

  let lastFocus = null;

  const openModal = () => {
    lastFocus = document.activeElement;
    modal.classList.remove("hidden");
    modal.setAttribute("aria-hidden", "false");
    scroller?.classList.add("no-scroll");
    document.body.classList.add("modal-open");
    (closeBtn || content).focus?.({ preventScroll: true });
  };

  const closeModal = () => {
    modal.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
    scroller?.classList.remove("no-scroll");
    document.body.classList.remove("modal-open");
    lastFocus?.focus?.({ preventScroll: true });
  };

  trigger.addEventListener("click", openModal);
  closeBtn?.addEventListener("click", closeModal);

  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  document.addEventListener("keydown", (e) => {
    if (modal.classList.contains("hidden")) return;

    if (e.key === "Escape") {
      e.preventDefault();
      closeModal();
      return;
    }

    if (e.key === "Tab") {
      const focusables = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (!focusables.length) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  });

  // 필요한 경우 여기에 실제 동작 연결
  callBtn?.addEventListener("click", () => {
    // 예: window.location.href = 'tel:010-0000-0000';
    closeModal();
  });
  reNavBtn?.addEventListener("click", () => {
    // 예: 재네비게이션 트리거
    closeModal();
  });
});
