document.addEventListener('DOMContentLoaded', function() {
    const socket = io.connect(window.location.origin);

    socket.on('connect', () => {
        console.log('WebSocket connection established.');
    });

    socket.on('chat_message', (data) => {
        addMessageToChat(data);
    });

    socket.on('like_updated', function (data) {
        likeMessage(data);
    });

    socket.on('dislike_updated', function (data) {
        dislikeMessage(data);
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
           <button class="like-button" data-message-id="${id}">&#x1F44D;</button>
            <span id='like_count_${id}'>${like_count}</span>
            <button class='dislike-button' data-message-id="${id}">&#x1F44E;</button>
            <span id='dislike_count_${id}'>${dislike_count}</span>
            <b>${username}</b>: ${msg}
        </div>
    `;
}

//<button className='like-button' onClick='likeMessage("${id}")'>&#x1F44D;</button>
function addMessageToChat(message) {
    const chatMessages = document.getElementById("chat-messages");
    const messageElement = document.createElement('div');
    messageElement.innerHTML = chatMessageHTML(message);
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to the bottom
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



function likeMessage(data) {
    console.log(data)
    const messageId = data.id;
    const newLikeCount = data.like_count;
    const likeCountElement = document.getElementById(`like_count_${messageId}`);
    likeCountElement.textContent = newLikeCount;
    }

function dislikeMessage(data) {

    console.log(data)
    const messageId = data.id;
    const newDislikeCount = data.dislike_count;
    const dislikeCountElement = document.getElementById(`dislike_count_${messageId}`);
    dislikeCountElement.textContent = newDislikeCount;

}







   // const request = new XMLHttpRequest();
    //const elem = document.getElementById('dislike_count_' + messageId);

    //const data = {
       // "messageId": messageId,
    //};
    //request.onreadystatechange = function () {
      //  if (this.readyState === 4 && this.status === 200) {

        //    const like_and_dislike_count_obj = JSON.parse(this.response)
          //  console.log(like_and_dislike_count_obj)
           // const likeCountElement = document.getElementById('like_count_' + messageId);
            //const dislikeCountElement = document.getElementById('dislike_count_' + messageId);
           // if (likeCountElement && dislikeCountElement) {
            //    likeCountElement.textContent = like_and_dislike_count_obj.like_count;
             //   dislikeCountElement.textContent = like_and_dislike_count_obj.dislike_count;
            //}
       // }
   // };
   // request.open("PUT", "/chat-messages/dislike/" + messageId);
    //request.setRequestHeader("Content-Type", "application/json");
    ///request.send(JSON.stringify(data));

