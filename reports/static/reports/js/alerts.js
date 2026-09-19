/* =========================================================
   NDMS ALERTS PAGE

   Alerts filtering, pagination and read state are handled
   by Django backend.

   This file only handles small UI improvements.

   Dashboard sidebar + notification dropdown:
   dashboard.js

   Avatar dropdown:
   navbar-avatar.js
   ========================================================= */


document.addEventListener(
    "DOMContentLoaded",
    function () {


        /* =================================================
           KEEP ACTIVE FILTER VISIBLE ON MOBILE
           ================================================= */

        const activeTab =
            document.querySelector(
                ".alerts-filter-tab.active"
            );


        const tabs =
            document.querySelector(
                ".alerts-filter-tabs"
            );


        if (
            activeTab &&
            tabs &&
            window.innerWidth <= 480
        ) {

            activeTab.scrollIntoView({
                behavior: "auto",
                inline: "center",
                block: "nearest"
            });

        }



        /* =================================================
           PREVENT DOUBLE SUBMIT
           WHEN MARKING ONE ALERT AS READ
           ================================================= */

        const alertForms =
            document.querySelectorAll(
                ".alert-read-form"
            );


        alertForms.forEach(
            function (form) {


                form.addEventListener(
                    "submit",
                    function () {


                        const button =
                            form.querySelector(
                                "button[type='submit']"
                            );


                        if (!button) {

                            return;

                        }


                        button.disabled = true;


                        button.setAttribute(
                            "aria-busy",
                            "true"
                        );


                    }
                );


            }
        );



        /* =================================================
           PREVENT DOUBLE SUBMIT
           MARK ALL AS READ
           ================================================= */

        const markAllButton =
            document.querySelector(
                ".alerts-mark-all"
            );


        if (markAllButton) {


            const markAllForm =
                markAllButton.closest(
                    "form"
                );


            if (markAllForm) {


                markAllForm.addEventListener(
                    "submit",
                    function () {


                        markAllButton.disabled =
                            true;


                        markAllButton.textContent =
                            "Marking as read...";


                    }
                );


            }

        }


    }
);