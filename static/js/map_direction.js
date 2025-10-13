document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".mart-dropdown").forEach((section) => {
    const header = section.querySelector(".bar-title");
    const icon = section.querySelector(".more-icon");
    const content = section.querySelector(
      ".mart-info, .mart-info2, .mat-block-set"
    );
    if (!header || !content) return;

    header.setAttribute("role", "button");
    header.setAttribute("tabindex", "0");
    header.setAttribute("aria-expanded", "false");

    const setState = (open) => {
      section.classList.toggle("open", open);
      header.setAttribute("aria-expanded", open ? "true" : "false");

      if (icon) {
        icon.style.transform = open ? "rotate(180deg)" : "rotate(0deg)";
        icon.style.filter = open ? "brightness(0) saturate(100%)" : "";
      }
    };

    const toggle = () => setState(!section.classList.contains("open"));

    header.addEventListener("click", toggle);
    header.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggle();
      }
    });

    section.classList.remove("open");
  });
});
