/* =========================================================
   NDMS — MY REPORTS JAVASCRIPT

   NOTE: Filtering, search and pagination are all handled by
   the backend (Django) through normal links/GET requests.

   Mobile sidebar toggling and the notification dropdown are
   already handled by dashboard.js, which this page also loads.
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    /* =====================================================
       DISMISS DJANGO MESSAGES
       (e.g. the success message shown after a report is
       deleted and the citizen is redirected back here)
       ===================================================== */

    const messageCloseButtons =
        document.querySelectorAll(".message-close");

    messageCloseButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            const message = button.closest(".django-message");

            if (message) {
                message.remove();
            }

        });

    });


    /* =====================================================
       SEARCH
       ===================================================== */

    const searchForm =
        document.getElementById("mrSearchForm");

    const searchInput =
        document.getElementById("mrSearchInput");

    if (searchForm && searchInput) {

        searchForm.addEventListener("submit", function () {

            const value = searchInput.value.trim();

            if (value === "") {

                searchInput.removeAttribute("name");

                window.setTimeout(function () {
                    searchInput.setAttribute("name", "q");
                }, 0);

            }

        });

    }


    /* =====================================================
       FILTERS POPOVER
       (Status + Disaster Type live inside this popover;
       both submit together via the Apply button so the
       toolbar itself stays lightweight)
       ===================================================== */

    const filtersToggle =
        document.getElementById("mrFiltersToggle");

    const filtersPanel =
        document.getElementById("mrFiltersPanel");

    const filtersClearBtn =
        document.getElementById("mrFiltersClear");

    const statusSelect =
        document.getElementById("mrStatusSelect");

    const disasterTypeSelect =
        document.getElementById("mrDisasterTypeSelect");


    function isFiltersPanelOpen() {

        return Boolean(
            filtersPanel &&
            !filtersPanel.hidden
        );

    }


    function openFiltersPanel() {

        if (!filtersPanel || !filtersToggle) {
            return;
        }

        filtersPanel.hidden = false;

        filtersToggle.setAttribute(
            "aria-expanded",
            "true"
        );

        window.requestAnimationFrame(function () {
            filtersPanel.setAttribute("data-open", "true");
        });

    }


    function closeFiltersPanel() {

        if (!filtersPanel || !filtersToggle) {
            return;
        }

        if (!isFiltersPanelOpen()) {
            return;
        }

        filtersPanel.removeAttribute("data-open");
        filtersPanel.hidden = true;

        filtersToggle.setAttribute(
            "aria-expanded",
            "false"
        );

    }


    if (filtersToggle && filtersPanel) {

        filtersToggle.addEventListener(
            "click",
            function (event) {

                event.stopPropagation();

                if (isFiltersPanelOpen()) {
                    closeFiltersPanel();
                } else {
                    openFiltersPanel();
                }

            }
        );

        filtersPanel.addEventListener(
            "click",
            function (event) {
                event.stopPropagation();
            }
        );

        document.addEventListener(
            "click",
            function (event) {

                if (
                    isFiltersPanelOpen() &&
                    !filtersPanel.contains(event.target) &&
                    !filtersToggle.contains(event.target)
                ) {
                    closeFiltersPanel();
                }

            }
        );

    }


    if (filtersClearBtn) {

        filtersClearBtn.addEventListener(
            "click",
            function () {

                if (statusSelect) {
                    statusSelect.value = "ALL";
                }

                if (disasterTypeSelect) {
                    disasterTypeSelect.value = "";
                }

                if (searchForm) {
                    searchForm.submit();
                }

            }
        );

    }


    /* =====================================================
       ESCAPE KEY
       (View Details is now a direct link/action in both the
       table and the mobile cards -- there is no action
       dropdown or in-page delete modal on this page anymore;
       deletion lives on the Report Detail page instead -- see
       report-detail.js)
       ===================================================== */

    document.addEventListener(
        "keydown",
        function (event) {

            if (event.key !== "Escape") {
                return;
            }

            if (isFiltersPanelOpen()) {
                closeFiltersPanel();
            }

        }
    );

});