document.addEventListener("DOMContentLoaded", function() {
    const dropdown = document.querySelector(".dropdown");
    const btn = dropdown.querySelector(".dropdownNow");
    const span = btn.querySelector("span"); // 텍스트 부분
    const menu = dropdown.querySelector(".dropdown-menu");
    const hiddenSelect = document.getElementById("periodSelect");

    // 드롭다운 버튼 클릭 → 메뉴 토글
    btn.addEventListener("click", () => {
        menu.style.display = (menu.style.display === "block") ? "none" : "block";
    });

    // 메뉴 항목 클릭 → span 텍스트 변경, select 값 변경, 폼 제출
    menu.querySelectorAll("li").forEach(li => {
        li.addEventListener("click", () => {
            span.innerText = li.innerText;   // span만 변경
            hiddenSelect.value = li.dataset.value;
            menu.style.display = "none";
            hiddenSelect.form.submit();
        });
    });

    // 외부 클릭 시 메뉴 닫기
    document.addEventListener("click", (e) => {
        if (!dropdown.contains(e.target)) {
            menu.style.display = "none";
        }
    });

    // 최신순/금액순 클릭 시 active 표시
    const sortLabels = document.querySelectorAll(".sort-label");
    sortLabels.forEach(label => {
        label.addEventListener("click", () => {
            sortLabels.forEach(l => l.classList.remove("active"));
            label.classList.add("active");
            label.querySelector("input").checked = true;
            label.querySelector("input").form.submit();
        });
    });

    // 페이지 로드 시 최신순 기본 active 설정
    const latestLabel = document.querySelector('input[name="sort"][value="latest"]').closest(".sort-label");
    latestLabel.classList.add("active");
});
