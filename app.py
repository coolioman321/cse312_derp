from flask import Flask, make_response, render_template, send_from_directory, request, redirect, url_for,jsonify
from pymongo import MongoClient
from util.helper import validate_password, escape_html, extract_credentials
import bcrypt
import hashlib
from util.auth_token_functions import check_user_auth, generate_auth_token

mongo_client = MongoClient('mongo')
db = mongo_client['derp']
users = db['users']
authToken = db['auth_token']
unique_id_counter = db['counter']
chat_collection = db['chat']

def create_app():
    app = Flask(__name__)

    # Serve the home page
    @app.route('/')
    def home_page():
        request_authToken = request.cookies.get('auth_token')
        user_auth_status = check_user_auth(request_authToken)
        rendered_template = render_template('index.html', user_logged_in=user_auth_status)

        if user_auth_status:
            hash_object = hashlib.sha256(request_authToken.encode())
            hashed_token = hash_object.hexdigest()
            auth_username = authToken.find_one({"auth_token": hashed_token})
            modified_template = rendered_template.replace("Guest", auth_username["username"])

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

            #insert current message into DB
            chat_collection.insert_one(response_info)
            
            #increment the counter by 1
            query = {"counter": {"$exists": True}}
            new_values = {"$set": {"counter": current_unique_counter['counter']+1}}
            unique_id_counter.update_one(query, new_values)

            # print(f"message: {message}")  

            #stores the post message in a database

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

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=8080)