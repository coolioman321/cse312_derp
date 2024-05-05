document.addEventListener('DOMContentLoaded', function () {
    const isSecure = window.location.protocol === 'https:';
    const socket = io.connect(window.location.origin, { secure: isSecure, reconnect: true, rejectUnauthorized: false });
    //const socket = io.connect(window.location.origin);

    socket.on('connect', () => {
        console.log('WebSocket connection established.');
    });

    socket.on('chat_message', (data) => {
        addMessageToChat(data)
    });

    socket.on('like_updated', function (data) {
        likeMessage(data);
    });

    socket.on('dislike_updated', function (data) {
        dislikeMessage(data);
    });

    socket.on('delete_updated', function (data) {
        deleteMessage(data);
    });

    socket.on('update_activity_status', function(data){
        console.log(data);
        console.log('in the update-activity-status');
        userList(data);
    });

    socket.on('cannot_delete_other_msgs', function (data) {

        alert(data.error)
    })

    socket.on("upload_complete", () => {
        document.getElementById('upload-button').disabled = false;  //re-enable the button
    })

    // Send button for chat
    document.getElementById('send-btn').addEventListener('click', () => {
        const message = document.getElementById("chat-text-box").value;
        const xsrfToken = document.getElementById("xsrf-token").value;
        document.getElementById("chat-text-box").value = ""; // clear input box

        socket.emit('send_chat', {
            message: message,
            xsrf_token: xsrfToken
        });
    });

    // on a click of the like button a call to the /like path is made
    document.getElementById('chat-messages').addEventListener('click', (event) => {
        if (event.target.classList.contains('like-button')) {
            const messageId = event.target.getAttribute('data-message-id');
            socket.emit('like', {
                id: messageId
            });
        }
    });

    // on a click of the like button a call to the /dislike path is made
    document.getElementById('chat-messages').addEventListener('click', (event) => {
        if (event.target.classList.contains('dislike-button')) {
            const messageId = event.target.getAttribute('data-message-id');
            socket.emit('dislike', {
                id: messageId
            });
        }
    });

    //event listener for delete button
    document.getElementById('chat-messages').addEventListener('click', (event) => {
        if (event.target.classList.contains('delete-button')) {
            const messageId = event.target.getAttribute('data-message-id');
            socket.emit('delete', {
                id: messageId
            });
        }
    });

    //upload button for images/videos
    const fileUploadButton = document.getElementById('upload-button'); // Ensure your upload button has this ID
    if (fileUploadButton) {
        fileUploadButton.addEventListener('click', function () {
            const fileInput = document.getElementById('file-upload');
            if (fileInput.files.length > 0) {

                let file = fileInput.files[0]
                console.log(`File Name: ${file.name}`);
                console.log(`File Type: ${file.type}`);
                console.log(`File Size: ${file.size} bytes`);

                uploadFile(file, socket);
                document.getElementById('upload-button').disabled = true;  // Disable the button
                fileInput.value = ""; // reset the file-upload text

            } else {
                alert('No file selected.');
            }
        });
    }


    // Optional - Send chat message when Enter key is pressed
    document.addEventListener("keypress", function (event) {
        const message = document.getElementById("chat-text-box").value;
        if (event.code === "Enter" && message !== "") {
            const xsrfToken = document.getElementById("xsrf-token").value;
            document.getElementById("chat-text-box").value = ""; // clear input box

            socket.emit('send_chat', {
                message: message,
                xsrf_token: xsrfToken
            });
        }
    });


});

function welcome() {
    const request = new XMLHttpRequest();
    request.onreadystatechange = function () {
        if (this.readyState === 4 && this.status === 200) {
            clearChat();
            const messages = JSON.parse(this.response);
            for (const message of messages) {
                addMessageToChat(message);
            }
        }
    }
    request.open("GET", "/chat-messages");
    request.send();
}

function clearChat() {
    const chatMessages = document.getElementById("chat-messages");
    chatMessages.innerHTML = "";
}

