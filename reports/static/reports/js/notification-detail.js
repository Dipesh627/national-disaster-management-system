/* =========================================================
   NDMS — NOTIFICATION DETAIL JAVASCRIPT
   Read-only Google Maps location display for a notification's
   linked disaster. Mirrors report-detail.js's read-only map
   (single non-draggable marker + address info window), reading
   the disaster's stored latitude/longitude/address straight
   from the #notificationMap data attributes rendered by
   notification_detail.html.

   window.initNotificationDetailMap is called automatically by
   the Google Maps script tag (see notification_detail.html)
   once the API has finished loading. Callback name and map
   element id are unique on purpose so this never collides with
   initReportDetailMap / initReportIncidentMap /
   initDisasterLocationMap on other pages.
   ========================================================= */

(function () {

    "use strict";

    function showMapFallback(message) {

        const mapElement = document.getElementById("notificationMap");

        if (mapElement) {

            mapElement.innerHTML =
                '<div class="nd-map-fallback">' +
                (message || "Unable to load the map. Please check " +
                    "your connection or try again later.") +
                "</div>";

        }

    }

    window.gm_authFailure = function () {
        showMapFallback();
    };

    window.ndmsNotificationMapsScriptError = function () {
        showMapFallback();
    };


    function escapeHtml(value) {

        const div = document.createElement("div");
        div.textContent = value;
        return div.innerHTML;

    }


    function initNotificationDetailMap() {

        const mapElement = document.getElementById("notificationMap");

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
                "Location not available for this disaster."
            );

            return;

        }

        const position = {
            lat: latitude,
            lng: longitude
        };

        const map = new google.maps.Map(mapElement, {
            center: position,
            zoom: 14,
            draggable: true,
            zoomControl: true,
            scrollwheel: false,
            streetViewControl: false,
            mapTypeControl: false,
            fullscreenControl: true,
            gestureHandling: "cooperative"
        });

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

        window.addEventListener("resize", function () {

            google.maps.event.trigger(map, "resize");
            map.setCenter(position);

        });

        const mapTypeToggle =
            document.getElementById("ndMapTypeToggle");

        if (mapTypeToggle) {

            const toggleButtons =
                mapTypeToggle.querySelectorAll(".nd-map-type-btn");

            toggleButtons.forEach(function (button) {

                button.addEventListener("click", function () {

                    map.setMapTypeId(button.dataset.mapType);

                    toggleButtons.forEach(function (otherButton) {
                        otherButton.classList.remove("is-active");
                    });

                    button.classList.add("is-active");

                });

            });

        }

    }

    window.initNotificationDetailMap = initNotificationDetailMap;

})();