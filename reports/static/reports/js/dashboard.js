/* =========================================================
   NDMS DASHBOARD JAVASCRIPT
   PROFESSIONAL CITIZEN DASHBOARD
   ========================================================= */


/* =========================================================
   ELEMENTS
   ========================================================= */

const sidebar =
    document.getElementById("dashboardSidebar");

const sidebarOverlay =
    document.getElementById("sidebarOverlay");

const mobileSidebarToggle =
    document.getElementById("mobileSidebarToggle");

const notificationButton =
    document.getElementById("notificationButton");

const notificationDropdown =
    document.getElementById("notificationDropdown");


/* =========================================================
   MOBILE SIDEBAR

   Body scroll lock: `body.sidebar-open { overflow: hidden }`
   (dashboard.css) is kept as a harmless fallback, but on mobile
   Android Chrome `overflow: hidden` alone does NOT reliably stop
   the background document from being touch-scrolled behind a
   position:fixed drawer. When the background still scrolls, the
   browser's dynamic address bar hides/shows mid-gesture, which
   changes the real (100dvh) viewport height WHILE the sidebar is
   open — that's what let the fixed sidebar's footer ("Back to
   Website") render outside the visible area / be intermittently
   unreachable, even though the sidebar itself is a correct flex
   column (brand / scrollable nav / footer).

   lockBodyScroll()/unlockBodyScroll() pin <body> with
   position:fixed at the current scroll offset while the drawer is
   open, so the background document cannot scroll (and so cannot
   trigger a toolbar-driven viewport resize) no matter how the user
   swipes inside the sidebar nav, then restore the exact previous
   scroll position on close (no jump to top). The open/close guards
   below (`already open` / `already closed`) matter here: several
   other handlers below (resize, pageshow, Escape) call
   closeSidebar() unconditionally just to be safe, and without the
   guard each of those would re-run unlockBodyScroll() and force
   window.scrollTo even when the sidebar was never opened, which is
   itself an unwanted scroll jump.
   ========================================================= */

let sidebarLockScrollY = 0;

function lockBodyScroll() {

    sidebarLockScrollY =
        window.scrollY || window.pageYOffset || 0;

    document.body.style.position = "fixed";
    document.body.style.top = "-" + sidebarLockScrollY + "px";
    document.body.style.left = "0";
    document.body.style.right = "0";
    document.body.style.width = "100%";

}

function unlockBodyScroll() {

    document.body.style.position = "";
    document.body.style.top = "";
    document.body.style.left = "";
    document.body.style.right = "";
    document.body.style.width = "";

    window.scrollTo(0, sidebarLockScrollY);

}


function openSidebar() {

    if (!sidebar) {
        return;
    }

    if (sidebar.classList.contains("open")) {
        return;
    }

    sidebar.classList.add("open");

    if (sidebarOverlay) {
        sidebarOverlay.classList.add("show");
    }

    document.body.classList.add("sidebar-open");

    lockBodyScroll();

    if (mobileSidebarToggle) {

        mobileSidebarToggle.setAttribute(
            "aria-expanded",
            "true"
        );

        mobileSidebarToggle.setAttribute(
            "aria-label",
            "Close dashboard menu"
        );

    }

}


function closeSidebar() {

    if (!sidebar) {
        return;
    }

    if (!sidebar.classList.contains("open")) {
        return;
    }

    sidebar.classList.remove("open");

    if (sidebarOverlay) {
        sidebarOverlay.classList.remove("show");
    }

    document.body.classList.remove("sidebar-open");

    unlockBodyScroll();

    if (mobileSidebarToggle) {

        mobileSidebarToggle.setAttribute(
            "aria-expanded",
            "false"
        );

        mobileSidebarToggle.setAttribute(
            "aria-label",
            "Open dashboard menu"
        );

    }

}


