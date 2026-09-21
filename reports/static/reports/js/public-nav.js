/* =========================================================
   NDMS SHARED PUBLIC NAVBAR - BEHAVIOUR
   ---------------------------------------------------------
   Single source of truth for the public navbar
   (partials/navbar.html + navbar.css). Loaded on every page
   that includes the partial. It handles:

     - scroll state        (.is-scrolled, via IntersectionObserver)
     - mobile hamburger    (#mobileMenuToggle / #publicMobileMenu)
     - dropdowns           ([data-nav-dropdown]: Disasters, Agencies)

   Interaction model
     Desktop  hover OR click opens a dropdown; Escape, outside
              click, or moving focus away closes it.
     Mobile   the hamburger opens a panel; dropdowns become
              accordions inside it. Escape, outside click,
              resizing to desktop, and following any link close
              the panel.

   Exposes window.NDMSPublicNav.closeMobileMenu() for page
   scripts that jump to an in-page anchor.
   ========================================================= */

(function () {
    "use strict";

    // Keep in sync with the breakpoint in navbar.css.
    var MOBILE_QUERY = "(max-width: 1120px)";

    var mobile = window.matchMedia(MOBILE_QUERY);
    var canHover = window.matchMedia("(hover: hover) and (pointer: fine)");

    function ready(fn) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", fn);
        } else {
            fn();
        }
    }

    function broadcast(name) {
        document.dispatchEvent(
            new CustomEvent("ndms:menu-opened", { detail: name })
        );
    }

    ready(function () {

        var header = document.getElementById("publicNavbar");

        if (!header) {
            return;
        }

        var toggle = document.getElementById("mobileMenuToggle");
        var panel = document.getElementById("publicMobileMenu");


        /* -------------------------------------------------
           SCROLL STATE
           IntersectionObserver on a 1px sentinel: no scroll
           handler runs while the user scrolls.
           ------------------------------------------------- */

        var sentinel = document.getElementById("navSentinel");

        if (sentinel && "IntersectionObserver" in window) {

            new IntersectionObserver(function (entries) {
                header.classList.toggle("is-scrolled", !entries[0].isIntersecting);
            }).observe(sentinel);

        } else {

            var ticking = false;

            window.addEventListener("scroll", function () {
                if (ticking) {
                    return;
                }
                ticking = true;
                window.requestAnimationFrame(function () {
                    header.classList.toggle("is-scrolled", window.scrollY > 4);
                    ticking = false;
                });
            }, { passive: true });
        }


        /* -------------------------------------------------
           DROPDOWNS
           ------------------------------------------------- */

        var dropdowns = Array.prototype.slice
            .call(document.querySelectorAll("[data-nav-dropdown]"))
            .map(function (root) {
                return {
                    root: root,
                    button: root.querySelector(".public-nav-dropdown-toggle"),
                    menu: root.querySelector(".public-nav-dropdown-menu"),
                    timer: null,
                    // true once opened by a click / key press. A panel
                    // that only opened because the mouse hovered it
                    // closes again when the mouse leaves.
                    pinned: false
                };
            })
            .filter(function (d) {
                return d.button && d.menu;
            });

        function isOpen(d) {
            return d.root.classList.contains("open");
        }

        function closeDropdown(d) {
            window.clearTimeout(d.timer);
            d.pinned = false;
            d.root.classList.remove("open");
            d.button.setAttribute("aria-expanded", "false");
        }

        function closeAllDropdowns(except) {
            dropdowns.forEach(function (d) {
                if (d !== except && isOpen(d)) {
                    closeDropdown(d);
                }
            });
        }

        function openDropdown(d) {
            window.clearTimeout(d.timer);
            closeAllDropdowns(d);

            d.root.classList.add("open");
            d.button.setAttribute("aria-expanded", "true");

            // On mobile the dropdown lives INSIDE the panel, so
            // broadcasting would make the panel close itself.
            if (!mobile.matches) {
                broadcast("dropdown");
            }
        }

        dropdowns.forEach(function (d) {

            // Click / Enter / Space. On a desktop the pointer has
            // already hovered the panel open, so the first click
            // pins it open instead of closing it again; the next
            // click closes it. Touch and keyboard start closed, so
            // they simply open, then close.
            d.button.addEventListener("click", function () {
                if (isOpen(d) && !d.pinned) {
                    d.pinned = true;
                } else if (isOpen(d)) {
                    closeDropdown(d);
                } else {
                    openDropdown(d);
                    d.pinned = true;
                }
            });

            // Arrow Down opens the panel and moves into it.
            d.button.addEventListener("keydown", function (event) {
                if (event.key === "ArrowDown") {
                    event.preventDefault();
                    openDropdown(d);
                    d.pinned = true;

                    var first = d.menu.querySelector("a");

                    if (first) {
                        first.focus();
                    }
                }
            });

            // Hover (desktop mice only; touch never hovers).
            d.root.addEventListener("mouseenter", function () {
                if (canHover.matches && !mobile.matches) {
                    openDropdown(d);
                }
            });

            d.root.addEventListener("mouseleave", function () {
                if (canHover.matches && !mobile.matches && !d.pinned) {
                    window.clearTimeout(d.timer);
                    d.timer = window.setTimeout(function () {
                        closeDropdown(d);
                    }, 140);
                }
            });

            // Keyboard focus leaving the dropdown closes it (desktop).
            d.root.addEventListener("focusout", function (event) {
                if (mobile.matches) {
                    return;
                }

                if (!d.root.contains(event.relatedTarget)) {
                    closeDropdown(d);
                }
            });
        });


        /* -------------------------------------------------
           MOBILE PANEL
           ------------------------------------------------- */

        function isPanelOpen() {
            return !!panel && panel.classList.contains("open");
        }

        function setPanel(open) {

            if (!panel || !toggle) {
                return;
            }

            panel.classList.toggle("open", open);
            document.body.classList.toggle("menu-open", open);

            toggle.setAttribute("aria-expanded", open ? "true" : "false");
            toggle.setAttribute(
                "aria-label",
                open ? "Close main menu" : "Open main menu"
            );

            if (open) {
                broadcast("mobile-menu");
            } else {
                closeAllDropdowns();
            }
        }

        if (toggle && panel) {

            toggle.addEventListener("click", function () {
                setPanel(!isPanelOpen());
            });

            // Following any link closes the panel (covers in-page
            // anchors, where the page does not reload).
            panel.addEventListener("click", function (event) {
                if (event.target.closest("a")) {
                    setPanel(false);
                }
            });
        }

        // Leaving the mobile layout while the panel is open.
        function onBreakpointChange() {
            if (!mobile.matches) {
                setPanel(false);
            }
            closeAllDropdowns();
        }

        if (mobile.addEventListener) {
            mobile.addEventListener("change", onBreakpointChange);
        } else if (mobile.addListener) {
            mobile.addListener(onBreakpointChange);
        }


        /* -------------------------------------------------
           GLOBAL: OUTSIDE CLICK + ESCAPE
           ------------------------------------------------- */

        document.addEventListener("click", function (event) {

            if (header.contains(event.target)) {

                // Click inside the header but outside every dropdown.
                dropdowns.forEach(function (d) {
                    if (isOpen(d) && !d.root.contains(event.target) && !mobile.matches) {
                        closeDropdown(d);
                    }
                });

                return;
            }

            closeAllDropdowns();

            if (isPanelOpen()) {
                setPanel(false);
            }
        });

        document.addEventListener("keydown", function (event) {

            if (event.key !== "Escape") {
                return;
            }

            // Mobile: Escape closes the whole panel (accordions included).
            if (mobile.matches && isPanelOpen()) {
                setPanel(false);

                if (toggle) {
                    toggle.focus();
                }

                return;
            }

            var openOne = dropdowns.filter(isOpen)[0];

            if (openOne) {
                var hadFocus = openOne.root.contains(document.activeElement);

                closeDropdown(openOne);

                if (hadFocus) {
                    openOne.button.focus();
                }

                return;
            }

            if (isPanelOpen()) {
                setPanel(false);

                if (toggle) {
                    toggle.focus();
                }
            }
        });

        // The account dropdown just opened: close everything else.
        document.addEventListener("ndms:menu-opened", function (event) {

            if (event.detail === "avatar") {
                closeAllDropdowns();

                if (isPanelOpen()) {
                    setPanel(false);
                }
            }
        });

        window.NDMSPublicNav = {
            closeMobileMenu: function () {
                setPanel(false);
            }
        };
    });
})();
