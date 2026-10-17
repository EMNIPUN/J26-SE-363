(function () {
  'use strict';

  var THEME_KEY = 'selvia-auth-theme';

  function $(selector, root) {
    return (root || document).querySelector(selector);
  }

  function $all(selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  }

  function initThemeToggle() {
    $all('[data-theme-toggle]').forEach(function (button) {
      button.addEventListener('click', function () {
        var root = document.documentElement;
        var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        root.setAttribute('data-theme', next);
        try {
          localStorage.setItem(THEME_KEY, next);
        } catch (e) {}
      });
    });
  }

  function initPasswordToggles() {
    $all('[data-toggle-password]').forEach(function (button) {
      var input = document.getElementById(button.getAttribute('data-toggle-password'));
      if (!input) return;
      button.addEventListener('click', function () {
        var reveal = input.type === 'password';
        input.type = reveal ? 'text' : 'password';
        button.setAttribute('aria-pressed', String(reveal));
        button.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
        input.focus({ preventScroll: true });
        var end = input.value.length;
        try {
          input.setSelectionRange(end, end);
        } catch (e) {}
      });
    });
  }

  function initCapsLock() {
    $all('[data-capslock]').forEach(function (input) {
      var hint = document.getElementById(input.getAttribute('data-capslock'));
      if (!hint) return;
      function update(event) {
        if (typeof event.getModifierState !== 'function') return;
        hint.hidden = !event.getModifierState('CapsLock');
      }
      input.addEventListener('keydown', update);
      input.addEventListener('keyup', update);
      input.addEventListener('blur', function () {
        hint.hidden = true;
      });
    });
  }

  var STRENGTH_LABELS = ['Not set', 'Weak', 'Fair', 'Good', 'Strong'];

  function evaluate(value) {
    var rules = {
      length: value.length >= 8,
      case: /[a-z]/.test(value) && /[A-Z]/.test(value),
      number: /\d/.test(value),
      symbol: /[^A-Za-z0-9]/.test(value)
    };
    var met = Object.keys(rules).filter(function (key) {
      return rules[key];
    }).length;
    var score = 0;
    if (value.length > 0) {
      score = Math.max(1, met);
      if (!rules.length) score = Math.min(score, 1);
      if (value.length >= 14 && met >= 3) score = 4;
    }
    return { rules: rules, score: score };
  }

  function initStrengthMeters() {
    $all('[data-strength]').forEach(function (input) {
      var meter = document.getElementById(input.getAttribute('data-strength'));
      if (!meter) return;
      var label = $('[data-strength-label]', meter);
      function update() {
        var result = evaluate(input.value);
        meter.setAttribute('data-score', String(result.score));
        if (label) label.textContent = STRENGTH_LABELS[result.score];
        $all('[data-rule]', meter).forEach(function (item) {
          item.classList.toggle('met', !!result.rules[item.getAttribute('data-rule')]);
        });
      }
      input.addEventListener('input', update);
      update();
    });
  }

  function initMatchHints() {
    $all('[data-match]').forEach(function (confirm) {
      var source = document.getElementById(confirm.getAttribute('data-match'));
      var hint = document.getElementById(confirm.getAttribute('data-match-hint'));
      if (!source || !hint) return;
      function update() {
        if (!confirm.value) {
          hint.hidden = true;
          confirm.setCustomValidity('');
          return;
        }
        var matches = confirm.value === source.value;
        var stillTyping = !matches && confirm.value.length < source.value.length;
        hint.hidden = false;
        hint.className = matches ? 'field-hint match-ok' : stillTyping ? 'field-hint' : 'field-error';
        hint.textContent = matches ? 'Passwords match' : stillTyping ? "Passwords don't match yet" : "Passwords don't match";
        confirm.setCustomValidity(matches ? '' : "Passwords don't match");
      }
      confirm.addEventListener('input', update);
      source.addEventListener('input', update);
    });
  }

  function initLoadingForms() {
    $all('form[data-loading-form]').forEach(function (form) {
      form.addEventListener('submit', function (event) {
        var button = event.submitter || $('button[type="submit"]', form);
        if (!button || button.classList.contains('is-loading')) return;
        if (button.name === 'cancel-aia') return;
        window.setTimeout(function () {
          $all('button[type="submit"]', form).forEach(function (b) {
            b.disabled = true;
          });
        }, 0);
        button.classList.add('is-loading');
        button.setAttribute('aria-busy', 'true');
        var text = button.getAttribute('data-loading-text');
        var label = $('.btn-label', button);
        if (text && label) {
          button.setAttribute('data-original-text', label.textContent);
          label.textContent = text;
        }
      });
    });
  }

  window.addEventListener('pageshow', function (event) {
    if (!event.persisted) return;
    $all('form[data-loading-form] button[type="submit"]').forEach(function (button) {
      button.disabled = false;
      button.classList.remove('is-loading');
      button.removeAttribute('aria-busy');
      var label = $('.btn-label', button);
      var original = button.getAttribute('data-original-text');
      if (label && original) label.textContent = original;
    });
  });

  function clearInvalidOnEdit() {
    $all('.input[aria-invalid="true"]').forEach(function (input) {
      input.addEventListener('input', function onEdit() {
        input.removeAttribute('aria-invalid');
        input.removeEventListener('input', onEdit);
      });
    });
  }

  function init() {
    initThemeToggle();
    initPasswordToggles();
    initCapsLock();
    initStrengthMeters();
    initMatchHints();
    initLoadingForms();
    clearInvalidOnEdit();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
