/* =========================================================
   NDMS — MY PROFILE JAVASCRIPT

   NOTE: Mobile sidebar toggling and the notification dropdown
   are already handled by dashboard.js, which this page also
   loads (same #dashboardSidebar / #notificationDropdown IDs).
   This file only adds the Personal Information edit/cancel
   interaction that is specific to the Profile page.
   ========================================================= */


document.addEventListener("DOMContentLoaded", function () {


    /* =====================================================
       ELEMENTS
       ===================================================== */

    const editButton =
        document.getElementById("pfEditButton");

    const cancelButton =
        document.getElementById("pfCancelButton");

    const editForm =
        document.getElementById("pfEditForm");


    /* =====================================================
       EDIT / VIEW MODE TOGGLE
       (view/edit are two DOM blocks; a class on <body>
       swaps which one is visible, so no data is lost when
       switching back and forth before saving)
       ===================================================== */

    function enterEditMode() {

        document.body.classList.add("pf-edit-mode");

        if (editButton) {
            editButton.setAttribute("aria-expanded", "true");
        }

        const firstField =
            editForm
                ? editForm.querySelector("#id_first_name")
                : null;

        if (firstField) {
            firstField.focus();
        }

    }


    function exitEditMode() {

        document.body.classList.remove("pf-edit-mode");

        if (editButton) {
            editButton.setAttribute("aria-expanded", "false");
        }

    }


    if (editButton) {

        editButton.addEventListener("click", function () {
            enterEditMode();
        });

    }


    if (cancelButton) {

        cancelButton.addEventListener("click", function () {

            if (editForm) {
                editForm.reset();
            }

            exitEditMode();

        });

    }


    /* =====================================================
       AUTO-OPEN EDIT MODE ON VALIDATION ERRORS
       (if the form was submitted with invalid data, Django
       re-renders this same page with field errors — open
       edit mode automatically so the errors are visible)
       ===================================================== */

    const hasFieldErrors =
        editForm
            ? editForm.querySelector(".pf-field-error")
            : null;

    if (hasFieldErrors) {
        enterEditMode();
    }


    /* =====================================================
       DISMISS DJANGO MESSAGES
       (same close behaviour already used on the Home page)
       ===================================================== */

    const messageCloseButtons =
        document.querySelectorAll(".message-close");

    messageCloseButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            const message = button.closest(".django-message");

            if (message) {
                message.remove();
            }

        });

    });


    /* =====================================================
       AVATAR EDIT POPOVER
       (camera badge on the header avatar -> Take Photo /
       Choose from Gallery / Remove Photo)
       ===================================================== */

    const avatarEditWrapper =
        document.getElementById("pfAvatarEditWrapper");

    const avatarEditBadge =
        document.getElementById("pfAvatarEditBadge");

    const avatarPopover =
        document.getElementById("pfAvatarPopover");

    const takePhotoBtn =
        document.getElementById("pfTakePhotoBtn");

    const chooseGalleryBtn =
        document.getElementById("pfChooseGalleryBtn");

    const removePhotoBtn =
        document.getElementById("pfRemovePhotoBtn");

    const removePhotoForm =
        document.getElementById("pfRemovePhotoForm");

    const viewPhotoBtn =
        document.getElementById("pfViewPhotoBtn");

    const viewPhotoModal =
        document.getElementById("pfViewPhotoModal");

    const viewPhotoClose =
        document.getElementById("pfViewPhotoClose");


    function openAvatarPopover() {

        if (!avatarPopover) {
            return;
        }

        avatarPopover.classList.add("show");

        if (avatarEditBadge) {
            avatarEditBadge.setAttribute("aria-expanded", "true");
        }

    }


    function closeAvatarPopover() {

        if (!avatarPopover) {
            return;
        }

        avatarPopover.classList.remove("show");

        if (avatarEditBadge) {
            avatarEditBadge.setAttribute("aria-expanded", "false");
        }

    }


    if (avatarEditBadge) {

        avatarEditBadge.addEventListener("click", function (event) {

            event.stopPropagation();

            if (avatarPopover && avatarPopover.classList.contains("show")) {
                closeAvatarPopover();
            } else {
                openAvatarPopover();
            }

        });

    }


    document.addEventListener("click", function (event) {

        if (
            avatarEditWrapper &&
            avatarPopover &&
            avatarPopover.classList.contains("show") &&
            !avatarEditWrapper.contains(event.target)
        ) {
            closeAvatarPopover();
        }

    });


    document.addEventListener("keydown", function (event) {

        if (
            event.key === "Escape" &&
            avatarPopover &&
            avatarPopover.classList.contains("show")
        ) {
            closeAvatarPopover();
        }

    });


    /* =====================================================
       VIEW PHOTO — LIGHTBOX
       Only ever wired up when the elements exist — the modal
       markup itself is only rendered by the template when the
       citizen already has a real avatar, so this is a no-op
       (and "View Photo" never appears in the popover) for the
       default-avatar case.
       ===================================================== */

    function openViewPhotoModal() {

        if (!viewPhotoModal) {
            return;
        }

        viewPhotoModal.classList.add("show");

        if (viewPhotoClose) {
            viewPhotoClose.focus();
        }

    }


    function closeViewPhotoModal() {

        if (!viewPhotoModal) {
            return;
        }

        viewPhotoModal.classList.remove("show");

    }


    if (viewPhotoBtn) {

        viewPhotoBtn.addEventListener("click", function () {

            closeAvatarPopover();

            openViewPhotoModal();

        });

    }


    if (viewPhotoClose) {

        viewPhotoClose.addEventListener("click", function () {
            closeViewPhotoModal();
        });

    }


    if (viewPhotoModal) {

        viewPhotoModal.addEventListener("click", function (event) {

            if (event.target === viewPhotoModal) {
                closeViewPhotoModal();
            }

        });

    }


    document.addEventListener("keydown", function (event) {

        if (
            event.key === "Escape" &&
            viewPhotoModal &&
            viewPhotoModal.classList.contains("show")
        ) {
            closeViewPhotoModal();
        }

    });


    /* =====================================================
       CHANGE PHOTO MODAL
       (same show/hide pattern already used by the report
       photo modal on report_detail.html)
       ===================================================== */

    const photoModal =
        document.getElementById("pfChangePhotoModal");

    const closePhotoBtn =
        document.getElementById("pfChangePhotoClose");

    const cancelPhotoBtn =
        document.getElementById("pfCancelPhotoBtn");

    const photoForm =
        document.getElementById("pfChangePhotoForm");

    const fileInput =
        document.getElementById("id_avatar");

    const choosePhotoLabel =
        document.getElementById("pfChoosePhotoLabel");

    const fileNameLabel =
        document.getElementById("pfPhotoFileName");

    const previewImage =
        document.getElementById("pfPhotoPreviewImage");

    const previewInitials =
        document.getElementById("pfPhotoPreviewInitials");

    const previewAvatarBlock =
        document.getElementById("pfPhotoPreviewAvatar");

    const saveButton =
        document.getElementById("pfSavePhotoBtn");

    const cropShell =
        document.getElementById("pfCropShell");

    const cropStage =
        document.getElementById("pfCropStage");

    const cropImage =
        document.getElementById("pfCropImage");

    const cropZoom =
        document.getElementById("pfCropZoom");

    const cropReset =
        document.getElementById("pfCropReset");

    const outputCanvas =
        document.getElementById("pfCropOutputCanvas");


    const MAX_AVATAR_BYTES = 5 * 1024 * 1024;

    const ALLOWED_AVATAR_TYPES = [
        "image/jpeg",
        "image/png",
    ];

    // Fixed resolution the final, cropped photo is rendered at
    // before upload — independent of how big the crop circle
    // is drawn on screen. Matches the Admin Profile crop stage.
    const CROP_OUTPUT_SIZE = 480;

    // Holds everything needed to redraw and re-crop the photo
    // the citizen currently has open in the crop stage. Null
    // whenever no new photo is being positioned.
    let cropState = null;

    // Tracks an in-progress drag on the crop stage.
    let cropDragState = null;


    /* =====================================================
       PHOTO CROP + ZOOM
       (same admin-style implementation used on the Admin
       Profile page — the citizen drags to reposition and
       uses the slider to zoom the photo inside a fixed
       circular stage. On save, exactly what's visible in
       that circle is rendered onto an offscreen canvas at a
       fixed resolution, turned into a File, and attached to
       the existing #id_avatar input — so AvatarUploadForm /
       change_photo() still just receive a normal image
       upload and needed no backend changes.)
       ===================================================== */

    function getCropStageSize() {

        if (cropStage && cropStage.clientWidth) {
            return cropStage.clientWidth;
        }

        return 220;

    }


    function clampCropPan() {

        if (!cropState) {
            return;
        }

        const scaledWidth =
            cropState.naturalWidth * cropState.scale;

        const scaledHeight =
            cropState.naturalHeight * cropState.scale;

        const maxX =
            Math.max(0, (scaledWidth - cropState.stageSize) / 2);

        const maxY =
            Math.max(0, (scaledHeight - cropState.stageSize) / 2);

        cropState.x = Math.min(maxX, Math.max(-maxX, cropState.x));
        cropState.y = Math.min(maxY, Math.max(-maxY, cropState.y));

    }


    function applyCropTransform() {

        if (!cropState || !cropImage) {
            return;
        }

        const scaledWidth =
            cropState.naturalWidth * cropState.scale;

        const scaledHeight =
            cropState.naturalHeight * cropState.scale;

        cropImage.style.width = scaledWidth + "px";
        cropImage.style.height = scaledHeight + "px";

        cropImage.style.transform =
            "translate(-50%, -50%) translate(" +
            cropState.x + "px, " + cropState.y + "px)";

    }


    function setCropZoomFromSlider(sliderValue) {

        if (!cropState) {
            return;
        }

        const t = Number(sliderValue) / 100;

        // Slider runs from the "cover" scale (photo just fills
        // the circle, value 0) up to 3x that scale (value 100).
        cropState.scale =
            cropState.minScale + t * (cropState.minScale * 2);

        clampCropPan();
        applyCropTransform();

    }


    function resetCropPosition() {

        if (!cropState) {
            return;
        }

        cropState.scale = cropState.minScale;
        cropState.x = 0;
        cropState.y = 0;

        if (cropZoom) {
            cropZoom.value = 0;
        }

        applyCropTransform();

    }


    function teardownCrop() {

        if (cropState && cropState.objectUrl) {
            URL.revokeObjectURL(cropState.objectUrl);
        }

        cropState = null;
        cropDragState = null;

        if (cropStage) {
            cropStage.classList.remove("is-dragging");
        }

        if (cropShell) {
            cropShell.hidden = true;
        }

        if (previewAvatarBlock) {
            previewAvatarBlock.hidden = false;
        }

        if (cropZoom) {
            cropZoom.value = 0;
        }

    }


    function initCrop(file) {

        const objectUrl = URL.createObjectURL(file);
        const probeImage = new Image();

        probeImage.onload = function () {

            const stageSize = getCropStageSize();

            const minScale = Math.max(
                stageSize / probeImage.naturalWidth,
                stageSize / probeImage.naturalHeight
            );

            cropState = {
                objectUrl: objectUrl,
                naturalWidth: probeImage.naturalWidth,
                naturalHeight: probeImage.naturalHeight,
                stageSize: stageSize,
                minScale: minScale,
                scale: minScale,
                x: 0,
                y: 0,
            };

            if (cropImage) {
                cropImage.src = objectUrl;
            }

            applyCropTransform();

            if (cropZoom) {
                cropZoom.value = 0;
            }

            if (cropShell) {
                cropShell.hidden = false;
            }

            if (previewAvatarBlock) {
                previewAvatarBlock.hidden = true;
            }

            if (saveButton) {
                saveButton.disabled = false;
            }

        };

        probeImage.onerror = function () {

            URL.revokeObjectURL(objectUrl);

            window.alert(
                "Could not read that image. Please try a different photo."
            );

        };

        probeImage.src = objectUrl;

    }


    function renderCroppedBlob(callback) {

        if (!cropState || !cropImage || !outputCanvas || !outputCanvas.getContext) {
            callback(null);
            return;
        }

        outputCanvas.width = CROP_OUTPUT_SIZE;
        outputCanvas.height = CROP_OUTPUT_SIZE;

        const ctx = outputCanvas.getContext("2d");

        if (!ctx) {
            callback(null);
            return;
        }

        // The size, in the original photo's own pixels, of the
        // area currently visible inside the circular stage.
        const visibleWidth = cropState.stageSize / cropState.scale;
        const visibleHeight = cropState.stageSize / cropState.scale;

        // Where that visible area sits within the original photo.
        const centerX =
            cropState.naturalWidth / 2 - cropState.x / cropState.scale;

        const centerY =
            cropState.naturalHeight / 2 - cropState.y / cropState.scale;

        const sourceX = centerX - visibleWidth / 2;
        const sourceY = centerY - visibleHeight / 2;

        ctx.clearRect(0, 0, CROP_OUTPUT_SIZE, CROP_OUTPUT_SIZE);

        ctx.drawImage(
            cropImage,
            sourceX,
            sourceY,
            visibleWidth,
            visibleHeight,
            0,
            0,
            CROP_OUTPUT_SIZE,
            CROP_OUTPUT_SIZE
        );

        if (outputCanvas.toBlob) {

            outputCanvas.toBlob(
                function (blob) {
                    callback(blob);
                },
                "image/jpeg",
                0.92
            );

        } else {

            callback(null);

        }

    }


    function resetPhotoForm() {

        if (photoForm) {
            photoForm.reset();
        }

        if (fileNameLabel) {
            fileNameLabel.textContent = "";
        }

        if (saveButton) {
            saveButton.disabled = true;
        }

        if (previewImage && previewImage.dataset.originalSrc !== undefined) {

            previewImage.src = previewImage.dataset.originalSrc;

            if (!previewImage.dataset.originalSrc) {
                previewImage.hidden = true;
            }

        }

        if (previewInitials) {
            previewInitials.hidden = false;
        }

        teardownCrop();

    }


    function openPhotoModal() {

        if (!photoModal) {
            return;
        }

        photoModal.classList.add("show");

        if (choosePhotoLabel) {
            choosePhotoLabel.hidden = false;
        }

        if (closePhotoBtn) {
            closePhotoBtn.focus();
        }

    }


    function closePhotoModal() {

        if (!photoModal) {
            return;
        }

        photoModal.classList.remove("show");

        resetPhotoForm();

    }


    if (previewImage) {
        previewImage.dataset.originalSrc = previewImage.src || "";
    }


    if (closePhotoBtn) {

        closePhotoBtn.addEventListener("click", function () {
            closePhotoModal();
        });

    }


    if (cancelPhotoBtn) {

        cancelPhotoBtn.addEventListener("click", function () {
            closePhotoModal();
        });

    }


    if (photoModal) {

        photoModal.addEventListener("click", function (event) {

            if (event.target === photoModal) {
                closePhotoModal();
            }

        });

    }


    document.addEventListener("keydown", function (event) {

        if (
            event.key === "Escape" &&
            photoModal &&
            photoModal.classList.contains("show")
        ) {
            closePhotoModal();
        }

    });


    /* -----------------------------------------------------
       DRAG TO REPOSITION
       Pointer events cover mouse, touch and pen with the
       same handlers.
       ----------------------------------------------------- */

    if (cropStage) {

        cropStage.addEventListener("pointerdown", function (event) {

            if (!cropState) {
                return;
            }

            cropDragState = {
                pointerId: event.pointerId,
                startX: event.clientX,
                startY: event.clientY,
                originX: cropState.x,
                originY: cropState.y,
            };

            cropStage.classList.add("is-dragging");

            if (cropStage.setPointerCapture) {
                cropStage.setPointerCapture(event.pointerId);
            }

        });

        cropStage.addEventListener("pointermove", function (event) {

            if (
                !cropDragState ||
                !cropState ||
                cropDragState.pointerId !== event.pointerId
            ) {
                return;
            }

            cropState.x =
                cropDragState.originX + (event.clientX - cropDragState.startX);

            cropState.y =
                cropDragState.originY + (event.clientY - cropDragState.startY);

            clampCropPan();
            applyCropTransform();

        });

        const endCropDrag = function (event) {

            if (!cropDragState || cropDragState.pointerId !== event.pointerId) {
                return;
            }

            if (cropStage.releasePointerCapture) {

                try {
                    cropStage.releasePointerCapture(event.pointerId);
                } catch (error) {
                    /* pointer already released — nothing to do */
                }

            }

            cropDragState = null;

            cropStage.classList.remove("is-dragging");

        };

        cropStage.addEventListener("pointerup", endCropDrag);
        cropStage.addEventListener("pointercancel", endCropDrag);

    }


    if (cropZoom) {

        cropZoom.addEventListener("input", function () {
            setCropZoomFromSlider(cropZoom.value);
        });

    }


    if (cropReset) {

        cropReset.addEventListener("click", function () {
            resetCropPosition();
        });

    }


    /* -----------------------------------------------------
       Render the crop and attach it to the file input in
       place of the originally-picked photo before the form
       actually submits.
       ----------------------------------------------------- */

    if (photoForm) {

        photoForm.addEventListener("submit", function (event) {

            if (!cropState || typeof DataTransfer === "undefined") {
                return;
            }

            event.preventDefault();

            if (saveButton) {
                saveButton.disabled = true;
            }

            renderCroppedBlob(function (blob) {

                if (!blob) {

                    if (saveButton) {
                        saveButton.disabled = false;
                    }

                    window.alert(
                        "Could not process that photo. Please try again."
                    );

                    return;

                }

                try {

                    const croppedFile = new File(
                        [blob],
                        "avatar.jpg",
                        { type: "image/jpeg" }
                    );

                    const dataTransfer = new DataTransfer();

                    dataTransfer.items.add(croppedFile);

                    fileInput.files = dataTransfer.files;

                } catch (error) {

                    // Fall back to uploading the originally
                    // picked photo, uncropped, rather than
                    // blocking the save entirely.

                }

                photoForm.submit();

            });

        });

    }


    /* -----------------------------------------------------
       AUTO-OPEN THE PHOTO MODAL ON AVATAR VALIDATION ERRORS
       (if change_photo() redirected back with a field error
       via Django messages/form re-render, surface it inside
       the modal instead of leaving it hidden)
       ----------------------------------------------------- */

    const hasAvatarFieldError =
        photoForm
            ? photoForm.querySelector(".pf-field-error")
            : null;

    if (hasAvatarFieldError) {
        openPhotoModal();
    }


    /* -----------------------------------------------------
       Take Photo / Choose from Gallery
       Both use the same underlying file input — the
       "capture" attribute is what hints a mobile browser to
       open the camera instead of the gallery. On desktop,
       both simply open the normal file picker.
       ----------------------------------------------------- */

    if (takePhotoBtn && fileInput) {

        takePhotoBtn.addEventListener("click", function () {

            closeAvatarPopover();

            fileInput.setAttribute("capture", "environment");

            fileInput.click();

        });

    }


    if (chooseGalleryBtn && fileInput) {

        chooseGalleryBtn.addEventListener("click", function () {

            closeAvatarPopover();

            fileInput.removeAttribute("capture");

            fileInput.click();

        });

    }


    if (removePhotoBtn && removePhotoForm) {

        removePhotoBtn.addEventListener("click", function () {

            closeAvatarPopover();

            const confirmed = window.confirm(
                "Remove your profile photo?"
            );

            if (confirmed) {
                removePhotoForm.submit();
            }

        });

    }


    if (fileInput) {

        fileInput.addEventListener("change", function () {

            const file =
                fileInput.files && fileInput.files[0];

            if (!file) {
                return;
            }


            /* -------------------------------------------
               CLIENT-SIDE VALIDATION
               (a first check only — the real, trusted
               validation happens server-side in
               AvatarUploadForm.clean_avatar)
               ------------------------------------------- */

            if (ALLOWED_AVATAR_TYPES.indexOf(file.type) === -1) {

                window.alert(
                    "Please choose a JPG or PNG image."
                );

                fileInput.value = "";

                return;

            }

            if (file.size > MAX_AVATAR_BYTES) {

                window.alert(
                    "That image is too large. Maximum size is 5MB."
                );

                fileInput.value = "";

                return;

            }


            if (fileNameLabel) {
                fileNameLabel.textContent = file.name;
            }


            /* -------------------------------------------
               Load the photo into the crop stage so the
               citizen can position and zoom it, then open
               the modal to show it. initCrop() enables the
               Save button once the photo has actually
               loaded successfully.
               ------------------------------------------- */

            initCrop(file);

            openPhotoModal();

        });

    }

});