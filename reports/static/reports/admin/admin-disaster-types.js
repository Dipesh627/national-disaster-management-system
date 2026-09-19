'use strict';

document.addEventListener('DOMContentLoaded', function () {

    /* =====================================================
       DESCRIPTION CHARACTER COUNT
       ===================================================== */

    const description =
        document.querySelector('.dt-form-textarea');

    const descriptionCount =
        document.getElementById('dtDescriptionCount');

    function updateDescriptionCount() {

        if (!description || !descriptionCount) {
            return;
        }

        const count = description.value.length;

        descriptionCount.textContent =
            `${count} ${count === 1 ? 'character' : 'characters'}`;
    }

    if (description && descriptionCount) {

        updateDescriptionCount();

        description.addEventListener(
            'input',
            updateDescriptionCount
        );
    }


    /* =====================================================
       DELETE CONFIRMATION
       Dialog behaviour lives in admin-confirm-modal.js; only the
       Disaster Types wording and usage fields are handled here.
       ===================================================== */

    const deleteModal =
        document.getElementById('dtDeleteModal');

    if (!deleteModal || !window.NDMSConfirmModal) {
        return;
    }


    const typeNameElement =
        document.getElementById('dtDeleteTypeName');

    const usageNote =
        document.getElementById('dtDeleteUsageNote');


    window.NDMSConfirmModal.init({

        modal: deleteModal,

        forms: document.querySelectorAll('.dt-delete-form'),

        confirmButton:
            document.getElementById('dtConfirmDelete'),

        bodyClass: 'dt-modal-open',

        onOpen: function (form) {

            const typeName =
                form.dataset.name || 'this disaster type';

            const reports =
                Number.parseInt(
                    form.dataset.reports || '0',
                    10
                );

            const disasters =
                Number.parseInt(
                    form.dataset.disasters || '0',
                    10
                );


            const hasUsage =
                (
                    Number.isFinite(reports)
                    && reports > 0
                )
                ||
                (
                    Number.isFinite(disasters)
                    && disasters > 0
                );


            if (typeNameElement) {
                typeNameElement.textContent = typeName;
            }


            if (usageNote) {
                usageNote.hidden = !hasUsage;
            }

        }

    });

});