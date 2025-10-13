// input 입력시 키보드 올라감

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
            gptBox.classList.add('up');
        } else {
            keyboardIcon.style.display = 'none';
            gptBox.classList.remove('up');
        }
    });

    // input 외부 클릭 시 원래 상태로 돌아오기
    document.addEventListener('click', (e) => {
        if (!input.contains(e.target)) { // 클릭한 곳이 input이 아니면
            keyboardIcon.style.display = 'none';
            gptBox.classList.remove('up');
        }
    });
});



// 사용자 질문 입력시 메시지 추가하는 합수
const nameParam = encodeURIComponent("{{ name }}");
const apiBase   = "{% url 'food:ingredient_idea_api' %}";

// 메시지 추가 함수
function append(role, text) {
    const wrap = document.querySelector(".chatBoard"); // #chat 대신 기존 chatBoard 사용

    const msgDiv = document.createElement("div");
    msgDiv.className = role === "user" ? "userMsg" : "gptMsg";

    const p = document.createElement("p");
    p.textContent = text;

    msgDiv.appendChild(p);
    wrap.appendChild(msgDiv);

    // 스크롤 최하단으로 이동
    wrap.scrollTop = wrap.scrollHeight;
}

// 초기 추천 메시지 불러오기
// async function fetchInitial() {
//     try {
//         const res = await fetch(`${apiBase}?name=${nameParam}`);
//         const data = await res.json();
//         if (data.ok) {
//             append("assistant", data.text);
//         } else {
//             append("assistant", "초기 추천을 불러오지 못했습니다.");
//         }
//     } catch (e) {
//         append("assistant", "네트워크 오류가 발생했습니다.");
//     }
// }

// // 사용자가 질문 입력 시
// document.getElementById("ask-form").addEventListener("submit", async (e) => {
//     e.preventDefault();
//     const input = document.getElementById("ask-input");
//     const q = input.value.trim();
//     if (!q) return;

//     append("user", q);
//     input.value = "";

//     try {
//         const res = await fetch(`${apiBase}?name=${nameParam}&q=${encodeURIComponent(q)}`);
//         const data = await res.json();
//         if (data.ok) {
//             append("assistant", data.text);
//         } else {
//             append("assistant", "답변을 불러오지 못했습니다.");
//         }
//     } catch (err) {
//         append("assistant", "네트워크 오류가 발생했습니다.");
//     }
// });

// // 페이지 로드 시 초기 메시지 불러오기
// fetchInitial();

