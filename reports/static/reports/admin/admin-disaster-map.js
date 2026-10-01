/* =========================================================
   NDMS ADMIN — DISASTER LOCATION MAP
   Google Maps location picker for Add Disaster / Edit
   Disaster.

   Mirrors the citizen-facing Report Incident map
   (reports/static/reports/js/report-incident.js): click to
   place, drag to move, Places search box, reverse geocoding,
   Nepal-only bounds — trimmed to only what the Disaster form
   needs (no photo upload, no "use current location").

   window.initDisasterLocationMap is called automatically by
   the Google Maps script tag (see disaster_form.html) once the
   API has finished loading. Callback name is unique on purpose
   so it never collides with initReportIncidentMap or
   initReportDetailMap on other pages.
   ========================================================= */

(function () {

    "use strict";


    const NEPAL_CENTER = {
        lat: 28.3949,
        lng: 84.1240
    };

    const NEPAL_DEFAULT_ZOOM = 7;

    const NEPAL_BOUNDS = {
        north: 30.45,
        south: 26.35,
        west: 80.05,
        east: 88.20
    };


    let map = null;
    let marker = null;
    let geocoder = null;

    let lastValidLat = null;
    let lastValidLng = null;

    let latitudeInput = null;
    let longitudeInput = null;
    let visibleLatitude = null;
    let visibleLongitude = null;
    let addressInput = null;
    let mapStatusMessage = null;
    let mapSearchInput = null;


    function cacheElements() {

        latitudeInput = document.getElementById("id_latitude");
        longitudeInput = document.getElementById("id_longitude");
        visibleLatitude = document.getElementById("visibleLatitude");
        visibleLongitude = document.getElementById("visibleLongitude");
        addressInput = document.getElementById("id_address");
        mapStatusMessage = document.getElementById("dsMapStatusMessage");
        mapSearchInput = document.getElementById("dsMapSearchInput");

    }


    function setStatus(message, type) {

        if (!mapStatusMessage) {
            return;
        }

        mapStatusMessage.textContent = message || "";

        mapStatusMessage.classList.remove(
            "ds-status-success",
            "ds-status-error"
        );

        if (type) {
            mapStatusMessage.classList.add("ds-status-" + type);
        }

    }


    function updateCoordinateFields(lat, lng) {

        const latFixed = lat.toFixed(6);
        const lngFixed = lng.toFixed(6);

        if (latitudeInput) latitudeInput.value = latFixed;
        if (longitudeInput) longitudeInput.value = lngFixed;
        if (visibleLatitude) visibleLatitude.value = latFixed;
        if (visibleLongitude) visibleLongitude.value = lngFixed;

    }


    function placeOrMoveMarker(lat, lng) {

        const position = { lat: lat, lng: lng };

        if (!marker) {

            marker = new google.maps.Marker({
                position: position,
                map: map,
                draggable: true
            });

            marker.addListener("dragend", function () {

                const position = marker.getPosition();

                verifyAndSetLocation(
                    position.lat(),
                    position.lng()
                );

            });

        } else {

            marker.setPosition(position);

        }

    }


    function removeMarker() {

        if (marker) {
            marker.setMap(null);
            marker = null;
        }

    }


    function isWithinNepalBounds(lat, lng) {

        return (
            lat <= NEPAL_BOUNDS.north &&
            lat >= NEPAL_BOUNDS.south &&
            lng >= NEPAL_BOUNDS.west &&
            lng <= NEPAL_BOUNDS.east
        );

    }


    function findCountryComponent(geocodeResult) {

        if (!geocodeResult || !geocodeResult.address_components) {
            return null;
        }

        for (let i = 0; i < geocodeResult.address_components.length; i++) {

            const component = geocodeResult.address_components[i];

            if (component.types && component.types.indexOf("country") !== -1) {
                return component;
            }

        }

        return null;

    }


    function applyValidLocation(lat, lng, address) {

        placeOrMoveMarker(lat, lng);
        updateCoordinateFields(lat, lng);

        lastValidLat = lat;
        lastValidLng = lng;

        if (address && addressInput) {
            addressInput.value = address;
        }

        setStatus("Location set successfully.", "success");

    }


    function handleInvalidLocation(message) {

        if (lastValidLat !== null && lastValidLng !== null) {

            placeOrMoveMarker(lastValidLat, lastValidLng);
            updateCoordinateFields(lastValidLat, lastValidLng);

        } else {

            removeMarker();

        }

        setStatus(message, "error");

    }


    function verifyAndSetLocation(lat, lng) {

        if (!isWithinNepalBounds(lat, lng)) {

            handleInvalidLocation(
                "Please select a location within Nepal."
            );

            return;

        }

        if (!geocoder) {

            applyValidLocation(lat, lng, null);
            return;

        }

        setStatus("Verifying location…", null);

        geocoder.geocode(
            { location: { lat: lat, lng: lng } },
            function (results, status) {

                if (status === "OK" && results && results.length) {

                    const countryComponent =
                        findCountryComponent(results[0]);

                    if (
                        countryComponent &&
                        countryComponent.short_name !== "NP"
                    ) {

                        handleInvalidLocation(
                            "Selected location is outside Nepal. " +
                            "Please choose a location within Nepal."
                        );

                        return;

                    }

                    applyValidLocation(
                        lat,
                        lng,
                        results[0].formatted_address
                    );

                    return;

                }

                // Bounding-box check already passed — accept the
                // point even if reverse geocoding has no data for
                // this exact point (common in remote areas).
                applyValidLocation(lat, lng, null);

            }
        );

    }


    function showMapLoadError() {

        const mapElement = document.getElementById("disasterLocationMap");

        if (mapElement) {

            mapElement.innerHTML =
                '<div class="ds-map-load-error">' +
                "Unable to load the map. Please check your " +
                "internet connection, or try again later." +
                "</div>";

        }

        setStatus(
            "Map failed to load. You can still save the " +
            "disaster once the map is available.",
            "error"
        );

    }

    window.gm_authFailure = showMapLoadError;
    window.ndmsDisasterMapsScriptError = showMapLoadError;


    function initMapSearchBox() {

        if (
            !mapSearchInput ||
            typeof google.maps.places === "undefined"
        ) {
            return;
        }

        const autocomplete = new google.maps.places.Autocomplete(
            mapSearchInput,
            {
                fields: ["geometry", "name", "formatted_address"],
                componentRestrictions: { country: "np" }
            }
        );

        autocomplete.setBounds(
            new google.maps.LatLngBounds(
                { lat: NEPAL_BOUNDS.south, lng: NEPAL_BOUNDS.west },
                { lat: NEPAL_BOUNDS.north, lng: NEPAL_BOUNDS.east }
            )
        );

        mapSearchInput.addEventListener("keydown", function (event) {

            if (event.key === "Enter") {
                event.preventDefault();
            }

        });

        autocomplete.addListener("place_changed", function () {

            const place = autocomplete.getPlace();

            if (!place || !place.geometry || !place.geometry.location) {

                setStatus(
                    "That location could not be found. Please " +
                    "try a different search or select it on the " +
                    "map directly.",
                    "error"
                );

                return;

            }

            const lat = place.geometry.location.lat();
            const lng = place.geometry.location.lng();

            map.setCenter({ lat: lat, lng: lng });
            map.setZoom(15);

            verifyAndSetLocation(lat, lng);

        });

    }


    function initMapTypeToggle() {

        const toggle = document.getElementById("dsMapTypeToggle");

        if (!toggle) {
            return;
        }

        const buttons = toggle.querySelectorAll(".ds-map-type-btn");

        buttons.forEach(function (button) {

            button.addEventListener("click", function () {

                const mapType = button.dataset.mapType;

                map.setMapTypeId(mapType);

                buttons.forEach(function (otherButton) {
                    otherButton.classList.remove("is-active");
                });

                button.classList.add("is-active");

            });

        });

    }


    function initDisasterLocationMap() {

        const mapElement = document.getElementById("disasterLocationMap");

        if (!mapElement || typeof google === "undefined" || !google.maps) {
            return;
        }

        cacheElements();

        geocoder = new google.maps.Geocoder();

        map = new google.maps.Map(mapElement, {
            center: NEPAL_CENTER,
            zoom: NEPAL_DEFAULT_ZOOM,
            restriction: {
                latLngBounds: NEPAL_BOUNDS,
                strictBounds: false
            },
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: true,
            zoomControl: true,
            gestureHandling: "greedy"
        });

        initMapSearchBox();
        initMapTypeToggle();

        map.addListener("click", function (event) {

            verifyAndSetLocation(
                event.latLng.lat(),
                event.latLng.lng()
            );

        });

        // Pre-fill from existing values (Edit Disaster — the form
        // re-renders the hidden lat/lng inputs with the saved
        // coordinates) or from a previous validation error on Add
        // Disaster.
        const existingLat =
            latitudeInput && latitudeInput.value
                ? parseFloat(latitudeInput.value)
                : NaN;

        const existingLng =
            longitudeInput && longitudeInput.value
                ? parseFloat(longitudeInput.value)
                : NaN;

        if (!isNaN(existingLat) && !isNaN(existingLng)) {

            lastValidLat = existingLat;
            lastValidLng = existingLng;

            placeOrMoveMarker(existingLat, existingLng);
            updateCoordinateFields(existingLat, existingLng);

            map.setCenter({ lat: existingLat, lng: existingLng });
            map.setZoom(13);

        }

        window.addEventListener("resize", function () {
            google.maps.event.trigger(map, "resize");
        });

    }

    window.initDisasterLocationMap = initDisasterLocationMap;

})();