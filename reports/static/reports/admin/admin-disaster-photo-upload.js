'use strict';

/* =========================================================
   NDMS ADMIN — OFFICIAL DISASTER PHOTO UPLOAD PREVIEW

   Client-side preview/remove for the "Official Disaster
   Photos" multi-file picker on the manual Add Disaster page
   only (reports/admin/disaster_form.html — the section, and
   this script, are never rendered when editing a disaster or
   creating one from a verified report).

   This is purely a UX convenience. The server independently
   validates every uploaded file's type, size, and genuineness
   regardless of what runs here (see
   AdminDisasterForm.clean_official_photos in reports/forms.py)
   — nothing about that validation depends on this script.

   Native <input type="file" multiple> has no built-in way to
   remove a single previously-selected file once chosen, so
   this keeps its own running list of File objects and rebuilds
   the input's FileList (via DataTransfer) whenever a photo is
   added or removed, so the form always submits exactly the
   files still shown in the preview grid.
   ========================================================= */

document.addEventListener('DOMContentLoaded', function () {

    const fileInput =
        document.getElementById('id_official_photos');

    const previewGrid =
        document.getElementById('dsPhotoUploadPreviewGrid');

    const errorElement =
        document.getElementById('dsPhotoUploadError');

    if (!fileInput || !previewGrid) {
        return;
    }

    const ALLOWED_TYPES = [
        'image/jpeg',
        'image/png',
        'image/webp',
    ];

    const MAX_PHOTOS = parseInt(
        fileInput.dataset.maxPhotos, 10
    ) || 10;

    const MAX_SIZE_BYTES = parseInt(
        fileInput.dataset.maxSizeBytes, 10
    ) || (8 * 1024 * 1024);


    // Running selection, kept in sync with fileInput.files on
    // every add/remove via syncInputFiles() below.
    let selectedFiles = [];


    function showError(message) {

        if (!errorElement) {
            return;
        }

        errorElement.textContent = message;
        errorElement.hidden = !message;
    }


    function syncInputFiles() {

        // Rebuilds the actual <input>'s FileList from our own
        // in-memory array — the only way to make a native file
        // input "forget" one previously-chosen file while
        // keeping the rest.
        const dataTransfer = new DataTransfer();

        selectedFiles.forEach(function (file) {
            dataTransfer.items.add(file);
        });

        fileInput.files = dataTransfer.files;
    }


    function renderPreviews() {

        previewGrid.innerHTML = '';

        selectedFiles.forEach(function (file, index) {

            const item = document.createElement('div');
            item.className = 'ds-photo-upload-item';

            const thumb = document.createElement('span');
            thumb.className = 'ds-photo-upload-thumb';

            const img = document.createElement('img');
            img.alt = file.name;
            img.loading = 'lazy';

            const objectUrl = URL.createObjectURL(file);
            img.src = objectUrl;

            img.addEventListener('load', function () {
                URL.revokeObjectURL(objectUrl);
            });

            thumb.appendChild(img);

            const removeButton = document.createElement('button');
            removeButton.type = 'button';
            removeButton.className = 'ds-photo-upload-remove';
            removeButton.setAttribute(
                'aria-label',
                'Remove ' + file.name
            );
            removeButton.innerHTML =
                '<svg viewBox="0 0 24 24" aria-hidden="true" '
                + 'fill="none" stroke="currentColor" '
                + 'stroke-width="2.4" stroke-linecap="round">'
                + '<path d="M6 6l12 12"></path>'
                + '<path d="M18 6L6 18"></path>'
                + '</svg>';

            removeButton.addEventListener('click', function () {

                selectedFiles.splice(index, 1);

                syncInputFiles();
                renderPreviews();

            });

            item.appendChild(thumb);
            item.appendChild(removeButton);

            previewGrid.appendChild(item);

        });

    }


    function isAlreadySelected(candidate) {

        return selectedFiles.some(function (existing) {

            return (
                existing.name === candidate.name
                && existing.size === candidate.size
                && existing.lastModified === candidate.lastModified
            );

        });

    }


    fileInput.addEventListener('change', function () {

        const newlyChosen = Array.from(fileInput.files || []);

        if (newlyChosen.length === 0) {
            return;
        }

        showError('');

        let rejectionMessage = '';

        newlyChosen.forEach(function (file) {

            if (rejectionMessage) {
                return;
            }

            if (ALLOWED_TYPES.indexOf(file.type) === -1) {
                rejectionMessage =
                    'Please choose only JPG, PNG, or WEBP images.';
                return;
            }

            if (file.size > MAX_SIZE_BYTES) {
                rejectionMessage =
                    '"' + file.name + '" is too large. Maximum '
                    + 'size is 8MB per photo.';
                return;
            }

            if (isAlreadySelected(file)) {
                return;
            }

            selectedFiles.push(file);

        });

        if (selectedFiles.length > MAX_PHOTOS) {

            rejectionMessage =
                'You can upload up to ' + MAX_PHOTOS
                + ' photos at once.';

            selectedFiles = selectedFiles.slice(0, MAX_PHOTOS);

        }

        if (rejectionMessage) {
            showError(rejectionMessage);
        }

        syncInputFiles();
        renderPreviews();

    });

});