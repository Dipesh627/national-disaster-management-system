/* =========================================================
   NDMS CITIZEN — SETTINGS JAVASCRIPT
   Handles:
     - Dismissing Django messages
     - Full input change tracking (selects, radio pills, toggles)
     - Dynamic Save Bar status (All preferences saved / Unsaved changes / Saving…)
     - Discard button restoring initial loaded state
     - Prevent navigation / tab close when dirty (beforeunload)
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    /* =====================================================
       1. DISMISS DJANGO MESSAGES
       ===================================================== */

    const messageCloseButtons = document.querySelectorAll(".message-close");

    messageCloseButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const message = button.closest(".django-message");
            if (message) {
                message.remove();
            }
        });
    });

    /* =====================================================
       2. SAVE STATE TRACKING & DISCARD
       ===================================================== */

    const settingsForm = document.getElementById("settingsForm");
    const saveBar = document.getElementById("stSaveBar");
    const saveStatusText = document.getElementById("stSaveStatusText");
    const saveButton = document.getElementById("stSaveButton");
    const discardButton = document.getElementById("stDiscardButton");

    if (settingsForm && saveBar && saveStatusText && saveButton) {

        // Collect all form controls
        const selectInputs = Array.from(settingsForm.querySelectorAll("select"));
        const checkboxInputs = Array.from(settingsForm.querySelectorAll("input[type='checkbox']"));
        const radioInputs = Array.from(settingsForm.querySelectorAll("input[type='radio']"));

        // Store initial values loaded from the server
        const initialSelects = new Map();
        selectInputs.forEach(function (sel) {
            initialSelects.set(sel, sel.value);
        });

        const initialCheckboxes = new Map();
        checkboxInputs.forEach(function (cb) {
            initialCheckboxes.set(cb, cb.checked);
        });

        const initialRadios = new Map();
        // Group radios by name
        const radioNames = new Set(radioInputs.map(function (r) { return r.name; }));
        radioNames.forEach(function (name) {
            const checkedRadio = settingsForm.querySelector(`input[type='radio'][name='${name}']:checked`);
            initialRadios.set(name, checkedRadio ? checkedRadio.value : null);
        });

        // Visual helper for radio pills
        function updateRadioPillStyles() {
            radioInputs.forEach(function (radio) {
                const pill = radio.closest(".st-radio-pill");
                if (pill) {
                    if (radio.checked) {
                        pill.classList.add("is-checked");
                    } else {
                        pill.classList.remove("is-checked");
                    }
                }
            });
        }
        updateRadioPillStyles();

        function isDirty() {
            // Check selects
            for (let [sel, initVal] of initialSelects) {
                if (sel.value !== initVal) {
                    return true;
                }
            }
            // Check checkboxes
            for (let [cb, initVal] of initialCheckboxes) {
                if (cb.checked !== initVal) {
                    return true;
                }
            }
            // Check radios
            for (let [name, initVal] of initialRadios) {
                const currentChecked = settingsForm.querySelector(`input[type='radio'][name='${name}']:checked`);
                const currentVal = currentChecked ? currentChecked.value : null;
                if (currentVal !== initVal) {
                    return true;
                }
            }
            return false;
        }

        function setStatus(state, text) {
            saveBar.classList.remove("st-dirty", "st-saving", "st-error");
            if (state) {
                saveBar.classList.add(state);
            }
            saveStatusText.textContent = text;
        }

        function refreshStatus() {
            updateRadioPillStyles();
            if (isDirty()) {
                setStatus("st-dirty", "Unsaved changes");
            } else {
                setStatus(null, "All preferences saved");
            }
        }

        settingsForm.addEventListener("input", refreshStatus);
        settingsForm.addEventListener("change", refreshStatus);

        // DISCARD BUTTON
        if (discardButton) {
            discardButton.addEventListener("click", function () {
                // Restore selects
                initialSelects.forEach(function (val, sel) {
                    sel.value = val;
                });
                // Restore checkboxes
                initialCheckboxes.forEach(function (val, cb) {
                    cb.checked = val;
                });
                // Restore radios
                initialRadios.forEach(function (val, name) {
                    const targetRadio = settingsForm.querySelector(`input[type='radio'][name='${name}'][value='${val}']`);
                    if (targetRadio) {
                        targetRadio.checked = true;
                    } else {
                        const allForName = settingsForm.querySelectorAll(`input[type='radio'][name='${name}']`);
                        allForName.forEach(function (r) { r.checked = false; });
                    }
                });

                refreshStatus();
            });
        }

        // SUBMIT STATE
        let isSubmitting = false;

        settingsForm.addEventListener("submit", function () {
            isSubmitting = true;
            setStatus("st-saving", "Saving…");
            saveButton.disabled = true;
            if (discardButton) {
                discardButton.disabled = true;
            }
        });

        // BEFOREUNLOAD WARNING
        window.addEventListener("beforeunload", function (event) {
            if (isDirty() && !isSubmitting) {
                event.preventDefault();
                event.returnValue = "";
            }
        });

    }

});
