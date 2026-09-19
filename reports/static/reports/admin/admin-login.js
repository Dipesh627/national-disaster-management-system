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
       FORM VALIDATION + LOADING
       ===================================================== */

    if (form && submitButton) {

        form.addEventListener(
            "submit",
            function (event) {

                const usernameValue =
                    username
                        ? username.value.trim()
                        : "";


                const passwordValue =
                    password
                        ? password.value
                        : "";


                /* Username validation */

                if (!usernameValue) {

                    event.preventDefault();

                    if (username) {
                        username.focus();
                    }

                    return;

                }


                /* Password validation */

                if (!passwordValue) {

                    event.preventDefault();

                    if (password) {
                        password.focus();
                    }

                    return;

                }


                /*
                 * Do not stop the normal Django POST.
                 * Only show loading state.
                 */

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