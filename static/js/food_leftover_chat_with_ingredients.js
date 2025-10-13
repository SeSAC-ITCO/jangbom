document.addEventListener('DOMContentLoaded', () => {
    // ===== GPT 입력 관련 =====
    const input = document.querySelector('.gptInput');
    const keyboardIcon = document.querySelector('.keyboard-icon');
    const foodBtn = document.querySelector('.foodBtn');
    const gptBox = document.getElementById('gptBox');

    // 초기 숨김
    keyboardIcon.style.display = 'none';

    input.addEventListener('input', () => {
        if (input.value.trim() !== "") {
            keyboardIcon.style.display = 'block';
            foodBtn.classList.add('up');
            gptBox.classList.add('up');
        } else {
            keyboardIcon.style.display = 'none';
            foodBtn.classList.remove('up');
            gptBox.classList.remove('up');
        }
    });

    document.addEventListener('click', (e) => {
        if (!input.contains(e.target)) {
            keyboardIcon.style.display = 'none';
            foodBtn.classList.remove('up');
            gptBox.classList.remove('up');
        }
    });

    // ===== 저장 완료 dialog 관련 =====
    const dialog = document.getElementById("savedRecipeDialog");
    if (dialog) {
        // 모달이 있을 때 화면에 나타내기
        dialog.style.display = "flex";
        dialog.showModal();

        const backBtn = dialog.querySelector("#backBtn");
        const confirmBtn = dialog.querySelector("#confirmBtn");

        if (backBtn) {
            backBtn.addEventListener("click", () => {
                dialog.close();
                dialog.style.display = "none"; // 화면에서 완전히 제거
            });
        }

        if (confirmBtn) {
            confirmBtn.addEventListener("click", () => {
                const href = confirmBtn.getAttribute("data-href");
                dialog.close();
                dialog.style.display = "none";
                if (href) window.location.href = href;
            });
        }
    }
});
