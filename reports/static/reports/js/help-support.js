/* =========================================================
   NDMS HELP & SUPPORT JAVASCRIPT

   Covers, on this page only:
     - FAQ accordion
     - Search (client-side filter over FAQ content)
     - Was this helpful widget
     - Report a Problem attachment filename preview
     - Dismissing Django messages

   This file intentionally does NOT touch sidebar, mobile
   menu, avatar dropdown, or notification dropdown behaviour
   — those already work on this page via the existing
   reports/js/dashboard.js and reports/js/navbar-avatar.js,
   which are loaded alongside this file and are not modified.
   ========================================================= */


document.addEventListener("DOMContentLoaded", function () {

    const faqController = initFaqAccordion();
    initHelpSearch(faqController);
    initWasThisHelpful();
    initAttachmentPreview();
    initMessageDismiss();
    initSupportFormSubmit();
    initIssueTypeSelect();


    /* =====================================================
       FAQ ACCORDION
       Returns a small controller so initHelpSearch() can open
       a specific FAQ item and scroll to it when a suggestion
       is picked from the search dropdown.
       ===================================================== */

    function initFaqAccordion() {

        const faqItems =
            Array.from(
                document.querySelectorAll(".hs-faq-item")
            );

        if (!faqItems || faqItems.length === 0) {
            return { items: [] };
        }

        faqItems.forEach(function (item, index) {

            if (!item.id) {
                item.id = "hs-faq-item-" + index;
            }

            const question =
                item.querySelector(".hs-faq-question");

            const answer =
                item.querySelector(".hs-faq-answer");

            if (!question || !answer) {
                return;
            }

            question.addEventListener("click", function () {
                toggleFaqItem(item);
            });

            question.addEventListener("keydown", function (event) {

                if (event.key === "Enter" || event.key === " ") {

                    event.preventDefault();
                    toggleFaqItem(item);

                }

            });

        });


        function toggleFaqItem(item) {

            const isOpen =
                item.getAttribute("data-open") === "true";

            // Only one FAQ item open at a time.
            faqItems.forEach(function (otherItem) {
                closeFaqItem(otherItem);
            });

            if (!isOpen) {
                openFaqItem(item);
            }

        }


        function openFaqItem(item) {

            const question =
                item.querySelector(".hs-faq-question");

            item.setAttribute("data-open", "true");

            if (question) {
                question.setAttribute("aria-expanded", "true");
            }

        }


        function closeFaqItem(item) {

            const question =
                item.querySelector(".hs-faq-question");

            item.setAttribute("data-open", "false");

            if (question) {
                question.setAttribute("aria-expanded", "false");
            }

        }


        return {
            items: faqItems,
            open: openFaqItem
        };

    }


    /* =====================================================
       SEARCH HELP
       Filters the FAQ list client-side against the static
       FAQ content already rendered in the page, and shows a
       live "as you type" suggestions dropdown underneath the
       search box. No page reload, no extra dependency.
       ===================================================== */

    function initHelpSearch(faqController) {

        const searchInput =
            document.getElementById("hsSearchInput");

        const clearButton =
            document.getElementById("hsSearchClear");

        const searchHint =
            document.getElementById("hsSearchHint");

        const emptyState =
            document.getElementById("hsSearchEmpty");

        const faqList =
            document.getElementById("hsFaqList");

        const suggestionsBox =
            document.getElementById("hsSearchSuggestions");

        if (!searchInput || !faqList) {
            return;
        }

        // Actual NDMS help topics — used both as the "Popular
        // searches" list shown on focus, and as the keyword
        // list that decides whether an unmatched query is
        // still NDMS-related ("no matching articles") or
        // completely unrelated ("out of scope for this help
        // center"), so the empty state never just says
        // "No results found".
        const popularSearches = [
            "How do I report an incident?",
            "How can I track my report?",
            "How do notifications work?",
            "How do I change my profile?",
            "How do I contact support?"
        ];

        const ndmsKeywords = [
            "ndms", "report", "reports", "reporting", "incident",
            "disaster", "alert", "alerts", "notification",
            "notifications", "profile", "settings", "account",
            "support", "help", "attachment", "photo", "status",
            "password", "login", "log", "citizen", "location",
            "severity", "feedback"
        ];

        const faqItems =
            Array.from(
                faqList.querySelectorAll(".hs-faq-item")
            );

        // Pre-read each FAQ's question/answer text once, so
        // typing doesn't re-parse the DOM on every keystroke.
        const STOPWORDS = [
            "how", "do", "does", "did", "i", "a", "an", "the",
            "is", "are", "can", "could", "my", "with", "what",
            "of", "to", "for", "in", "on", "will", "would",
            "should", "this", "that", "it", "be", "as", "me",
            "you", "your", "and", "or", "if", "so", "we", "us"
        ];

        // Splits a query into its meaningful words (drops
        // filler words like "how"/"do"/"my" and anything
        // shorter than 3 letters).
        function getSignificantWords(query) {

            return query
                .split(/[^a-z0-9]+/)
                .filter(function (word) {
                    return (
                        word.length >= 3 &&
                        STOPWORDS.indexOf(word) === -1
                    );
                });

        }

        // A query "matches" an FAQ entry if either the whole
        // typed phrase appears verbatim (exact/partial phrase
        // search), or a good share of its meaningful words
        // appear somewhere in the entry — since real users
        // rarely type a question using the exact same wording
        // as the FAQ itself (e.g. "track my report" should
        // still find "check my submitted reports").
        function queryMatchesHaystack(haystack, query, queryWords) {

            if (haystack.indexOf(query) !== -1) {
                return true;
            }

            if (queryWords.length === 0) {
                return false;
            }

            const hits =
                queryWords.filter(function (word) {
                    return haystack.indexOf(word) !== -1;
                }).length;

            return hits / queryWords.length >= 0.5;

        }


        const faqEntries =
            faqItems.map(function (item) {

                const questionEl =
                    item.querySelector(".hs-faq-question span");

                const answerEl =
                    item.querySelector(".hs-faq-answer-inner");

                const question =
                    (questionEl
                        ? questionEl.textContent
                        : item.textContent
                    ).replace(/\s+/g, " ").trim();

                const answer =
                    (answerEl
                        ? answerEl.textContent
                        : ""
                    ).replace(/\s+/g, " ").trim();

                return {
                    item: item,
                    question: question,
                    answer: answer,
                    haystack:
                        (question + " " + answer).toLowerCase()
                };

            });

        let activeIndex = -1;
        let currentMatches = [];

        searchInput.addEventListener("input", function () {
            runSearch(searchInput.value);
        });

        searchInput.addEventListener("focus", function () {

            if (searchInput.value.trim().length > 0) {
                openSuggestions();
            } else {
                renderPopularSearches();
            }

        });

        searchInput.addEventListener("keydown", function (event) {
            handleKeyNav(event);
        });

        document.addEventListener("click", function (event) {

            const wrap =
                document.getElementById("hsSearchInput")
                    ? searchInput.closest(".hs-search-wrap")
                    : null;

            if (wrap && !wrap.contains(event.target)) {
                closeSuggestions();
            }

        });

        if (clearButton) {

            clearButton.addEventListener("click", function () {

                searchInput.value = "";
                runSearch("");
                closeSuggestions();
                searchInput.focus();

            });

        }


        function runSearch(rawQuery) {

            const query =
                rawQuery.trim().toLowerCase();

            if (clearButton) {
                clearButton.hidden = query.length === 0;
            }

            if (query.length === 0) {

                faqItems.forEach(function (item) {
                    item.hidden = false;
                });

                if (emptyState) {
                    emptyState.hidden = true;
                }

                if (searchHint) {
                    searchHint.textContent = "";
                }

                closeSuggestions();

                return;

            }

            const queryWords = getSignificantWords(query);

            const matches =
                faqEntries.filter(function (entry) {
                    return queryMatchesHaystack(
                        entry.haystack,
                        query,
                        queryWords
                    );
                });

            faqEntries.forEach(function (entry) {
                entry.item.hidden =
                    matches.indexOf(entry) === -1;
            });

            if (matches.length > 0) {

                if (emptyState) {
                    emptyState.hidden = true;
                }

                if (searchHint) {
                    searchHint.textContent =
                        matches.length + " help article" +
                        (matches.length === 1 ? "" : "s") +
                        " found";
                }

            } else {

                showEmptyState(query);

                if (searchHint) {
                    searchHint.textContent = "";
                }

            }

            renderSuggestions(matches, query);

        }


        // A query counts as "about NDMS" if it shares a word
        // with an actual FAQ question/answer, or contains one
        // of the known NDMS topic keywords. Anything else
        // (e.g. "cook rice", "youtube") is treated as
        // out-of-scope for this help center.
        function isNdmsRelatedQuery(query) {

            const matchesKeyword =
                ndmsKeywords.some(function (keyword) {
                    return query.indexOf(keyword) !== -1;
                });

            if (matchesKeyword) {
                return true;
            }

            const queryWords = getSignificantWords(query);

            return faqEntries.some(function (entry) {
                return queryMatchesHaystack(
                    entry.haystack,
                    query,
                    queryWords
                );
            });

        }


        function showEmptyState(query) {

            if (!emptyState) {
                return;
            }

            const titleEl =
                document.getElementById("hsSearchEmptyTitle");

            const descriptionEl =
                document.getElementById(
                    "hsSearchEmptyDescription"
                );

            const related = isNdmsRelatedQuery(query);

            if (titleEl) {

                titleEl.textContent =
                    related
                        ? "No matching help articles"
                        : "We couldn't find that in NDMS Help";

            }

            if (descriptionEl) {

                descriptionEl.textContent =
                    related
                        ? "Try a different search or choose " +
                            "one of the common topics below."
                        : "This help center only contains " +
                            "information about NDMS services, " +
                            "reports, alerts, account settings, " +
                            "and support.";

            }

            emptyState.hidden = false;

        }


        function renderPopularSearches() {

            if (!suggestionsBox) {
                return;
            }

            suggestionsBox.innerHTML = "";

            const label =
                document.createElement("div");

            label.className = "hs-search-suggestions-label";
            label.textContent = "Popular searches";

            suggestionsBox.appendChild(label);

            popularSearches.forEach(function (phrase) {

                const option =
                    document.createElement("button");

                option.type = "button";
                option.className = "hs-search-suggestion";
                option.setAttribute("role", "option");

                const icon =
                    document.createElement("span");

                icon.className = "hs-search-suggestion-icon";
                icon.setAttribute("aria-hidden", "true");
                icon.textContent = "⌕";

                const text =
                    document.createElement("span");

                text.className = "hs-search-suggestion-text";

                const questionLine =
                    document.createElement("span");

                questionLine.className =
                    "hs-search-suggestion-question";

                questionLine.textContent = phrase;

                text.appendChild(questionLine);
                option.appendChild(icon);
                option.appendChild(text);

                option.addEventListener("click", function () {

                    searchInput.value = phrase;
                    runSearch(phrase);
                    searchInput.focus();

                });

                suggestionsBox.appendChild(option);

            });

            currentMatches = [];
            activeIndex = -1;

            openSuggestions();

        }


        function renderSuggestions(matches, query) {

            if (!suggestionsBox) {
                return;
            }

            currentMatches = matches;
            activeIndex = -1;

            suggestionsBox.innerHTML = "";

            if (matches.length === 0) {

                const empty =
                    document.createElement("div");

                empty.className =
                    "hs-search-suggestions-empty";

                empty.textContent =
                    "No matching help articles.";

                suggestionsBox.appendChild(empty);
                openSuggestions();

                return;

            }

            matches.slice(0, 6).forEach(function (entry, index) {

                const option =
                    document.createElement("button");

                option.type = "button";
                option.className = "hs-search-suggestion";
                option.id = "hs-search-suggestion-" + index;
                option.setAttribute("role", "option");

                const icon =
                    document.createElement("span");

                icon.className =
                    "hs-search-suggestion-icon";

                icon.setAttribute("aria-hidden", "true");

                icon.textContent = "?";

                const text =
                    document.createElement("span");

                text.className =
                    "hs-search-suggestion-text";

                const questionLine =
                    document.createElement("span");

                questionLine.className =
                    "hs-search-suggestion-question";

                questionLine.innerHTML =
                    highlightMatch(entry.question, query);

                text.appendChild(questionLine);

                if (entry.answer) {

                    const answerLine =
                        document.createElement("span");

                    answerLine.className =
                        "hs-search-suggestion-answer";

                    answerLine.textContent = entry.answer;

                    text.appendChild(answerLine);

                }

                option.appendChild(icon);
                option.appendChild(text);

                option.addEventListener("click", function () {
                    selectSuggestion(entry);
                });

                suggestionsBox.appendChild(option);

            });

            openSuggestions();

        }


        function highlightMatch(text, query) {

            const escaped =
                text.replace(/[&<>]/g, function (char) {
                    return (
                        { "&": "&amp;", "<": "&lt;", ">": "&gt;" }
                    )[char];
                });

            if (!query) {
                return escaped;
            }

            const escapedQuery =
                query.replace(
                    /[.*+?^${}()|[\]\\]/g,
                    "\\$&"
                );

            const pattern =
                new RegExp("(" + escapedQuery + ")", "ig");

            return escaped.replace(pattern, "<mark>$1</mark>");

        }


        function selectSuggestion(entry) {

            searchInput.value = entry.question;

            closeSuggestions();

            faqItems.forEach(function (item) {
                item.hidden = false;
            });

            if (emptyState) {
                emptyState.hidden = true;
            }

            if (searchHint) {
                searchHint.textContent = "";
            }

            if (clearButton) {
                clearButton.hidden = false;
            }

            if (faqController && faqController.open) {
                faqController.open(entry.item);
            }

            entry.item.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });

        }


        function openSuggestions() {

            if (!suggestionsBox) {
                return;
            }

            suggestionsBox.hidden = false;

            searchInput.setAttribute(
                "aria-expanded",
                "true"
            );

        }


        function closeSuggestions() {

            if (!suggestionsBox) {
                return;
            }

            suggestionsBox.hidden = true;
            suggestionsBox.innerHTML = "";

            searchInput.setAttribute(
                "aria-expanded",
                "false"
            );

            activeIndex = -1;
            currentMatches = [];

        }


        function handleKeyNav(event) {

            if (
                !suggestionsBox ||
                suggestionsBox.hidden ||
                currentMatches.length === 0
            ) {
                return;
            }

            const options =
                Array.from(
                    suggestionsBox.querySelectorAll(
                        ".hs-search-suggestion"
                    )
                );

            if (options.length === 0) {
                return;
            }

            if (event.key === "ArrowDown") {

                event.preventDefault();
                activeIndex =
                    (activeIndex + 1) % options.length;
                highlightActive(options);

            } else if (event.key === "ArrowUp") {

                event.preventDefault();
                activeIndex =
                    (activeIndex - 1 + options.length) %
                    options.length;
                highlightActive(options);

            } else if (event.key === "Enter") {

                if (activeIndex >= 0 &&
                    currentMatches[activeIndex]
                ) {

                    event.preventDefault();
                    selectSuggestion(
                        currentMatches[activeIndex]
                    );

                }

            } else if (event.key === "Escape") {

                closeSuggestions();

            }

        }


        function highlightActive(options) {

            options.forEach(function (option, index) {

                option.classList.toggle(
                    "is-active",
                    index === activeIndex
                );

                if (index === activeIndex) {
                    option.scrollIntoView({ block: "nearest" });
                }

            });

        }

    }


    /* =====================================================
       WAS THIS HELPFUL
       Purely client-side acknowledgement — no backend
       feedback system exists for per-topic ratings, so this
       intentionally does not persist anything server-side.
       ===================================================== */

    function initWasThisHelpful() {

        const prompt =
            document.getElementById("hsHelpfulPrompt");

        const yesButton =
            document.getElementById("hsHelpfulYes");

        const noButton =
            document.getElementById("hsHelpfulNo");

        const yesResponse =
            document.getElementById("hsHelpfulYesResponse");

        const noResponse =
            document.getElementById("hsHelpfulNoResponse");

        if (!yesButton || !noButton) {
            return;
        }

        yesButton.addEventListener("click", function () {
            showResponse(yesResponse, noResponse);
        });

        noButton.addEventListener("click", function () {
            showResponse(noResponse, yesResponse);
        });


        function showResponse(toShow, toHide) {

            if (prompt) {
                prompt.hidden = true;
            }

            if (toHide) {
                toHide.hidden = true;
            }

            if (toShow) {
                toShow.hidden = false;
            }

        }

    }


    /* =====================================================
       REPORT A PROBLEM — ATTACHMENT PREVIEW
       Purely a UX nicety (shows the chosen filename). The
       real validation of type/size happens server-side in
       SupportRequestForm.clean_attachment — this never
       trusts the client.
       ===================================================== */

    function initAttachmentPreview() {

        const fileInput =
            document.getElementById("id_attachment");

        const fileNameLabel =
            document.getElementById("hsFileUploadName");

        if (!fileInput || !fileNameLabel) {
            return;
        }

        fileInput.addEventListener("change", function () {

            if (fileInput.files && fileInput.files.length > 0) {
                fileNameLabel.textContent =
                    fileInput.files[0].name;
            } else {
                fileNameLabel.textContent = "No file chosen";
            }

        });

    }


    /* =====================================================
       ISSUE TYPE — CUSTOM DROPDOWN
       Builds a styled listbox on top of the real
       <select id="id_issue_type"> so the OPEN menu matches
       the NDMS UI on every device (a native <select>'s popup
       is drawn by the OS/browser and can't be restyled via
       CSS — this replaces it with our own). The real select
       stays in the DOM and is what actually submits with the
       form; this only keeps it in sync.
       ===================================================== */

    function initIssueTypeSelect() {

        const nativeSelect =
            document.getElementById("id_issue_type");

        const wrap =
            nativeSelect
                ? nativeSelect.closest(".hs-select-wrap")
                : null;

        const trigger =
            document.getElementById("hsIssueTypeTrigger");

        const triggerLabel =
            trigger
                ? trigger.querySelector(
                    ".hs-select-trigger-label"
                  )
                : null;

        const menu =
            document.getElementById("hsIssueTypeMenu");

        if (
            !nativeSelect ||
            !wrap ||
            !trigger ||
            !triggerLabel ||
            !menu
        ) {
            return;
        }


        let options = [];
        let activeIndex = -1;


        function buildOptions() {

            options = [];
            menu.innerHTML = "";

            Array.prototype.forEach.call(
                nativeSelect.options,
                function (opt, index) {

                    const item =
                        document.createElement("div");

                    item.className = "hs-select-option";
                    item.setAttribute("role", "option");
                    item.setAttribute("id", "hsIssueTypeOpt" + index);
                    item.setAttribute(
                        "aria-selected",
                        opt.selected ? "true" : "false"
                    );
                    item.textContent = opt.textContent;

                    item.addEventListener("click", function () {
                        selectIndex(index);
                        closeMenu();
                        trigger.focus();
                    });

                    menu.appendChild(item);
                    options.push(item);

                }
            );

            syncLabel();

        }


        function syncLabel() {

            const selectedOption =
                nativeSelect.options[nativeSelect.selectedIndex];

            triggerLabel.textContent =
                selectedOption ? selectedOption.textContent : "";

        }


        function selectIndex(index) {

            if (index < 0 || index >= nativeSelect.options.length) {
                return;
            }

            nativeSelect.selectedIndex = index;

            nativeSelect.dispatchEvent(
                new Event("change", { bubbles: true })
            );

            options.forEach(function (item, i) {
                item.setAttribute(
                    "aria-selected",
                    i === index ? "true" : "false"
                );
            });

            syncLabel();

        }


        function setActive(index) {

            if (activeIndex >= 0 && options[activeIndex]) {
                options[activeIndex].classList.remove("is-active");
            }

            activeIndex = index;

            if (activeIndex >= 0 && options[activeIndex]) {

                options[activeIndex].classList.add("is-active");

                options[activeIndex].scrollIntoView({
                    block: "nearest"
                });

            }

        }


        function openMenu() {

            wrap.classList.add("open");
            trigger.setAttribute("aria-expanded", "true");
            menu.hidden = false;

            setActive(
                nativeSelect.selectedIndex >= 0
                    ? nativeSelect.selectedIndex
                    : 0
            );

        }


        function closeMenu() {

            wrap.classList.remove("open");
            trigger.setAttribute("aria-expanded", "false");

            // Wait for the fade-out transition (see .hs-select-menu
            // in help-support.css) before actually hiding it, same
            // as the open state relies on `hidden` being cleared
            // before the "open" class triggers the transition.
            window.setTimeout(function () {

                if (!wrap.classList.contains("open")) {
                    menu.hidden = true;
                }

            }, 180);

            setActive(-1);

        }


        trigger.addEventListener("click", function () {

            if (wrap.classList.contains("open")) {
                closeMenu();
            } else {
                openMenu();
            }

        });


        trigger.addEventListener("keydown", function (event) {

            if (event.key === "ArrowDown") {

                event.preventDefault();

                if (!wrap.classList.contains("open")) {
                    openMenu();
                } else {
                    setActive(
                        Math.min(activeIndex + 1, options.length - 1)
                    );
                }

            } else if (event.key === "ArrowUp") {

                event.preventDefault();

                if (wrap.classList.contains("open")) {
                    setActive(Math.max(activeIndex - 1, 0));
                }

            } else if (event.key === "Enter" || event.key === " ") {

                event.preventDefault();

                if (!wrap.classList.contains("open")) {
                    openMenu();
                } else if (activeIndex >= 0) {
                    selectIndex(activeIndex);
                    closeMenu();
                }

            } else if (event.key === "Escape") {

                closeMenu();

            }

        });


        document.addEventListener("click", function (event) {

            if (
                wrap.classList.contains("open") &&
                !wrap.contains(event.target)
            ) {
                closeMenu();
            }

        });


        buildOptions();

        wrap.classList.add("is-enhanced");
        trigger.hidden = false;

    }


    /* =====================================================
       REPORT A PROBLEM — SUBMIT STATE
       Prevents double submission and shows a "Sending…"
       state while the request round-trips. The actual
       save/validation is still done server-side by
       help_support() + SupportRequestForm; this is only a
       UX guard on the client.
       ===================================================== */

    function initSupportFormSubmit() {

        const form =
            document.querySelector(".hs-report-form");

        const submitButton =
            form
                ? form.querySelector(".hs-submit-btn")
                : null;

        if (!form || !submitButton) {
            return;
        }

        form.addEventListener("submit", function (event) {

            if (form.dataset.submitting === "true") {
                event.preventDefault();
                return;
            }

            form.dataset.submitting = "true";

            submitButton.disabled = true;
            submitButton.classList.add("is-loading");
            submitButton.textContent = "Sending…";

        });

    }


    /* =====================================================
       DISMISS DJANGO MESSAGES
       ===================================================== */

    function initMessageDismiss() {

        const closeButtons =
            document.querySelectorAll(".message-close");

        closeButtons.forEach(function (button) {

            button.addEventListener("click", function () {

                const message =
                    button.closest(".django-message");

                if (message) {
                    message.remove();
                }

            });

        });

    }

});