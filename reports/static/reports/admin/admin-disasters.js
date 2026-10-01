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

   Open / close / Escape / focus / confirm-submit behaviour lives in
   admin-confirm-modal.js (load it first); only the wording swap
   below is specific to this dialog.
   ========================================================= */

document.addEventListener('DOMContentLoaded', function () {

    /* =====================================================
       CONFIRMATION MODAL
       ===================================================== */

    const closeModal =
        document.getElementById('dsCloseModal');

    if (!closeModal || !window.NDMSConfirmModal) {
        return;
    }


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


    // Remember the stock wording so a form without the optional
    // data-confirm-* attributes still gets the original dialog.
    const defaultHeading =
        headingElement ? headingElement.textContent : '';

    const defaultBody =
        bodyElement ? bodyElement.innerHTML : '';

    const defaultConfirmLabel =
        confirmLabelElement ? confirmLabelElement.textContent : '';


    window.NDMSConfirmModal.init({

        modal: closeModal,

        forms: document.querySelectorAll('.ds-close-form'),

        confirmButton: confirmCloseButton,

        bodyClass: 'ds-modal-open',

        onOpen: function (form) {

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

        }

    });

});
