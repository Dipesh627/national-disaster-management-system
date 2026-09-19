/* =========================================================
   NDMS ADMIN — SETTINGS JAVASCRIPT

   NOTE: Sidebar toggling, the topbar profile dropdown and the
   mobile overlay are already handled by admin-shell.js, which
   every admin page (including this one) already loads via
   base.html. This file only adds:

     1. The Change Password show/hide interaction.
     2. An instant live preview of Reduce Motion / High
        Contrast / Font Size — toggling the SAME classes
        dashboard-shell.css already reads on #adminShell, so
        the preview is not a separate mechanism from what
        actually gets applied once the page is saved/reloaded.
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {


    /* =====================================================
       CHANGE PASSWORD — SHOW / HIDE
       ===================================================== */

    const securityCard =
        document.querySelector(".as-security");

    const changePasswordButton =
        document.getElementById("asChangePasswordButton");

    const cancelPasswordButton =
        document.getElementById("asCancelPasswordButton");

    const passwordForm =
        document.getElementById("asPasswordForm");


    function openPasswordForm() {

        if (!securityCard) {
            return;
        }

        securityCard.classList.add("as-security-open");

        if (changePasswordButton) {
            changePasswordButton.setAttribute("aria-expanded", "true");
        }

        const firstField =
            passwordForm
                ? passwordForm.querySelector("#id_old_password")
                : null;

        if (firstField) {
            firstField.focus();
        }

    }


    function closePasswordForm() {

        if (!securityCard) {
            return;
        }

        securityCard.classList.remove("as-security-open");

        if (changePasswordButton) {
            changePasswordButton.setAttribute("aria-expanded", "false");
        }

    }


    if (changePasswordButton) {

        changePasswordButton.addEventListener("click", function () {

            if (securityCard && securityCard.classList.contains("as-security-open")) {
                closePasswordForm();
            } else {
                openPasswordForm();
            }

        });

    }


    if (cancelPasswordButton) {

        cancelPasswordButton.addEventListener("click", function () {

            if (passwordForm) {
                passwordForm.reset();
            }

            closePasswordForm();

        });

    }


    /* -----------------------------------------------------
       AUTO-OPEN ON VALIDATION ERRORS
       (if the password form was submitted with invalid data,
       admin_settings() re-renders this same page with field
       errors — open it automatically so the errors are
       visible instead of hiding behind the collapsed row)
       ----------------------------------------------------- */

    const hasPasswordFieldErrors =
        passwordForm
            ? passwordForm.querySelector(".as-field-error")
            : null;

    if (hasPasswordFieldErrors) {
        openPasswordForm();
    }


    /* =====================================================
       ACCESSIBILITY — INSTANT LIVE PREVIEW

       These are the exact same classes dashboard-shell.css
       already applies admin-wide from the saved preference
       (see base.html) — toggling them here on change just
       lets an admin see the effect immediately, before
       clicking Save Changes.
       ===================================================== */

    const adminShell =
        document.getElementById("adminShell");

    const reduceMotionInput =
        document.getElementById("id_reduce_motion");

    const highContrastInput =
        document.getElementById("id_high_contrast");

    const fontSizeInputs =
        document.querySelectorAll(
            'input[name="font_size"]'
        );


    if (adminShell && reduceMotionInput) {

        reduceMotionInput.addEventListener("change", function () {

            adminShell.classList.toggle(
                "admin-reduce-motion",
                reduceMotionInput.checked
            );

        });

    }


    if (adminShell && highContrastInput) {

        highContrastInput.addEventListener("change", function () {

            adminShell.classList.toggle(
                "admin-high-contrast",
                highContrastInput.checked
            );

        });

    }


    if (adminShell && fontSizeInputs.length) {

        fontSizeInputs.forEach(function (input) {

            input.addEventListener("change", function () {

                adminShell.classList.toggle(
                    "admin-font-large",
                    input.checked && input.value === "LARGE"
                );

            });

        });

    }

});