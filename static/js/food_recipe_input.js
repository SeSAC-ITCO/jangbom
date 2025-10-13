document.addEventListener('DOMContentLoaded', () => {
    const input = document.querySelector('.gptInput');
    const keyboardIcon = document.querySelector('.keyboard-icon');
    const foodBtn = document.querySelector('.foodBtn'); // 재료 담기 버튼
    const selectBtn = document.querySelector('.selectBtn');
    const gptBox = document.getElementById('gptBox');
    const form = document.getElementById('filterForm');
    const hiddenInput = document.querySelector('.ingredientsGet input[name="recipe"]');

    keyboardIcon.style.display = 'none';
    foodBtn.style.display = 'none';

    input.addEventListener('input', () => {
        hiddenInput.value = input.value;
    });

    // input 글자 체크
    input.addEventListener('input', () => {
        const hasText = input.value.trim() !== "";
        keyboardIcon.style.display = hasText ? 'block' : 'none';
        foodBtn.style.display = hasText ? 'flex' : 'none';
        selectBtn.classList.toggle('hidden', hasText);
        gptBox.classList.toggle('up', hasText);
    });

    // 외부 클릭 시 초기화
    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !form.contains(e.target)) {
            keyboardIcon.style.display = 'none';
            foodBtn.style.display = 'none';
            selectBtn.classList.remove('hidden');
            gptBox.classList.remove('up');
            input.value = '';
        }
    });

    // form submit은 기본 동작 유지
    foodBtn.addEventListener('click', () => {
        form.submit(); // 재료 담기 버튼 클릭 시 submit 강제
    });
});



