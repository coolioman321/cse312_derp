from flask import Flask, make_response, render_template, send_from_directory, request, redirect, url_for,jsonify
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
from util.helper import validate_password, escape_html, extract_credentials
import bcrypt
import hashlib
import json
from util.auth_token_functions import check_user_auth, generate_auth_token, return_username_of_authenticated_user
import secrets
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
import time

mongo_client = MongoClient('mongo')
db = mongo_client['derp']
users = db['users']
authToken = db['auth_token']
unique_id_counter = db['counter']
chat_collection = db['chat']
liked_messages = db['liked_messages']
disliked_messages = db['disliked_messages']

file_count = 0
file_storage = {}

banned_ips = {}
request_counts = {}

def create_app():
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB limit
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_port=1, x_prefix=1)
    socketio = SocketIO(app, async_mode='eventlet',  max_http_buffer_size=1e8)
    
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["50 per 10 seconds"],
        storage_uri="memory://",
        strategy="moving-window"
    )
    limiter.init_app(app)

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

    @app.route('/favicon.ico')
    def host_favicon():
        print('serving favicon', flush = True)
        print("in favicon", flush = True)
        response = send_from_directory('.', 'images/favicon.ico', mimetype='image/x-icon')
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
                # Secure the cookie
                response.headers["Set-Cookie"] = "auth_token=" + generated_auth_token + "; Secure"
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
    
    @socketio.on('send_chat')
    def handle_chat_message(json):
        username = return_username_of_authenticated_user() or "Guest"
        message = escape_html(json['message'])
        xsrf_token = json.get('xsrf_token')

        # Validate XSRF Token
        if username != "Guest":
            user_record = users.find_one({"username": username})
            if not xsrf_token or xsrf_token != user_record.get("xsrf_token"):
                emit('chat_response', {'success': False, 'message': 'XSRF token mismatch'})
                return

        # Initialize the counter
        document_count = unique_id_counter.count_documents({})
        if document_count == 0:
            unique_id_counter.insert_one({"counter": 1})

        # Store the chat message in the database
        message_id = unique_id_counter.find_one_and_update({}, {'$inc': {'counter': 1}}, return_document=True).get('counter')
        print(type(message_id), flush = True)
        chat_message = {"username": username, "message": message, "id": message_id}
        chat_collection.insert_one(chat_message)
        
        # Remove the '_id' field as it's not JSON serializable
        if '_id' in chat_message:
                chat_message['_id'] = str(chat_message['_id'])

        # Broadcast the chat message to all clients
        emit('chat_message', chat_message, broadcast=True)
    
    @app.route('/chat-messages', methods=['GET'])
    def handle_get_chat_messages():
        all_data = chat_collection.find({})
        response_list = []

        for document in all_data:
            # Remove the '_id' field as it's not JSON serializable
            del document['_id']
            response_list.append(document)
        
        return jsonify(response_list)

    @socketio.on('like')
    def chat_messages_like(data):
        message_id = data['id']
        print(message_id, flush = True)
        print("in the like", flush = True)
        print(type(message_id), flush = True)
        if chat_collection.find_one({"id": int(message_id)}) is not None:
            print("found the message ", flush = True)
            exists = chat_collection.find_one({"id": int(message_id)})
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
                    if(liked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is None and (disliked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is None)):
                        #if the message hasn't been liked or disliked by this user already
                            
                        current_id = {"id": int(message_id)}

                        # current_id will always exist because the message have to be up before the user can like it
                        current_chat_msg = chat_collection.find_one(current_id)
                        new_like_count = current_chat_msg.get('like_count', 0) +1
                        chat_collection.update_one(current_id,
                                                {"$set": {"like_count": new_like_count}})
                        liked_messages.insert_one({"username" : username_auth, "id" : int(message_id)})
                        emit('like_updated', {
                            'id': message_id,
                            'like_count': new_like_count,
                            'dislike_count': current_chat_msg.get('dislike_count', 0)
                        }, broadcast=True)

                        return jsonify({'like_count': new_like_count, 'dislike_count': current_chat_msg.get('dislike_count', 0)}), 200

                    elif(liked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is None and (disliked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is not None)):

                        print("in the new condiiton ",flush = True )
                        current_id = {"id": int(message_id)}

                        # current_id will always exist because the message have to be up before the user can like it
                        current_chat_msg = chat_collection.find_one(current_id)
                        new_like_count = current_chat_msg.get('like_count', 0) + 1
                        chat_collection.update_one(current_id,
                                               {"$set": {"like_count": new_like_count}})
                        liked_messages.insert_one({"username" : username_auth, "id" : int(message_id)})


                        updated_dislike_count = current_chat_msg.get('dislike_count', 0) -1
                        chat_collection.update_one(current_id,
                                               {"$set": {"dislike_count": updated_dislike_count}})
                        disliked_messages.delete_one({"username" : username_auth, "id" : int(message_id)})
                        emit('like_updated', {
                            'id': message_id,
                            'like_count': new_like_count,
                            'dislike_count': updated_dislike_count
                        }, broadcast=True)

                        return jsonify({'like_count': new_like_count, 'dislike_count': current_chat_msg.get('dislike_count', 0)}), 200


                    elif(liked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is not None and (disliked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is None)):
                        #if the message has been liked already, unlike it
                        

                        current_id = {"id": int(message_id)}
                        current_mgs = chat_collection.find_one(current_id)
                        new_like_count =  current_mgs['like_count']- 1
                        chat_collection.update_one(current_id,
                                                {"$set": {"like_count": new_like_count}})
                        liked_messages.delete_one({"username" : username_auth, "id" : int(message_id)})
                        emit('like_updated', {
                            'id': message_id,
                            'like_count': new_like_count,
                            'dislike_count': current_mgs.get('dislike_count', 0)
                        }, broadcast=True)

                        print("This is undo_like Like", flush= True)
                        return jsonify({'like_count': new_like_count, 'dislike_count': current_mgs.get('dislike_count', 0)})
                    
                    elif(liked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is None and (disliked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is not None)):
                        
                        # switch from dislike to like
                        current_id = {"id": int(message_id)}
                        current_msg = chat_collection.find_one(current_id)
                        updated_dislike_count = current_msg['dislike_count'] - 1
                        updated_like_count = current_msg.get('like_count', 0) +1
                        chat_collection.update_one(current_id,
                                                    {"$set": {"dislike_count": updated_dislike_count, "like_count": updated_like_count}})
                        disliked_messages.delete_one({"username" : username_auth, "id" : int(message_id)})
                        liked_messages.insert_one({"username" : username_auth, "id" : int(message_id)})
                        emit('like_updated', {
                            'id': message_id,
                            'like_count':  updated_like_count,
                            'dislike_count': updated_dislike_count
                        }, broadcast=True)
                        return jsonify({'like_count': updated_like_count, 'dislike_count': updated_dislike_count})
                    else:
                        return jsonify({"error": "Unauthorized"}), 401

                return jsonify({"error": "Unauthorized"}), 401
        else:
            print("message not found", flush = True)
            return jsonify({"error": "Unauthorized"}), 401

    @socketio.on('dislike')
    def chat_messages_dislike(data):
        message_id = data['id']
        if chat_collection.find_one({"id": int(message_id)}) is not None:
            exists = chat_collection.find_one({"id": int(message_id)})
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
                    if(liked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is None and (disliked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is None)):
                        #if the message has already been liked by this user or already disliked
                       
                        current_id = {"id": int(message_id)}
                        current_msg = chat_collection.find_one(current_id)
                        updated_dislike_count = current_msg.get('dislike_count', 0) + 1
                        chat_collection.update_one(current_id,
                                                    {"$set": {"dislike_count": updated_dislike_count}})
                        disliked_messages.insert_one({"username" : username_auth, "id" : int(message_id)})
                        emit('dislike_updated', {
                            'id': message_id,
                            'like_count': current_msg.get('like_count', 0),
                            'dislike_count': updated_dislike_count
                        }, broadcast=True)

                        return jsonify({"like_count": current_msg.get('like_count', 0), 'dislike_count': updated_dislike_count})
                      
                    elif (liked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is not None and (disliked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is None)):
                        #if the message has been liked already and a dislike is pressed, swap like and dislike
                        current_id = {"id": int(message_id)}
                        current_msg = chat_collection.find_one(current_id)
                        updated_dislike_count = current_msg.get('dislike_count',0) + 1
                        chat_collection.update_one(current_id,
                                               {"$set": {"dislike_count": updated_dislike_count}})
                        disliked_messages.insert_one({"username" : username_auth, "id" : int(message_id)})

                        new_like_count = current_msg.get('like_count', 0) - 1
                        chat_collection.update_one(current_id,
                                               {"$set": {"like_count": new_like_count}})
                        liked_messages.delete_one({"username" : username_auth, "id" : int(message_id)})
                        emit('dislike_updated', {
                        'id': message_id,
                        'like_count': new_like_count,
                        'dislike_count': updated_dislike_count
                        }, broadcast=True)

                        return jsonify({"like_count": current_msg.get('like_count', 0), 'dislike_count': updated_dislike_count})

                    elif(liked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is None and (disliked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is not None)):
                        #if the message has been liked already, unlike it
                        
                        current_id = {"id": int(message_id)}
                        current_msg = chat_collection.find_one(current_id)
                        updated_dislike_count = current_msg.get('dislike_count',0) - 1
                        chat_collection.update_one(current_id,
                                                    {"$set": {"dislike_count": updated_dislike_count}})
                        disliked_messages.delete_one({"username" : username_auth, "id" : int(message_id)})
                        emit('dislike_updated', {
                            'id': message_id,
                            'like_count': current_msg.get('like_count', 0),
                            'dislike_count': updated_dislike_count
                        }, broadcast=True)

                        return jsonify({"like_count": current_msg.get('like_count', 0), 'dislike_count': updated_dislike_count})
                    
                    elif(liked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is not None and (disliked_messages.find_one({"username" : username_auth, "id" : int(message_id)}) is None)):
                        
                        # switch from like to dislike
                        current_id = {"id": int(message_id)}
                        current_msg = chat_collection.find_one(current_id)
                        updated_like_count = current_msg.get('like_count',0) -1
                        updated_dislike_count = current_msg.get('dislike_count', 0) + 1
                        chat_collection.update_one(current_id,
                                                    {"$set": {"dislike_count": updated_dislike_count, "like_count": updated_like_count}})
                        disliked_messages.insert_one({"username" : username_auth, "id" : int(message_id)})
                        liked_messages.delete_one({"username" : username_auth, "id" : int(message_id)})
                        emit('dislike_updated', {
                            'id': message_id,
                            'like_count': current_msg.get('like_count', 0),
                            'dislike_count': updated_dislike_count
                        }, broadcast=True)

                        return jsonify({'like_count': updated_like_count, 'dislike_count': updated_dislike_count})
                    
                    else:
                        return jsonify({"error": "Unauthorized"}), 401

                return jsonify({"error": "Unauthorized"}), 401

            return jsonify({"error": "Unauthorized"}), 401

    @socketio.on('delete')
    def delete_chat_message(data):
        print("in the delete bend", flush = True)
        message_id = data['id']
        # Check if the auth token is present
        request_auth_token = request.cookies.get('auth_token')
        if request_auth_token is None:
            print('1', flush= True)
            return jsonify({"error": "Unauthorized - No auth token provided"}), 401

        # Verify the auth token
        hash_object = hashlib.sha256(request_auth_token.encode())
        hashed_request_authToken = hash_object.hexdigest()
        username_authToken = authToken.find_one({"auth_token": hashed_request_authToken})

        # Check if the user is authorized to delete the message
        if username_authToken is None:
            print('2', flush= True)
            return jsonify({"error": "Unauthorized - Invalid auth token"}), 401

        # (assuming the 'username' field in the message document indicates the message owner)

        message = chat_collection.find_one({"id": int(message_id)})

        if message is None:
            print(f'3 id = {message_id}', flush= True)
            return jsonify({"error": "Message not found"}), 404

        if username_authToken['username'] != message.get('username', ''):
            return emit('cannot_delete_other_msgs', {'error': "User cannot delete other's messages"})

        # Proceed with message deletion
        result = chat_collection.delete_one({"id": int(message_id)})

        if result.deleted_count > 0:
            print("emitting", flush = True)
            print(message_id, flush = True)
            print(type(message_id), flush = True)
            emit('delete_updated', {

                'id': message_id,

            }, broadcast=True)
            return jsonify({"success": True, "message": "Message deleted successfully."}), 200
        else:
            return jsonify({"error": "Message not found or could not be deleted"}), 404

    @socketio.on('file_upload')
    def handle_upload_files(json):

        print(f"\n\nbinary_data: {json}\n\n", flush = True)

        #{chunk: event.target.result, filename: file.name, finished: offset >= file.size}

        bin_data = json['chunk']
        user_named_filename = json['filename'].replace('/', '')
        status = json['finished']

        global file_storage
        if user_named_filename not in file_storage:
            file_storage[user_named_filename] = bytearray()

        file_storage[user_named_filename] += bin_data


        if status == True:
            username = return_username_of_authenticated_user() or "Guest"  # Ensure this function is adapted for WebSocket context
            complete_file_process(username, user_named_filename)
            return 

    def complete_file_process(username, user_named_filename):

        global file_storage
        data = file_storage[user_named_filename] 

        sig_check = data[:17]
        print(f'sig: {sig_check[:17]}', flush=True)
        file_extension = ''
        if len(sig_check) > 16:
             # Check for jpg signature
            if sig_check[:2] == b'\xFF\xD8':
                file_extension = 'jpg'
            # Check for png signature
            elif sig_check[:8] == b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A':
                file_extension = 'png'
            # Check for gif signature
            elif sig_check[:6] in [b'GIF87a', b'GIF89a']:
                file_extension = 'gif'
            # Check for mp4 signature
            elif b'ftypisom' in sig_check or b'ftypmp42' in sig_check or b'ftypMSNV' in sig_check:
                file_extension = 'mp4'
                print(f'\n\nMP4 is uploaded\n\n', flush = True)
            elif b'\x00\x00\x00\x14\x66\x74\x79\x70\x71\x74\x20\x20' in sig_check:
                file_extension = 'mov'
                print(f'\n\nMOV is uploaded\n\n', flush = True)
        
        #skip everything else if file extension 
        if file_extension != '':

            global file_count
            file_count += 1
            filename = f'file_{file_count}.{file_extension}'
            filename = filename.replace('/', '') # Prevent directory traversal
            
            file_path = os.path.join('images', filename)  # Ensure directory exists and is writable

            with open(file_path, 'wb') as f:
                f.write(data)

            # Construct the appropriate media tag based on the file type
            media_tag = generate_media_tag(filename, file_path)
            
            # Insert the message into the database (chat collection or similar)
            insert_media_message(username, media_tag)

            # Notify the user (optional)
            emit('upload_complete', {'message': 'Upload complete', 'file_path': file_path})

        else:
            print(f'\n\n\nfile_extension is empty \n\n\n', flush= True)

    def generate_media_tag(filename, filepath):
        # Determine the file extension
        if filename.endswith('.jpg') or filename.endswith('.png') or filename.endswith('.gif'):
            return f'<img src="/images/{filename}" alt="Uploaded image" style="max-width: 100%; max-height: 100%;">'
        elif filename.endswith('.mp4') or filename.endswith('.mov'):
            return f'<video controls autoplay muted style="max-width: 100%; max-height: 100%;"><source src="/images/{filename}" type="video/mp4">Your browser does not support the video tag.</video>'
        return ""

    def insert_media_message(username, media_tag):
        # Assuming a function to insert messages into a database or similar
        document_count = unique_id_counter.count_documents({})
        if document_count == 0:
            unique_id_counter.insert_one({"counter": 1})
        current_unique_counter = unique_id_counter.find_one_and_update({}, {'$inc': {'counter': 1}}, return_document=True)

        chat_message = {"message": media_tag, "username": username, "id": current_unique_counter['counter']}

        chat_collection.insert_one(chat_message)
        
        del chat_message['_id']

        # Broadcast the chat message to all clients
        emit('chat_message', chat_message, broadcast=True)
    
    @app.before_request
    def check_ban_status():
        ip = get_remote_address()
        current_time = time.time()

        if ip in banned_ips:
            ban_time = banned_ips[ip]
            if current_time < ban_time:
                time_left = int(ban_time - current_time)
                # Attach a flag to the request context to indicate this was a ban hit
                request.is_banned = True  
                return make_response(
                    jsonify(error="Banned", message=f"Access temporarily blocked. Please try again in {time_left} seconds."), 429
                )
            else:
                # Ban time has expired, remove the IP from the banned list
                del banned_ips[ip]

        # Initialize or reset the request count for IP
        if ip not in request_counts or current_time > request_counts[ip]['reset_time']:
            request_counts[ip] = {'count': 1, 'reset_time': current_time + 10}  # Reset every 10 seconds
        else:
            request_counts[ip]['count'] += 1

        remaining = max(0, 50 - request_counts[ip]['count'])
        print(f"IP {ip} has made {request_counts[ip]['count']} requests. {remaining} requests left before limit.", flush=True)

    @app.after_request
    def after_request_func(response):
        ip = get_remote_address()
        # Only reset count and set ban if this wasn't already a ban response
        if response.status_code == 429 and not getattr(request, 'is_banned', False):
            # Reset count and set ban on rate limit
            banned_ips[ip] = time.time() + 30
            request_counts[ip]['count'] = 0
            print(f"IP {ip} banned for exceeding rate limits. No more requests allowed for 30 seconds.", flush=True)
        return response

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return make_response(
            jsonify(error="Banned", message="Access temporarily blocked. Please try again in 30 seconds."), 429
        )

    return app, socketio

    
    
if __name__ == "__main__":
    app, socketio = create_app()
    socketio.run(app, debug=True, host="0.0.0.0", port=8080)