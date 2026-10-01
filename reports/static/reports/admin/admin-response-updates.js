'use strict';

document.addEventListener('DOMContentLoaded', function () {

    /* =====================================================
       DELETE CONFIRMATION
       Dialog behaviour lives in admin-confirm-modal.js; only the
       Response Updates context lines (disaster / agency names)
       are handled here.
       ===================================================== */

    const deleteModal =
        document.getElementById('ruDeleteModal');

    if (!deleteModal || !window.NDMSConfirmModal) {
        return;
    }


    const deleteContext =
        document.getElementById('ruDeleteContext');

    const disasterNameElement =
        document.getElementById('ruDeleteDisasterName');

    const agencyNameElement =
        document.getElementById('ruDeleteAgencyName');


    window.NDMSConfirmModal.init({

        modal: deleteModal,

        forms: document.querySelectorAll('.ru-delete-form'),

        confirmButton:
            document.getElementById('ruConfirmDelete'),

        bodyClass: 'ru-modal-open',

        onOpen: function (form) {

            const disasterName =
                form.dataset.disaster || '';

            const agencyName =
                form.dataset.agency || '';

            const hasContext =
                Boolean(disasterName) || Boolean(agencyName);


            if (disasterNameElement) {
                disasterNameElement.textContent = disasterName;
            }

            if (agencyNameElement) {
                agencyNameElement.textContent = agencyName;
            }

            if (deleteContext) {
                deleteContext.hidden = !hasContext;
            }

        }

    });

});
