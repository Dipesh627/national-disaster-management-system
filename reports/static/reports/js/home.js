/* =========================================================
   NDMS HOME PAGE - BEHAVIOUR
   ---------------------------------------------------------
   The navbar (menu, dropdowns, scroll state) is handled by
   public-nav.js. This file only drives the Home page:

     - in-page anchor scrolling (offset for the sticky header)
     - scroll reveal + timeline draw   (IntersectionObserver)
     - feedback form: star rating, counter, inline validation
     - dismissible Django messages
     - citizen-reviews carousel (native scroll-snap + buttons)

   Everything degrades gracefully: without JS the page is fully
   visible, the form submits normally (the server validates),
   and the reviews row can still be swiped / scrolled.
   ========================================================= */

(function () {
    "use strict";

    var reduceMotion = window.matchMedia
        && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function ready(fn) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", fn);
        } else {
            fn();
        }
    }

    ready(function () {

        /* -------------------------------------------------
           1. IN-PAGE ANCHORS  (#contact, #feedback, ...)
           Handles "#x" and "/#x" (footer / navbar links on
           this page) without a reload. scroll-padding-top in
           about.css keeps the sticky header from covering
           the target.
           ------------------------------------------------- */

        document.addEventListener("click", function (event) {

            var link = event.target.closest("a[href*='#']");

            if (!link || event.defaultPrevented || event.button !== 0
                || event.metaKey || event.ctrlKey || event.shiftKey) {
                return;
            }

            var url;

            try {
                url = new URL(link.href, window.location.href);
            } catch (e) {
                return;
            }

            if (url.origin !== window.location.origin
                || url.pathname !== window.location.pathname
                || !url.hash || url.hash === "#") {
                return;
            }

            var target = document.getElementById(decodeURIComponent(url.hash.slice(1)));

            if (!target) {
                return;
            }

            event.preventDefault();

            target.scrollIntoView({
                behavior: reduceMotion ? "auto" : "smooth",
                block: "start"
            });

            // Keep the URL shareable and move keyboard focus.
            if (window.history && window.history.replaceState) {
                window.history.replaceState(null, "", url.hash);
            }

            if (!target.hasAttribute("tabindex")) {
                target.setAttribute("tabindex", "-1");
            }

            target.focus({ preventScroll: true });
        });


        /* -------------------------------------------------
           2. SCROLL REVEAL + TIMELINE DRAW
           One observer, no scroll listeners.
           ------------------------------------------------- */

        var revealTargets = Array.prototype.slice.call(
            document.querySelectorAll(".reveal, #processSteps")
        );

        function show(node) {
            node.classList.add("is-visible");
        }

        if (!("IntersectionObserver" in window) || reduceMotion) {

            revealTargets.forEach(show);

        } else {

            var observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        show(entry.target);
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.15, rootMargin: "0px 0px -8% 0px" });

            revealTargets.forEach(function (node, index) {

                // Light stagger for siblings that enter together
                // (the disaster-type cards).
                if (node.classList.contains("type-card")) {
                    var slot = Array.prototype.indexOf.call(
                        node.parentNode.children, node
                    );
                    node.style.transitionDelay = Math.min(slot, 3) * 70 + "ms";
                }

                observer.observe(node);
            });
        }


        /* -------------------------------------------------
           3. DJANGO MESSAGES
           ------------------------------------------------- */

        document.querySelectorAll(".message-close").forEach(function (button) {
            button.addEventListener("click", function () {
                var message = button.closest(".django-message");

                if (message) {
                    message.remove();
                }
            });
        });


        /* -------------------------------------------------
           4. FEEDBACK FORM
           The server stays the source of truth (it validates
           and saves). This only gives instant, inline
           feedback and prevents an avoidable round trip.
           ------------------------------------------------- */

        var form = document.getElementById("feedbackForm");

        if (form) {

            var radios = Array.prototype.slice.call(
                form.querySelectorAll("input[name='rating']")
            );
            var status = document.getElementById("ratingStatus");
            var ratingError = document.getElementById("ratingError");
            var message = document.getElementById("feedbackMessage");
            var messageError = document.getElementById("messageError");
            var counter = document.getElementById("feedbackCharacterCount");

            var LABELS = ["Select a rating", "Poor", "Fair", "Good", "Very good", "Excellent"];

            function selectedRating() {
                var checked = radios.filter(function (radio) {
                    return radio.checked;
                })[0];

                return checked ? parseInt(checked.value, 10) : 0;
            }

            function updateStatus() {
                var value = selectedRating();

                if (status) {
                    status.textContent = value
                        ? value + " of 5 \u2013 " + LABELS[value]
                        : LABELS[0];
                    status.classList.toggle("has-value", value > 0);
                }

                if (value && ratingError) {
                    ratingError.hidden = true;
                }
            }

            radios.forEach(function (radio) {
                radio.addEventListener("change", updateStatus);
            });

            function updateCounter() {
                if (!message || !counter) {
                    return;
                }

                var length = message.value.length;
                var max = message.maxLength > 0 ? message.maxLength : 500;

                counter.textContent = length + " / " + max;
                counter.classList.toggle("is-near", length >= max * 0.9);

                if (message.value.trim() && messageError) {
                    messageError.hidden = true;
                    message.classList.remove("is-invalid");
                    message.removeAttribute("aria-invalid");
                }
            }

            if (message) {
                message.addEventListener("input", updateCounter);
            }

            form.addEventListener("submit", function (event) {

                var problems = [];

                if (!selectedRating()) {
                    if (ratingError) {
                        ratingError.hidden = false;
                    }
                    problems.push(radios[0]);
                }

                if (message && !message.value.trim()) {
                    if (messageError) {
                        messageError.hidden = false;
                    }
                    message.classList.add("is-invalid");
                    message.setAttribute("aria-invalid", "true");
                    problems.push(message);
                }

                if (problems.length) {
                    event.preventDefault();
                    problems[0].focus();
                }
            });

            updateStatus();
            updateCounter();
        }


        /* -------------------------------------------------
           5. CITIZEN REVIEWS CAROUSEL
           The track scrolls natively (scroll-snap). Buttons
           page it; their disabled state follows whether the
           first / last card is fully in view.
           ------------------------------------------------- */

        var track = document.getElementById("reviewsTrack");
        var prev = document.getElementById("reviewPrev");
        var next = document.getElementById("reviewNext");

        if (track && prev && next) {

            var cards = track.querySelectorAll(".review-card");

            function pageBy(direction) {
                var first = cards[0];

                if (!first) {
                    return;
                }

                var gap = parseFloat(window.getComputedStyle(track).columnGap) || 20;
                var visible = Math.max(
                    1,
                    Math.round(track.clientWidth / (first.offsetWidth + gap))
                );

                track.scrollBy({
                    left: direction * visible * (first.offsetWidth + gap),
                    behavior: reduceMotion ? "auto" : "smooth"
                });
            }

            prev.addEventListener("click", function () { pageBy(-1); });
            next.addEventListener("click", function () { pageBy(1); });

            if ("IntersectionObserver" in window && cards.length) {

                var edge = new IntersectionObserver(function (entries) {
                    entries.forEach(function (entry) {
                        var atEdge = entry.intersectionRatio > 0.95;

                        if (entry.target === cards[0]) {
                            prev.disabled = atEdge;
                        }

                        if (entry.target === cards[cards.length - 1]) {
                            next.disabled = atEdge;
                        }
                    });
                }, { root: track, threshold: [0, 0.95, 1] });

                edge.observe(cards[0]);
                edge.observe(cards[cards.length - 1]);

            } else if (cards.length < 2) {

                prev.disabled = true;
                next.disabled = true;
            }
        }
    });
})();