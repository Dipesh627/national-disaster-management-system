'use strict';

document.addEventListener('DOMContentLoaded', function () {

    /* =====================================================
       DELETE CONFIRMATION
       ===================================================== */

    const deleteModal =
        document.getElementById('eaDeleteModal');

    if (!deleteModal) {
        return;
    }


    const deleteForms =
        document.querySelectorAll('.ea-delete-form');

    const agencyNameElement =
        document.getElementById('eaDeleteAgencyName');

    const usageNote =
        document.getElementById('eaDeleteUsageNote');

    const confirmDeleteButton =
        document.getElementById('eaConfirmDelete');

    const closeButtons =
        deleteModal.querySelectorAll('[data-modal-close]');


    let pendingDeleteForm = null;
    let lastDeleteTrigger = null;


    function openDeleteModal(form) {

        pendingDeleteForm = form;
        lastDeleteTrigger =
            form.querySelector('button[type="submit"]');

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


        deleteModal.hidden = false;

        deleteModal.setAttribute(
            'aria-hidden',
            'false'
        );

        document.body.classList.add(
            'ea-modal-open'
        );


        if (confirmDeleteButton) {

            window.requestAnimationFrame(
                function () {
                    confirmDeleteButton.focus();
                }
            );

        }

    }


    function closeDeleteModal() {

        deleteModal.hidden = true;

        deleteModal.setAttribute(
            'aria-hidden',
            'true'
        );

        document.body.classList.remove(
            'ea-modal-open'
        );

        pendingDeleteForm = null;


        if (lastDeleteTrigger) {

            window.requestAnimationFrame(
                function () {
                    lastDeleteTrigger.focus();
                }
            );

        }

        lastDeleteTrigger = null;
    }


    deleteForms.forEach(function (form) {

        form.addEventListener(
            'submit',
            function (event) {

                event.preventDefault();

                openDeleteModal(form);

            }
        );

    });


    closeButtons.forEach(function (button) {

        button.addEventListener(
            'click',
            function () {
                closeDeleteModal();
            }
        );

    });


    if (confirmDeleteButton) {

        confirmDeleteButton.addEventListener(
            'click',
            function () {

                if (!pendingDeleteForm) {
                    return;
                }

                const formToSubmit =
                    pendingDeleteForm;

                pendingDeleteForm = null;

                formToSubmit.submit();

            }
        );

    }


    document.addEventListener(
        'keydown',
        function (event) {

            if (
                event.key === 'Escape'
                &&
                !deleteModal.hidden
            ) {
                closeDeleteModal();
            }

        }
    );

});
