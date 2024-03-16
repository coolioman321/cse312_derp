from flask import Flask, make_response, render_template, send_from_directory, request, redirect, url_for
from pymongo import MongoClient
from util.helper import validate_password, escape_html, extract_credentials
import bcrypt
import secrets
import hashlib
from util.auth_token_functions import check_user_auth, generate_auth_token

mongo_client = MongoClient('mongo')
db = mongo_client['derp']
users = db['users']
authToken = db['auth_token']

def login_register_form():
    login_register_strings = '''<form id="registrationForm" action="/register" method="POST">
        <h2>Register</h2>
        <div>
            <label for="username">Username:</label>
            <input type="text" id="username" name="username" required>
        </div>
        <div>
            <label for="password">Password:</label>
            <input type="password" id="password" name="password" required minlength="8">
        </div>
        <div>
            <label for="confirmPassword">Confirm Password:</label>
            <input type="password" id="confirmPassword" name="confirmPassword" required>
        </div>
        <button type="submit">Register</button>
    </form>

    <!-- Login Form -->
    <!-- Login: -->
    <form id="loginForm" action="/login" method="POST">
        <h2>Login</h2>
        <div>
            <label for="username">Username:</label>
            <input type="text" id="login_username" name="login_username" required>
        </div>
        <div>
            <label for="password">Password:</label>
            <input type="password" id="login_password" name="login_password" required minlength="8">
        </div>
        <button type="submit">Login</button>
    </form>'''

    return str(login_register_strings)

def log_out_form():
    logout_form_string = '''<form action="/log-out" id = 'log_out' method="post">
            <input type="submit" value="Log out">
        </form>'''
    return str(logout_form_string)

def create_app():
    app = Flask(__name__)

    # Serve the home page
    @app.route('/')
    def home_page():
        user_auth_status = check_user_auth(request.cookies.get('auth_token'))
        rendered_template = render_template('index.html', user_logged_in=user_auth_status)

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
    def host_js():
        response = send_from_directory('.', 'app.js', mimetype='text/javascript')
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
            print(f"\n\n\nTRUE\n\n\n")

            if(bcrypt.checkpw(password.encode('utf-8'),stored_password)):
            #if the passwords match
                with open("templates/index.html", "rt") as file:
                    content = file.read()
                    content =  content.replace(login_register_form(),log_out_form())
                    content = content.replace("guest", username)

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

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=8080)