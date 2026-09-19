/* =========================================================
   NDMS ABOUT PAGE
   ABOUT JAVASCRIPT
   ========================================================= */


document.addEventListener(
    "DOMContentLoaded",
    function () {


        /* =================================================
           NOTE: the mobile hamburger toggle (#mobileMenuToggle /
           #publicMobileMenu) is wired up centrally by the shared
           reports/js/public-nav.js, loaded on every page that
           includes the public navbar partial. That keeps the
           behavior identical (and actually present) on Home,
           About, View Disasters and Disaster Detail alike,
           instead of each page reimplementing it separately.
           ================================================= */


        /* =================================================
           SMOOTH ANCHOR SCROLL
           ================================================= */

        const anchorLinks =
            document.querySelectorAll(
                'a[href^="#"]'
            );


        anchorLinks.forEach(
            function (link) {

                link.addEventListener(
                    "click",
                    function (event) {

                        const targetId =
                            link.getAttribute(
                                "href"
                            );


                        if (
                            !targetId ||
                            targetId === "#"
                        ) {

                            return;

                        }


                        const target =
                            document.querySelector(
                                targetId
                            );


                        if (!target) {

                            return;

                        }


                        event.preventDefault();


                        const navbar =
                            document.querySelector(
                                ".public-navbar"
                            );


                        const navbarHeight =
                            navbar
                                ? navbar.offsetHeight
                                : 0;


                        const targetPosition =
                            target
                                .getBoundingClientRect()
                                .top
                            +
                            window.scrollY
                            -
                            navbarHeight
                            -
                            15;


                        window.scrollTo(
                            {
                                top:
                                    targetPosition,

                                behavior:
                                    "smooth"
                            }
                        );


                        if (
                            window.NDMSPublicNav &&
                            window.NDMSPublicNav.closeMobileMenu
                        ) {

                            window.NDMSPublicNav.closeMobileMenu();

                        }

                    }
                );

            }
        );


        /* =================================================
           LIGHTWEIGHT SCROLL REVEAL (IntersectionObserver)
           Matches the Home page's ".reveal" fade-up pattern
           so the About page shares the same animation feel.
           ================================================= */

        const reduceMotion =
            window.matchMedia &&
            window.matchMedia(
                "(prefers-reduced-motion: reduce)"
            ).matches;


        const reveals =
            document.querySelectorAll(
                ".reveal"
            );


        if (
            reduceMotion ||
            !("IntersectionObserver" in window)
        ) {

            reveals.forEach(
                function (element) {

                    element.classList.add(
                        "reveal-visible"
                    );

                }
            );

        } else {

            const revealObserver =
                new IntersectionObserver(
                    function (entries) {

                        entries.forEach(
                            function (entry) {

                                if (
                                    entry.isIntersecting
                                ) {

                                    entry.target.classList.add(
                                        "reveal-visible"
                                    );

                                    revealObserver.unobserve(
                                        entry.target
                                    );

                                }

                            }
                        );

                    },
                    {
                        threshold: 0.1,
                        rootMargin: "0px 0px -30px 0px"
                    }
                );


            reveals.forEach(
                function (element) {

                    revealObserver.observe(
                        element
                    );

                }
            );

        }


    }
);