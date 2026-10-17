// Show/hide password buttons, multi-step forms and a "please wait" state while a form is submitted.
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

  // A form marked data-steps shows one <fieldset data-step> at a time.
  // Without this script every step is visible and the form still works.
  function initSteps(form) {
    var steps = Array.prototype.slice.call(form.querySelectorAll("[data-step]"));
    var progress = form.querySelector("[data-progress]");
    var bars = progress.querySelectorAll(".progress-bar span");
    var label = form.querySelector("[data-progress-label]");
    var current = 0;

    function fields(step) {
      return Array.prototype.slice.call(step.querySelectorAll("input"));
    }

    function show(index) {
      current = index;
      steps.forEach(function (step, i) {
        step.hidden = i !== index;
      });
      bars.forEach(function (bar, i) {
        bar.classList.toggle("done", i <= index);
      });
      label.textContent =
        "Step " + (index + 1) + " of " + steps.length + " · " + steps[index].getAttribute("data-title");
      var first = fields(steps[index])[0];
      if (first && first.type !== "checkbox") first.focus();
    }

    function valid(step) {
      var confirm = step.querySelector("#password-confirm");
      var password = step.querySelector("#password");
      if (confirm && password) {
        confirm.setCustomValidity(confirm.value === password.value ? "" : "The passwords do not match.");
      }
      return fields(step).every(function (input) {
        return input.reportValidity();
      });
    }

    function summarise() {
      var email = form.querySelector("#email");
      var out = form.querySelector("[data-summary-email]");
      var box = form.querySelector("[data-summary]");
      if (!email || !out || !box) return;
      out.textContent = email.value;
      box.hidden = false;
    }

    function next() {
      if (!valid(steps[current])) return;
      if (current + 1 === steps.length - 1) summarise();
      show(current + 1);
    }

    form.addEventListener("click", function (event) {
      if (event.target.closest("[data-next]")) next();
      else if (event.target.closest("[data-back]")) show(current - 1);
    });

    // Enter moves to the next step; only the last step submits.
    form.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" || event.target.type === "checkbox") return;
      if (current < steps.length - 1) {
        event.preventDefault();
        next();
      }
    });

    progress.hidden = false;
    // After a server error, reopen the step that has it.
    var failed = steps.findIndex(function (step) {
      return step.querySelector("[aria-invalid=true]");
    });
    show(failed > 0 ? failed : 0);
    if (failed > 0) summarise();
  }

  document.querySelectorAll("form[data-steps]").forEach(initSteps);
})();