function toggleSidebar() {

    if (!sidebar) {
        return;
    }

    if (sidebar.classList.contains("open")) {

        closeSidebar();

    } else {

        openSidebar();

    }

}


if (mobileSidebarToggle) {

    mobileSidebarToggle.addEventListener(
        "click",
        function (event) {

            event.preventDefault();

            toggleSidebar();

        }
    );

}


if (sidebarOverlay) {

    sidebarOverlay.addEventListener(
        "click",
        function () {

            closeSidebar();

        }
    );

}


/* =========================================================
   SIDEBAR NAVIGATION
   ========================================================= */

/* Excludes .sidebar-group-toggle (the Disasters expand/collapse
   button) — clicking it only opens a submenu, it never navigates,
   so it must not also close the mobile drawer. */
const sidebarLinks =
    document.querySelectorAll(
        ".sidebar-link:not(.sidebar-group-toggle), .sidebar-sublink"
    );


sidebarLinks.forEach(
    function (link) {

        link.addEventListener(
            "click",
            function () {

                if (window.innerWidth <= 850) {

                    closeSidebar();

                }

            }
        );

    }
);


/* =========================================================
   NOTIFICATION DROPDOWN
   ========================================================= */

const notificationWrapper =
    document.querySelector(".notification-wrapper");

/* Desktop = pointer:fine + hover:hover devices, matching the
   same hover-capable check the avatar dropdown already uses
   (navbar-avatar.js), so both topbar dropdowns behave the
   same way on the same devices. */
const notificationHoverCapable =
    window.matchMedia &&
    window.matchMedia(
        "(hover: hover) and (pointer: fine)"
    ).matches;

let notificationHoverCloseTimer = null;


function openNotifications() {

    if (!notificationDropdown) {
        return;
    }

    if (notificationHoverCloseTimer) {
        clearTimeout(notificationHoverCloseTimer);
        notificationHoverCloseTimer = null;
    }

    notificationDropdown.classList.add(
        "show"
    );

    if (notificationButton) {

        notificationButton.setAttribute(
            "aria-expanded",
            "true"
        );

    }

    /* Let the avatar dropdown (navbar-avatar.js) know a menu
       just opened, so only one topbar dropdown is ever open
       at a time. */
    document.dispatchEvent(
        new CustomEvent(
            "ndms:menu-opened",
            { detail: "notifications" }
        )
    );

}


function closeNotifications() {

    if (!notificationDropdown) {
        return;
    }

    if (notificationHoverCloseTimer) {
        clearTimeout(notificationHoverCloseTimer);
        notificationHoverCloseTimer = null;
    }

    notificationDropdown.classList.remove(
        "show"
    );

    if (notificationButton) {

        notificationButton.setAttribute(
            "aria-expanded",
            "false"
        );

    }

}


function toggleNotifications() {

    if (!notificationDropdown) {
        return;
    }

    if (
        notificationDropdown.classList.contains(
            "show"
        )
    ) {

        closeNotifications();

    } else {

        openNotifications();

    }

}


if (notificationButton) {

    notificationButton.addEventListener(
        "click",
        function (event) {

            event.preventDefault();

            event.stopPropagation();

            toggleNotifications();

        }
    );

}


/* =========================================================
   NOTIFICATION DROPDOWN — DESKTOP HOVER
   Hovering the bell (or the open dropdown itself) opens/keeps
   it open, matching the avatar dropdown's hover behaviour.
   Leaving the combined area closes it after a short delay, so
   moving the cursor from the bell into the dropdown never
   closes it in transit. Mobile/touch keeps click-only, since
   touch devices don't have a real "hover" state.
   ========================================================= */

if (notificationHoverCapable && notificationWrapper) {

    notificationWrapper.addEventListener(
        "mouseenter",
        function () {

            openNotifications();

        }
    );

    notificationWrapper.addEventListener(
        "mouseleave",
        function () {

            notificationHoverCloseTimer =
                setTimeout(
                    closeNotifications,
                    150
                );

        }
    );

}


