'use strict';

document.addEventListener('DOMContentLoaded', function () {

    /* =====================================================
       DELETE CONFIRMATION
       Dialog behaviour lives in admin-confirm-modal.js; only the
       Emergency Agencies wording and usage fields are handled here.
       ===================================================== */

    const deleteModal =
        document.getElementById('eaDeleteModal');

    if (!deleteModal || !window.NDMSConfirmModal) {
        return;
    }


    const agencyNameElement =
        document.getElementById('eaDeleteAgencyName');

    const usageNote =
        document.getElementById('eaDeleteUsageNote');


    window.NDMSConfirmModal.init({

        modal: deleteModal,

        forms: document.querySelectorAll('.ea-delete-form'),

        confirmButton:
            document.getElementById('eaConfirmDelete'),

        bodyClass: 'ea-modal-open',

        onOpen: function (form) {

            const agencyName =
                form.dataset.name || 'this emergency agency';

            const updates =
                Number.parseInt(
                    form.dataset.updates || '0',
                    10
                );

            const hasUsage =
                Number.isFinite(updates)
                && updates > 0;


            if (agencyNameElement) {
                agencyNameElement.textContent = agencyName;
            }


            if (usageNote) {
                usageNote.hidden = !hasUsage;
            }

        }

    });

});
