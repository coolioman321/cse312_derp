function passwordValidation(passwordValue) {
    // At least 1 uppercase letter
    var hasUpperCase = /[A-Z]/.test(passwordValue);

    // At least 1 lowercase letter
    var hasLowerCase = /[a-z]/.test(passwordValue);

    // At least 1 digit
    var hasDigit = /\d/.test(passwordValue);

    // At least 1 special character
    var hasSpecial = /[^A-Za-z0-9]/.test(passwordValue);

    if (!hasUpperCase) {
        return 'Password must contain at least 1 uppercase letter'
    }

    if (!hasLowerCase) {
        return 'Password must contain at least 1 lowercase letter'
    }

    if (!hasDigit) {
        return 'Password must contain at least 1 digit'
    }

    if (!hasSpecial) {
        return 'Password must contain at least 1 special character'
    }

    return ''; // Password is valid
}

var passwordInput = document.getElementById('password')
if (passwordInput) {
    // Add an event listener to the password input field
    document.getElementById('password').addEventListener('input', function () {
        var passwordInput = document.getElementById('password');

        // Validate the password
        var errorMessage = passwordValidation(passwordInput.value);
        passwordInput.setCustomValidity(errorMessage);

        // Trigger fake input event on confirmPassword field to re-validate it in case it was invalid before
        document.getElementById('confirmPassword').dispatchEvent(new Event('input'));
    });
}

// Add an event listener to the confirm password input field
var confirmPasswordInput = document.getElementById('confirmPassword')
if (confirmPasswordInput) {
    document.getElementById('confirmPassword').addEventListener('input', function () {
        var confirmPasswordInput = document.getElementById('confirmPassword');
        var password = document.getElementById('password').value;

        // Validate the confirm password
        if (password !== confirmPasswordInput.value) {
            confirmPasswordInput.setCustomValidity('Passwords do not match');
        } else {
            confirmPasswordInput.setCustomValidity('');
        }
    });
}


