'use strict';

/* =========================================================
   NDMS ADMIN — SHARED CONFIRM-BEFORE-SUBMIT MODAL CONTROLLER

   Behaviour common to the Admin confirmation dialogs:

     - a matching form's submit is intercepted and opens the
       dialog instead
     - any [data-modal-close] element inside the dialog closes it
     - Escape closes it while it is open
     - focus moves to the confirm button on open and returns to
       the form's submit button on close
     - the confirm button submits the original form (so its CSRF
       token and hidden fields are sent unchanged)

   Everything page-specific — which text or warning to show,
   which data-* attributes to read — belongs in the onOpen
   callback supplied by the page script.

   Usage:

     NDMSConfirmModal.init({
         modal:         document.getElementById('...'),   // required
         forms:         document.querySelectorAll('...'), // required
         confirmButton: document.getElementById('...'),
         bodyClass:     'page-modal-open',                // optional
         onOpen:        function (form) { ... }           // optional
     });

   Load this file before the page script that calls it. Call
   init() once per dialog; each call registers one Escape
   listener.
   ========================================================= */

(function (window, document) {

    function init(config) {

        const modal = config && config.modal;

        if (!modal) {
            return null;
        }

        const forms = config.forms || [];
        const confirmButton = config.confirmButton || null;
        const bodyClass = config.bodyClass || '';
        const onOpen = config.onOpen;

        const closeButtons =
            modal.querySelectorAll('[data-modal-close]');

        let pendingForm = null;
        let lastTrigger = null;


        function open(form) {

            pendingForm = form;
            lastTrigger =
                form.querySelector('button[type="submit"]');

            if (typeof onOpen === 'function') {
                onOpen(form);
            }

            modal.hidden = false;

            modal.setAttribute('aria-hidden', 'false');

            if (bodyClass) {
                document.body.classList.add(bodyClass);
            }

            if (confirmButton) {

                window.requestAnimationFrame(function () {
                    confirmButton.focus();
                });

            }

        }


        function close() {

            modal.hidden = true;

            modal.setAttribute('aria-hidden', 'true');

            if (bodyClass) {
                document.body.classList.remove(bodyClass);
            }

            pendingForm = null;

            const triggerToFocus = lastTrigger;

            if (triggerToFocus) {

                window.requestAnimationFrame(function () {
                    triggerToFocus.focus();
                });

            }

            lastTrigger = null;
        }


        Array.prototype.forEach.call(forms, function (form) {

            form.addEventListener('submit', function (event) {

                event.preventDefault();

                open(form);

            });

        });


        Array.prototype.forEach.call(closeButtons, function (button) {

            button.addEventListener('click', function () {
                close();
            });

        });


        if (confirmButton) {

            confirmButton.addEventListener('click', function () {

                if (!pendingForm) {
                    return;
                }

                const formToSubmit = pendingForm;

                pendingForm = null;

                formToSubmit.submit();

            });

        }


        document.addEventListener('keydown', function (event) {

            if (event.key === 'Escape' && !modal.hidden) {
                close();
            }

        });


        return {
            open: open,
            close: close
        };

    }


    window.NDMSConfirmModal = {
        init: init
    };

})(window, document);
