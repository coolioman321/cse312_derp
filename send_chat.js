function sendChat() {
    const chatTextBox = document.getElementById("chat-text-box");
    const message = chatTextBox.value;
    const xsrfToken = document.getElementById("xsrf-token").value; // Get the XSRF token
    chatTextBox.value = "";

    const request = new XMLHttpRequest();
    request.onreadystatechange = function () {
        if (this.readyState === 4 && this.status === 200) {
            console.log(this.response);
        }
    }
    const messageJSON = {
        "message": message,
        "xsrf_token": xsrfToken // Add the XSRF token to the message
    };
    request.open("POST", "/chat-messages");
    request.setRequestHeader("Content-Type", "application/json");
    request.send(JSON.stringify(messageJSON));
    chatTextBox.focus();
}

function chatMessageHTML(messageJSON) {
    const username = messageJSON.username;
    const message = messageJSON.message;
    const messageId = messageJSON.id;
    const LikeCount = messageJSON.like_count || 0; //check existing like count, set 0  if none exists
    const DislikeCount = messageJSON.dislike_count || 0; //check existing like count, set 0  if none exists
    let messageHTML = `
    <br>
    <button onclick='deleteMessage("${messageId}")'>X</button>
    <button class='like-button' onclick='likeMessage("${messageId}")'>&#x1F44D;</button>
    <span id='like_count_${messageId}'>${LikeCount}</span>
    <button class='dislike-button' onclick='dislikeMessage("${messageId}")'>&#x1F44E;</button>
    <span id='dislike_count_${messageId}'>${DislikeCount}</span>
    <span id='message_${messageId}'><b>${username}</b>: ${message}</span>
`;
    return messageHTML;
}

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

function addMessageToChat(messageJSON) {
    const chatMessages = document.getElementById("chat-messages");
    chatMessages.innerHTML += chatMessageHTML(messageJSON);
    chatMessages.scrollIntoView(false);
    chatMessages.scrollTop = chatMessages.scrollHeight - chatMessages.clientHeight;
}

function clearChat() {
    const chatMessages = document.getElementById("chat-messages");
    chatMessages.innerHTML = "";
}

function updateChat() {
    const request = new XMLHttpRequest();
    request.onreadystatechange = function () {
        if (this.readyState === 4 && this.status === 200) {
            clearChat();
            const messages = JSON.parse(this.response);
            for (const message of messages) {
                addMessageToChat(message);
                // console.log(message)
            }
        }
    }
    request.open("GET", "/chat-messages");
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

updateChat();
setInterval(updateChat, 1000);

