
function handle_button(){


    var header = document.getElementById('presentHeader');
    header.innerText = "Now why would you do that!";


}

document.addEventListener('DOMContentLoaded', function(){
    var button = document.getElementById('Button');

    button.addEventListener('click',handle_button);
});