/* =========================================================
   NDMS PUBLIC HOME INTERACTION SCRIPTS
   Lightweight, accessible, professional interactions
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const reduceMotion =
        window.matchMedia &&
        window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches;


    /* =====================================================
       1. SMOOTH LOCAL ANCHOR SCROLLING

       (Mobile hamburger / public-nav toggle now lives in the
       shared reports/js/public-nav.js, loaded on every page
       that includes the public navbar partial.)
       ===================================================== */

    document
        .querySelectorAll('a[href^="#"]')
        .forEach(function (link) {
            link.addEventListener("click", function (event) {
                const id = link.getAttribute("href");
                if (!id || id === "#") {
                    return;
                }

                const target = document.querySelector(id);
                if (!target) {
                    return;
                }

                event.preventDefault();

                const nav = document.querySelector(".public-navbar");
                const offset = nav ? nav.offsetHeight + 16 : 16;
                const top = target.getBoundingClientRect().top + window.scrollY - offset;

                window.scrollTo({
                    top: top,
                    behavior: reduceMotion ? "auto" : "smooth"
                });
            });
        });


    /* =====================================================
       2. FEEDBACK STAR RATING
       ===================================================== */

    const stars = Array.from(document.querySelectorAll(".rating-star"));
    const ratingValue = document.getElementById("ratingValue");
    const ratingStatus = document.getElementById("ratingStatus");
    const ratingInput = document.getElementById("ratingInput");
    let selectedRating = 0;

    const labels = {
        1: "Very Poor",
        2: "Poor",
        3: "Average",
        4: "Good",
        5: "Excellent"
    };

    function paintStars(value) {
        stars.forEach(function (star) {
            star.classList.toggle(
                "selected",
                Number(star.dataset.rating) <= value
            );
        });

        if (ratingStatus) {
            if (value) {
                ratingStatus.textContent = value + " out of 5 — " + labels[value];
                ratingStatus.style.color = "var(--navy)";
            } else {
                ratingStatus.textContent = "Select a rating";
                ratingStatus.style.color = "var(--muted)";
            }
        }
    }

    stars.forEach(function (star) {
        star.addEventListener("mouseenter", function () {
            paintStars(Number(star.dataset.rating));
        });

        star.addEventListener("focus", function () {
            paintStars(Number(star.dataset.rating));
        });

        star.addEventListener("click", function () {
            selectedRating = Number(star.dataset.rating);
            if (ratingValue) {
                ratingValue.value = selectedRating;
            }
            paintStars(selectedRating);
        });

        star.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                star.click();
            }
        });
    });

    if (ratingInput) {
        ratingInput.addEventListener("mouseleave", function () {
            paintStars(selectedRating);
        });
    }


    /* =====================================================
       3. FEEDBACK CHARACTER COUNTER
       ===================================================== */

    const feedbackMessage = document.getElementById("feedbackMessage");
    const count = document.getElementById("feedbackCharacterCount");

    if (feedbackMessage && count) {
        function updateCount() {
            count.textContent = feedbackMessage.value.length + " / " + feedbackMessage.maxLength;
        }

        feedbackMessage.addEventListener("input", updateCount);
        updateCount();
    }


    /* =====================================================
       4. FEEDBACK FORM SUBMISSION VALIDATION
       ===================================================== */

    const feedbackForm = document.getElementById("feedbackForm");

    if (feedbackForm) {
        feedbackForm.addEventListener("submit", function (event) {
            if (!ratingValue || !ratingValue.value || Number(ratingValue.value) < 1) {
                event.preventDefault();
                alert("Please select a star rating before submitting your feedback.");
                if (stars[0]) stars[0].focus();
                return;
            }

            if (feedbackMessage && !feedbackMessage.value.trim()) {
                event.preventDefault();
                feedbackMessage.focus();
                return;
            }

            const submit = feedbackForm.querySelector(".feedback-submit-btn");
            if (submit) {
                submit.disabled = true;
                submit.innerHTML = "Submitting Feedback...";
            }
        });
    }


    /* =====================================================
       5. DJANGO MESSAGES CLOSE
       ===================================================== */

    document
        .querySelectorAll(".message-close")
        .forEach(function (button) {
            button.addEventListener("click", function () {
                const box = button.closest(".django-message");
                if (box) {
                    box.remove();
                }
            });
        });


    /* =====================================================
       6. CITIZEN REVIEWS CAROUSEL
       ===================================================== */

    const viewport = document.getElementById("reviewsViewport");
    const track = document.getElementById("reviewsTrack");
    const prev = document.getElementById("reviewPrev");
    const next = document.getElementById("reviewNext");

    if (viewport && track) {
        const cards = Array.from(track.querySelectorAll(".review-card"));
        let index = 0;

        function visibleCount() {
            if (window.innerWidth <= 600) {
                return 1;
            }
            if (window.innerWidth <= 850) {
                return 2;
            }
            return 3;
        }

        function resizeCards() {
            if (!cards.length) {
                return;
            }

            const visible = visibleCount();
            const styles = window.getComputedStyle(track);
            const gap = parseFloat(styles.gap || styles.columnGap) || 0;
            const width = (viewport.clientWidth - gap * (visible - 1)) / visible;

            cards.forEach(function (card) {
                card.style.flexBasis = width + "px";
                card.style.width = width + "px";
            });
        }

        function updateCarousel() {
            resizeCards();
            const max = Math.max(0, cards.length - visibleCount());
            index = Math.max(0, Math.min(index, max));

            if (cards[0]) {
                const gap = parseFloat(window.getComputedStyle(track).gap) || 0;
                track.style.transform = "translate3d(-" + (index * (cards[0].offsetWidth + gap)) + "px, 0, 0)";
            }

            if (prev) {
                prev.disabled = index <= 0;
            }
            if (next) {
                next.disabled = index >= max;
            }
        }

        if (prev) {
            prev.addEventListener("click", function () {
                index--;
                updateCarousel();
            });
        }

        if (next) {
            next.addEventListener("click", function () {
                index++;
                updateCarousel();
            });
        }

        let timer;
        window.addEventListener("resize", function () {
            clearTimeout(timer);
            timer = setTimeout(updateCarousel, 120);
        });

        updateCarousel();
    }


    /* =====================================================
       7. LIGHTWEIGHT SCROLL REVEAL (IntersectionObserver)
       ===================================================== */

    const reveals = document.querySelectorAll(".reveal");

    if (reduceMotion || !("IntersectionObserver" in window)) {
        reveals.forEach(function (element) {
            element.classList.add("reveal-visible");
        });
    } else {
        const observer = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("reveal-visible");
                        observer.unobserve(entry.target);
                    }
                });
            },
            {
                threshold: 0.1,
                rootMargin: "0px 0px -30px 0px"
            }
        );

        reveals.forEach(function (element) {
            observer.observe(element);
        });
    }

});