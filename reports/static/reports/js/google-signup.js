/* =========================================================
   NDMS - GOOGLE SIGN-UP: COMPLETE YOUR NDMS PROFILE
   Loaded (deferred) by templates/reports/google_signup_confirm.html.

   Two conveniences. Neither is a security control: the server
   (views.google_signup_confirm) validates the username and the
   Terms consent again on every submit, and the database enforces
   uniqueness, so the page still works with JavaScript off.

   1. Live username feedback
      While the person types, show a spinner ("Checking
      availability...") then "Username available" or the reason it
      cannot be used, both in the box (tick / cross) and in the
      #username_status line under it. Format problems are caught locally; availability
      is asked of the server (views.google_username_check), which
      only answers a browser that is midway through a Google
      sign-up. Messages for "taken" / "available" come from the
      server so the wording is defined in one place.

   2. Double-submit guard
      A second click on "Create Account" while the first
      is still in flight is ignored, so one person cannot fire two
      simultaneous sign-ups. (Cancel is never blocked.)
   ========================================================= */

(function () {

    "use strict";

    // Google's "Complete Your NDMS Profile" page: username feedback
    // plus the double-submit guard.
    const form = document.querySelector("form[data-google-signup]");

    if (!form) {
        return;
    }

    const input = document.getElementById("username");
    const status = document.getElementById("username_status");
    const wrap = input ? input.closest(".auth-input-wrap") : null;
    const primary = form.querySelector(".auth-btn");


    /* -----------------------------------------------------
       1. LIVE USERNAME FEEDBACK
       ----------------------------------------------------- */

    // Same rule as USERNAME_RE in reports/views.py.
    const VALID = /^[A-Za-z0-9._-]{3,30}$/;

    // Only letters/digits/dot/underscore/hyphen, but not enough
    // of them yet - not worth an error while still typing.
    const TOO_SHORT = /^[A-Za-z0-9._-]{1,2}$/;

    const INVALID_MESSAGE = "Please enter a valid username.";

    const CHECKING_MESSAGE = "Checking availability\u2026";

    const DEBOUNCE_MS = 250;

    const checkUrl = input ? input.getAttribute("data-check-url") : "";

    let timer = null;

    // Bumped on every keystroke; a slow reply for an older value
    // must never overwrite feedback for what is in the box now.
    let sequence = 0;


    function setStatus(kind, text) {

        if (!status || !input) {
            return;
        }

        status.replaceChildren();

        status.className = "google-field-msg";

        // Drives the spinner / tick / cross inside the box.
        if (wrap) {
            wrap.setAttribute("data-state", kind || "");
        }

        if (!kind) {

            input.removeAttribute("aria-invalid");

            return;
        }

        status.classList.add("google-field-msg--" + kind);

        const icon = document.createElement("span");
        icon.className = "google-field-msg__icon";
        icon.setAttribute("aria-hidden", "true");

        const label = document.createElement("span");
        label.className = "google-field-msg__text";
        label.textContent = text;

        // "Checking..." changes on every keystroke; keep it out of
        // the screen-reader announcements and read only the result.
        if (kind === "checking") {
            label.setAttribute("aria-hidden", "true");
        }

        status.appendChild(icon);
        status.appendChild(label);

        if (kind === "error") {
            input.setAttribute("aria-invalid", "true");
        } else {
            input.removeAttribute("aria-invalid");
        }

    }


    function askServer(value, ticket) {

        fetch(checkUrl + "?username=" + encodeURIComponent(value), {
            method: "GET",
            credentials: "same-origin",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json"
            }
        })
            .then(function (response) {

                if (!response.ok) {
                    throw new Error("unavailable");
                }

                return response.json();

            })
            .then(function (data) {

                if (ticket !== sequence) {
                    return;
                }

                if (data.status === "available") {
                    setStatus("ok", data.message);
                } else if (data.status === "taken" || data.status === "invalid") {
                    setStatus("error", data.message || INVALID_MESSAGE);
                } else {
                    setStatus(null);
                }

            })
            .catch(function () {

                // No feedback is better than wrong feedback; the
                // server still decides on submit.
                if (ticket === sequence) {
                    setStatus(null);
                }

            });

    }


    function review(value, options) {

        window.clearTimeout(timer);

        sequence += 1;

        const ticket = sequence;

        if (!value) {

            setStatus(null);

            return;
        }

        if (!VALID.test(value)) {

            // Still typing a short name: wait. Wrong characters or
            // too long: say so straight away.
            if (TOO_SHORT.test(value) && !options.showShort) {
                setStatus(null);
            } else {
                setStatus("error", INVALID_MESSAGE);
            }

            return;
        }

        // Well-formed. Show that a check is under way, then ask
        // the server - after a short pause while typing,
        // immediately on blur.
        if (!checkUrl || !window.fetch) {

            setStatus(null);

            return;
        }

        setStatus("checking", CHECKING_MESSAGE);

        if (options.immediate) {
            askServer(value, ticket);
        } else {
            timer = window.setTimeout(function () {
                askServer(value, ticket);
            }, DEBOUNCE_MS);
        }

    }


    if (input && status) {

        input.addEventListener("input", function () {
            review(input.value.trim(), {
                showShort: false,
                immediate: false
            });
        });

        input.addEventListener("blur", function () {
            review(input.value.trim(), {
                showShort: true,
                immediate: true
            });
        });

        // Browser autofill / back-navigation can leave a value in
        // the box that no input event ever reported.
        if (input.value.trim() && !status.textContent.trim()) {
            review(input.value.trim(), {
                showShort: true,
                immediate: true
            });
        }

    }


    /* -----------------------------------------------------
       2. DOUBLE-SUBMIT GUARD
       ----------------------------------------------------- */

    let submitting = false;

    function setBusy(busy) {

        submitting = busy;

        form.setAttribute("aria-busy", busy ? "true" : "false");

        if (primary) {
            primary.classList.toggle("is-loading", busy);
            primary.setAttribute("aria-disabled", busy ? "true" : "false");
        }

    }

    form.addEventListener("submit", function (event) {

        // "submit" only fires once the browser's own validation has
        // passed, so a rejected attempt never locks the button.
        const submitter = event.submitter;

        if (submitter && submitter.name === "cancel") {
            return;
        }

        if (submitting) {
            event.preventDefault();
            return;
        }

        setBusy(true);

    });

    // Back/forward cache can restore this page with the button
    // still marked busy.
    window.addEventListener("pageshow", function (event) {

        if (event.persisted) {
            setBusy(false);
        }

    });

})();