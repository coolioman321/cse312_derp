from flask import Flask, make_response, render_template, send_from_directory, request, redirect, url_for,jsonify
from pymongo import MongoClient
from util.helper import validate_password, escape_html, extract_credentials
import bcrypt
import hashlib
import json
from util.auth_token_functions import check_user_auth, generate_auth_token, return_username_of_authenticated_user

mongo_client = MongoClient('mongo')
db = mongo_client['derp']
users = db['users']
authToken = db['auth_token']
unique_id_counter = db['counter']
chat_collection = db['chat']
liked_messages = db['liked_messages']
disliked_messages = db['disliked_messages']

def create_app():
    app = Flask(__name__)

    # Serve the home page
    @app.route('/')
    def home_page():
        user_auth_status = check_user_auth(request.cookies.get("auth_token"))
        rendered_template = render_template('index.html', user_logged_in=user_auth_status)
        username = return_username_of_authenticated_user()
        if username != None: 
            modified_template = rendered_template.replace("Guest", username)
            #updates guest to the current user
            rendered_template = modified_template

        # Create a response object from the rendered template
        response = make_response(rendered_template)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Type"] = 'text/html'
        
        return response

    # Serve CSS files
    @app.route('/style.css')
    def host_css():
        response = send_from_directory('.', 'style.css', mimetype='text/css')
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    # Serve image files from the 'images' directory
    @app.route('/images/<filename>')
    def host_image(filename):
        response = send_from_directory('images', filename, mimetype='image/jpeg')
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    # Serve JavaScript files
    @app.route('/app.js')
    def host_app_js():
        response = send_from_directory('.', 'app.js', mimetype='text/javascript')
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
    
    @app.route('/send_chat.js')
    def host_sendChat_js():
        response = send_from_directory('.', 'send_chat.js', mimetype='text/javascript')
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    # Serve the registration page
    @app.route('/register', methods=['POST'])
    def register():
        username = request.form['username']
        password = request.form['password']
        confirmPassword = request.form['confirmPassword']
        
        # Validate password
        if not validate_password(password):
            return redirect(url_for('home_page'))
        
        # Check if password and confirm password match
        if password != confirmPassword:
            return redirect(url_for('home_page'))
        
        # Check if username is already taken
        if users.find_one({"username": username}):
            return redirect(url_for('home_page'))
        
        # Salt and hash the password
        encrypted_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Insert the user into the database
        users.insert_one({"username": username, "password": encrypted_pw})
        
        # Redirect back to homepage
        return redirect(url_for('home_page'))

    @app.route('/login', methods=['POST'])
    def login():

        username = request.form["login_username"]
        password = request.form["login_password"]
        #look into if the auth token exist
        request_auth_token = request.cookies.get('auth_token')

        # if request have a cookie of auth token
        if request_auth_token != None:
            hash_object = hashlib.sha256(request_auth_token.encode())
            hashed_request_authToken = hash_object.hexdigest()
            username_authToken = authToken.find_one({"auth_token": hashed_request_authToken})

            # if auth_matches up with the auth_token in the database authToken
            if username_authToken:

                return redirect(url_for('home_page'))

        stored_record = users.find_one({"username":username})
        if stored_record:
            stored_password = stored_record["password"]

            if(bcrypt.checkpw(password.encode('utf-8'),stored_password)):
            #if the passwords match

                ##### SET AUTHENTICATION #####
                response = redirect(url_for('home_page'))
                generated_auth_token = generate_auth_token(username)
                hash_object = hashlib.sha256(generated_auth_token.encode())
                hashed_auth_token = hash_object.hexdigest()
                response.set_cookie('auth_token', generated_auth_token, max_age=3600, httponly=True)  # Expires in 1 hour
                authToken.find_one_and_delete({"username": username})
                authToken.insert_one({"username": username, "auth_token": hashed_auth_token})
                return response

        return redirect(url_for('home_page'))

    @app.route('/log-out', methods=['POST'])
    def logout():

        ####REMOVE AUTHENTICATION#####
        token = request.cookies.get('auth_token')
        if token:
            hash_object = hashlib.sha256(token.encode())
            hashed_token = hash_object.hexdigest()
            authToken.delete_one({"auth_token": hashed_token})

        response = make_response(redirect(url_for('home_page')))
        response.set_cookie('auth_token', '', expires=0)  # Clear the cookie
        return response
    
    @app.route('/chat-messages', methods=['POST'])
    def handle_post_chat_message():
        # Ensure the request has JSON content
        if request.is_json:
            # Parse the JSON data
            data = request.get_json()
            message = data.get('message', '') 
            if message == '':
                return jsonify({"success": False, "message": "message is empty"}), 400
            
            #initialize the counter
            document_count = unique_id_counter.count_documents({})
            if document_count == 0: 
                unique_id_counter.insert_one({"counter": 1})
            
            current_unique_counter = unique_id_counter.find_one({}, {"counter":1})

            response_info = {"message": message, "username": "guest", "id": f"{current_unique_counter['counter']}"}
            username = return_username_of_authenticated_user()
            if username != None:
                response_info["username"] = username

            #insert current message into DB
            chat_collection.insert_one(response_info)

            #increment the counter by 1
            query = {"counter": {"$exists": True}}
            new_values = {"$set": {"counter": current_unique_counter['counter']+1}}
            unique_id_counter.update_one(query, new_values)

            # print(f"message: {message}")  

            # Send a response back to the frontend
            return jsonify({"success": True, "message": f"id: {current_unique_counter['counter']} message:{message}"}), 200
        else:
            return jsonify({"success": False, "message": "Request was not JSON."}), 400

    @app.route('/chat-messages', methods=['GET'])
    def handle_get_chat_messages():
        all_data = chat_collection.find({})
        response_list = []

        for document in all_data:
            # Remove the '_id' field as it's not JSON serializable
            del document['_id']
            response_list.append(document)
        
        return jsonify(response_list)

    @app.route('/chat-messages/like/<int:message_id>', methods=['PUT'])
    def chat_messages_like(message_id):
        exists = chat_collection.find_one({"id": str(message_id)})
        if exists:
            request_auth_token = request.cookies.get('auth_token')
            if request_auth_token:
                hash_object = hashlib.sha256(request_auth_token.encode())
                hashed_request_authToken = hash_object.hexdigest()
                username_authToken = authToken.find_one({"auth_token": hashed_request_authToken})
                if username_authToken:
                    username_auth = username_authToken["username"]
                    if username_auth != exists["username"]:
                        already_liked = liked_messages.find_one({"username": username_auth, "id": str(message_id)})
                        already_disliked = disliked_messages.find_one({"username": username_auth, "id": str(message_id)})
                        if request.is_json:
                            like_count = exists.get('like_count', 0)
                            dislike_count = exists.get('dislike_count', 0)

                            if already_liked:
                                like_count = max(like_count - 1, 0)
                                liked_messages.delete_one({"username": username_auth, "id": str(message_id)})
                            elif already_disliked:
                                dislike_count = max(dislike_count - 1, 0)
                                like_count += 1
                                disliked_messages.delete_one({"username": username_auth, "id": str(message_id)})
                                liked_messages.insert_one({"username": username_auth, "id": str(message_id)})
                            else:
                                like_count += 1
                                liked_messages.insert_one({"username": username_auth, "id": str(message_id)})

                            chat_collection.update_one({"id": str(message_id)},
                                                       {"$set": {"like_count": like_count, "dislike_count": dislike_count}})
                            return jsonify({"like_count": like_count, "dislike_count": dislike_count}), 200
                        else:
                            return jsonify({"success": False, "message": "Request was not JSON."}), 400
                    else:
                        return jsonify({"error": "Unauthorized - cannot like your own message"}), 401
                else:
                    return jsonify({"error": "Unauthorized - invalid auth token"}), 401
            else:
                return jsonify({"error": "Unauthorized - no auth token"}), 401
        else:
            return jsonify({"error": "Message not found"}), 404

    @app.route('/chat-messages/dislike/<int:message_id>', methods=['PUT'])
    def chat_messages_dislike(message_id):
        exists = chat_collection.find_one({"id": str(message_id)})
        if exists:
            request_auth_token = request.cookies.get('auth_token')
            if request_auth_token:
                hash_object = hashlib.sha256(request_auth_token.encode())
                hashed_request_authToken = hash_object.hexdigest()
                username_authToken = authToken.find_one({"auth_token": hashed_request_authToken})
                if username_authToken:
                    username_auth = username_authToken["username"]
                    if username_auth != exists["username"]:
                        already_liked = liked_messages.find_one({"username": username_auth, "id": str(message_id)})
                        already_disliked = disliked_messages.find_one({"username": username_auth, "id": str(message_id)})
                        if request.is_json:
                            dislike_count = exists.get('dislike_count', 0)
                            like_count = exists.get('like_count', 0)

                            if already_disliked:
                                dislike_count = max(dislike_count - 1, 0)
                                disliked_messages.delete_one({"username": username_auth, "id": str(message_id)})
                            elif already_liked:
                                like_count = max(like_count - 1, 0)
                                dislike_count += 1
                                liked_messages.delete_one({"username": username_auth, "id": str(message_id)})
                                disliked_messages.insert_one({"username": username_auth, "id": str(message_id)})
                            else:
                                dislike_count += 1
                                disliked_messages.insert_one({"username": username_auth, "id": str(message_id)})

                            chat_collection.update_one({"id": str(message_id)},
                                                       {"$set": {"dislike_count": dislike_count, "like_count": like_count}})
                            return jsonify({"dislike_count": dislike_count, "like_count": like_count}), 200
                        else:
                            return jsonify({"success": False, "message": "Request was not JSON."}), 400
                    else:
                        return jsonify({"error": "Unauthorized - cannot dislike your own message"}), 401
                else:
                    return jsonify({"error": "Unauthorized - invalid auth token"}), 401
            else:
                return jsonify({"error": "Unauthorized - no auth token"}), 401
        else:
            return jsonify({"error": "Message not found"}), 404


    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=8080)