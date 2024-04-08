from flask import Flask, make_response, render_template, send_from_directory, request, redirect, url_for,jsonify
from pymongo import MongoClient
from util.helper import validate_password, escape_html, extract_credentials
import bcrypt
import hashlib
import json
from util.auth_token_functions import check_user_auth, generate_auth_token, return_username_of_authenticated_user
import secrets
import os

mongo_client = MongoClient('mongo')
db = mongo_client['derp']
users = db['users']
authToken = db['auth_token']
unique_id_counter = db['counter']
chat_collection = db['chat']
liked_messages = db['liked_messages']
disliked_messages = db['disliked_messages']

file_count = 0

def create_app():
    app = Flask(__name__)

    # Serve the home page
    @app.route('/')
    def home_page():
        user_auth_status = check_user_auth(request.cookies.get("auth_token"))
        rendered_template = render_template('index.html', user_logged_in=user_auth_status)
        username = return_username_of_authenticated_user()
        if username != None: 
            username = escape_html(username) # Escape HTML characters in username
            modified_template = rendered_template.replace("Guest", username)
            #updates guest to the current user
            rendered_template = modified_template
            
            # Retrieve XSRF token for this user from the database
            user_record = users.find_one({"username": username})
            if user_record:
                xsrf_token = user_record.get("xsrf_token", None)
                # Or generate a new one if it doesn't exist
                if xsrf_token is None:
                    # Generate a new XSRF token
                    xsrf_token = secrets.token_hex(16)
                    users.update_one({"username": username}, {"$set": {"xsrf_token": xsrf_token}})
                # Inject the XSRF token into the value of the hidden input field
                rendered_template = rendered_template.replace("REPLACE_THIS_XSRF_TOKEN", xsrf_token)              

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
                response.headers["X-Content-Type-Options"] = "nosniff"
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
        response.set_cookie('auth_token', '', expires=0, httponly=True)  # Clear the cookie
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
    
    @app.route('/chat-messages', methods=['POST'])
    def handle_post_chat_message():
        # Ensure the request has JSON content
        if request.is_json:
            # Parse the JSON data
            data = request.get_json()
            message = data.get('message', '')
            message = escape_html(message) # Escape HTML characters in message
            if message == '':
                return jsonify({"success": False, "message": "message is empty"}), 400
            
            #initialize the counter
            document_count = unique_id_counter.count_documents({})
            if document_count == 0: 
                unique_id_counter.insert_one({"counter": 1})
            
            current_unique_counter = unique_id_counter.find_one({}, {"counter":1})

            response_info = {"message": message, "username": "Guest", "id": f"{current_unique_counter['counter']}"}
            username = return_username_of_authenticated_user()
            if username != None:
                username = escape_html(username) # Escape HTML characters in username
                response_info["username"] = username
                
                # Check if user's XSRF token matches the one in the database
                user_record = users.find_one({"username": username})
                if user_record:
                    xsrf_token = user_record.get("xsrf_token", None)
                    # If token doesn't match, return a 403 error
                    if xsrf_token != data.get("xsrf_token"):
                        return jsonify({"success": False, "message": "XSRF token does not match"}), 403

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

        if chat_collection.find_one({"id": str(message_id)}) != None:
            exists = chat_collection.find_one({"id": str(message_id)})
            request_auth_token = request.cookies.get('auth_token')

        # if request have a cookie of auth token
            if request_auth_token != None:
                hash_object = hashlib.sha256(request_auth_token.encode())
                hashed_request_authToken = hash_object.hexdigest()
                username_authToken = authToken.find_one({"auth_token": hashed_request_authToken})
                username_auth = username_authToken["username"]
                user_of_message_clicked = exists["username"]
                if username_auth != user_of_message_clicked:
                    print("usernames not the same", flush= True)
                #cannot like your own messages
                    if(liked_messages.find_one({"username" : username_auth, "id" : str(message_id)}) is None and (disliked_messages.find_one({"username" : username_auth, "id" : str(message_id)}) is None)):
                        #if the message hasn't been liked or disliked by this user already
                            
                        current_id = {"id": str(message_id)}

                        # current_id will always exist because the message have to be up before the user can like it
                        current_chat_msg = chat_collection.find_one(current_id)
                        new_like_count = current_chat_msg.get('like_count', 0) +1
                        chat_collection.update_one(current_id,
                                                {"$set": {"like_count": new_like_count}})
                        liked_messages.insert_one({"username" : username_auth, "id" : str(message_id)})
                    
                        return jsonify({'like_count': new_like_count, 'dislike_count': current_chat_msg.get('dislike_count', 0)}), 200
                    
                        
                    elif(liked_messages.find_one({"username" : username_auth, "id" : str(message_id)}) is not None and (disliked_messages.find_one({"username" : username_auth, "id" : str(message_id)}) is None)):
                        #if the message has been liked already, unlike it
                        

                        current_id = {"id": str(message_id)}
                        current_mgs = chat_collection.find_one(current_id)
                        new_like_count =  current_mgs['like_count']- 1
                        chat_collection.update_one(current_id,
                                                {"$set": {"like_count": new_like_count}})
                        liked_messages.delete_one({"username" : username_auth, "id" : str(message_id)})

                        print("This is undo_like Like", flush= True)
                        return jsonify({'like_count': new_like_count, 'dislike_count': current_mgs.get('dislike_count', 0)}), 200
                    
                    elif(liked_messages.find_one({"username" : username_auth, "id" : str(message_id)}) is None and (disliked_messages.find_one({"username" : username_auth, "id" : str(message_id)}) is not None)):
                        
                        # switch from dislike to like
                        current_id = {"id": str(message_id)}
                        current_msg = chat_collection.find_one(current_id)
                        updated_dislike_count = current_msg['dislike_count'] - 1
                        updated_like_count = current_msg.get('like_count', 0) +1
                        chat_collection.update_one(current_id,
                                                    {"$set": {"dislike_count": updated_dislike_count, "like_count": updated_like_count}})
                        disliked_messages.delete_one({"username" : username_auth, "id" : str(message_id)})
                        liked_messages.insert_one({"username" : username_auth, "id" : str(message_id)})

                        return jsonify({'like_count': updated_like_count, 'dislike_count': updated_dislike_count}), 200
                    else:
                        return jsonify({"error": "Unauthorized"}), 401

                return jsonify({"error": "Unauthorized"}), 401

            return jsonify({"error": "Unauthorized"}), 401

    @app.route('/chat-messages/dislike/<int:message_id>', methods=['PUT'])
    def chat_messages_dislike(message_id):

        if chat_collection.find_one({"id": str(message_id)}) != None:
            exists = chat_collection.find_one({"id": str(message_id)})
            request_auth_token = request.cookies.get('auth_token')

            # if request have a cookie of auth token
            if request_auth_token != None:
                hash_object = hashlib.sha256(request_auth_token.encode())
                hashed_request_authToken = hash_object.hexdigest()
                username_authToken = authToken.find_one({"auth_token": hashed_request_authToken})
                username_auth = username_authToken["username"]
                user_of_message_clicked = exists["username"]
                if username_auth != user_of_message_clicked:
                    print("usernames not the same")
                    #cannot like your own messages
                    if(liked_messages.find_one({"username" : username_auth, "id" : str(message_id)}) is None and (disliked_messages.find_one({"username" : username_auth, "id" : str(message_id)}) is None)):
                        #if the message has already been liked by this user or already disliked
                       
                        current_id = {"id": str(message_id)}

                        current_msg = chat_collection.find_one(current_id)

                        updated_dislike_count = current_msg.get('dislike_count', 0) + 1

                        chat_collection.update_one(current_id,
                                                    {"$set": {"dislike_count": updated_dislike_count}})
                        disliked_messages.insert_one({"username" : username_auth, "id" : str(message_id)})

                        return jsonify({"like_count": current_msg.get('like_count', 0), 'dislike_count': updated_dislike_count}), 200
                      
                        
                    elif(liked_messages.find_one({"username" : username_auth, "id" : str(message_id)}) is None and (disliked_messages.find_one({"username" : username_auth, "id" : str(message_id)}) is not None)):
                        #if the message has been liked already, unlike it
                        
                        current_id = {"id": str(message_id)}
                        current_msg = chat_collection.find_one(current_id)
                        
                        updated_dislike_count = current_msg['dislike_count'] - 1

                        chat_collection.update_one(current_id,
                                                    {"$set": {"dislike_count": updated_dislike_count}})
                        
                        disliked_messages.delete_one({"username" : username_auth, "id" : str(message_id)})

                        return jsonify({"like_count": current_msg.get('like_count', 0), 'dislike_count': updated_dislike_count}), 200
                    
                    elif(liked_messages.find_one({"username" : username_auth, "id" : str(message_id)}) is not None and (disliked_messages.find_one({"username" : username_auth, "id" : str(message_id)}) is None)):
                        
                        # switch from like to dislike
                        current_id = {"id": str(message_id)}
                        current_msg = chat_collection.find_one(current_id)
                        updated_like_count = current_msg['like_count'] -1
                        updated_dislike_count = current_msg.get('dislike_count', 0) + 1
                        chat_collection.update_one(current_id,
                                                    {"$set": {"dislike_count": updated_dislike_count, "like_count": updated_like_count}})
                        disliked_messages.insert_one({"username" : username_auth, "id" : str(message_id)})
                        liked_messages.delete_one({"username" : username_auth, "id" : str(message_id)})

                        return jsonify({'like_count': updated_like_count, 'dislike_count': updated_dislike_count}), 200
                    
                    else:
                        return jsonify({"error": "Unauthorized"}), 401

                return jsonify({"error": "Unauthorized"}), 401

            return jsonify({"error": "Unauthorized"}), 401
        
    @app.route('/chat-messages/<message_id>', methods=['DELETE'])
    def delete_chat_message(message_id):
        # Check if the auth token is present
        request_auth_token = request.cookies.get('auth_token')
        if request_auth_token is None:
            return jsonify({"error": "Unauthorized - No auth token provided"}), 401

        # Verify the auth token
        hash_object = hashlib.sha256(request_auth_token.encode())
        hashed_request_authToken = hash_object.hexdigest()
        username_authToken = authToken.find_one({"auth_token": hashed_request_authToken})

        if username_authToken is None:
            return jsonify({"error": "Unauthorized - Invalid auth token"}), 401

        # Check if the user is authorized to delete the message
        # (assuming the 'username' field in the message document indicates the message owner)
        message = chat_collection.find_one({"id": message_id})
        if message is None:
            return jsonify({"error": "Message not found"}), 404

        if username_authToken['username'] != message.get('username', ''):
            return jsonify({"error": "Unauthorized - User cannot delete this message"}), 403

        # Proceed with message deletion
        result = chat_collection.delete_one({"id": message_id})

        if result.deleted_count > 0:
            return jsonify({"success": True, "message": "Message deleted successfully."}), 200
        else:
            return jsonify({"error": "Message not found or could not be deleted"}), 404

    @app.route('/upload', methods=['POST'])
    def upload_file():
        # Check if the POST request has the file part
        if 'file' not in request.files:
            return redirect(url_for('home_page'))
        file = request.files['file']
        
        # If the user does not select a file, the browser submits an empty part without a filename.
        if file.filename == '':
            return redirect(url_for('home_page'))
        
        # Read file signature from first 16 bytes
        file_signature = file.read(16)
        
        # Check for jpg signature
        if file_signature[:2] == b'\xFF\xD8':
            file_extension = 'jpg'
        # Check for png signature
        elif file_signature[:8] == b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A':
            file_extension = 'png'
        # Check for gif signature
        elif file_signature[:6] in [b'GIF87a', b'GIF89a']:
            file_extension = 'gif'
        # Check for mp4 signature
        elif b'ftypisom' in file_signature or b'ftypmp42' in file_signature or b'ftypMSNV' in file_signature:
            file_extension = 'mp4'
        else:
            return redirect(url_for('home_page'))
        
        # Generate unique filename with its extension
        global file_count
        file_count += 1
        filename = f'file_{file_count}.{file_extension}'
        filename = filename.replace('/', '') # Prevent directory traversal
        filepath = os.path.join('images', filename)
        
        # Save the file to disk
        with open(filepath, 'wb') as f:
            f.write(file_signature)
            f.write(file.read())

        # Create img tag for jpg, png, and gif files
        if file_extension in ['jpg', 'png', 'gif']:
            msg = f'<img src="/images/{filename}" alt="Uploaded image" style="max-width: 100%; max-height: 100%;">'
        # Create video tag for mp4 files
        elif file_extension == 'mp4':
            msg = f'<video controls autoplay muted style="max-width: 100%; max-height: 100%;"><source src="/images/{filename}" type="video/mp4">Your browser does not support the video tag.</video>'

        # Generate unique ID for the chat message
        document_count = unique_id_counter.count_documents({})
        if document_count == 0: 
            unique_id_counter.insert_one({"counter": 1})
        current_unique_counter = unique_id_counter.find_one({}, {"counter":1})
        
        # If auth_token cookie exists, set username of the user with that token
        username = return_username_of_authenticated_user()
        if username is not None:
            username = escape_html(username)
        else:
            username = 'Guest'
            
        # Insert the chat message into the database
        chat_collection.insert_one({"message": msg, "username": username, "id": f"{current_unique_counter['counter']}"})
        
        # Return to the homepage
        return redirect(url_for('home_page'))

    return app

    
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=8080)