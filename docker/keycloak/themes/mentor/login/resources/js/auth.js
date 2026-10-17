// Show/hide password buttons and a "please wait" state while a form is submitted.
(function () {
  document.addEventListener("click", function (event) {
    var toggle = event.target.closest("[data-toggle-password]");
    if (!toggle) return;
    var input = document.getElementById(toggle.getAttribute("data-toggle-password"));
    if (!input) return;
    var show = input.type === "password";
    input.type = show ? "text" : "password";
    toggle.setAttribute("aria-pressed", String(show));
    toggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });

  document.addEventListener("submit", function (event) {
    var button = event.target.querySelector("button[type=submit][data-busy-label]");
    if (!button) return;
    // Disable after the browser has collected the form values, so the submit still goes through.
    setTimeout(function () {
      button.disabled = true;
      button.textContent = button.getAttribute("data-busy-label");
    }, 0);
  });
})();
