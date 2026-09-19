/* =========================================================
   NDMS — CITIZEN PREFERENCE RESOLVER
   =========================================================

   The citizen's saved preferences are already rendered onto
   <html> by the server ({% citizen_html_attrs %}), so theme,
   text size, reduce motion and high contrast are correct on
   the very first paint with no JavaScript involved.

   This file exists for ONE job: resolving the "System" theme
   choice, which only the browser knows the answer to.

       data-theme="system"  ->  data-theme="light" | "dark"

   It is loaded synchronously in <head>, BEFORE any stylesheet
   renders content, so switching the attribute cannot cause a
   visible flash of the wrong theme.

   It writes nothing to storage and reads nothing about the
   user — the source of truth is always the UserSettings row,
   which means preferences can never leak between accounts on
   a shared browser.
   ========================================================= */

(function () {

    'use strict';

    var root = document.documentElement;

    if (!root) {
        return;
    }

    // Only act when the citizen actually chose "System".
    if (root.getAttribute('data-theme-choice') !== 'system') {
        return;
    }

    var query = null;

    try {
        query = window.matchMedia('(prefers-color-scheme: dark)');
    } catch (e) {
        query = null;
    }

    function apply(prefersDark) {
        root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    }

    if (!query) {
        // Browser cannot tell us — fall back to the project's
        // existing light appearance.
        apply(false);
        return;
    }

    apply(query.matches);

    // Keep following the OS while the page is open (e.g. macOS /
    // Windows auto dark mode at sunset).
    function onChange(event) {
        apply(event.matches);
    }

    if (typeof query.addEventListener === 'function') {
        query.addEventListener('change', onChange);
    } else if (typeof query.addListener === 'function') {
        // Older Safari.
        query.addListener(onChange);
    }

}());