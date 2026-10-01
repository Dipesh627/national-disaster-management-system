/* =========================================================
   NDMS - ABOUT PAGE
   ---------------------------------------------------------
   One job: when the "How NDMS works" flow scrolls into view,
   add .is-visible so its connectors draw in once
   (about-page.css). Without JS, or when the browser has no
   IntersectionObserver, the connectors are simply shown
   fully drawn.

   The mobile menu and dropdowns belong to the shared
   public-nav.js; in-page anchors use CSS smooth scrolling
   (about.css).
   ========================================================= */

(function () {
    "use strict";

    var flow = document.getElementById("abFlow");

    if (!flow) {
        return;
    }

    if (!("IntersectionObserver" in window)) {
        flow.classList.add("is-visible");
        return;
    }

    var observer = new IntersectionObserver(
        function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    flow.classList.add("is-visible");
                    observer.disconnect();
                }
            });
        },
        { threshold: 0.35 }
    );

    observer.observe(flow);
})();