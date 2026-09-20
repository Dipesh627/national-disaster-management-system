/* =========================================================
   NDMS ADMIN — SETTINGS JAVASCRIPT

   NOTE: Sidebar toggling, the topbar profile dropdown and the
   mobile overlay are already handled by admin-shell.js, which
   every admin page (including this one) already loads via
   base.html. This file only adds the Change Password show/hide
   interaction below.
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

});