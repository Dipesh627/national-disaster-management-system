/* =========================================================
   NDMS THEME (light / dark)

   The initial theme is applied by the inline script in
   partials/theme_head.html before first paint. This file:
     - wires every [data-theme-toggle] button
     - persists the choice (localStorage "ndms-theme")
     - keeps aria-pressed / tooltip in sync
     - follows the OS setting until the user picks a theme
     - syncs open tabs through the "storage" event

   Nothing here talks to the server.
   ========================================================= */

(function () {
    "use strict";

    var KEY = "ndms-theme";
    var root = document.documentElement;
    var media = window.matchMedia
        ? window.matchMedia("(prefers-color-scheme: dark)")
        : null;
    var reduceMotion = window.matchMedia
        && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function current() {
        return root.getAttribute("data-theme") === "dark" ? "dark" : "light";
    }

    function stored() {
        try {
            var value = localStorage.getItem(KEY);
            return value === "light" || value === "dark" ? value : null;
        } catch (e) {
            return null;
        }
    }

    function syncButtons() {
        var dark = current() === "dark";

        document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
            button.setAttribute("aria-pressed", dark ? "true" : "false");
            button.setAttribute(
                "title",
                dark ? "Switch to light theme" : "Switch to dark theme"
            );
        });
    }

    function apply(theme, persist) {
        if (!reduceMotion) {
            root.classList.add("theme-switching");
            window.setTimeout(function () {
                root.classList.remove("theme-switching");
            }, 260);
        }

        root.setAttribute("data-theme", theme);

        if (persist) {
            try { localStorage.setItem(KEY, theme); } catch (e) {}
        }

        syncButtons();
    }

    document.addEventListener("click", function (event) {
        var button = event.target.closest("[data-theme-toggle]");

        if (!button) {
            return;
        }

        apply(current() === "dark" ? "light" : "dark", true);
    });

    // Follow the operating system until the user has chosen.
    if (media && media.addEventListener) {
        media.addEventListener("change", function (event) {
            if (!stored()) {
                apply(event.matches ? "dark" : "light", false);
            }
        });
    }

    // Another tab changed the theme.
    window.addEventListener("storage", function (event) {
        if (event.key === KEY && (event.newValue === "light" || event.newValue === "dark")) {
            apply(event.newValue, false);
        }
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", syncButtons);
    } else {
        syncButtons();
    }
})();