function uploadMessageHTML(message) {
    const { username, message: msg, id, like_count = 0, dislike_count = 0 } = message;
    return `
        <div id="message_${id}">
            <button class = 'delete-button' data-message-id="${id}">X</button>
            <b>${username}</b>: 
            <br>
            ${msg}
            <br>
            <button class="like-button" data-message-id="${id}">&#x1F44D;</button>
            <span id='like_count_${id}'>${like_count}</span>
            <button class='dislike-button' data-message-id="${id}">&#x1F44E;</button>
            <span id='dislike_count_${id}'>${dislike_count}</span>
        </div>
        <br>
    `;
}

function chatMessageHTML(message) {
    const { username, message: msg, id, like_count = 0, dislike_count = 0 } = message;
    return `
        <div id="message_${id}">
            <button class = 'delete-button' data-message-id="${id}">X</button>
           <button class="like-button" data-message-id="${id}">&#x1F44D;</button>
            <span id='like_count_${id}'>${like_count}</span>
            <button class='dislike-button' data-message-id="${id}">&#x1F44E;</button>
            <span id='dislike_count_${id}'>${dislike_count}</span>
            <b>${username}</b>: ${msg}
        </div>
        <br>
    `;
}


function userList(data) {

    const user_list = document.getElementById("active-users");
    user_list.innerHTML = "";
    for (let username in data) {
        if (data.hasOwnProperty(username)) {
            let duration = data[username]
            console.log(duration);
            user_list.innerHTML += userHTML(username, duration);
        }}}



//<button className='like-button' onClick='likeMessage("${id}")'>&#x1F44D;</button>
function addMessageToChat(message) {
    const chatMessages = document.getElementById("chat-messages");
    const messageElement = document.createElement('div');

    messageType = message.messageType ?? "text"
    if(messageType === 'text'){

        messageElement.innerHTML = chatMessageHTML(message);
    }else{

        messageElement.innerHTML = uploadMessageHTML(message);
    }
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to the bottom
}

function userHTML(username,duration) {
    console.log('in the userHTML ');

    let messageHTML = "<div class='user' id='user_" + username + "'><span> " + username + " - Active: " + duration + " seconds</span></div>";
    return messageHTML }

function deleteMessage(data) {
    console.log('in the delete');
    const messageId = data.id
    const messageElement = document.getElementById(`message_${messageId}`);
    if (messageElement) {
        console.log('deleting');
        messageElement.remove(); //remove
    } else {
        console.log(`Message not found.`);}

}



function likeMessage(data) {
    console.log(data)
    const messageId = data.id;
    const newLikeCount = data.like_count;
    const newDislikeCount = data.dislike_count;
    const likeCountElement = document.getElementById(`like_count_${messageId}`);
    const dislikeCountElement = document.getElementById(`dislike_count_${messageId}`);
    likeCountElement.textContent = newLikeCount;
    dislikeCountElement.textContent = newDislikeCount;
}

function dislikeMessage(data) {

    console.log(data)
    const messageId = data.id;
    const newDislikeCount = data.dislike_count;
    const newLikeCount = data.like_count;
    const likeCountElement = document.getElementById(`like_count_${messageId}`);
    const dislikeCountElement = document.getElementById(`dislike_count_${messageId}`);
    dislikeCountElement.textContent = newDislikeCount;
    likeCountElement.textContent = newLikeCount;

}

function uploadFile(file, socket) {
    const CHUNK_SIZE = 1024 * 1024; // 1MB
    let offset = 0;

    function sendNextChunk() {
        const reader = new FileReader();

        reader.onload = function (event) {
            socket.emit('file_upload', { chunk: event.target.result, filename: file.name, finished: offset >= file.size });
            if (offset < file.size) {
                sendNextChunk();
            }
        };

        reader.onerror = function (event) {
            console.error("File could not be read: " + event.target.error);
        };

        const chunk = file.slice(offset, offset + CHUNK_SIZE);
        reader.readAsArrayBuffer(chunk);
        offset += CHUNK_SIZE;
    }

    sendNextChunk();
}

/* Set the width of the side navigation to 250px */
function openNav() {
    document.getElementById("mySidenav").style.width = "250px";
    document.getElementById("chatSection").style.marginLeft = "250px";
}

/* Set the width of the side navigation to 0 */
function closeNav() {
    document.getElementById("mySidenav").style.width = "0";
    document.getElementById("chatSection").style.marginLeft = "0";
}





