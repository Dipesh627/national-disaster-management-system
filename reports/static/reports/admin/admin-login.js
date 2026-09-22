document.addEventListener("DOMContentLoaded", function () {

    "use strict";


    /* =====================================================
       ELEMENTS
       ===================================================== */

    const form =
        document.getElementById("adminLoginForm");

    const username =
        document.getElementById("adminUsername");

    const password =
        document.getElementById("adminPassword");

    const passwordToggle =
        document.getElementById("adminPasswordToggle");

    const submitButton =
        document.getElementById("adminLoginSubmit");


    /* =====================================================
       PASSWORD VISIBILITY
       ===================================================== */

    if (password && passwordToggle) {

        passwordToggle.addEventListener(
            "click",
            function () {

                const isVisible =
                    password.type === "text";


                password.type =
                    isVisible
                        ? "password"
                        : "text";


                passwordToggle.classList.toggle(
                    "is-visible",
                    !isVisible
                );


                passwordToggle.setAttribute(
                    "aria-pressed",
                    String(!isVisible)
                );


                passwordToggle.setAttribute(
                    "aria-label",
                    isVisible
                        ? "Show password"
                        : "Hide password"
                );


                password.focus();

            }
        );

    }


    /* =====================================================
       LOADING STATE
       Both fields already carry the native `required` attribute
       (see admin/login.html), so the browser blocks submission
       and focuses the empty field on its own - this handler no
       longer duplicates that check. It only shows the loading
       state once the browser has allowed the submit through,
       and it does not stop the normal Django POST.
       ===================================================== */

    if (form && submitButton) {

        form.addEventListener(
            "submit",
            function () {

                submitButton.classList.add(
                    "is-loading"
                );

            }
        );

    }


    /* =====================================================
       ESCAPE TO HIDE PASSWORD
       ===================================================== */

    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Escape" &&
                password &&
                password.type === "text"
            ) {

                password.type =
                    "password";


                if (passwordToggle) {

                    passwordToggle.classList.remove(
                        "is-visible"
                    );


                    passwordToggle.setAttribute(
                        "aria-pressed",
                        "false"
                    );


                    passwordToggle.setAttribute(
                        "aria-label",
                        "Show password"
                    );

                }

            }

        }
    );


    /* =====================================================
       BROWSER BACK / FORWARD CACHE
       ===================================================== */

    window.addEventListener(
        "pageshow",
        function () {

            if (submitButton) {

                submitButton.classList.remove(
                    "is-loading"
                );

            }

        }
    );

});