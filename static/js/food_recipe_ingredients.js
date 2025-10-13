const mainBoard = document.getElementById('mainBoard');

let isDragging = false;
let startY;
let scrollTop;

mainBoard.addEventListener('mousedown', (e) => {
  isDragging = true;
  mainBoard.classList.add('dragging');
  startY = e.pageY - mainBoard.offsetTop;
  scrollTop = mainBoard.scrollTop;
  e.preventDefault(); // 텍스트 선택 방지
});

mainBoard.addEventListener('mouseleave', () => {
  isDragging = false;
  mainBoard.classList.remove('dragging');
});

mainBoard.addEventListener('mouseup', () => {
  isDragging = false;
  mainBoard.classList.remove('dragging');
});

mainBoard.addEventListener('mousemove', (e) => {
  if(!isDragging) return;
  e.preventDefault();
  const y = e.pageY - mainBoard.offsetTop;
  const walk = y - startY;
  mainBoard.scrollTop = scrollTop - walk;
});
