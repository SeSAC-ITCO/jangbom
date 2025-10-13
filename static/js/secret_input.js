document.addEventListener("DOMContentLoaded", () => {
  const form       = document.getElementById("confirmForm");
  const pwBox      = document.getElementById("pwNums");
  const btnNext    = document.getElementById("submitBtn");
  const dialpad    = document.getElementById("dialpad");
  const boxes      = Array.from(document.querySelectorAll(".pw-num"));
  const pinError   = document.getElementById("pinError");
  const success    = document.getElementById("confirmSuccess");
  const okBtn      = document.getElementById("confirmOkBtn");
  const passwordEl = document.getElementById("passwordField");
  const stateEl    = document.getElementById("state");
  const root       = document.documentElement;

  let hidden = document.getElementById("pinHidden");
  if (!hidden) {
    hidden = document.createElement("input");
    hidden.type = "tel";
    hidden.inputMode = "numeric";
    hidden.autocomplete = "one-time-code";
    hidden.maxLength = 4;
    hidden.id = "pinHidden";
    Object.assign(hidden.style, {
      position: "absolute",
      opacity: 0,
      pointerEvents: "none",
      width: "1px",
      height: "1px",
      left: "-9999px",
      top: "0",
    });
    document.body.appendChild(hidden);
  }

  // --- 다이얼패드/버튼 플로팅 보정 ---
  const setDialpadHeight = () => {
    const kb = window.visualViewport
      ? Math.max(0, window.innerHeight - window.visualViewport.height)
      : 0;
    const ph = dialpad?.getBoundingClientRect().height || 0;
    root.style.setProperty("--dialpad-h", `${kb || ph}px`);
  };

  const openDialpad = () => {
    dialpad?.classList.remove("hidden");
    document.body.classList.add("keyboard-open");
    btnNext.classList.add("lifted");
    requestAnimationFrame(() => {
      setDialpadHeight();
      hidden.focus({ preventScroll: true });
    });
  };

  const closeDialpad = () => {
    dialpad?.classList.add("hidden");
    document.body.classList.remove("keyboard-open");
    btnNext.classList.remove("lifted");
    root.style.setProperty("--dialpad-h", "0px");
    hidden.blur();
  };

  const renderBoxes = (val) => {
    const digits = (val || "").replace(/\D/g, "").slice(0, 4);
    boxes.forEach((b, i) => {
      b.textContent = digits[i] ?? "";
      b.classList.toggle("has-value", !!digits[i]);
      b.classList.toggle("next", i === digits.length && digits.length < boxes.length);
      b.classList.remove("error");
    });
    hidden.value = digits;
    btnNext.disabled = digits.length !== 4;

    // if (pinError && !pinError.hasAttribute("hidden")) {
    //   pinError.setAttribute("hidden", "");
    // }
  };

  // 초기 상태
  closeDialpad();
  renderBoxes("");
  btnNext.disabled = true;

  // 입력 반영
  hidden.addEventListener("input", () => renderBoxes(hidden.value));

  // 박스 클릭/포커스 → 다이얼패드 오픈
  pwBox.addEventListener("click", openDialpad);
  pwBox.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openDialpad();
    }
  });

  // 바깥 클릭 → 닫기
  document.addEventListener("click", (e) => {
    if (!document.body.classList.contains("keyboard-open")) return;
    const within =
      e.target.closest("#pwNums") ||
      e.target.closest("#dialpad") ||
      e.target.closest("#submitBtn");
    if (!within) closeDialpad();
  });

  // 키보드 높이 변화(iOS)
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", () => {
      if (document.body.classList.contains("keyboard-open")) setDialpadHeight();
    });
  }

  // 폼 제출(서버 검증): 4자리 아니면 막고 흔들기
  form.addEventListener("submit", (e) => {
    const digits = hidden.value || "";
    if (digits.length !== 4) {
      e.preventDefault();
      boxes.forEach((b) => {
        b.classList.add("error", "shake");
        setTimeout(() => b.classList.remove("shake"), 300);
      });
      if (pinError) {
        pinError.removeAttribute("hidden");
        pinError.textContent = "4자리 인증번호를 입력하세요";
      }
      return;
    }
    // 서버가 읽는 필드에 값 채우고 전송
    passwordEl.value = digits;
    closeDialpad();
    btnNext.disabled = true; // 중복 제출 방지
  });

  // --- 서버 응답으로 성공여부 처리 ---
  const isSuccess = stateEl?.dataset?.success === "1";
  const redirectUrl = stateEl?.dataset?.redirectUrl || "";

  if (isSuccess) {
    // 성공 모달 오픈
    success?.setAttribute("aria-hidden", "false");
    success?.classList.add("open");
  } else {
    // 실패면 서버가 띄운 에러문구가 p.pin-error에 이미 들어있음
    // 재입력 시 자동으로 숨김 처리됨
  }

  // 성공 모달 확인
  okBtn?.addEventListener("click", (e) => {
    if (okBtn.tagName === "A") {
      // href 있으므로 기본 이동
      return;
    }
    e.preventDefault();
    if (redirectUrl) {
      window.location.href = redirectUrl;
    } else {
      // 혹시 대비
      success?.classList.remove("open");
      success?.setAttribute("aria-hidden", "true");
    }
  });
});
