

// 검색창 placeholder 숨기기 전용
(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const scope = document.querySelector(".address-search");
    if (!scope) return;

    const input = scope.querySelector(".input-mat"); // textarea
    const label = scope.querySelector(".input-placeholder"); // 회색 안내 문구
    const btn = scope.querySelector(".input-mat-check"); // 돋보기 버튼(선택)

    if (!input || !label) return;

    const hideLabel = () => {
      label.hidden = true;
    };
    const showLabelIfEmpty = () => {
      if (input.value.trim() === "") label.hidden = false;
    };

    input.addEventListener("focus", hideLabel);
    input.addEventListener("input", hideLabel);
    input.addEventListener("blur", showLabelIfEmpty);

    // 돋보기 눌러도 포커스 + 숨김
    if (btn) {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        input.focus();
        hideLabel();
      });
    }

    // 자동완성으로 값이 미리 들어간 경우 초기 상태 맞추기
    if (input.value.trim() !== "") hideLabel();
  });
})();
