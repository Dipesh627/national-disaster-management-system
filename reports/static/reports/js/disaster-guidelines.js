/* =========================================================
   NDMS — DISASTER AWARENESS & GUIDELINES JS
   Comprehensive Public Disaster Safety & Awareness Center
   Bilingual: English + नेपाली
   Handles: Instant bilingual switching, accessible accordions,
   risk category jumping, and sticky toolbar interactions.
   ========================================================= */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        initLanguageSwitcher();
        initAccordions();
        initRiskCardsJump();
        initCategoryFilters();
        initSmoothAnchors();
    });

    /* =====================================================
       1. BILINGUAL SWITCHER
       Instant, non-reloading DOM language toggle.
       Persists in localStorage and checks URL ?lang= parameter.
       ===================================================== */
    function initLanguageSwitcher() {
        var pageBody = document.body;
        var langBtns = document.querySelectorAll('[data-lang-btn]');

        if (!langBtns.length) {
            return;
        }

        function setLanguage(lang, savePreference) {
            var validLang = (lang === 'ne') ? 'ne' : 'en';

            pageBody.setAttribute('data-lang', validLang);
            document.documentElement.setAttribute('lang', validLang);

            langBtns.forEach(function (btn) {
                var btnLang = btn.getAttribute('data-lang-btn');
                var isActive = (btnLang === validLang);

                btn.classList.toggle('is-active', isActive);
                btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
            });

            if (savePreference !== false) {
                try {
                    localStorage.setItem('ndms_guidelines_lang', validLang);
                } catch (e) {
                    // localStorage unavailable (e.g. private browsing storage disabled)
                }
            }
        }

        // 1. Check URL param ?lang=en or ?lang=ne
        var urlParams = new URLSearchParams(window.location.search);
        var urlLang = urlParams.get('lang');
        var initialLang = 'en';

        if (urlLang === 'ne' || urlLang === 'en') {
            initialLang = urlLang;
        } else {
            // 2. Check localStorage
            try {
                var storedLang = localStorage.getItem('ndms_guidelines_lang');
                if (storedLang === 'ne' || storedLang === 'en') {
                    initialLang = storedLang;
                }
            } catch (e) {
                initialLang = 'en';
            }
        }

        setLanguage(initialLang, false);

        // Bind click events on buttons
        langBtns.forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                var targetLang = btn.getAttribute('data-lang-btn');
                setLanguage(targetLang, true);
            });
        });
    }

    /* =====================================================
       2. DISASTER GUIDELINES ACCORDION
       Accessible, keyboard-friendly accordion.
       Language switching NEVER resets opened accordions.
       ===================================================== */
    function initAccordions() {
        var headers = document.querySelectorAll('.accordion-header');

        headers.forEach(function (header) {
            header.addEventListener('click', function () {
                var item = header.closest('.accordion-item');
                if (!item) return;

                var isExpanded = item.classList.contains('is-expanded');

                if (isExpanded) {
                    item.classList.remove('is-expanded');
                    header.setAttribute('aria-expanded', 'false');
                } else {
                    item.classList.add('is-expanded');
                    header.setAttribute('aria-expanded', 'true');
                }
            });

            header.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    header.click();
                }
            });
        });
    }

    /* =====================================================
       3. RISK CARDS QUICK JUMP
       Clicking a card in "Know Your Risks" scrolls to its
       accordion item, expands it, and focuses the header.
       ===================================================== */
    function initRiskCardsJump() {
        var riskCards = document.querySelectorAll('.risk-type-card[data-target-id]');

        riskCards.forEach(function (card) {
            card.addEventListener('click', function () {
                var targetId = card.getAttribute('data-target-id');
                var targetItem = document.getElementById(targetId);

                if (targetItem) {
                    // Open accordion if closed
                    targetItem.classList.add('is-expanded');
                    var header = targetItem.querySelector('.accordion-header');
                    if (header) {
                        header.setAttribute('aria-expanded', 'true');
                    }

                    // Reset filter to 'all' if filtering is active
                    resetFilterToAll();

                    // Smooth scroll with offset for sticky toolbar
                    var toolbar = document.querySelector('.guidelines-sticky-toolbar');
                    var offset = toolbar ? toolbar.offsetHeight + 80 : 100;
                    var itemPos = targetItem.getBoundingClientRect().top + window.pageYOffset - offset;

                    window.scrollTo({
                        top: itemPos,
                        behavior: 'smooth'
                    });

                    if (header) {
                        header.focus();
                    }
                }
            });
        });
    }

    /* =====================================================
       4. CATEGORY FILTER BUTTONS
       Filter accordions by hazard category (all / flood / etc.)
       ===================================================== */
    function initCategoryFilters() {
        var filterBtns = document.querySelectorAll('.guideline-filter-btn[data-filter]');
        var accordionItems = document.querySelectorAll('.accordion-item[data-disaster-category]');

        if (!filterBtns.length || !accordionItems.length) {
            return;
        }

        filterBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                var filterValue = btn.getAttribute('data-filter');

                filterBtns.forEach(function (b) {
                    b.classList.remove('is-active');
                });
                btn.classList.add('is-active');

                accordionItems.forEach(function (item) {
                    var itemCat = item.getAttribute('data-disaster-category');
                    if (filterValue === 'all' || itemCat === filterValue) {
                        item.style.display = 'block';
                    } else {
                        item.style.display = 'none';
                    }
                });
            });
        });
    }

    function resetFilterToAll() {
        var allBtn = document.querySelector('.guideline-filter-btn[data-filter="all"]');
        if (allBtn && !allBtn.classList.contains('is-active')) {
            allBtn.click();
        }
    }

    /* =====================================================
       5. SMOOTH ANCHOR SCROLLING (OFFSET AWARE)
       Accounts for fixed/sticky navbar + toolbar heights.
       ===================================================== */
    function initSmoothAnchors() {
        var anchorLinks = document.querySelectorAll('a[href^="#"]:not([href="#"])');

        anchorLinks.forEach(function (link) {
            link.addEventListener('click', function (e) {
                var targetId = link.getAttribute('href').substring(1);
                var targetEl = document.getElementById(targetId);

                if (targetEl) {
                    e.preventDefault();
                    var toolbar = document.querySelector('.guidelines-sticky-toolbar');
                    var offset = toolbar ? toolbar.offsetHeight + 24 : 80;
                    var pos = targetEl.getBoundingClientRect().top + window.pageYOffset - offset;

                    window.scrollTo({
                        top: pos,
                        behavior: 'smooth'
                    });
                }
            });
        });
    }
})();
