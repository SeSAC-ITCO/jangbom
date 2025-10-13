const mainBoard = document.getElementById('mainBoard');

let isDown = false;
let startY;
let scrollTop;

mainBoard.addEventListener('mousedown', (e) => {
    isDown = true;
    mainBoard.classList.add('active');
    startY = e.pageY - mainBoard.offsetTop;
    scrollTop = mainBoard.scrollTop;
});

mainBoard.addEventListener('mouseleave', () => {
    isDown = false;
    mainBoard.classList.remove('active');
});

mainBoard.addEventListener('mouseup', () => {
    isDown = false;
    mainBoard.classList.remove('active');
});

mainBoard.addEventListener('mousemove', (e) => {
    if (!isDown) return;
    e.preventDefault();
    const y = e.pageY - mainBoard.offsetTop;
    const walk = (y - startY) * 1; // 스크롤 속도 조절
    mainBoard.scrollTop = scrollTop - walk;
});