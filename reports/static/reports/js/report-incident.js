/* =========================================================
   NDMS — REPORT INCIDENT JAVASCRIPT
   Google Maps location picker, photo upload and form
   validation.

   NOTE: Mobile sidebar toggling and the notification dropdown
   are already handled by dashboard.js, which this page also
   loads (same #dashboardSidebar / #notificationDropdown IDs).
   This file only adds map resize calls into that existing
   behaviour where needed.

   MAP NOTES:
   - Uses the official Google Maps JavaScript API + the
     Geocoding API (see GOOGLE_MAPS_API_KEY in ndms/settings.py
     for where to put your key).
   - window.initReportIncidentMap is called automatically by
     the Google Maps script tag (see report_incident.html) once
     the API has finished loading.
   - window.gm_authFailure / window.ndmsMapsScriptError handle
     an invalid key / failed script load respectively.
   ========================================================= */

(function () {

    "use strict";


    /* =====================================================
       CONSTANTS
       ===================================================== */

    const NEPAL_CENTER = {
        lat: 28.3949,
        lng: 84.1240
    };

    const NEPAL_DEFAULT_ZOOM = 7;

    // Deliberate, fixed zoom used whenever a location is selected
    // via "Use My Current Location" — a close, local/street level
    // view (buildings, named roads, nearby places visible) with the
    // marker sitting at the exact visual center of the map. Fixed
    // rather than derived from the map's previous zoom, so the
    // result looks the same every time regardless of where the map
    // happened to be zoomed to beforehand.
    const CURRENT_LOCATION_ZOOM = 16;

    // If the browser's own reported accuracy radius for a
    // geolocation fix is worse than this (meters), the citizen is
    // warned that the pin may not be exactly right — common on
    // desktops/laptops without a GPS chip, where the browser falls
    // back to WiFi/IP-based positioning that can be off by several
    // kilometers (this is a device/browser limitation, not
    // something the map or this page can correct on its own).
    const LOW_ACCURACY_THRESHOLD_METERS = 3000;

    // Rectangular bounding box — used ONLY to visually restrict the
    // map (restriction.latLngBounds) and as the map's initial
    // viewport. It is intentionally loose (it includes real slices
    // of India/Tibet at the corners, since Nepal itself is a long,
    // narrow, diagonal shape that a rectangle can't trace exactly).
    // It must NOT be used on its own to decide whether a location is
    // "in Nepal" — see NEPAL_POLYGON below for that.
    const NEPAL_BOUNDS = {
        north: 30.45,
        south: 26.35,
        west: 80.05,
        east: 88.20
    };

    // Simplified outline of Nepal's actual border (lat, lng pairs,
    // roughly west-to-east along the southern/India border, then
    // back west along the northern/Tibet border, including the
    // Mustang salient that pushes north into the Tibetan plateau).
    // This is what actually decides "inside Nepal" — the rectangle
    // above is only used for the map's pan/zoom viewport, since on
    // its own it wrongly includes large parts of India and Tibet
    // (e.g. Lucknow, Patna and Lhasa all fall inside NEPAL_BOUNDS).
    // It's a simplification, not a survey-accurate border, but it
    // is far more accurate than a rectangle for keeping citizens
    // from selecting a point that is clearly not in Nepal.
    const NEPAL_POLYGON = [
        { lat: 30.20, lng: 80.09 },
        { lat: 29.70, lng: 80.18 },
        { lat: 28.85, lng: 80.10 },
        { lat: 28.60, lng: 80.55 },
        { lat: 28.70, lng: 81.05 },
        { lat: 28.05, lng: 81.60 },
        { lat: 27.85, lng: 82.35 },
        { lat: 27.50, lng: 83.00 },
        { lat: 27.50, lng: 83.45 },
        { lat: 27.15, lng: 83.90 },
        { lat: 27.00, lng: 84.45 },
        { lat: 27.00, lng: 84.87 },
        { lat: 26.65, lng: 85.35 },
        { lat: 26.60, lng: 85.90 },
        { lat: 26.45, lng: 86.35 },
        { lat: 26.40, lng: 86.90 },
        { lat: 26.45, lng: 87.28 },
        { lat: 26.50, lng: 87.90 },
        { lat: 26.55, lng: 88.17 },
        { lat: 27.05, lng: 88.15 },
        { lat: 27.45, lng: 88.05 },
        { lat: 27.90, lng: 88.10 },
        { lat: 28.05, lng: 87.55 },
        { lat: 28.10, lng: 86.90 },
        { lat: 28.25, lng: 86.35 },
        { lat: 28.35, lng: 85.60 },
        { lat: 28.75, lng: 85.15 },
        { lat: 29.00, lng: 84.55 },
        { lat: 29.30, lng: 83.90 },
        { lat: 29.65, lng: 83.35 },
        { lat: 29.85, lng: 82.85 },
        { lat: 30.00, lng: 82.30 },
        { lat: 30.20, lng: 81.55 },
        { lat: 30.40, lng: 81.20 },
        { lat: 30.20, lng: 80.09 }
    ];

    const MAX_PHOTOS = 5;

    const ALLOWED_TYPES = [
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp"
    ];

    // No custom style array on purpose — leaving this unset
    // (or passing an empty array) tells Google Maps to render
    // its own genuine default styling in BOTH Roadmap and
    // Satellite/Hybrid mode: real colors, real business/POI
    // icons, real transit lines, and full place-name labels
    // everywhere (including on the satellite layer). A custom
    // "styles" array used to be applied here, which is what
    // was muting the colors and hiding labels in Satellite
    // mode — removed so the map looks and behaves exactly like
    // maps.google.com.
    const NDMS_MAP_STYLE = [];


    /* =====================================================
       MAP STATE (shared across functions in this file)
       ===================================================== */

    let map = null;
    let marker = null;
    let geocoder = null;

    let lastValidLat = null;
    let lastValidLng = null;

    // Elements used by both the map logic and the rest of the
    // page. Populated once, from initReportIncidentMap /
    // DOMContentLoaded — whichever runs first for a given
    // element does not matter since neither writes to it.

    let latitudeInput = null;
    let longitudeInput = null;
    let visibleLatitude = null;
    let visibleLongitude = null;
    let addressInput = null;
    let mapStatusMessage = null;
    let useCurrentLocationBtn = null;
    let mapSearchInput = null;


    function cacheSharedElements() {

        if (!latitudeInput) {
            latitudeInput = document.getElementById("id_latitude");
        }

        if (!longitudeInput) {
            longitudeInput = document.getElementById("id_longitude");
        }

        if (!visibleLatitude) {
            visibleLatitude = document.getElementById("visibleLatitude");
        }

        if (!visibleLongitude) {
            visibleLongitude = document.getElementById("visibleLongitude");
        }

        if (!addressInput) {
            addressInput = document.getElementById("id_address");
        }

        if (!mapStatusMessage) {
            mapStatusMessage = document.getElementById("mapStatusMessage");
        }

        if (!useCurrentLocationBtn) {
            useCurrentLocationBtn =
                document.getElementById("useCurrentLocationBtn");
        }

        if (!mapSearchInput) {
            mapSearchInput =
                document.getElementById("mapSearchInput");
        }

    }


    /* =====================================================
       STATUS MESSAGE HELPERS
       ===================================================== */

    function setStatus(message, type) {

        if (!mapStatusMessage) {
            return;
        }

        mapStatusMessage.textContent = message || "";

        mapStatusMessage.classList.remove(
            "ri-status-success",
            "ri-status-error"
        );

        if (type) {
            mapStatusMessage.classList.add("ri-status-" + type);
        }

    }


    function clearLocationError() {

        const locationError = document.querySelector(
            ".ri-map-container + .ri-field-error"
        );

        if (locationError) {
            locationError.textContent = "";
        }

    }


    /* =====================================================
       COORDINATE FIELDS
       ===================================================== */

    function updateCoordinateFields(lat, lng) {

        const latFixed = lat.toFixed(6);
        const lngFixed = lng.toFixed(6);

        if (latitudeInput) {
            latitudeInput.value = latFixed;
        }

        if (longitudeInput) {
            longitudeInput.value = lngFixed;
        }

        if (visibleLatitude) {
            visibleLatitude.value = latFixed;
        }

        if (visibleLongitude) {
            visibleLongitude.value = lngFixed;
        }

        clearLocationError();

    }


    /* =====================================================
       MARKER
       ===================================================== */

    function placeOrMoveMarker(lat, lng) {

        const position = {
            lat: lat,
            lng: lng
        };

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


    /* =====================================================
       NEPAL BORDER CHECK (fast, offline, no network call)
       ===================================================== */
    //
    // Point-in-polygon test (standard ray-casting algorithm)
    // against NEPAL_POLYGON. Replaces the old rectangle-only
    // check, which incorrectly accepted large parts of India
    // and Tibet just because they share the same latitude/
    // longitude range as Nepal (e.g. Lucknow, Patna, Lhasa were
    // all being accepted as "within Nepal").
    //
    function isWithinNepalBounds(lat, lng) {

        let inside = false;

        for (
            let i = 0, j = NEPAL_POLYGON.length - 1;
            i < NEPAL_POLYGON.length;
            j = i++
        ) {

            const vertexI = NEPAL_POLYGON[i];
            const vertexJ = NEPAL_POLYGON[j];

            const intersects =
                (vertexI.lat > lat) !== (vertexJ.lat > lat) &&
                lng <
                    (vertexJ.lng - vertexI.lng) *
                        (lat - vertexI.lat) /
                        (vertexJ.lat - vertexI.lat) +
                    vertexI.lng;

            if (intersects) {
                inside = !inside;
            }

        }

        return inside;

    }


    function findCountryComponent(geocodeResult) {

        if (!geocodeResult || !geocodeResult.address_components) {
            return null;
        }

        for (
            let i = 0;
            i < geocodeResult.address_components.length;
            i++
        ) {

            const component = geocodeResult.address_components[i];

            if (component.types && component.types.indexOf("country") !== -1) {
                return component;
            }

        }

        return null;

    }


    /* =====================================================
       APPLY / REJECT A CANDIDATE LOCATION
       ===================================================== */

    function applyValidLocation(lat, lng, address) {

        placeOrMoveMarker(lat, lng);
        updateCoordinateFields(lat, lng);

        lastValidLat = lat;
        lastValidLng = lng;

        if (address) {

            addressInput.value = address;

        } else if (addressInput && !addressInput.value) {

            addressInput.placeholder =
                "Address couldn't be detected automatically. " +
                "You can enter it manually.";

        }

        // Citizen-facing success state — includes the detected
        // address when we actually have one (never invented).
        if (address) {
            setStatus("✓ Location selected — " + address, "success");
        } else {
            setStatus("✓ Location selected", "success");
        }

    }


    function handleInvalidLocation(message) {

        if (lastValidLat !== null && lastValidLng !== null) {

            // Snap back to the last valid location instead of
            // leaving an out-of-Nepal marker/coordinates behind.
            placeOrMoveMarker(lastValidLat, lastValidLng);
            updateCoordinateFields(lastValidLat, lastValidLng);

        } else {

            removeMarker();

        }

        setStatus(message, "error");

    }


    /* =====================================================
       VERIFY A CANDIDATE LOCATION IS INSIDE NEPAL
       ===================================================== */
    //
    // Two layers of verification, per requirements:
    //   1. Border polygon check (fast, offline, always available —
    //      see NEPAL_POLYGON / isWithinNepalBounds above).
    //   2. Google Geocoding API reverse lookup of the actual
    //      country for that point. If Geocoding has no data
    //      for a remote point (common in mountainous areas),
    //      we fall back to the polygon result rather than
    //      rejecting a legitimate report.
    //
    function verifyAndSetLocation(lat, lng, onDone) {

        if (!isWithinNepalBounds(lat, lng)) {

            handleInvalidLocation(
                "Please select a location within Nepal."
            );

            if (onDone) {
                onDone(false);
            }

            return;

        }

        if (!geocoder) {

            // Geocoder not ready yet — bounding box already
            // passed, so accept the point without an address.
            applyValidLocation(lat, lng, null);

            if (onDone) {
                onDone(true);
            }

            return;

        }

        setStatus("Verifying location…", null);

        geocoder.geocode(
            {
                location: {
                    lat: lat,
                    lng: lng
                }
            },
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

                        if (onDone) {
                            onDone(false);
                        }

                        return;

                    }

                    applyValidLocation(
                        lat,
                        lng,
                        results[0].formatted_address
                    );

                    if (onDone) {
                        onDone(true);
                    }

                    return;

                }

                // ZERO_RESULTS / OVER_QUERY_LIMIT / etc. The
                // border polygon check already confirmed the point
                // is inside Nepal, so accept it — remote areas
                // often have no reverse-geocoding data at all.
                if (status !== "ZERO_RESULTS") {

                    // Logged so this is diagnosable from the
                    // browser console — REQUEST_DENIED usually
                    // means the Geocoding API isn't enabled for
                    // this key, or billing isn't set up on the
                    // Google Cloud project.
                    console.warn(
                        "NDMS: reverse geocoding failed with " +
                        "status \"" + status + "\". If this " +
                        "happens for every location, confirm the " +
                        "Geocoding API (not just the Maps " +
                        "JavaScript API) is enabled for your key, " +
                        "and that the Google Cloud project has " +
                        "billing enabled."
                    );

                    // Citizen-facing copy stays free of Google Cloud
                    // / API wording (the console.warn above already
                    // carries that detail for developers) — the
                    // location itself is still valid and selected,
                    // only the address lookup didn't return a result.
                    applyValidLocation(lat, lng, null);

                    setStatus(
                        "Address couldn't be detected " +
                        "automatically. Your location is still " +
                        "selected. You can enter the address " +
                        "manually.",
                        null
                    );

                    if (onDone) {
                        onDone(true);
                    }

                    return;

                }

                applyValidLocation(lat, lng, null);

                if (onDone) {
                    onDone(true);
                }

            }
        );

    }


    /* =====================================================
       GOOGLE MAPS LOAD FAILURE HANDLING
       ===================================================== */

    function showMapLoadError() {

        const mapElement = document.getElementById("incidentMap");

        if (mapElement) {

            mapElement.innerHTML =
                '<div class="ri-map-load-error">' +
                "Unable to load the map. Please check your " +
                "internet connection, or try again later." +
                "</div>";

        }

        setStatus(
            "Map failed to load. You can still submit a report " +
            "once the map is available.",
            "error"
        );

    }


    // Called by Google if the API key is invalid/misconfigured.
    window.gm_authFailure = showMapLoadError;

    // Called (see report_incident.html) if the Google Maps
    // script itself fails to load, e.g. no network connection.
    window.ndmsMapsScriptError = showMapLoadError;


    /* =====================================================
       MAP INITIALIZATION
       (invoked by the Google Maps script's callback param —
       see report_incident.html)
       ===================================================== */

    function createLayerToggleControl(targetMap) {

        const container = document.createElement("div");
        container.className = "ri-layer-control";

        const standardBtn = document.createElement("button");
        standardBtn.type = "button";
        standardBtn.className = "ri-layer-btn active";
        standardBtn.textContent = "Standard";

        const satelliteBtn = document.createElement("button");
        satelliteBtn.type = "button";
        satelliteBtn.className = "ri-layer-btn";
        satelliteBtn.textContent = "Satellite";

        container.appendChild(standardBtn);
        container.appendChild(satelliteBtn);

        // Prevent map click/drag from firing when interacting
        // with the control itself.
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

            // HYBRID (not SATELLITE) — satellite imagery WITH
            // the roads/place-name label overlay on top, so
            // town/village names stay visible. Plain SATELLITE
            // is imagery only, with no labels at all.
            targetMap.setMapTypeId(google.maps.MapTypeId.HYBRID);

            satelliteBtn.classList.add("active");
            standardBtn.classList.remove("active");

        });

        return container;

    }


    /* =====================================================
       "SEARCH GOOGLE MAPS" BOX (Places Autocomplete)
       Real Google-Maps-style search bar overlaid on the map.
       Selecting a result runs through the exact same
       verifyAndSetLocation() pipeline as a manual map click —
       Nepal validation, marker placement, and reverse-geocoded
       address auto-fill all stay identical either way.
       ===================================================== */

    function initMapSearchBox() {

        if (
            !mapSearchInput ||
            typeof google.maps.places === "undefined"
        ) {

            // Places library wasn't loaded (see the
            // "&libraries=places" param on the Google Maps
            // script tag in report_incident.html) — the map
            // and every other feature still work fine without
            // it, so fail silently rather than block the page.
            return;

        }

        const autocomplete = new google.maps.places.Autocomplete(
            mapSearchInput,
            {
                fields: ["geometry", "name", "formatted_address"],
                componentRestrictions: { country: "np" }
            }
        );

        // Bias results toward Nepal without hard-blocking
        // anything Google itself considers a Nepal result.
        autocomplete.setBounds(
            new google.maps.LatLngBounds(
                { lat: NEPAL_BOUNDS.south, lng: NEPAL_BOUNDS.west },
                { lat: NEPAL_BOUNDS.north, lng: NEPAL_BOUNDS.east }
            )
        );

        // Prevent the Enter key inside the search box from
        // submitting the incident report form.
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


    function initReportIncidentMap() {

        const mapElement = document.getElementById("incidentMap");

        if (!mapElement || typeof google === "undefined" || !google.maps) {
            return;
        }

        cacheSharedElements();

        geocoder = new google.maps.Geocoder();

        map = new google.maps.Map(mapElement, {
            center: NEPAL_CENTER,
            zoom: NEPAL_DEFAULT_ZOOM,
            styles: NDMS_MAP_STYLE,
            // minZoom (not strictBounds) is what keeps India/Tibet/
            // Bhutan from flooding into view when zoomed out — it
            // caps how far the user can manually zoom out, without
            // ever forcing an automatic zoom change on its own.
            // strictBounds:true was tried instead, but it forces
            // Google to silently override the zoom level on every
            // setCenter() call (e.g. "Use My Current Location") to
            // guarantee the bounds always fill the viewport — that
            // was the source of the unwanted "auto zoom" bug.
            minZoom: NEPAL_DEFAULT_ZOOM,
            restriction: {
                latLngBounds: NEPAL_BOUNDS,
                strictBounds: false
            },
            // Google's default Map/Satellite control uses its own
            // stock blue "active" color, which clashes with the
            // NDMS palette — replaced below with a custom control
            // styled to match the rest of the dashboard.
            mapTypeControl: false,
            streetViewControl: true,
            fullscreenControl: true,
            zoomControl: true,
            gestureHandling: "greedy"
        });

        // TOP_LEFT: Google's own fullscreen / camera / zoom /
        // street-view controls stack down the RIGHT edge, and on
        // a short phone map they collided with this toggle.
        // (On desktop the search pill is offset to the right of
        // the toggle — see .ri-map-search-wrap in the CSS.)
        map.controls[google.maps.ControlPosition.TOP_LEFT].push(
            createLayerToggleControl(map)
        );

        initMapSearchBox();

        map.addListener("click", function (event) {

            verifyAndSetLocation(
                event.latLng.lat(),
                event.latLng.lng()
            );

        });

        // If the form is being re-rendered after a validation
        // error elsewhere (e.g. description too short), the
        // hidden latitude/longitude fields already carry the
        // previously selected coordinates — restore the marker
        // so the user does not have to re-pick the location.
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

            map.setCenter({
                lat: existingLat,
                lng: existingLng
            });

            map.setZoom(13);

        }

        /* -------------------------------------------------
           RESPONSIVE MAP
           ------------------------------------------------- */

        window.addEventListener("resize", function () {
            google.maps.event.trigger(map, "resize");
        });

        const mobileSidebarToggle =
            document.getElementById("mobileSidebarToggle");

        if (mobileSidebarToggle) {

            mobileSidebarToggle.addEventListener("click", function () {

                setTimeout(function () {

                    google.maps.event.trigger(map, "resize");
                    map.setCenter(map.getCenter());

                }, 260);

            });

        }

    }

    window.initReportIncidentMap = initReportIncidentMap;


    /* =====================================================
       PAGE LOGIC (photo upload, current-location button,
       form validation) — unrelated to map initialization
       timing, so this still runs on DOMContentLoaded.
       ===================================================== */

    document.addEventListener("DOMContentLoaded", function () {

        cacheSharedElements();

        const choosePhotosBtn =
            document.getElementById("choosePhotosBtn");

        const photoInput =
            document.getElementById("photoInput");

        const photoCount =
            document.getElementById("photoCount");

        const photoError =
            document.getElementById("photoError");

        const photoPreviewGrid =
            document.getElementById("photoPreviewGrid");

        const reportForm =
            document.getElementById("reportIncidentForm");

        const submitReportBtn =
            document.getElementById("submitReportBtn");

        const severityGrid =
            document.getElementById("severityGrid");

        const severityError =
            document.getElementById("severityError");

        const validationAlert =
            document.getElementById("riValidationAlert");

        const validationAlertList =
            document.getElementById("riValidationAlertList");

        const incidentStartDateField =
            document.getElementById("id_incident_start_date");


        /* =================================================
           INCIDENT START DATE & TIME -- BROWSER-SIDE FUTURE
           RESTRICTION ONLY
           Sets `max` to the current local date/time so most
           browsers won't even open a future date in the
           picker. This is purely a UX convenience -- it is
           NOT the real validation boundary, since a request
           can always be edited/replayed. The authoritative
           check is server-side (see
           DisasterReportForm.clean_incident_start_date()).
           This field is intentionally left blank -- it is
           never pre-filled with "now" or with any other
           value.
           ================================================= */

        if (incidentStartDateField) {

            const pad = function (n) {
                return String(n).padStart(2, "0");
            };

            const now = new Date();

            const nowValue =
                now.getFullYear() + "-" +
                pad(now.getMonth() + 1) + "-" +
                pad(now.getDate()) + "T" +
                pad(now.getHours()) + ":" +
                pad(now.getMinutes());

            incidentStartDateField.setAttribute("max", nowValue);


            /* =============================================
               INCIDENT START DATE & TIME -- CUSTOM PICKER
               Replaces the native datetime-local calendar/
               clock popup (which is drawn by the browser/OS
               and looks and sizes itself differently on every
               device -- sometimes overflowing the screen, as
               on the compound Chrome/Edge widget) with a
               custom calendar + time control built the same
               way the Disaster Type dropdown replaces the
               native <select> list above. The real hidden
               <input type="datetime-local"> stays the source
               of truth for validation/submission -- this UI
               only ever writes to its .value.
               ============================================= */

            const dtPicker =
                document.getElementById("riDateTimePicker");

            const dtTrigger =
                document.getElementById("riDtTrigger");

            const dtTriggerText =
                document.getElementById("riDtTriggerText");

            const dtPanel =
                document.getElementById("riDtPanel");

            const dtCalTitle =
                document.getElementById("riDtCalTitle");

            const dtDays =
                document.getElementById("riDtDays");

            const dtPrevMonth =
                document.getElementById("riDtPrevMonth");

            const dtNextMonth =
                document.getElementById("riDtNextMonth");

            const dtHourValue =
                document.getElementById("riDtHourValue");

            const dtMinuteValue =
                document.getElementById("riDtMinuteValue");

            const dtAmPm =
                document.getElementById("riDtAmPm");

            const dtNowBtn =
                document.getElementById("riDtNow");

            const dtClearBtn =
                document.getElementById("riDtClear");

            const dtDoneBtn =
                document.getElementById("riDtDone");

            if (
                dtPicker && dtTrigger && dtTriggerText && dtPanel &&
                dtCalTitle && dtDays && dtPrevMonth && dtNextMonth &&
                dtHourValue && dtMinuteValue && dtAmPm &&
                dtNowBtn && dtClearBtn && dtDoneBtn
            ) {

                const monthNames = [
                    "January", "February", "March", "April",
                    "May", "June", "July", "August",
                    "September", "October", "November", "December"
                ];

                // { year, month (0-11), day, hour (0-23), minute }
                let selected = null;

                let viewYear = now.getFullYear();
                let viewMonth = now.getMonth();

                const todayDateOnly = new Date(
                    now.getFullYear(), now.getMonth(), now.getDate()
                );

                function formatTrigger(sel) {

                    const d = new Date(
                        sel.year, sel.month, sel.day,
                        sel.hour, sel.minute
                    );

                    const dateStr = d.toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric"
                    });

                    const h12 = (sel.hour % 12) || 12;
                    const ampm = sel.hour < 12 ? "AM" : "PM";

                    return (
                        dateStr + ", " + h12 + ":" +
                        pad(sel.minute) + " " + ampm
                    );

                }

                function syncNativeInput() {

                    if (!selected) {

                        incidentStartDateField.value = "";

                        dtTriggerText.textContent =
                            "Select date & time";

                        dtTrigger.classList.add(
                            "ri-select-placeholder"
                        );

                    } else {

                        incidentStartDateField.value =
                            selected.year + "-" +
                            pad(selected.month + 1) + "-" +
                            pad(selected.day) + "T" +
                            pad(selected.hour) + ":" +
                            pad(selected.minute);

                        dtTriggerText.textContent =
                            formatTrigger(selected);

                        dtTrigger.classList.remove(
                            "ri-select-placeholder"
                        );

                        incidentStartDateField.classList.remove(
                            "ri-invalid"
                        );

                    }

                    incidentStartDateField.dispatchEvent(
                        new Event("change", { bubbles: true })
                    );

                }

                function renderCalendar() {

                    dtCalTitle.textContent =
                        monthNames[viewMonth] + " " + viewYear;

                    dtDays.innerHTML = "";

                    const firstWeekday =
                        new Date(viewYear, viewMonth, 1).getDay();

                    const daysInMonth =
                        new Date(viewYear, viewMonth + 1, 0).getDate();

                    const daysInPrevMonth =
                        new Date(viewYear, viewMonth, 0).getDate();

                    const cells = [];

                    for (let i = 0; i < firstWeekday; i++) {

                        cells.push({
                            day: daysInPrevMonth - firstWeekday + 1 + i,
                            outside: true
                        });

                    }

                    for (let d = 1; d <= daysInMonth; d++) {

                        cells.push({ day: d, outside: false });

                    }

                    const remainder = cells.length % 7;

                    if (remainder !== 0) {

                        for (let i = 1; i <= 7 - remainder; i++) {

                            cells.push({ day: i, outside: true });

                        }

                    }

                    cells.forEach(function (cell) {

                        const btn = document.createElement("button");
                        btn.type = "button";
                        btn.className = "ri-dt-day";
                        btn.textContent = String(cell.day);

                        if (cell.outside) {

                            btn.classList.add("ri-dt-day-outside");
                            btn.disabled = true;
                            btn.tabIndex = -1;
                            dtDays.appendChild(btn);
                            return;

                        }

                        const cellDateOnly = new Date(
                            viewYear, viewMonth, cell.day
                        );

                        if (
                            viewYear === now.getFullYear() &&
                            viewMonth === now.getMonth() &&
                            cell.day === now.getDate()
                        ) {
                            btn.classList.add("ri-dt-day-today");
                        }

                        if (
                            selected &&
                            selected.year === viewYear &&
                            selected.month === viewMonth &&
                            selected.day === cell.day
                        ) {
                            btn.classList.add("ri-dt-day-selected");
                        }

                        if (cellDateOnly.getTime() > todayDateOnly.getTime()) {

                            btn.disabled = true;
                            btn.classList.add("ri-dt-day-disabled");

                        } else {

                            btn.addEventListener("click", function () {

                                let hour =
                                    selected ? selected.hour : now.getHours();

                                let minute =
                                    selected ? selected.minute : now.getMinutes();

                                if (cellDateOnly.getTime() === todayDateOnly.getTime()) {

                                    const candidate = new Date(
                                        viewYear, viewMonth, cell.day,
                                        hour, minute
                                    );

                                    if (candidate.getTime() > now.getTime()) {
                                        hour = now.getHours();
                                        minute = now.getMinutes();
                                    }

                                }

                                selected = {
                                    year: viewYear,
                                    month: viewMonth,
                                    day: cell.day,
                                    hour: hour,
                                    minute: minute
                                };

                                renderCalendar();
                                renderTime();
                                syncNativeInput();

                            });

                        }

                        dtDays.appendChild(btn);

                    });

                }

                function renderTime() {

                    const hour =
                        selected ? selected.hour : now.getHours();

                    const minute =
                        selected ? selected.minute : now.getMinutes();

                    const h12 = (hour % 12) || 12;

                    dtHourValue.textContent = pad(h12);
                    dtMinuteValue.textContent = pad(minute);
                    dtAmPm.textContent = hour < 12 ? "AM" : "PM";

                }

                function ensureSelected() {

                    if (!selected) {

                        selected = {
                            year: now.getFullYear(),
                            month: now.getMonth(),
                            day: now.getDate(),
                            hour: now.getHours(),
                            minute: now.getMinutes()
                        };

                    }

                }

                function wouldBeFuture(hour, minute) {

                    const cellDateOnly = new Date(
                        selected.year, selected.month, selected.day
                    );

                    const candidate = new Date(
                        selected.year, selected.month, selected.day,
                        hour, minute
                    );

                    return (
                        cellDateOnly.getTime() === todayDateOnly.getTime() &&
                        candidate.getTime() > now.getTime()
                    );

                }

                function stepTime(unit, dir) {

                    ensureSelected();

                    let hour = selected.hour;
                    let minute = selected.minute;

                    if (unit === "hour") {

                        hour = (hour + (dir === "up" ? 1 : -1) + 24) % 24;

                    } else {

                        minute = (minute + (dir === "up" ? 1 : -1) + 60) % 60;

                    }

                    if (wouldBeFuture(hour, minute)) {
                        return;
                    }

                    selected.hour = hour;
                    selected.minute = minute;

                    renderTime();
                    syncNativeInput();

                }

                function toggleAmPm() {

                    ensureSelected();

                    const hour =
                        selected.hour < 12 ?
                            selected.hour + 12 : selected.hour - 12;

                    if (wouldBeFuture(hour, selected.minute)) {
                        return;
                    }

                    selected.hour = hour;

                    renderTime();
                    syncNativeInput();

                }

                function openPanel() {

                    dtPicker.classList.add("ri-select-open");
                    dtTrigger.setAttribute("aria-expanded", "true");

                    if (selected) {
                        viewYear = selected.year;
                        viewMonth = selected.month;
                    }

                    renderCalendar();
                    renderTime();

                }

                function closePanel() {

                    dtPicker.classList.remove("ri-select-open");
                    dtTrigger.setAttribute("aria-expanded", "false");

                }

                function togglePanel() {

                    if (dtPicker.classList.contains("ri-select-open")) {
                        closePanel();
                    } else {
                        openPanel();
                    }

                }

                // Pre-fill from an existing value, e.g. when the
                // form is re-rendered with other validation errors
                // and Django re-populates this bound field.
                if (incidentStartDateField.value) {

                    const parts =
                        incidentStartDateField.value.split(/[-T:]/);

                    if (parts.length >= 5) {

                        selected = {
                            year: parseInt(parts[0], 10),
                            month: parseInt(parts[1], 10) - 1,
                            day: parseInt(parts[2], 10),
                            hour: parseInt(parts[3], 10),
                            minute: parseInt(parts[4], 10)
                        };

                        viewYear = selected.year;
                        viewMonth = selected.month;

                    }

                }

                if (selected) {
                    dtTriggerText.textContent = formatTrigger(selected);
                } else {
                    dtTrigger.classList.add("ri-select-placeholder");
                }

                dtTrigger.addEventListener("click", function (event) {

                    event.stopPropagation();
                    togglePanel();

                });

                dtTrigger.addEventListener("keydown", function (event) {

                    if (
                        event.key === "Enter" ||
                        event.key === " " ||
                        event.key === "ArrowDown"
                    ) {

                        event.preventDefault();
                        openPanel();

                    } else if (event.key === "Escape") {

                        closePanel();

                    }

                });

                dtPanel.addEventListener("click", function (event) {

                    event.stopPropagation();

                });

                dtPrevMonth.addEventListener("click", function () {

                    viewMonth -= 1;

                    if (viewMonth < 0) {
                        viewMonth = 11;
                        viewYear -= 1;
                    }

                    renderCalendar();

                });

                dtNextMonth.addEventListener("click", function () {

                    viewMonth += 1;

                    if (viewMonth > 11) {
                        viewMonth = 0;
                        viewYear += 1;
                    }

                    renderCalendar();

                });

                dtPanel.querySelectorAll(".ri-dt-step-btn").forEach(
                    function (btn) {

                        btn.addEventListener("click", function () {

                            const unit = btn.closest(".ri-dt-stepper")
                                .getAttribute("data-unit");

                            stepTime(unit, btn.getAttribute("data-dir"));

                        });

                    }
                );

                dtAmPm.addEventListener("click", toggleAmPm);

                dtNowBtn.addEventListener("click", function () {

                    selected = {
                        year: now.getFullYear(),
                        month: now.getMonth(),
                        day: now.getDate(),
                        hour: now.getHours(),
                        minute: now.getMinutes()
                    };

                    viewYear = selected.year;
                    viewMonth = selected.month;

                    renderCalendar();
                    renderTime();
                    syncNativeInput();

                });

                dtClearBtn.addEventListener("click", function () {

                    selected = null;

                    renderCalendar();
                    renderTime();
                    syncNativeInput();

                });

                dtDoneBtn.addEventListener("click", function () {

                    closePanel();
                    dtTrigger.focus();

                });

                document.addEventListener("click", function (event) {

                    if (!dtPicker.contains(event.target)) {
                        closePanel();
                    }

                });

                document.addEventListener("keydown", function (event) {

                    if (
                        event.key === "Escape" &&
                        dtPicker.classList.contains("ri-select-open")
                    ) {

                        closePanel();
                        dtTrigger.focus();

                    }

                });

            }

        }


        /* =================================================
           DISASTER TYPE CUSTOM SELECT DROPDOWN
           Syncs the custom button trigger + panel listbox
           with Django's native #id_disaster_type element.
           Handles keyboard navigation, URL preselection,
           dynamic options, and validation states.
           ================================================= */

        const dtSelectWrapper =
            document.getElementById("riDisasterTypeSelect");

        const dtNativeSelect =
            document.getElementById("id_disaster_type");

        const dtTrigger =
            document.getElementById("riDisasterTypeTrigger");

        const dtTriggerText =
            document.getElementById("riDisasterTypeTriggerText");

        const dtPanel =
            document.getElementById("riDisasterTypePanel");

        if (
            dtSelectWrapper &&
            dtNativeSelect &&
            dtTrigger &&
            dtTriggerText &&
            dtPanel
        ) {

            // Preselection from query parameter if not already selected
            const urlParams =
                new URLSearchParams(window.location.search);

            const dtParam =
                (urlParams.get("disaster_type") || "").trim();

            if (dtParam && (!dtNativeSelect.value || dtNativeSelect.value === "")) {

                for (let i = 0; i < dtNativeSelect.options.length; i++) {

                    const opt = dtNativeSelect.options[i];

                    if (
                        opt.value === dtParam ||
                        opt.text.trim().toLowerCase() === dtParam.toLowerCase()
                    ) {
                        dtNativeSelect.selectedIndex = i;
                        break;
                    }

                }

            }

            function syncFromNativeSelect() {

                const selectedOption =
                    dtNativeSelect.options[dtNativeSelect.selectedIndex];

                if (selectedOption && selectedOption.value) {

                    dtTriggerText.textContent = selectedOption.text;
                    dtTrigger.classList.remove("ri-select-placeholder");
                    dtNativeSelect.classList.remove("ri-invalid");

                } else {

                    dtTriggerText.textContent = "Select disaster type";
                    dtTrigger.classList.add("ri-select-placeholder");

                }

                const items =
                    dtPanel.querySelectorAll(".ri-select-option");

                items.forEach(function (item) {

                    const isSelected =
                        item.getAttribute("data-value") ===
                        (dtNativeSelect.value || "");

                    item.classList.toggle(
                        "ri-select-option-selected",
                        isSelected
                    );

                    item.setAttribute(
                        "aria-selected",
                        isSelected ? "true" : "false"
                    );

                });

            }

            function openDtDropdown() {

                dtSelectWrapper.classList.add("ri-select-open");
                dtTrigger.setAttribute("aria-expanded", "true");

                const targetItem =
                    dtPanel.querySelector(".ri-select-option-selected") ||
                    dtPanel.firstElementChild;

                if (targetItem) {
                    targetItem.focus();
                }

            }

            function closeDtDropdown() {

                dtSelectWrapper.classList.remove("ri-select-open");
                dtTrigger.setAttribute("aria-expanded", "false");

            }

            function toggleDtDropdown() {

                if (dtSelectWrapper.classList.contains("ri-select-open")) {
                    closeDtDropdown();
                } else {
                    openDtDropdown();
                }

            }

            // Populate options from native select
            dtPanel.innerHTML = "";

            for (let i = 0; i < dtNativeSelect.options.length; i++) {

                const opt = dtNativeSelect.options[i];

                const li = document.createElement("li");
                li.className = "ri-select-option";
                li.setAttribute("role", "option");
                li.setAttribute("tabindex", "0");
                li.setAttribute("data-value", opt.value);

                if (!opt.value) {

                    li.classList.add("ri-select-option-empty");
                    li.textContent =
                        opt.text && opt.text.indexOf("---") === -1
                            ? opt.text
                            : "Select disaster type";

                } else {

                    li.textContent = opt.text;

                }

                li.addEventListener("click", function () {

                    dtNativeSelect.value = opt.value;

                    dtNativeSelect.dispatchEvent(
                        new Event("change", { bubbles: true })
                    );

                    closeDtDropdown();
                    dtTrigger.focus();

                });

                li.addEventListener("keydown", function (e) {

                    if (e.key === "Enter" || e.key === " ") {

                        e.preventDefault();
                        li.click();

                    } else if (e.key === "ArrowDown") {

                        e.preventDefault();
                        const next = li.nextElementSibling;
                        if (next) {
                            next.focus();
                        }

                    } else if (e.key === "ArrowUp") {

                        e.preventDefault();
                        const prev = li.previousElementSibling;
                        if (prev) {
                            prev.focus();
                        } else {
                            dtTrigger.focus();
                        }

                    } else if (e.key === "Escape") {

                        e.preventDefault();
                        closeDtDropdown();
                        dtTrigger.focus();

                    }

                });

                dtPanel.appendChild(li);

            }

            dtTrigger.addEventListener("click", function (event) {

                event.stopPropagation();
                toggleDtDropdown();

            });

            dtTrigger.addEventListener("keydown", function (event) {

                if (
                    event.key === "ArrowDown" ||
                    event.key === "Enter" ||
                    event.key === " "
                ) {

                    event.preventDefault();
                    openDtDropdown();

                } else if (event.key === "Escape") {

                    closeDtDropdown();

                }

            });

            document.addEventListener("click", function (event) {

                if (!dtSelectWrapper.contains(event.target)) {
                    closeDtDropdown();
                }

            });

            // NOTE: the Disaster Type list intentionally opens on
            // click (or Enter/Space/ArrowDown) only -- see
            // dtTrigger's click/keydown listeners above. There is
            // no mouseenter/hover trigger; hovering the closed
            // control must never reveal the panel.

            dtNativeSelect.addEventListener("change", syncFromNativeSelect);

            syncFromNativeSelect();

        }


        /* =================================================
           DESCRIPTION — LIVE CHARACTER COUNT
           Same pattern as the feedback form's character
           counter (home.js #feedbackCharacterCount) -- just
           without a "/ max" denominator, since the incident
           description has no fixed maximum length.
           ================================================= */

        const descriptionCharCountField =
            document.getElementById("id_description");

        const descriptionCharCount =
            document.getElementById("riDescriptionCharCount");

        if (descriptionCharCountField && descriptionCharCount) {

            function updateDescriptionCharCount() {

                const length =
                    descriptionCharCountField.value.length;

                descriptionCharCount.textContent =
                    length + (length === 1 ? " character" : " characters");

            }

            descriptionCharCountField.addEventListener(
                "input",
                updateDescriptionCharCount
            );

            updateDescriptionCharCount();

        }


        /* =================================================
           INCIDENT SEVERITY CARDS
           The real <input type="radio"> already carries the
           form value to Django on submit (see forms.py /
           report_incident.html) -- this only mirrors the
           native :checked state onto an .is-selected class on
           the card for browsers/situations where the CSS
           :has() selector doesn't apply, and clears any error
           state once a card is picked.
           ================================================= */

        function clearSeverityError() {

            if (severityGrid) {
                severityGrid.classList.remove("ri-invalid");
            }

            if (severityError) {
                severityError.textContent = "";
            }

        }


        if (severityGrid) {

            const severityCards =
                severityGrid.querySelectorAll(".ri-severity-card");

            const severityInputs =
                severityGrid.querySelectorAll(
                    "input[name='reported_severity']"
                );

            severityInputs.forEach(function (input) {

                input.addEventListener("change", function () {

                    severityCards.forEach(function (card) {
                        card.classList.remove("is-selected");
                    });

                    if (input.checked) {

                        const selectedCard =
                            input.closest(".ri-severity-card");

                        if (selectedCard) {
                            selectedCard.classList.add("is-selected");
                        }

                    }

                    clearSeverityError();

                });

            });

            // Restore visual state on load (e.g. the form is being
            // re-rendered after a validation error elsewhere and a
            // severity was already picked before that submit).
            severityInputs.forEach(function (input) {

                if (input.checked) {

                    const selectedCard =
                        input.closest(".ri-severity-card");

                    if (selectedCard) {
                        selectedCard.classList.add("is-selected");
                    }

                }

            });

        }


        /* =================================================
           USE MY CURRENT LOCATION
           ================================================= */

        if (useCurrentLocationBtn) {

            useCurrentLocationBtn.addEventListener(
                "click",
                function () {

                    if (!map || !geocoder) {

                        setStatus(
                            "Map is still loading. Please wait a " +
                            "moment and try again.",
                            "error"
                        );

                        return;

                    }

                    if (!navigator.geolocation) {

                        setStatus(
                            "Geolocation is not supported by your " +
                            "browser.",
                            "error"
                        );

                        return;

                    }

                    useCurrentLocationBtn.disabled = true;

                    setStatus("Getting your current location…", null);

                    navigator.geolocation.getCurrentPosition(

                        function (position) {

                            const lat = position.coords.latitude;
                            const lng = position.coords.longitude;
                            const accuracy = position.coords.accuracy;

                            verifyAndSetLocation(lat, lng, function (isValid) {

                                if (isValid) {

                                    // Marker is already placed by
                                    // verifyAndSetLocation() above.
                                    //
                                    // google.maps.event.trigger(map,
                                    // "resize") forces the map to
                                    // re-measure its container before
                                    // we center/zoom — without this,
                                    // if the map's container size was
                                    // ever stale (e.g. it was laid out
                                    // before a font/webfont finished
                                    // loading, or the browser's mobile
                                    // address bar hid/showed), Maps
                                    // centers using the WRONG size and
                                    // the pin visibly lands off to one
                                    // side instead of the middle.
                                    google.maps.event.trigger(map, "resize");

                                    map.setCenter({
                                        lat: lat,
                                        lng: lng
                                    });

                                    map.setZoom(CURRENT_LOCATION_ZOOM);

                                    // Re-assert the center one tick
                                    // later, after layout has fully
                                    // settled from the resize above —
                                    // belt-and-braces so the pin ends
                                    // up dead center every time.
                                    window.setTimeout(function () {

                                        map.setCenter({
                                            lat: lat,
                                            lng: lng
                                        });

                                    }, 150);

                                    // The map itself is centered
                                    // correctly on whatever lat/lng the
                                    // browser handed back — if the pin
                                    // still doesn't look right, it's
                                    // almost always because the fix
                                    // itself was imprecise (common
                                    // without a GPS chip), not a map
                                    // rendering issue. Surface that to
                                    // the citizen instead of silently
                                    // trusting a coarse fix.
                                    if (
                                        typeof accuracy === "number" &&
                                        accuracy > LOW_ACCURACY_THRESHOLD_METERS
                                    ) {

                                        const accuracyKm =
                                            Math.round(accuracy / 100) / 10;

                                        setStatus(
                                            "✓ Location selected, but " +
                                            "your device could only " +
                                            "narrow it down to about " +
                                            accuracyKm + " km. If the " +
                                            "pin looks wrong, search " +
                                            "for the place or tap the " +
                                            "exact spot on the map.",
                                            null
                                        );

                                    }

                                } else {

                                    setStatus(
                                        "Your current location is outside " +
                                        "Nepal. Please select a location " +
                                        "within Nepal to continue.",
                                        "error"
                                    );

                                }

                                useCurrentLocationBtn.disabled = false;

                            });

                        },

                        function () {

                            setStatus(
                                "Couldn't access your current location. " +
                                "You can search for a place or choose a " +
                                "point on the map.",
                                "error"
                            );

                            useCurrentLocationBtn.disabled = false;

                        },

                        {
                            enableHighAccuracy: true,
                            timeout: 10000
                        }

                    );

                }
            );

        }


        /* =================================================
           PHOTO UPLOAD
           ================================================= */

        let selectedFiles = [];


        function refreshPhotoCount() {

            if (photoCount) {

                photoCount.textContent =
                    selectedFiles.length + " / " + MAX_PHOTOS +
                    " photos selected";

            }

        }


        function showPhotoError(message) {

            if (photoError) {
                photoError.textContent = message;
            }

        }


        function clearPhotoError() {

            if (photoError) {
                photoError.textContent = "";
            }

        }


        function syncFileInput() {

            if (typeof DataTransfer === "undefined") {
                return;
            }

            const dataTransfer = new DataTransfer();

            selectedFiles.forEach(function (file) {
                dataTransfer.items.add(file);
            });

            photoInput.files = dataTransfer.files;

        }


        function renderPhotoPreviews() {

            if (!photoPreviewGrid) {
                return;
            }

            photoPreviewGrid.innerHTML = "";

            selectedFiles.forEach(function (file, index) {

                const card = document.createElement("div");
                card.className = "ri-photo-card";

                const img = document.createElement("img");
                img.src = URL.createObjectURL(file);
                img.alt = "Selected incident photo " + (index + 1);
                img.onload = function () {
                    URL.revokeObjectURL(img.src);
                };

                /*
                 * The thumbnail click target is a dedicated button
                 * (.ri-photo-view) covering the image — kept
                 * completely separate from .ri-photo-remove below
                 * so viewing a photo can never accidentally remove
                 * it. Opens the large preview/lightbox; never
                 * submits the form or navigates away.
                 */
                const viewBtn = document.createElement("button");
                viewBtn.type = "button";
                viewBtn.className = "ri-photo-view";
                viewBtn.setAttribute(
                    "aria-label",
                    "View photo " + (index + 1) + " of " +
                    selectedFiles.length + " larger"
                );

                viewBtn.addEventListener("click", function () {
                    openPhotoLightbox(index);
                });

                const removeBtn = document.createElement("button");
                removeBtn.type = "button";
                removeBtn.className = "ri-photo-remove";
                removeBtn.setAttribute(
                    "aria-label",
                    "Remove photo " + (index + 1)
                );
                removeBtn.textContent = "×";

                removeBtn.addEventListener("click", function () {

                    selectedFiles.splice(index, 1);

                    syncFileInput();
                    renderPhotoPreviews();
                    refreshPhotoCount();
                    clearPhotoError();
                    closePhotoLightbox();

                });

                card.appendChild(img);
                card.appendChild(viewBtn);
                card.appendChild(removeBtn);
                photoPreviewGrid.appendChild(card);

            });

            refreshPhotoCount();

            // Keep an open lightbox in sync if a photo was removed
            // while it was showing (e.g. via keyboard) rather than
            // leaving it pointing at a stale/shifted index.
            if (lightboxOpenIndex !== null) {

                if (!selectedFiles.length) {
                    closePhotoLightbox();
                } else {
                    showLightboxPhoto(
                        Math.min(lightboxOpenIndex, selectedFiles.length - 1)
                    );
                }

            }

        }


        /* =================================================
           PHOTO LIGHTBOX
           Large preview opened by clicking/tapping a thumbnail.
           Purely a viewer: it never submits the form, removes a
           photo, or navigates away. Closes on Escape, on the
           close button, or by clicking outside the image.
           ================================================= */

        const photoLightbox =
            document.getElementById("riPhotoLightbox");

        const lightboxImage =
            document.getElementById("riLightboxImage");

        const lightboxClose =
            document.getElementById("riLightboxClose");

        const lightboxPrev =
            document.getElementById("riLightboxPrev");

        const lightboxNext =
            document.getElementById("riLightboxNext");

        const lightboxCounter =
            document.getElementById("riLightboxCounter");

        let lightboxOpenIndex = null;
        let lightboxObjectUrl = null;

        function showLightboxPhoto(index) {

            if (
                !photoLightbox || !lightboxImage ||
                index < 0 || index >= selectedFiles.length
            ) {
                return;
            }

            lightboxOpenIndex = index;

            if (lightboxObjectUrl) {
                URL.revokeObjectURL(lightboxObjectUrl);
            }

            lightboxObjectUrl =
                URL.createObjectURL(selectedFiles[index]);

            lightboxImage.src = lightboxObjectUrl;
            lightboxImage.alt =
                "Incident photo " + (index + 1) + " of " +
                selectedFiles.length;

            if (lightboxCounter) {

                lightboxCounter.textContent =
                    selectedFiles.length > 1
                        ? (index + 1) + " / " + selectedFiles.length
                        : "";

            }

            const showNav = selectedFiles.length > 1;

            if (lightboxPrev) {
                lightboxPrev.style.display = showNav ? "" : "none";
            }

            if (lightboxNext) {
                lightboxNext.style.display = showNav ? "" : "none";
            }

        }

        function openPhotoLightbox(index) {

            if (!photoLightbox) {
                return;
            }

            showLightboxPhoto(index);

            photoLightbox.classList.add("show");
            document.body.style.overflow = "hidden";

            if (lightboxClose) {
                lightboxClose.focus();
            }

        }

        function closePhotoLightbox() {

            if (!photoLightbox) {
                return;
            }

            photoLightbox.classList.remove("show");
            document.body.style.overflow = "";

            if (lightboxObjectUrl) {
                URL.revokeObjectURL(lightboxObjectUrl);
                lightboxObjectUrl = null;
            }

            lightboxOpenIndex = null;

        }

        function showAdjacentLightboxPhoto(delta) {

            if (lightboxOpenIndex === null || !selectedFiles.length) {
                return;
            }

            const nextIndex =
                (lightboxOpenIndex + delta + selectedFiles.length) %
                selectedFiles.length;

            showLightboxPhoto(nextIndex);

        }

        if (photoLightbox) {

            if (lightboxClose) {

                lightboxClose.addEventListener(
                    "click",
                    closePhotoLightbox
                );

            }

            if (lightboxPrev) {

                lightboxPrev.addEventListener("click", function () {
                    showAdjacentLightboxPhoto(-1);
                });

            }

            if (lightboxNext) {

                lightboxNext.addEventListener("click", function () {
                    showAdjacentLightboxPhoto(1);
                });

            }

            // Click outside the image (on the dark backdrop) closes
            // the lightbox -- a click on the stage/image/nav/close
            // button itself does not, since those are all children
            // of .ri-lightbox-stage.
            photoLightbox.addEventListener("click", function (event) {

                if (event.target === photoLightbox) {
                    closePhotoLightbox();
                }

            });

            document.addEventListener("keydown", function (event) {

                if (!photoLightbox.classList.contains("show")) {
                    return;
                }

                if (event.key === "Escape") {

                    event.preventDefault();
                    closePhotoLightbox();

                } else if (event.key === "ArrowLeft") {

                    event.preventDefault();
                    showAdjacentLightboxPhoto(-1);

                } else if (event.key === "ArrowRight") {

                    event.preventDefault();
                    showAdjacentLightboxPhoto(1);

                }

            });

        }


        function addFiles(fileList) {

            clearPhotoError();

            const incomingFiles = Array.from(fileList);

            let rejectedInvalidType = false;

            const validFiles = incomingFiles.filter(function (file) {

                const isValidType =
                    ALLOWED_TYPES.indexOf(file.type) !== -1;

                if (!isValidType) {
                    rejectedInvalidType = true;
                }

                return isValidType;

            });

            if (rejectedInvalidType) {
                showPhotoError("Only image files are allowed.");
            }

            const availableSlots =
                MAX_PHOTOS - selectedFiles.length;

            let filesToAdd = validFiles;

            if (validFiles.length > availableSlots) {

                filesToAdd = validFiles.slice(0, availableSlots);

                showPhotoError(
                    "You can upload a maximum of " +
                    MAX_PHOTOS + " photos."
                );

            }

            selectedFiles = selectedFiles.concat(filesToAdd);

            syncFileInput();
            renderPhotoPreviews();

        }


        if (choosePhotosBtn && photoInput) {

            choosePhotosBtn.addEventListener("click", function () {

                if (selectedFiles.length >= MAX_PHOTOS) {

                    showPhotoError(
                        "You can upload a maximum of " +
                        MAX_PHOTOS + " photos."
                    );

                    return;

                }

                photoInput.click();

            });

            photoInput.addEventListener("change", function (event) {

                if (event.target.files && event.target.files.length) {
                    addFiles(event.target.files);
                }

                /*
                 * Reset the native input's own file list so the
                 * same file can be re-selected later if removed;
                 * our own selectedFiles array remains the source
                 * of truth and stays synced via DataTransfer.
                 */

                photoInput.value = "";
                syncFileInput();

            });

        }


        refreshPhotoCount();


        /* =================================================
           FORM VALIDATION + DOUBLE-SUBMIT PREVENTION
           ================================================= */

        if (reportForm) {

            reportForm.addEventListener("submit", function (event) {

                let hasError = false;

                const missingItems = [];

                const disasterTypeField =
                    document.getElementById("id_disaster_type");

                const descriptionField =
                    document.getElementById("id_description");

                [
                    disasterTypeField,
                    descriptionField
                ].forEach(function (field) {

                    if (field) {
                        field.classList.remove("ri-invalid");
                    }

                });

                if (disasterTypeField && !disasterTypeField.value) {

                    disasterTypeField.classList.add("ri-invalid");
                    missingItems.push("Disaster Type");
                    hasError = true;

                }

                if (
                    descriptionField &&
                    descriptionField.value.trim().length < 10
                ) {

                    descriptionField.classList.add("ri-invalid");
                    missingItems.push(
                        "Incident Description (at least 10 characters)"
                    );
                    hasError = true;

                }

                if (incidentStartDateField) {

                    incidentStartDateField.classList.remove(
                        "ri-invalid"
                    );

                    if (!incidentStartDateField.value) {

                        incidentStartDateField.classList.add(
                            "ri-invalid"
                        );
                        missingItems.push("Incident Start Date & Time");
                        hasError = true;

                    } else if (
                        new Date(incidentStartDateField.value) >
                        new Date()
                    ) {

                        incidentStartDateField.classList.add(
                            "ri-invalid"
                        );
                        missingItems.push(
                            "Incident Start Date & Time " +
                            "(cannot be in the future)"
                        );
                        hasError = true;

                    }

                }

                clearSeverityError();

                if (severityGrid) {

                    const severitySelected =
                        severityGrid.querySelector(
                            "input[name='reported_severity']:checked"
                        );

                    if (!severitySelected) {

                        severityGrid.classList.add("ri-invalid");

                        if (severityError) {

                            severityError.textContent =
                                "Please select the incident severity.";

                        }

                        missingItems.push("Reported Severity");
                        hasError = true;

                    }

                }

                if (
                    !latitudeInput || !latitudeInput.value ||
                    !longitudeInput || !longitudeInput.value
                ) {

                    setStatus(
                        "Please select the incident location on the map.",
                        "error"
                    );

                    missingItems.push("Incident Location");
                    hasError = true;

                }

                if (selectedFiles.length > MAX_PHOTOS) {

                    showPhotoError(
                        "You can upload a maximum of " +
                        MAX_PHOTOS + " photos."
                    );

                    missingItems.push(
                        "Photos (maximum " + MAX_PHOTOS + ")"
                    );
                    hasError = true;

                }

                /* =============================================
                   VALIDATION SUMMARY BANNER
                   Lists only the items that actually failed, so
                   the citizen doesn't have to hunt through the
                   whole page to find what's missing.
                   ============================================= */

                if (validationAlert && validationAlertList) {

                    if (hasError) {

                        validationAlertList.innerHTML = "";

                        missingItems.forEach(function (item) {

                            const listItem =
                                document.createElement("li");

                            listItem.textContent = item;

                            validationAlertList.appendChild(listItem);

                        });

                        validationAlert.style.display = "";

                        validationAlert.scrollIntoView({
                            behavior: "smooth",
                            block: "start"
                        });

                    } else {

                        validationAlert.style.display = "none";

                    }

                }

                if (hasError) {

                    event.preventDefault();
                    return;

                }

                if (submitReportBtn) {

                    submitReportBtn.disabled = true;

                    submitReportBtn.textContent =
                        "Submitting…";

                }

            });

        }

    });

})();