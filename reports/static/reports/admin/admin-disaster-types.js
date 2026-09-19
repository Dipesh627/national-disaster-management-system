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
       ===================================================== */

    const deleteModal =
        document.getElementById('dtDeleteModal');

    if (!deleteModal) {
        return;
    }


    const deleteForms =
        document.querySelectorAll('.dt-delete-form');

    const typeNameElement =
        document.getElementById('dtDeleteTypeName');

    const usageNote =
        document.getElementById('dtDeleteUsageNote');

    const confirmDeleteButton =
        document.getElementById('dtConfirmDelete');

    const closeButtons =
        deleteModal.querySelectorAll('[data-modal-close]');


    let pendingDeleteForm = null;
    let lastDeleteTrigger = null;


    function openDeleteModal(form) {

        pendingDeleteForm = form;
        lastDeleteTrigger =
            form.querySelector('button[type="submit"]');

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


        deleteModal.hidden = false;

        deleteModal.setAttribute(
            'aria-hidden',
            'false'
        );

        document.body.classList.add(
            'dt-modal-open'
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
            'dt-modal-open'
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