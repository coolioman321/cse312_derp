console.log('Hello from script.js!');

document.addEventListener('DOMContentLoaded', function () {
    var greetingElement = document.getElementById('greeting');
    greetingElement.innerHTML = 'Hello, World!';

    var clickMeButton = document.getElementById('clickMeButton');
    clickMeButton.addEventListener('click', function () {
        console.log('Button clicked!');
    });
});