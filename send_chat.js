let socket;

document.addEventListener('DOMContentLoaded', function () {
    socket = io.connect(window.location.origin);
    socket.on('connect', () => {
        console.log('WebSocket connection established.');
    });

    socket.on('chat_message', (data) => {
        addMessageToChat(data);
    });

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

                uploadFile(file);
            } else {
                console.error('No file selected.');
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

function chatMessageHTML(message) {
    const { username, message: msg, id, like_count = 0, dislike_count = 0 } = message;
    return `
        <div id="message_${id}">
            <button onclick='deleteMessage("${id}")'>X</button>
            <button class='like-button' onclick='likeMessage("${id}")'>&#x1F44D;</button>
            <span id='like_count_${id}'>${like_count}</span>
            <button class='dislike-button' onclick='dislikeMessage("${id}")'>&#x1F44E;</button>
            <span id='dislike_count_${id}'>${dislike_count}</span>
            <b>${username}</b>: ${msg}
        </div>
    `;
}

function addMessageToChat(message) {
    const chatMessages = document.getElementById("chat-messages");
    const messageElement = document.createElement('div');
    messageElement.innerHTML = chatMessageHTML(message);
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to the bottom
}


function uploadFile(file) {
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



// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// EVERYTHING BELOW NEEDS TO BE UPDATED TO WORK WITH WEBSOCKETS
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

function deleteMessage(messageId) {
    const request = new XMLHttpRequest();
    request.onreadystatechange = function () {
        if (this.readyState === 4 && this.status === 200) {
            console.log(this.response);
        }
    }
    request.open("DELETE", "/chat-messages/" + messageId);
    request.send();
}

function likeMessage(messageId) {

    const request = new XMLHttpRequest();

    const data = {
        "messageId": messageId,
    };

    request.onreadystatechange = function () {
        if (this.readyState === 4 && this.status === 200) {
            // this message includes the updated like count

            const like_and_dislike_count_obj = JSON.parse(this.response)
            console.log(like_and_dislike_count_obj)
            const likeCountElement = document.getElementById('like_count_' + messageId);
            const dislikeCountElement = document.getElementById('dislike_count_' + messageId);
            if (likeCountElement && dislikeCountElement) {
                likeCountElement.textContent = like_and_dislike_count_obj.like_count;
                dislikeCountElement.textContent = like_and_dislike_count_obj.dislike_count;
            }
        }
    };
    request.open("PUT", "/chat-messages/like/" + messageId);
    request.setRequestHeader("Content-Type", "application/json");
    request.send(JSON.stringify(data));
}

function dislikeMessage(messageId) {
    const request = new XMLHttpRequest();
    const elem = document.getElementById('dislike_count_' + messageId);

    const data = {
        "messageId": messageId,
    };
    request.onreadystatechange = function () {
        if (this.readyState === 4 && this.status === 200) {

            const like_and_dislike_count_obj = JSON.parse(this.response)
            console.log(like_and_dislike_count_obj)
            const likeCountElement = document.getElementById('like_count_' + messageId);
            const dislikeCountElement = document.getElementById('dislike_count_' + messageId);
            if (likeCountElement && dislikeCountElement) {
                likeCountElement.textContent = like_and_dislike_count_obj.like_count;
                dislikeCountElement.textContent = like_and_dislike_count_obj.dislike_count;
            }
        }
    };
    request.open("PUT", "/chat-messages/dislike/" + messageId);
    request.setRequestHeader("Content-Type", "application/json");
    request.send(JSON.stringify(data));
}

