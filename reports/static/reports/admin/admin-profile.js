/* =========================================================
   NDMS ADMIN — MY PROFILE JAVASCRIPT

   NOTE: Sidebar toggling, the topbar profile dropdown and the
   mobile overlay are already handled by admin-shell.js, which
   every admin page (including this one) already loads via
   base.html. This file only adds the Personal Information
   edit/cancel interaction and the avatar management popover
   that are specific to the Profile page.
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {


    /* =====================================================
       ELEMENTS — PERSONAL INFORMATION EDIT / VIEW TOGGLE
       ===================================================== */

    const editButton =
        document.getElementById("apEditButton");

    const cancelButton =
        document.getElementById("apCancelButton");

    const editForm =
        document.getElementById("apEditForm");


    /* =====================================================
       EDIT / VIEW MODE TOGGLE
       (view/edit are two DOM blocks; a class on <body> swaps
       which one is visible. Identity and Account Information
       stay in the DOM the entire time — only the Personal
       Information view/edit blocks swap.)
       ===================================================== */

    function enterEditMode() {

        document.body.classList.add("ap-edit-mode");

        if (editButton) {
            editButton.setAttribute("aria-expanded", "true");
        }

        const firstField =
            editForm
                ? editForm.querySelector("#id_full_name")
                : null;

        if (firstField) {
            firstField.focus();
        }

    }


    function exitEditMode() {

        document.body.classList.remove("ap-edit-mode");

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
       (if the profile form was submitted with invalid data,
       admin_profile() re-renders this same page with field
       errors — open edit mode automatically so the errors
       are visible instead of hiding behind the view fields)
       ===================================================== */

    const hasFieldErrors =
        editForm
            ? editForm.querySelector(".ap-field-error")
            : null;

    if (hasFieldErrors) {
        enterEditMode();
    }


    /* =====================================================
       AVATAR EDIT POPOVER
       (camera badge on the identity avatar -> Take Photo /
       Choose from Gallery / Remove Photo)
       ===================================================== */

    const avatarEditWrapper =
        document.getElementById("apAvatarEditWrapper");

    const avatarEditBadge =
        document.getElementById("apAvatarEditBadge");

    const avatarPopover =
        document.getElementById("apAvatarPopover");

    const takePhotoBtn =
        document.getElementById("apTakePhotoBtn");

    const chooseGalleryBtn =
        document.getElementById("apChooseGalleryBtn");

    const removePhotoBtn =
        document.getElementById("apRemovePhotoBtn");

    const removePhotoForm =
        document.getElementById("apRemovePhotoForm");

    const viewPhotoBtn =
        document.getElementById("apViewPhotoBtn");

    const viewPhotoModal =
        document.getElementById("apViewPhotoModal");

    const viewPhotoClose =
        document.getElementById("apViewPhotoClose");


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
       admin already has a real avatar, so this is a no-op
       (and "View Photo" never appears in the popover) for the
       default-avatar case. Same pattern already used on the
       citizen Profile page.
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
       (same show/hide pattern already used on the citizen
       Profile page's photo modal)
       ===================================================== */

    const photoModal =
        document.getElementById("apChangePhotoModal");

    const closePhotoBtn =
        document.getElementById("apChangePhotoClose");

    const cancelPhotoBtn =
        document.getElementById("apCancelPhotoBtn");

    const photoForm =
        document.getElementById("apChangePhotoForm");

    const fileInput =
        document.getElementById("id_avatar");

    const choosePhotoLabel =
        document.getElementById("apChoosePhotoLabel");

    const fileNameLabel =
        document.getElementById("apPhotoFileName");

    const previewImage =
        document.getElementById("apPhotoPreviewImage");

    const previewInitials =
        document.getElementById("apPhotoPreviewInitials");

    const previewAvatarBlock =
        document.getElementById("apPhotoPreviewAvatar");

    const saveButton =
        document.getElementById("apSavePhotoBtn");

    const cropShell =
        document.getElementById("apCropShell");

    const cropStage =
        document.getElementById("apCropStage");

    const cropImage =
        document.getElementById("apCropImage");

    const cropZoom =
        document.getElementById("apCropZoom");

    const cropReset =
        document.getElementById("apCropReset");

    const outputCanvas =
        document.getElementById("apCropOutputCanvas");


    const MAX_AVATAR_BYTES = 5 * 1024 * 1024;

    const ALLOWED_AVATAR_TYPES = [
        "image/jpeg",
        "image/png",
    ];

    // Fixed resolution the final, cropped photo is rendered at
    // before upload — independent of how big the crop circle
    // is drawn on screen.
    const CROP_OUTPUT_SIZE = 480;

    // Holds everything needed to redraw and re-crop the photo
    // the admin currently has open in the crop stage. Null
    // whenever no new photo is being positioned.
    let cropState = null;

    // Tracks an in-progress drag on the crop stage.
    let cropDragState = null;


    /* =====================================================
       PHOTO CROP + ZOOM

       The admin drags to reposition and uses the slider to
       zoom the photo inside a fixed circular stage. On save,
       exactly what's visible in that circle is rendered onto
       an offscreen canvas at a fixed resolution, turned into a
       File, and attached to the existing #id_avatar input —
       so AvatarUploadForm / admin_profile() still just receive
       a normal image upload and needed no backend changes.
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
       (if admin_profile() re-rendered the page because the
       uploaded avatar failed validation, surface that error
       inside the modal instead of leaving it hidden)
       ----------------------------------------------------- */

    const hasAvatarFieldError =
        photoForm
            ? photoForm.querySelector(".ap-field-error")
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
               admin can position and zoom it, then open the
               modal to show it. initCrop() enables the Save
               button once the photo has actually loaded.
               ------------------------------------------- */

            initCrop(file);

            openPhotoModal();

        });

    }

});