'use strict';

/* =========================================================
   NDMS ADMIN — DISASTER CONFIRMATION MODAL

   Generic confirm-before-submit helper for disaster status
   changes. Any form carrying the .ds-close-form class is
   intercepted and routed through the #dsCloseModal dialog.

   Each form may customise the dialog through data-* attributes:

     data-title          — the disaster name
     data-confirm-title  — dialog heading
     data-confirm-body   — dialog body text
     data-confirm-label  — confirm button label

   When those optional attributes are absent the original
   "Close Disaster?" wording is used, so existing markup keeps
   behaving exactly as before.
   ========================================================= */

document.addEventListener('DOMContentLoaded', function () {

    /* =====================================================
       CONFIRMATION MODAL
       ===================================================== */

    const closeModal =
        document.getElementById('dsCloseModal');

    if (!closeModal) {
        return;
    }


    const closeForms =
        document.querySelectorAll('.ds-close-form');

    const titleElement =
        document.getElementById('dsCloseDisasterTitle');

    const headingElement =
        document.getElementById('dsCloseModalTitle');

    const bodyElement =
        document.getElementById('dsCloseModalBody');

    const confirmCloseButton =
        document.getElementById('dsConfirmClose');

    const confirmLabelElement =
        document.getElementById('dsConfirmCloseLabel');

    const closeButtons =
        closeModal.querySelectorAll('[data-modal-close]');


    // Remember the stock wording so a form without the optional
    // data-confirm-* attributes still gets the original dialog.
    const defaultHeading =
        headingElement ? headingElement.textContent : '';

    const defaultBody =
        bodyElement ? bodyElement.innerHTML : '';

    const defaultConfirmLabel =
        confirmLabelElement ? confirmLabelElement.textContent : '';


    let pendingCloseForm = null;
    let lastCloseTrigger = null;


    function openCloseModal(form) {

        pendingCloseForm = form;
        lastCloseTrigger =
            form.querySelector('button[type="submit"]');

        const disasterTitle =
            form.dataset.title || 'this disaster';

        if (headingElement) {

            headingElement.textContent =
                form.dataset.confirmTitle || defaultHeading;

        }

        if (bodyElement) {

            if (form.dataset.confirmBody) {

                // textContent, never innerHTML — the disaster
                // title is user-supplied data and must never be
                // parsed as markup.
                bodyElement.textContent = form.dataset.confirmBody;

            } else {

                bodyElement.innerHTML = defaultBody;

                if (titleElement) {
                    titleElement.textContent = disasterTitle;
                }

            }

        }

        if (confirmLabelElement) {

            confirmLabelElement.textContent =
                form.dataset.confirmLabel || defaultConfirmLabel;

        }

        closeModal.hidden = false;

        closeModal.setAttribute('aria-hidden', 'false');

        document.body.classList.add('ds-modal-open');

        if (confirmCloseButton) {

            window.requestAnimationFrame(function () {
                confirmCloseButton.focus();
            });

        }

    }


    function closeCloseModal() {

        closeModal.hidden = true;

        closeModal.setAttribute('aria-hidden', 'true');

        document.body.classList.remove('ds-modal-open');

        pendingCloseForm = null;

        if (lastCloseTrigger) {

            window.requestAnimationFrame(function () {
                lastCloseTrigger.focus();
            });

        }

        lastCloseTrigger = null;
    }


    closeForms.forEach(function (form) {

        form.addEventListener('submit', function (event) {

            event.preventDefault();

            openCloseModal(form);

        });

    });


    closeButtons.forEach(function (button) {

        button.addEventListener('click', function () {
            closeCloseModal();
        });

    });


    if (confirmCloseButton) {

        confirmCloseButton.addEventListener('click', function () {

            if (!pendingCloseForm) {
                return;
            }

            const formToSubmit = pendingCloseForm;

            pendingCloseForm = null;

            formToSubmit.submit();

        });

    }


    document.addEventListener('keydown', function (event) {

        if (event.key === 'Escape' && !closeModal.hidden) {
            closeCloseModal();
        }

    });

});