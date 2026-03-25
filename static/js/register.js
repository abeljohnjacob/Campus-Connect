const programme = document.getElementById("programme");
const semester = document.getElementById("semester");
const form = document.getElementById("registerForm");

const password = document.getElementById("password");
const confirmPassword = document.getElementById("confirmPassword");
const passError = document.getElementById("passError");
const confirmError = document.getElementById("confirmError");

/* Programme → Semester */
programme.addEventListener("change", () => {
    semester.innerHTML = '<option value="" disabled selected hidden>Select semester</option>';
    let count = (programme.value === "MCA" || programme.value === "MBA") ? 4 : 8;

    for (let i = 1; i <= count; i++) {
        let opt = document.createElement("option");
        opt.value = `S${i}`;
        opt.textContent = `S${i}`;
        semester.appendChild(opt);
    }
});

/* Form Validation */
form.addEventListener("submit", (e) => {

    passError.classList.add("d-none");
    confirmError.classList.add("d-none");

    if (password.value.length < 6) {
        e.preventDefault();
        passError.classList.remove("d-none");
        password.focus();
        return;
    }

    if (password.value !== confirmPassword.value) {
        e.preventDefault();
        confirmError.classList.remove("d-none");
        confirmPassword.focus();
    }
});
