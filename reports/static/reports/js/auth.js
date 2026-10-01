/* =========================================================
   NDMS - CITIZEN AUTH PAGES
   Loaded (deferred) by templates/reports/auth_base.html.

   1. Password show / hide
      Any <button data-password-toggle> inside an
      .auth-input-wrap controls the <input> in that wrapper.

   2. Invalid field focus (any auth form)
      When the server sends a form back with errors, the first
      field marked aria-invalid="true" receives focus so the
      person (and a screen reader) lands on the problem.

   3. Digits-only inputs
      An <input data-digits-only> accepts only 0-9 (plus one
      leading "+" for phone numbers). Typing or pasting anything
      else is removed straight away. The server validates again.

   4. Login form (only on the page that has form[data-auth-login])
      Keeps the login page out of browser history.

      Login is only an authentication checkpoint. A plain form
      POST + redirect would leave it in history beneath the page
      the user lands on, so Back from Report Incident would
      return here. Instead the form is sent with fetch(); on
      success the server (which has already created the session
      and validated `next`) replies with the destination and
      location.replace() swaps THIS history entry for it.

      A wrong password is shown in place (same alert markup the
      server renders), so a failed attempt does not add extra
      Login entries to history either.

      Anything unexpected (network error, non-JSON reply) falls
      back to the normal form submit, and with JavaScript off the
      form simply posts as before.
   ========================================================= */

(function () {

    "use strict";


    /* -----------------------------------------------------
       1. PASSWORD SHOW / HIDE
       ----------------------------------------------------- */

    document.querySelectorAll("[data-password-toggle]").forEach(function (toggle) {

        const wrap = toggle.closest(".auth-input-wrap");
        const input = wrap && wrap.querySelector("input");

        if (!input) {
            return;
        }

        // "Show password" / "Show confirm password" -> keep the
        // noun the template chose and only swap the verb.
        const noun = (toggle.getAttribute("aria-label") || "Show password")
            .replace(/^(Show|Hide)\s+/, "");

        toggle.addEventListener("click", function () {

            const reveal = input.type === "password";

            input.type = reveal ? "text" : "password";

            toggle.setAttribute("aria-pressed", reveal ? "true" : "false");

            toggle.setAttribute(
                "aria-label",
                (reveal ? "Hide " : "Show ") + noun
            );

        });

    });


    /* -----------------------------------------------------
       2. FOCUS THE FIRST INVALID FIELD
       ----------------------------------------------------- */

    const firstInvalid =
        document.querySelector('.auth-form [aria-invalid="true"]');

    if (firstInvalid) {
        firstInvalid.focus();
    }


    /* -----------------------------------------------------
       3. DIGITS-ONLY INPUTS
       ----------------------------------------------------- */

    document.querySelectorAll("input[data-digits-only]").forEach(function (input) {

        input.addEventListener("input", function () {

            const raw = input.value;

            const plus = raw.trim().charAt(0) === "+" ? "+" : "";

            const clean = plus + raw.replace(/\D/g, "");

            if (clean !== raw) {
                input.value = clean;
            }

        });

    });


    /* -----------------------------------------------------
       4. LOGIN FORM
       ----------------------------------------------------- */

    const form = document.querySelector("form[data-auth-login]");

    if (!form || !window.fetch || !window.FormData) {
        return;
    }

    const submitButton = form.querySelector('button[type="submit"]');

    let submitting = false;


    function setBusy(busy) {

        submitting = busy;

        form.setAttribute("aria-busy", busy ? "true" : "false");

        if (submitButton) {
            submitButton.classList.toggle("is-loading", busy);
            submitButton.disabled = busy;
        }

    }


    function showError(message) {

        // Reuse the server-rendered alert if it is already on
        // the page; otherwise build the same markup.
        let box = form.parentNode.querySelector(".auth-alert");

        if (!box) {

            box = document.createElement("div");
            box.className = "auth-alert";
            box.setAttribute("role", "alert");

            const icon = document.createElement("span");
            icon.className = "auth-alert__icon";
            icon.setAttribute("aria-hidden", "true");
            icon.textContent = "!";

            const text = document.createElement("span");
            text.className = "auth-alert__text";

            box.appendChild(icon);
            box.appendChild(text);

            form.parentNode.insertBefore(box, form);

        }

        box.querySelector(".auth-alert__text").textContent = message;

        const password = document.getElementById("password");

        if (password) {
            password.value = "";
            password.focus();
        }

    }


    form.addEventListener("submit", async function (event) {

        event.preventDefault();

        if (submitting) {
            return;
        }

        setBusy(true);

        try {

            const response = await fetch(window.location.href, {
                method: "POST",
                body: new FormData(form),
                credentials: "same-origin",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json"
                }
            });

            const data = await response.json();

            if (response.ok && data.success && data.redirect_url) {

                // Defence in depth only - the server has
                // already validated this URL.
                const target =
                    new URL(data.redirect_url, window.location.href);

                if (target.origin === window.location.origin) {

                    window.location.replace(target.href);

                    return;

                }

            } else if (response.status === 401 && data.error) {

                showError(data.error);

                setBusy(false);

                return;

            }

        } catch (error) {
            // fall through to the normal submit below
        }

        // Normal form submit (does not re-fire this handler).
        form.submit();

    });


    // Returning via Back/Forward can restore the page from the
    // browser cache with the busy state still applied.
    window.addEventListener("pageshow", function (event) {

        if (event.persisted) {
            setBusy(false);
        }

    });

})();