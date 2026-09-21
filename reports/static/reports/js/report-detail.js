/* =========================================================
   NDMS — REPORT DETAIL JAVASCRIPT
   Read-only Google Maps location display and incident photo
   lightbox.

   NOTE: Mobile sidebar toggling and the notification dropdown
   are already handled by dashboard.js, which this page also
   loads (same #dashboardSidebar / #notificationDropdown IDs).

   MAP NOTES:
   - Uses the official Google Maps JavaScript API (see
     GOOGLE_MAPS_API_KEY in ndms/settings.py for where to put
     your key).
   - window.initReportDetailMap is called automatically by the
     Google Maps script tag (see report_detail.html) once the
     API has finished loading.
   - window.gm_authFailure / window.ndmsMapsScriptError handle
     an invalid key / failed script load respectively.
   - The map reads the report's stored latitude/longitude/
     address straight from the #reportDetailMap data attributes
     already rendered by report_detail.html — no new location
     system is introduced.
   ========================================================= */

(function () {

    "use strict";


    /* =====================================================
       MAP LOAD FAILURE HANDLING
       ===================================================== */

    function showMapFallback(message) {

        const mapElement = document.getElementById("reportDetailMap");

        if (mapElement) {

            mapElement.innerHTML =
                '<div class="rd-map-fallback">' +
                (message || "Unable to load the map. Please check " +
                    "your connection or try again later.") +
                "</div>";

        }

    }


    // Called by Google if the API key is invalid/misconfigured.
    window.gm_authFailure = function () {
        showMapFallback();
    };

    // Called (see report_detail.html) if the Google Maps script
    // itself fails to load, e.g. no network connection.
    window.ndmsMapsScriptError = function () {
        showMapFallback();
    };


    function escapeHtml(value) {

        const div = document.createElement("div");
        div.textContent = value;
        return div.innerHTML;

    }


    // No custom style array on purpose — see the matching
    // comment in report-incident.js. Leaving this empty makes
    // Google Maps render its own genuine default styling in
    // both Roadmap and Satellite/Hybrid mode (real colors, real
    // business/POI icons, and full place-name labels on the
    // satellite layer too), so this read-only map always looks
    // and behaves exactly like maps.google.com — matching the
    // Report Incident map above.
    const NDMS_MAP_STYLE = [];


    /* =====================================================
       MAP INITIALIZATION
       (invoked by the Google Maps script's callback param —
       see report_detail.html)
       ===================================================== */

    function initReportDetailMap() {

        const mapElement = document.getElementById("reportDetailMap");

        if (!mapElement || typeof google === "undefined" || !google.maps) {
            return;
        }

        const latitude =
            parseFloat(mapElement.dataset.latitude);

        const longitude =
            parseFloat(mapElement.dataset.longitude);

        const address =
            mapElement.dataset.address || "";

        if (isNaN(latitude) || isNaN(longitude)) {

            showMapFallback(
                "No location was recorded for this report."
            );

            return;

        }

        const position = {
            lat: latitude,
            lng: longitude
        };

        function createLayerToggleControl(targetMap) {

            const container = document.createElement("div");
            container.className = "rd-layer-control";

            const standardBtn = document.createElement("button");
            standardBtn.type = "button";
            standardBtn.className = "rd-layer-btn active";
            standardBtn.textContent = "Standard";

            const satelliteBtn = document.createElement("button");
            satelliteBtn.type = "button";
            satelliteBtn.className = "rd-layer-btn";
            satelliteBtn.textContent = "Satellite";

            container.appendChild(standardBtn);
            container.appendChild(satelliteBtn);

            [standardBtn, satelliteBtn].forEach(function (btn) {

                btn.addEventListener("mousedown", function (event) {
                    event.stopPropagation();
                });

                btn.addEventListener("touchstart", function (event) {
                    event.stopPropagation();
                }, { passive: true });

            });

            standardBtn.addEventListener("click", function (event) {

                event.stopPropagation();

                targetMap.setMapTypeId(google.maps.MapTypeId.ROADMAP);

                standardBtn.classList.add("active");
                satelliteBtn.classList.remove("active");

            });

            satelliteBtn.addEventListener("click", function (event) {

                event.stopPropagation();

                // HYBRID = satellite imagery + the roads/place
                // name label overlay, so town/village names stay
                // visible. Plain SATELLITE is imagery only.
                targetMap.setMapTypeId(google.maps.MapTypeId.HYBRID);

                satelliteBtn.classList.add("active");
                standardBtn.classList.remove("active");

            });

            return container;

        }


        const map = new google.maps.Map(mapElement, {
            center: position,
            zoom: 15,
            styles: NDMS_MAP_STYLE,
            draggable: true,
            zoomControl: true,
            scrollwheel: false,
            streetViewControl: true,
            // Custom control below replaces Google's stock
            // blue-highlighted Map/Satellite buttons so the
            // active state matches the NDMS navy/red palette.
            mapTypeControl: false,
            fullscreenControl: true,
            gestureHandling: "cooperative"
        });

        // TOP_LEFT: Google's own fullscreen / camera / zoom /
        // street-view controls stack down the RIGHT edge, and on
        // a short phone map they collided with this toggle.
        // Nothing else lives in the top-left corner.
        map.controls[google.maps.ControlPosition.TOP_LEFT].push(
            createLayerToggleControl(map)
        );

        // Read-only: a single, non-draggable marker at the
        // exact reported location.
        const marker = new google.maps.Marker({
            position: position,
            map: map
        });

        if (address) {

            const infoWindow = new google.maps.InfoWindow({
                content:
                    '<div style="font-size:12px;max-width:220px;">' +
                    escapeHtml(address) +
                    "</div>"
            });

            marker.addListener("click", function () {
                infoWindow.open(map, marker);
            });

        }

        /* -------------------------------------------------
           RESPONSIVE MAP
           ------------------------------------------------- */

        window.addEventListener("resize", function () {

            google.maps.event.trigger(map, "resize");
            map.setCenter(position);

        });

        const mobileSidebarToggle =
            document.getElementById("mobileSidebarToggle");

        if (mobileSidebarToggle) {

            mobileSidebarToggle.addEventListener("click", function () {

                setTimeout(function () {

                    google.maps.event.trigger(map, "resize");
                    map.setCenter(position);

                }, 260);

            });

        }

    }

    window.initReportDetailMap = initReportDetailMap;


    /* =====================================================
       PHOTO LIGHTBOX
       ===================================================== */

    document.addEventListener("DOMContentLoaded", function () {

        /* =====================================================
           DISMISS DJANGO MESSAGES
           (e.g. the error message shown here after an
           ineligible delete attempt is safely rejected)
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


        const photoThumbs =
            document.querySelectorAll(".rd-photo-thumb");

        const photoModal =
            document.getElementById("rdPhotoModal");

        const photoModalImage =
            document.getElementById("rdPhotoModalImage");

        const photoModalClose =
            document.getElementById("rdPhotoModalClose");


        function openPhotoModal(imageUrl) {

            if (!photoModal || !photoModalImage) {
                return;
            }

            photoModalImage.src = imageUrl;
            photoModal.classList.add("show");
            document.body.classList.add("sidebar-open");

        }


        function closePhotoModal() {

            if (!photoModal || !photoModalImage) {
                return;
            }

            photoModal.classList.remove("show");
            document.body.classList.remove("sidebar-open");
            photoModalImage.src = "";

        }


        photoThumbs.forEach(function (thumb) {

            thumb.addEventListener("click", function () {

                const fullImageUrl = thumb.dataset.full;

                if (fullImageUrl) {
                    openPhotoModal(fullImageUrl);
                }

            });

        });


        if (photoModalClose) {

            photoModalClose.addEventListener("click", closePhotoModal);

        }


        if (photoModal) {

            photoModal.addEventListener("click", function (event) {

                if (event.target === photoModal) {
                    closePhotoModal();
                }

            });

        }


        /* =====================================================
           REJECT CONFIRMATION MODAL
           ===================================================== */

        const openRejectBtn =
            document.getElementById("rdOpenRejectModal");

        const rejectModal =
            document.getElementById("rdRejectModal");

        const closeRejectBtn =
            document.getElementById("rdRejectModalClose");

        const cancelRejectBtn =
            document.getElementById("rdRejectModalCancel");

        const backdropReject =
            document.getElementById("rdRejectModalBackdrop");

        function openRejectModal() {

            if (!rejectModal) {
                return;
            }

            rejectModal.hidden = false;
            rejectModal.setAttribute("aria-hidden", "false");
            rejectModal.classList.add("show");
            document.body.classList.add("sidebar-open");

        }

        function closeRejectModal() {

            if (!rejectModal) {
                return;
            }

            rejectModal.classList.remove("show");
            rejectModal.hidden = true;
            rejectModal.setAttribute("aria-hidden", "true");
            document.body.classList.remove("sidebar-open");

        }

        if (openRejectBtn) {

            openRejectBtn.addEventListener("click", openRejectModal);

        }

        if (closeRejectBtn) {

            closeRejectBtn.addEventListener("click", closeRejectModal);

        }

        if (cancelRejectBtn) {

            cancelRejectBtn.addEventListener("click", closeRejectModal);

        }

        if (backdropReject) {

            backdropReject.addEventListener("click", closeRejectModal);

        }


        /* =====================================================
           DELETE REPORT CONFIRMATION MODAL
           (only rendered when the report is still eligible for
           deletion -- see report_detail()'s can_delete flag in
           views.py; the elements below simply won't exist on
           the page otherwise, so every lookup here is guarded)
           ===================================================== */

        const openDeleteBtn =
            document.getElementById("rdOpenDeleteModal");

        const deleteModal =
            document.getElementById("rdDeleteConfirmModal");

        const deleteForm =
            document.getElementById("rdDeleteReportForm");

        const deleteCancelBtn =
            document.getElementById("rdDeleteCancelBtn");

        const deleteConfirmBtn =
            document.getElementById("rdDeleteConfirmBtn");

        let isDeleting = false;

        function openDeleteModal() {

            if (!deleteModal) {
                return;
            }

            deleteModal.hidden = false;

            document.body.classList.add("sidebar-open");

            window.requestAnimationFrame(function () {

                if (deleteCancelBtn) {
                    deleteCancelBtn.focus();
                }

            });

        }

        function closeDeleteModal() {

            if (!deleteModal) {
                return;
            }

            if (isDeleting) {
                return;
            }

            deleteModal.hidden = true;

            document.body.classList.remove("sidebar-open");

        }

        if (openDeleteBtn) {

            openDeleteBtn.addEventListener("click", openDeleteModal);

        }

        if (deleteCancelBtn) {

            deleteCancelBtn.addEventListener("click", closeDeleteModal);

        }

        if (deleteModal) {

            deleteModal.addEventListener("click", function (event) {

                if (event.target === deleteModal) {
                    closeDeleteModal();
                }

            });

        }

        if (deleteForm) {

            deleteForm.addEventListener("submit", function (event) {

                if (isDeleting) {
                    event.preventDefault();
                    return;
                }

                isDeleting = true;

                if (deleteConfirmBtn) {

                    deleteConfirmBtn.disabled = true;

                    deleteConfirmBtn.textContent = "Deleting…";

                }

            });

        }


        document.addEventListener("keydown", function (event) {

            if (event.key === "Escape") {
                closePhotoModal();
                closeRejectModal();
                closeDeleteModal();
            }

        });


    });

})();