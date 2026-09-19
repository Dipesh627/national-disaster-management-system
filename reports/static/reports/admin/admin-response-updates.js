'use strict';

document.addEventListener('DOMContentLoaded', function () {

    /* =====================================================
       DELETE CONFIRMATION
       ===================================================== */

    const deleteModal =
        document.getElementById('ruDeleteModal');

    if (!deleteModal) {
        return;
    }


    const deleteForms =
        document.querySelectorAll('.ru-delete-form');

    const deleteContext =
        document.getElementById('ruDeleteContext');

    const disasterNameElement =
        document.getElementById('ruDeleteDisasterName');

    const agencyNameElement =
        document.getElementById('ruDeleteAgencyName');

    const confirmDeleteButton =
        document.getElementById('ruConfirmDelete');

    const closeButtons =
        deleteModal.querySelectorAll('[data-modal-close]');


    let pendingDeleteForm = null;
    let lastDeleteTrigger = null;


    function openDeleteModal(form) {

        pendingDeleteForm = form;
        lastDeleteTrigger =
            form.querySelector('button[type="submit"]');

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


        deleteModal.hidden = false;

        deleteModal.setAttribute(
            'aria-hidden',
            'false'
        );

        document.body.classList.add(
            'ru-modal-open'
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
            'ru-modal-open'
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
