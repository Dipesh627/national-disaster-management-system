/* =========================================================
   NDMS SHARED NAVBAR
   AVATAR DROPDOWN BEHAVIOUR

   Shared by the public navbar and the dashboard-shell topbar.
   (The public navbar's Disasters / Agencies dropdowns and mobile
   menu are handled by public-nav.js.)

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

        // true once the menu was opened/kept by a click or key press.
        // A menu that only opened because the mouse hovered it closes
        // again when the mouse leaves; a click pins it open.
        let pinned = false;


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

            pinned = false;

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

                // Desktop: the pointer already hovered the menu open,
                // so the first click keeps it open (pinned) instead of
                // closing it. Touch / keyboard start closed.
                if (isOpen() && !pinned) {

                    pinned = true;

                } else if (isOpen()) {

                    closeMenu();

                } else {

                    openMenu();

                    pinned = true;

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

                    if (pinned) {

                        return;

                    }

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


        // Scrolling the page (mobile especially, where the menu
        // floats over the content instead of pushing it down)
        // should dismiss an open dropdown instead of leaving it
        // hanging over content that has moved past it.
        window.addEventListener(
            "scroll",
            function () {

                if (isOpen()) {

                    closeMenu();

                }

            },
            { passive: true }
        );


        // Another navbar widget (the public mobile hamburger
        // menu, a Disasters / Agencies dropdown) just opened — close this
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