/* Another topbar dropdown (the avatar menu) just opened —
   close this one so only one shows at a time. */
document.addEventListener(
    "ndms:menu-opened",
    function (event) {

        if (
            event.detail !== "notifications" &&
            notificationDropdown &&
            notificationDropdown.classList.contains("show")
        ) {

            closeNotifications();

        }

    }
);


/* =========================================================
   CLOSE NOTIFICATION ON OUTSIDE CLICK
   ========================================================= */

document.addEventListener(
    "click",
    function (event) {

        if (
            !notificationDropdown ||
            !notificationButton
        ) {

            return;

        }

        const clickedInsideDropdown =
            notificationDropdown.contains(
                event.target
            );

        const clickedButton =
            notificationButton.contains(
                event.target
            );

        if (
            !clickedInsideDropdown &&
            !clickedButton
        ) {

            closeNotifications();

        }

    }
);


/* =========================================================
   NOTIFICATION ITEMS
   ========================================================= */

const notificationItems =
    document.querySelectorAll(
        ".notification-item"
    );


notificationItems.forEach(
    function (item) {

        item.addEventListener(
            "click",
            function () {

                /*
                 * Notification items are normally links.
                 * Closing the dropdown keeps navigation clean.
                 */

                closeNotifications();

            }
        );

    }
);


/* =========================================================
   VIEW ALL NOTIFICATIONS
   ========================================================= */

const viewAllNotifications =
    document.querySelector(
        ".view-all-notifications"
    );


if (viewAllNotifications) {

    viewAllNotifications.addEventListener(
        "click",
        function () {

            closeNotifications();

        }
    );

}


/* =========================================================
   KEYBOARD ACCESSIBILITY
   ========================================================= */

document.addEventListener(
    "keydown",
    function (event) {

        if (event.key === "Escape") {

            closeNotifications();

            closeSidebar();

        }

    }
);


/* =========================================================
   WINDOW RESIZE
   ========================================================= */

window.addEventListener(
    "resize",
    function () {

        /*
         * Desktop ma sidebar automatically reset.
         */

        if (window.innerWidth > 850) {

            closeSidebar();

        }

    }
);


/* =========================================================
   PREVENT SIDEBAR SCROLL LOCK ISSUES
   ========================================================= */

window.addEventListener(
    "pageshow",
    function () {

        if (window.innerWidth > 850) {

            closeSidebar();

        }

        closeNotifications();

    }
);


/* =========================================================
   REDUCED MOTION SUPPORT
   ========================================================= */

const prefersReducedMotion =
    window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    );


function handleReducedMotion() {

    if (
        prefersReducedMotion &&
        prefersReducedMotion.matches
    ) {

        document.documentElement.classList.add(
            "reduce-motion"
        );

    } else {

        document.documentElement.classList.remove(
            "reduce-motion"
        );

    }

}


handleReducedMotion();


if (
    prefersReducedMotion &&
    typeof prefersReducedMotion.addEventListener === "function"
) {

    prefersReducedMotion.addEventListener(
        "change",
        handleReducedMotion
    );

}


/* =========================================================
   SIDEBAR — DISASTERS SUBMENU

   Self-contained: only touches ".sidebar-group" elements, so
   it can't interfere with the sidebar toggle / notification /
   avatar logic above. Server-rendered "is-open" already
   expands the group when a Disasters page is active; this
   only handles the user manually opening/closing it.
   ========================================================= */

document.querySelectorAll(".sidebar-group").forEach(function (group) {

    const toggle = group.querySelector(".sidebar-group-toggle");

    if (!toggle) {
        return;
    }

    toggle.addEventListener("click", function () {

        const isOpen = group.classList.toggle("is-open");

        toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");

    });

});


/* =========================================================
   INITIAL STATE
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        closeNotifications();

        if (window.innerWidth > 850) {

            closeSidebar();

        }

    }
);