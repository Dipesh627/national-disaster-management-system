document.addEventListener("DOMContentLoaded", () => {
    const shell = document.getElementById("adminShell");
    const sidebar = document.getElementById("adminSidebar");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebarOverlay = document.getElementById("sidebarOverlay");

    const profile = document.querySelector(".admin-profile");
    const profileButton = document.getElementById("adminProfileButton");
    const profileMenu = document.getElementById("adminProfileMenu");

    const alerts = document.querySelector(".admin-alerts");
    const alertButton = document.getElementById("adminAlertButton");
    const alertDropdown = document.getElementById("adminAlertDropdown");

    const searchWrap = document.getElementById("adminSearch");
    const searchToggle = document.getElementById("searchToggle");
    const searchForm = document.getElementById("adminSearchForm");
    const searchInput = document.getElementById("adminSearchInput");
    const searchClear = document.getElementById("searchClear");

    const MOBILE_BREAKPOINT = 820;

    const isMobile = () => window.innerWidth <= MOBILE_BREAKPOINT;

    /* Desktop = pointer:fine + hover:hover devices, matching the
       citizen dashboard's avatar/notification hover behaviour
       (navbar-avatar.js / dashboard.js), so the admin topbar
       dropdowns behave the same way on the same devices. */
    const hoverCapable =
        window.matchMedia &&
        window.matchMedia("(hover: hover) and (pointer: fine)").matches;

    let profileHoverCloseTimer = null;
    let alertsHoverCloseTimer = null;

    /* =====================================================
       SIDEBAR
       ===================================================== */

    /* Body scroll lock (mobile sidebar open state).

       A plain `overflow: hidden` on <body> — the previous
       implementation — does not reliably block background touch
       scrolling on iOS/Safari; the page behind the overlay can still
       drag/scroll while the sidebar sheet is open, which is what
       made the fixed sidebar *appear* to move with the page. The
       standard robust fix is to also pin the body to its current
       scroll position with `position: fixed`, then restore that
       exact scroll position when unlocking. `sidebarScrollLocked`
       guards against calling this twice in a row (e.g. duplicate
       resize events) and losing the saved position. */

    let sidebarScrollLockY = 0;
    let sidebarScrollLocked = false;

    function lockBodyScroll() {
        if (sidebarScrollLocked) return;
        sidebarScrollLocked = true;

        sidebarScrollLockY = window.scrollY || window.pageYOffset || 0;

        document.body.style.top = `-${sidebarScrollLockY}px`;
        document.body.classList.add("admin-sidebar-lock");
    }

    function unlockBodyScroll() {
        if (!sidebarScrollLocked) return;
        sidebarScrollLocked = false;

        document.body.classList.remove("admin-sidebar-lock");
        document.body.style.top = "";

        window.scrollTo(0, sidebarScrollLockY);
    }

    function syncBodyLock() {
        const shouldLock = Boolean(
            shell?.classList.contains("sidebar-open") && isMobile()
        );

        if (shouldLock) {
            lockBodyScroll();
        } else {
            unlockBodyScroll();
        }
    }

    /* aria-hidden on the sidebar must track whether the mobile drawer
       is actually open, not just the viewport width. Previously this
       was only set once on load and again on resize, so opening the
       drawer on mobile never cleared aria-hidden="true" -- the nav
       links stayed hidden from assistive tech the whole time the
       drawer was visually open. On desktop the sidebar is always
       visible, so it's always aria-hidden="false" there regardless
       of the sidebar-open class. */
    function syncSidebarAriaHidden() {
        if (!sidebar) return;

        const hidden =
            isMobile() && !shell?.classList.contains("sidebar-open");

        sidebar.setAttribute("aria-hidden", hidden ? "true" : "false");
    }

    function openSidebar() {
        if (!shell) return;

        shell.classList.add("sidebar-open");
        sidebarToggle?.setAttribute("aria-expanded", "true");
        syncBodyLock();
        syncSidebarAriaHidden();
    }

    function closeSidebar() {
        if (!shell) return;

        shell.classList.remove("sidebar-open");
        sidebarToggle?.setAttribute("aria-expanded", "false");
        syncBodyLock();
        syncSidebarAriaHidden();
    }

    sidebarToggle?.addEventListener("click", () => {
        if (shell?.classList.contains("sidebar-open")) {
            closeSidebar();
        } else {
            closeProfile();
            closeAlerts();
            openSidebar();
        }
    });

    sidebarOverlay?.addEventListener("click", closeSidebar);

    document
        .querySelectorAll(".sidebar-link, .sidebar-footer-link")
        .forEach((link) => {
            link.addEventListener("click", () => {
                if (isMobile()) closeSidebar();
            });
        });

    window.addEventListener("resize", () => {
        if (!isMobile()) closeSidebar();
        syncBodyLock();
        syncSidebarAriaHidden();
    });

    /* Keep the active sidebar item in view on load — without this,
       a long menu can scroll the active link out of sight above the
       fold (e.g. "Feedback") and the user has to scroll down to find
       it themselves.

       This intentionally does NOT use Element.scrollIntoView(). That
       API walks every scrollable ancestor between the element and
       the viewport and scrolls whichever ones it decides are
       necessary — on this layout that chain includes the document
       itself, so it can end up scrolling the whole page/viewport
       instead of just the sidebar. Setting `.sidebar-navigation`'s
       own `scrollTop` directly guarantees only that one internal
       container ever moves. */
    const sidebarNav = document.querySelector(".sidebar-navigation");
    const activeLink = sidebarNav?.querySelector(".sidebar-link.is-active");

    if (sidebarNav && activeLink) {
        const navRect = sidebarNav.getBoundingClientRect();
        const linkRect = activeLink.getBoundingClientRect();

        const isAbove = linkRect.top < navRect.top;
        const isBelow = linkRect.bottom > navRect.bottom;

        if (isAbove || isBelow) {
            const linkCenter = (linkRect.top + linkRect.bottom) / 2;
            const navCenter = (navRect.top + navRect.bottom) / 2;

            sidebarNav.scrollTop += linkCenter - navCenter;
        }
    }

    /* =====================================================
       PROFILE DROPDOWN
       ===================================================== */

    function openProfile() {
        if (!profile || !profileButton || !profileMenu) return;

        if (profileHoverCloseTimer) {
            clearTimeout(profileHoverCloseTimer);
            profileHoverCloseTimer = null;
        }

        closeSearch();
        closeAlerts();
        profile.classList.add("open");
        profileButton.setAttribute("aria-expanded", "true");
    }

    function closeProfile() {
        if (!profile || !profileButton || !profileMenu) return;

        if (profileHoverCloseTimer) {
            clearTimeout(profileHoverCloseTimer);
            profileHoverCloseTimer = null;
        }

        profile.classList.remove("open");
        profileButton.setAttribute("aria-expanded", "false");
    }

    function toggleProfile() {
        if (!profile) return;

        if (profile.classList.contains("open")) {
            closeProfile();
        } else {
            openProfile();
        }
    }

    profileButton?.addEventListener("click", (event) => {
        event.stopPropagation();
        toggleProfile();
    });

    profileMenu?.addEventListener("click", (event) => {
        event.stopPropagation();
    });

    /* Desktop hover: hovering the avatar (or the open dropdown
       itself) opens/keeps it open. Leaving the combined area
       closes it after a short delay so moving the cursor from
       the button into the menu never closes it in transit. */
    if (hoverCapable && profile) {

        profile.addEventListener("mouseenter", () => {
            openProfile();
        });

        profile.addEventListener("mouseleave", () => {
            profileHoverCloseTimer = setTimeout(closeProfile, 150);
        });
    }

    /* =====================================================
       ADMIN ALERTS DROPDOWN
       ===================================================== */

    function openAlerts() {
        if (!alerts || !alertButton || !alertDropdown) return;

        if (alertsHoverCloseTimer) {
            clearTimeout(alertsHoverCloseTimer);
            alertsHoverCloseTimer = null;
        }

        closeSearch();
        closeProfile();
        alerts.classList.add("open");
        alertButton.setAttribute("aria-expanded", "true");
    }

    function closeAlerts() {
        if (!alerts || !alertButton || !alertDropdown) return;

        if (alertsHoverCloseTimer) {
            clearTimeout(alertsHoverCloseTimer);
            alertsHoverCloseTimer = null;
        }

        alerts.classList.remove("open");
        alertButton.setAttribute("aria-expanded", "false");
    }

    function toggleAlerts() {
        if (!alerts) return;

        if (alerts.classList.contains("open")) {
            closeAlerts();
        } else {
            openAlerts();
        }
    }

    alertButton?.addEventListener("click", (event) => {
        event.stopPropagation();
        toggleAlerts();
    });

    alertDropdown?.addEventListener("click", (event) => {
        event.stopPropagation();
    });

    /* Desktop hover — same pattern as the profile dropdown above. */
    if (hoverCapable && alerts) {

        alerts.addEventListener("mouseenter", () => {
            openAlerts();
        });

        alerts.addEventListener("mouseleave", () => {
            alertsHoverCloseTimer = setTimeout(closeAlerts, 150);
        });
    }

    /* =====================================================
       SEARCH — GLOBAL ADMIN SEARCH
       (independent from every module's own request.GET.q
       search/filter; submits only to its own endpoint)
       ===================================================== */

    function syncSearchClear() {
        if (!searchInput || !searchClear) return;

        searchClear.hidden = searchInput.value.trim().length === 0;
    }

    function openSearch() {
        if (!searchToggle || !searchForm) return;

        closeProfile();
        closeAlerts();
        searchForm.hidden = false;
        searchToggle.hidden = true;
        searchToggle.setAttribute("aria-expanded", "true");

        syncSearchClear();

        requestAnimationFrame(() => searchInput?.focus());
    }

    function closeSearch() {
        if (!searchToggle || !searchForm) return;

        searchForm.hidden = true;
        searchToggle.hidden = false;
        searchToggle.setAttribute("aria-expanded", "false");

        if (searchInput) searchInput.value = "";
        if (searchClear) searchClear.hidden = true;
    }

    searchToggle?.addEventListener("click", () => {
        if (searchForm && !searchForm.hidden) {
            searchInput?.focus();
        } else {
            openSearch();
        }
    });

    searchInput?.addEventListener("input", syncSearchClear);

    searchClear?.addEventListener("click", () => {
        if (!searchInput) return;

        searchInput.value = "";
        syncSearchClear();
        searchInput.focus();
    });

    searchForm?.addEventListener("submit", (event) => {
        if (!searchInput) return;

        const trimmed = searchInput.value.trim();

        if (!trimmed) {
            /* Empty query: do nothing, keep the search open. */
            event.preventDefault();
            searchInput.focus();
            return;
        }

        searchInput.value = trimmed;
    });

    /* =====================================================
       OUTSIDE CLICK
       ===================================================== */

    document.addEventListener("click", (event) => {
        const target = event.target;

        if (profile && profileMenu && !profile.contains(target)) {
            closeProfile();
        }

        if (alerts && alertDropdown && !alerts.contains(target)) {
            closeAlerts();
        }

        if (searchWrap && searchForm && !searchForm.hidden && !searchWrap.contains(target)) {
            closeSearch();
        }
    });

    /* =====================================================
       KEYBOARD
       ===================================================== */

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeSearch();
            closeProfile();
            closeAlerts();
            if (isMobile()) closeSidebar();
            return;
        }

        /* Quick search shortcut: / */
        if (
            event.key === "/" &&
            !event.ctrlKey &&
            !event.metaKey &&
            !event.altKey
        ) {
            const active = document.activeElement;

            if (
                active &&
                ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName)
            ) {
                return;
            }

            if (active?.isContentEditable) return;

            event.preventDefault();
            openSearch();
        }
    });

    /* =====================================================
       INITIAL STATE
       (profileMenu / alertDropdown visibility is handled purely
       by CSS via the "open" class on their .admin-profile /
       .admin-alerts wrapper — no hidden attribute to set here,
       since toggling that would force display:none and break
       the open/close transition.)
       ===================================================== */

    if (searchForm) {
        searchForm.hidden = true;
    }

    if (searchClear) {
        searchClear.hidden = true;
    }

    syncSidebarAriaHidden();
});