document.addEventListener("DOMContentLoaded", () => {
    const modal = document.querySelector(".modal");      // 모달창
    const userLoc = document.querySelector(".userLoc");  // 주소 설정 영역
    const mainBoard = document.getElementById("mainBoard"); // mainBoard 영역
    const basket = document.querySelector(".basket-container"); // 장바구니

    if (modal && userLoc && mainBoard) {
        // mainBoard 클릭 시 모달 열기
        mainBoard.addEventListener("click", (e) => {
            // userLoc 클릭은 무시
            if (userLoc.contains(e.target)) return;

            e.preventDefault();   // 링크/버튼 기본 동작 막기
            e.stopPropagation();  // 이벤트 버블링 막기
            modal.classList.remove("hidden");
        });

        // 장바구니 클릭 시 모달 열기
        if (basket) {
            basket.addEventListener("click", (e) => {
                e.preventDefault();   // 링크 이동 막기
                e.stopPropagation();  // 이벤트 버블링 막기
                modal.classList.remove("hidden");
            });
        }

        // 모달 배경 클릭 시 닫기
        modal.addEventListener("click", (e) => {
            if (e.target === modal) {
                modal.classList.add("hidden");
            }
        });
    }
});
