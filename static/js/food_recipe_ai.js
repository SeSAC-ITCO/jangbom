document.addEventListener('DOMContentLoaded', () => {
    const input = document.querySelector('.gptInput');
    const keyboardIcon = document.querySelector('.keyboard-icon');
    const foodBtn = document.querySelector('.foodBtn');
    const gptBox = document.getElementById('gptBox');

    // 초기 숨김 상태
    keyboardIcon.style.display = 'none';

    input.addEventListener('input', () => {
        if (input.value.trim() !== "") {
            keyboardIcon.style.display = 'block';
            if (foodBtn) {
                foodBtn.classList.add('up');
            } else {
                // ✅ chat_history가 비어있을 때는 gptBox만 올리기
                const isEmptyChat = document.body.dataset.emptyChat === "true";
                if (isEmptyChat) {
                    gptBox.classList.add('up');
                }
            }
            gptBox.classList.add('up');
        } else {
            keyboardIcon.style.display = 'none';
            if (foodBtn) foodBtn.classList.remove('up');
            gptBox.classList.remove('up');
        }
    });

    document.addEventListener('click', (e) => {
        if (!gptBox.contains(e.target)) {
            keyboardIcon.style.display = 'none';
            if (foodBtn) foodBtn.classList.remove('up');
            gptBox.classList.remove('up');
        }
    });
});
