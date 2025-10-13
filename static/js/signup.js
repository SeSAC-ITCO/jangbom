function goStep(stepNumber) {
    // 모든 step 숨기기
    document.querySelectorAll('.step').forEach(step => step.classList.remove('active'));
    // 선택한 step만 보이기
    document.getElementById(`step${stepNumber}`).classList.add('active');
}


// document.querySelector('.completeBtn').addEventListener('click', () => {
//     window.location.href = '/jangbom/static/html/splash.html';
// });

