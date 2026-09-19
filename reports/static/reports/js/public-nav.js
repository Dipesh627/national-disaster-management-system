/* =========================================================
   NDMS SHARED PUBLIC NAVBAR
   MOBILE HAMBURGER MENU BEHAVIOUR

   Single source of truth for opening/closing the public mobile
   nav panel (#publicMobileMenu / #mobileMenuToggle). Previously
   this logic was duplicated inside home.js and about.js, which
   meant pages that share the same navbar partial but don't load
   either of those files (View Disasters, Disaster Detail) had a
   hamburger button that did nothing — the panel, and the
   Disasters dropdown living inside it, could never open.

   Loaded on every page that includes
   reports/partials/navbar.html: home.html, about.html,
   disaster_list.html, disaster_detail.html.

   Exposes window.NDMSPublicNav.closeMobileMenu() so other,
   page-specific scripts (e.g. about.js's smooth-scroll handler)
   can still close the menu after an in-page anchor jump without
   duplicating this logic.
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const menuToggle =
            document.getElementById(
                "mobileMenuToggle"
            );

        const mobileMenu =
            document.getElementById(
                "publicMobileMenu"
            );


        if (
            !menuToggle ||
            !mobileMenu
        ) {

            return;

        }


        function openMenu() {

            mobileMenu.classList.add(
                "open"
            );

            menuToggle.classList.add(
                "active"
            );

            menuToggle.setAttribute(
                "aria-expanded",
                "true"
            );

            menuToggle.setAttribute(
                "aria-label",
                "Close main menu"
            );

            document.body.classList.add(
                "menu-open"
            );

            // Let other navbar widgets (account/avatar dropdown)
            // know a menu just opened, so only one is ever open
            // at a time.
            document.dispatchEvent(
                new CustomEvent(
                    "ndms:menu-opened",
                    { detail: "mobile" }
                )
            );

        }


        function closeMenu() {

            mobileMenu.classList.remove(
                "open"
            );

            menuToggle.classList.remove(
                "active"
            );

            menuToggle.setAttribute(
                "aria-expanded",
                "false"
            );

            menuToggle.setAttribute(
                "aria-label",
                "Open main menu"
            );

            document.body.classList.remove(
                "menu-open"
            );

        }


        function toggleMenu() {

            if (mobileMenu.classList.contains("open")) {

                closeMenu();

            } else {

                openMenu();

            }

        }


        menuToggle.addEventListener(
            "click",
            function (event) {

                event.stopPropagation();

                toggleMenu();

            }
        );


        // Close after tapping any nav link, including the ones
        // inside the Disasters dropdown — they all navigate to a
        // new page, so the panel should not stay open behind it.
        mobileMenu
            .querySelectorAll(".public-nav a")
            .forEach(function (link) {
                link.addEventListener("click", closeMenu);
            });


        document.addEventListener(
            "click",
            function (event) {

                if (
                    !mobileMenu.contains(event.target) &&
                    !menuToggle.contains(event.target)
                ) {

                    closeMenu();

                }

            }
        );


        document.addEventListener(
            "keydown",
            function (event) {

                if (event.key === "Escape") {

                    closeMenu();

                }

            }
        );


        window.addEventListener(
            "resize",
            function () {

                if (window.innerWidth > 850) {

                    closeMenu();

                }

            }
        );


        // Another navbar widget (the avatar dropdown) just
        // opened — close this menu so only one shows at a time.
        document.addEventListener(
            "ndms:menu-opened",
            function (event) {

                if (
                    event.detail !== "mobile" &&
                    mobileMenu.classList.contains("open")
                ) {

                    closeMenu();

                }

            }
        );


        // Small cross-script API so page-specific scripts (e.g.
        // about.js's anchor-scroll handler) can close the mobile
        // menu without re-implementing this logic.
        window.NDMSPublicNav = window.NDMSPublicNav || {};
        window.NDMSPublicNav.closeMobileMenu = closeMenu;

    }
);