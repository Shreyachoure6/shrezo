// auth.js
// Toggles a password field between hidden (dots) and visible (plain text)
// when the eye icon next to it is clicked.

function togglePasswordVisibility(inputId, iconId) {
    const passwordInput = document.getElementById(inputId);
    const icon = document.getElementById(iconId);

    if (passwordInput.type === "password") {
        passwordInput.type = "text";   // show the actual characters
        icon.textContent = "👁";        // change icon to "hide" state
    } else {
        passwordInput.type = "password"; // hide it again
        icon.textContent = "👁";          // change icon back to "show" state
    }
}