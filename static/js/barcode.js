
document.addEventListener("DOMContentLoaded", () => {
  const root = document.documentElement;
  const form = document.querySelector("form.request-pw");
  const pwBox = document.querySelector(".pw-nums");
  const pinBoxes = Array.from(document.querySelectorAll(".pw-num"));
  const btnNext = document.querySelector(".completenumBtn");
  const dialpad = document.getElementById("dialpad");
  const success = document.getElementById("confirmSuccess");
  const okBtn = document.getElementById("confirmOkBtn");
  const codeField = document.getElementById("code"); // 서버 전송용
  const usePoint = document.getElementById("use_point");
  const leftPointEl = document.getElementById("leftPoint");

  const LEFT_POINT =
    Number(
      (
        document.querySelector(".usepointBox")?.dataset?.leftPoint ??
        (leftPointEl?.textContent || "0")
      ).replace(/[^\d]/g, "")
    ) || 0;

  // 네이티브 키보드용 숨은 입력
  let hidden = document.getElementById("pinHidden");
  if (!hidden) {
    hidden = document.createElement("input");
    hidden.id = "pinHidden";
    hidden.type = "tel";
    hidden.inputMode = "numeric";
    hidden.autocomplete = "one-time-code";
    hidden.maxLength = 4;
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

  // 키패드, 버튼 플로팅
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
    btnNext?.classList.add("lifted");
    setDialpadHeight();
    hidden.focus({ preventScroll: true });
  };

  const closeDialpad = () => {
    dialpad?.classList.add("hidden");
    document.body.classList.remove("keyboard-open");
    btnNext?.classList.remove("lifted");
    root.style.removeProperty("--dialpad-h");
    hidden.blur();
  };

  // PIN 박스 렌더링
  const renderPin = (val) => {
    const digits = String(val || "")
      .replace(/\D/g, "")
      .slice(0, 4);
    pinBoxes.forEach((b, i) => {
      const filled = !!digits[i];
      b.textContent = filled ? "•" : "";
      b.classList.toggle("has-value", filled);
      b.classList.toggle(
        "next",
        i === digits.length && digits.length < pinBoxes.length
      );
      b.classList.remove("error");
    });
    hidden.value = digits;
    btnNext.disabled = digits.length !== 4;
    hidePinError();
  };

  // ---- PIN 에러 문구 ----
  const getPinErrEl = () => {
    let el = document.getElementById("pinError");
    if (!el) {
      el = document.createElement("p");
      el.id = "pinError";
      el.className = "pin-error";
      el.hidden = true;
      el.innerHTML =
        '<img src="/static/img/triangle-alert.svg" alt="" /> 인증번호를 4자리로 입력해주세요';
      pwBox?.insertAdjacentElement("afterend", el);
    }
    return el;
  };
  const showPinError = (msg) => {
    const el = getPinErrEl();
    if (msg) el.lastChild.nodeValue = " " + msg;
    el.hidden = false;
  };
  const hidePinError = () => {
    const el = document.getElementById("pinError");
    if (el) el.hidden = true;
  };

  // 초기화
  closeDialpad();
  renderPin("");

  hidden.addEventListener("input", () => renderPin(hidden.value));
  pwBox?.addEventListener("click", openDialpad);

  // 바깥 클릭 닫기
  document.addEventListener("click", (e) => {
    if (!document.body.classList.contains("keyboard-open")) return;
    const within =
      e.target.closest(".pw-nums") ||
      e.target.closest("#dialpad") ||
      e.target.closest(".completenumBtn");
    if (!within) closeDialpad();
  });

  // 뷰포트 변화(iOS)
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", () => {
      if (document.body.classList.contains("keyboard-open")) setDialpadHeight();
    });
  }

  // ---- 포인트 입력 완료 & 남은 포인트 갱신 ----
  const errSet = document.querySelector(".error-ment-set");
  const errEmpty = errSet?.querySelector("#usePointErrEmpty");
  const errStep = errSet?.querySelector("#usePointErrStep");
  const toggle = (el, show) => {
    if (el) el.hidden = !show;
  };
  const fmt = (n) => n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");

  const validateUsePoint = () => {
    if (!usePoint) return true;
    const raw = usePoint.value.replace(/[^\d]/g, "");
    usePoint.value = raw;
    const v = Number(raw || "0");

    toggle(errEmpty, false);
    toggle(errStep, false);

    let ok = true;
    if (!raw || v === 0) {
      toggle(errEmpty, true);
      ok = false;
    } else if (v % 100 !== 0) {
      toggle(errStep, true);
      ok = false;
    } else if (v > LEFT_POINT) {
      ok = false;
    } // 잔액 초과는 비활성만

    if (leftPointEl) {
      const remain = Math.max(0, LEFT_POINT - (ok ? v : 0));
      leftPointEl.textContent = fmt(remain);
    }
    return ok;
  };

  usePoint?.addEventListener("input", validateUsePoint);

  form?.addEventListener("submit", (e) => {
    const pin = hidden.value;
    const pinOk = /^\d{4}$/.test(pin);
    const pointOk = validateUsePoint();

    if (!pinOk || !pointOk) {
      e.preventDefault();
      if (!pinOk) {
        showPinError();
        pinBoxes.forEach((b) => {
          b.classList.add("shake");
          setTimeout(() => b.classList.remove("shake"), 300);
        });
        hidden.focus({ preventScroll: true });
      }
      return;
    }

    if (codeField) codeField.value = pin;
  });

  okBtn?.addEventListener("click", () => {
    success?.classList.remove("open");
    success?.setAttribute("aria-hidden", "true");
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const okBtn = document.getElementById("confirmOkBtn");
  if (!okBtn) return;

  okBtn.addEventListener("click", () => {
    const next = okBtn.dataset.next || "/";
    window.location.assign(next);
  });
});
