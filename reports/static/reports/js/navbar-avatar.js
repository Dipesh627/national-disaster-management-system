/* =========================================================
   NDMS SHARED NAVBAR
   AVATAR DROPDOWN BEHAVIOUR

   Self-contained: only touches elements with the "ndmsAvatar*"
   ids/classes added for this feature, so it cannot interfere
   with any other page script (home.js, about.js, etc.).

   Desktop: hover OR click opens the dropdown; moving into the
   dropdown keeps it open; leaving the combined avatar+dropdown
   area closes it. Click also toggles it (click again closes).
   Mobile / touch: click/tap toggles only — hover is not relied
   on, since touch devices don't have a real "hover" state.
   Outside click and Escape always close it, on every device.
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const wrapper =
            document.getElementById(
                "ndmsAvatarWrapper"
            );

        const button =
            document.getElementById(
                "ndmsAvatarBtn"
            );

        const menu =
            document.getElementById(
                "ndmsAvatarMenu"
            );


        if (
            !wrapper ||
            !button ||
            !menu
        ) {

            return;

        }


        // Desktop = pointer:fine + hover:hover devices, matching
        // the shared navbar's own ≤850px mobile breakpoint used
        // elsewhere in this file (resize handler below).
        const hoverCapable =
            window.matchMedia &&
            window.matchMedia(
                "(hover: hover) and (pointer: fine)"
            ).matches;


        let hoverCloseTimer = null;


        function openMenu() {

            if (hoverCloseTimer) {

                clearTimeout(hoverCloseTimer);

                hoverCloseTimer = null;

            }

            wrapper.classList.add(
                "open"
            );

            button.setAttribute(
                "aria-expanded",
                "true"
            );

            // Let other navbar widgets (e.g. the public mobile
            // hamburger menu, the Disasters dropdown) know a menu
            // just opened, so only one is ever open at a time.
            document.dispatchEvent(
                new CustomEvent(
                    "ndms:menu-opened",
                    { detail: "avatar" }
                )
            );

        }


        function closeMenu() {

            if (hoverCloseTimer) {

                clearTimeout(hoverCloseTimer);

                hoverCloseTimer = null;

            }

            wrapper.classList.remove(
                "open"
            );

            button.setAttribute(
                "aria-expanded",
                "false"
            );

        }


        function isOpen() {

            return wrapper.classList.contains(
                "open"
            );

        }


        button.addEventListener(
            "click",
            function (event) {

                event.stopPropagation();

                if (isOpen()) {

                    closeMenu();

                } else {

                    openMenu();

                }

            }
        );


        // ---------------------------------------------------
        // DESKTOP HOVER
        // Hovering the avatar (or the open dropdown itself)
        // opens/keeps it open. Leaving the combined area closes
        // it after a short delay, so moving the cursor from the
        // avatar into the dropdown never closes it in transit.
        // ---------------------------------------------------

        if (hoverCapable) {

            wrapper.addEventListener(
                "mouseenter",
                function () {

                    openMenu();

                }
            );


            wrapper.addEventListener(
                "mouseleave",
                function () {

                    hoverCloseTimer =
                        setTimeout(
                            closeMenu,
                            150
                        );

                }
            );

        }


        document.addEventListener(
            "click",
            function (event) {

                if (
                    isOpen() &&
                    !wrapper.contains(
                        event.target
                    )
                ) {

                    closeMenu();

                }

            }
        );


        document.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key === "Escape" &&
                    isOpen()
                ) {

                    closeMenu();

                    button.focus();

                }

            }
        );


        window.addEventListener(
            "resize",
            function () {

                if (
                    window.innerWidth <= 850 &&
                    isOpen()
                ) {

                    closeMenu();

                }

            }
        );


        // Another navbar widget (the public mobile hamburger
        // menu, the Disasters dropdown) just opened — close this
        // dropdown so only one shows at a time on mobile.
        document.addEventListener(
            "ndms:menu-opened",
            function (event) {

                if (
                    event.detail !== "avatar" &&
                    isOpen()
                ) {

                    closeMenu();

                }

            }
        );


        const menuLinks =
            menu.querySelectorAll(
                "a"
            );

        menuLinks.forEach(
            function (link) {

                link.addEventListener(
                    "click",
                    function () {

                        closeMenu();

                    }
                );

            }
        );

    }
);


/* =========================================================
   NDMS SHARED NAVBAR
   "DISASTERS" NAV DROPDOWN BEHAVIOUR

   Self-contained: only touches "disastersDropdown*" ids, so it
   cannot interfere with home.js / about.js / the avatar script
   above. Mirrors the avatar dropdown's interaction model (hover
   + click on desktop, tap-to-toggle on mobile, outside click /
   Escape always close) so both dropdowns feel identical.

   On mobile the dropdown lives INSIDE the collapsible hamburger
   panel, so opening it must never broadcast a "close everything
   else" event while the panel itself is that "everything else" —
   the broadcast is skipped below 851px for that reason.
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const dropdown =
            document.getElementById(
                "disastersDropdown"
            );

        const toggle =
            document.getElementById(
                "disastersDropdownToggle"
            );

        const menu =
            document.getElementById(
                "disastersDropdownMenu"
            );


        if (
            !dropdown ||
            !toggle ||
            !menu
        ) {

            return;

        }


        const hoverCapable =
            window.matchMedia &&
            window.matchMedia(
                "(hover: hover) and (pointer: fine)"
            ).matches;


        let hoverCloseTimer = null;


        function isMobileLayout() {

            return window.innerWidth <= 850;

        }


        function openDropdown() {

            if (hoverCloseTimer) {

                clearTimeout(hoverCloseTimer);

                hoverCloseTimer = null;

            }

            dropdown.classList.add(
                "open"
            );

            toggle.setAttribute(
                "aria-expanded",
                "true"
            );

            // Don't ask other widgets to close while this
            // dropdown is itself living inside the mobile
            // hamburger panel — see file header note.
            if (!isMobileLayout()) {

                document.dispatchEvent(
                    new CustomEvent(
                        "ndms:menu-opened",
                        { detail: "disasters" }
                    )
                );

            }

        }


        function closeDropdown() {

            if (hoverCloseTimer) {

                clearTimeout(hoverCloseTimer);

                hoverCloseTimer = null;

            }

            dropdown.classList.remove(
                "open"
            );

            toggle.setAttribute(
                "aria-expanded",
                "false"
            );

        }


        function isOpen() {

            return dropdown.classList.contains(
                "open"
            );

        }


        toggle.addEventListener(
            "click",
            function (event) {

                event.stopPropagation();

                if (isOpen()) {

                    closeDropdown();

                } else {

                    openDropdown();

                }

            }
        );


        if (hoverCapable) {

            dropdown.addEventListener(
                "mouseenter",
                function () {

                    if (!isMobileLayout()) {

                        openDropdown();

                    }

                }
            );


            dropdown.addEventListener(
                "mouseleave",
                function () {

                    hoverCloseTimer =
                        setTimeout(
                            closeDropdown,
                            150
                        );

                }
            );

        }


        document.addEventListener(
            "click",
            function (event) {

                if (
                    isOpen() &&
                    !dropdown.contains(
                        event.target
                    )
                ) {

                    closeDropdown();

                }

            }
        );


        document.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key === "Escape" &&
                    isOpen()
                ) {

                    closeDropdown();

                    toggle.focus();

                }

            }
        );


        window.addEventListener(
            "resize",
            function () {

                if (isOpen()) {

                    closeDropdown();

                }

            }
        );


        // Another navbar widget (avatar dropdown, or the mobile
        // hamburger reopening fresh) just opened — close this one
        // so only one shows at a time.
        document.addEventListener(
            "ndms:menu-opened",
            function (event) {

                if (
                    event.detail !== "disasters" &&
                    isOpen()
                ) {

                    closeDropdown();

                }

            }
        );


        const menuLinks =
            menu.querySelectorAll(
                "a"
            );

        menuLinks.forEach(
            function (link) {

                link.addEventListener(
                    "click",
                    function () {

                        closeDropdown();

                    }
                );

            }
        );


        // ---------------------------------------------------
        // MOBILE: AUTO-EXPAND ON DISASTER-RELATED PAGES
        //
        // The toggle's "active" class is already set server-side
        // (see partials/navbar.html) from the real Django route,
        // so it's already true exactly when the current page is
        // /disasters/, /disasters/<id>/ or the report-incident
        // flow. Reusing that instead of re-deriving the route in
        // JS means this can never disagree with the active-state
        // logic. Only applies on mobile: on desktop this class
        // just drives the underline styling, and the dropdown
        // itself should stay closed until hovered/tapped.
        // ---------------------------------------------------

        if (
            isMobileLayout() &&
            toggle.classList.contains("active")
        ) {

            openDropdown();

        }

    }
);