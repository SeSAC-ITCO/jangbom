document.addEventListener("DOMContentLoaded", () => {
  const list = document.querySelector(".search-result-list");
  if (!list) return;

  // 카드 클릭 → 저장 POST
  list.addEventListener("click", (e) => {
    const item = e.target.closest(".result-item");
    if (!item) return;

    if (e.target.closest(".field-input") || e.target.closest("label")) return;

    const form = item.querySelector(".result-form");
    if (!form) return;

    if (typeof form.requestSubmit === "function") form.requestSubmit();
    else form.submit();
  });

  list.addEventListener("keydown", (e) => {
    const item = e.target.closest(".result-item");
    if (!item) return;

    if (e.isComposing) return;

    const inDetail = e.target.classList?.contains("field-input");

    if (inDetail && e.key === "Enter") {
      e.preventDefault();
      const form = item.querySelector(".result-form");
      if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
      return;
    }

    if (!inDetail && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      const form = item.querySelector(".result-form");
      if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
    }
  });
});
