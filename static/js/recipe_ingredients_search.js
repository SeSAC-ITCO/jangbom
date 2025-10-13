// recipe_ingredients_search.js
document.addEventListener("DOMContentLoaded", () => {
  const root = document.documentElement;
  const input = document.querySelector(".input-rec"); // 검색창 (textarea)
  const bar = document.querySelector(".add-mat"); // 하단 바
  const dialpad = document.getElementById("dialpad"); // 가짜 키패드

  if (!input || !bar || !dialpad) return;

  const setKeyboardHeight = () => {
    // iOS/안드 네이티브 키보드 높이 추정 → 없으면 가짜 dialpad 높이 사용
    const kb = window.visualViewport
      ? Math.max(0, window.innerHeight - window.visualViewport.height)
      : 0;
    const ph = dialpad.getBoundingClientRect().height || 0;
    root.style.setProperty("--dialpad-h", `${kb || ph}px`);
  };

  const openKeyboardUI = () => {
    dialpad.classList.remove("hidden"); // 가짜 키패드 표시(데스크톱 미리보기)
    document.body.classList.add("keyboard-open");
    bar.classList.add("lifted"); // 하단 바 띄우기
    requestAnimationFrame(setKeyboardHeight);
  };

  const closeKeyboardUI = () => {
    dialpad.classList.add("hidden");
    document.body.classList.remove("keyboard-open");
    bar.classList.remove("lifted");
    root.style.setProperty("--dialpad-h", "0px");
  };

  // 초기 상태는 항상 닫힘
  closeKeyboardUI();

  // 검색창 포커스 시 열기
  input.addEventListener("focus", openKeyboardUI);

  // 바깥 클릭 시 닫기 (검색창/키패드/하단바 제외)
  document.addEventListener("mousedown", (e) => {
    if (!document.body.classList.contains("keyboard-open")) return;
    const inside =
      e.target.closest(".input-rec") ||
      e.target.closest("#dialpad") ||
      e.target.closest(".add-mat");
    if (!inside) {
      input.blur();
      closeKeyboardUI();
    }
  });

  // 화면 높이 변화(네이티브 키보드 열림/닫힘)에 따라 보정
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", () => {
      if (document.body.classList.contains("keyboard-open"))
        setKeyboardHeight();
    });
  }

  // 완료 버튼 누르면 닫기 (원하면 여기서 검색 실행/전송 로직 추가)
  const doneBtn = document.querySelector(".add-item-done");
  doneBtn?.addEventListener("click", () => {
    input.blur();
    closeKeyboardUI();
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const input = document.querySelector(".input-rec");
  const done = document.querySelector(".add-item-done");
  if (!input || !done) return;

  // 초기 상태는 비활성
  const sync = () => {
    const hasText = input.value.trim().length > 0;
    done.disabled = !hasText;
  };

  // 입력 이벤트
  input.addEventListener("input", sync);

  // 페이지 진입/뒤로가기 복원 시도
  window.addEventListener("pageshow", sync);

  // 최초 한 번
  sync();
});
