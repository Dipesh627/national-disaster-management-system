/* =========================================================
   NDMS — DISASTER UNREAD RED-DOT INDICATOR
   VIEW DISASTERS AUTO-READ

   Fires exactly one safe, CSRF-protected POST to
   'mark_disaster_alerts_read' when a signed-in citizen opens
   View Disasters, so their unread DISASTER_ALERT notification(s)
   become read and the red dot clears on the next page render
   (Home navbar, Disasters dropdown, Dashboard sidebar all read
   the same shared has_unread_disaster_alert context value).

   Only runs at all when the server has already determined there
   is something to mark read: disaster_list.html only renders the
   data-mark-disaster-alerts-read="1" attribute (and the read
   endpoint URL) on <body> for an authenticated citizen who
   currently has an unread Disaster Alert. Anonymous visitors and
   Admin accounts never get that attribute, so this script is a
   silent no-op for them.

   Does not touch report/general notifications, does not affect
   any other citizen's read state, and never runs more than once
   per page load.
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        var body =
            document.body;

        if (
            !body ||
            body.getAttribute("data-mark-disaster-alerts-read") !== "1"
        ) {
            return;
        }

        var readUrl =
            body.getAttribute("data-mark-disaster-alerts-read-url");

        if (!readUrl) {
            return;
        }


        // -----------------------------------------------------
        // CSRF TOKEN (Django's documented cookie-based pattern —
        // no visible form/hidden input is needed for this
        // background call).
        // -----------------------------------------------------

        function getCookie(name) {

            var cookieValue = null;

            if (document.cookie && document.cookie !== "") {

                var cookies = document.cookie.split(";");

                for (var i = 0; i < cookies.length; i++) {

                    var cookie = cookies[i].trim();

                    if (cookie.substring(0, name.length + 1) === (name + "=")) {

                        cookieValue = decodeURIComponent(
                            cookie.substring(name.length + 1)
                        );

                        break;

                    }

                }

            }

            return cookieValue;

        }

        var csrfToken =
            getCookie("csrftoken");

        if (!csrfToken) {
            // No token available — never attempt an unprotected
            // mutation; the red dot simply stays until a later
            // successful attempt (e.g. next page load).
            return;
        }


        // -----------------------------------------------------
        // SAFE, CSRF-PROTECTED POST
        // (fire-and-forget: this page has already rendered
        // correctly regardless of the outcome)
        // -----------------------------------------------------

        fetch(
            readUrl,
            {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": csrfToken
                }
            }
        ).catch(
            function (error) {

                // Never break the page for this — the existing
                // Disaster Alert(s) simply remain unread until
                // the next successful attempt.

                if (window.console && window.console.error) {
                    console.error(
                        "NDMS: could not mark Disaster Alerts as read.",
                        error
                    );
                }

            }
        );

    }
);