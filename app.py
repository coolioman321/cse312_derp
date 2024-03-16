import datetime
import hashlib
import os
from lib2to3.btm_utils import tokens

from flask import Flask, make_response, render_template, send_from_directory, request, redirect, url_for, session
from pymongo import MongoClient
from util.helper import validate_password, escape_html,extract_credentials
import bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'
mongo_client = MongoClient('mongo')
db = mongo_client['derp']
users = db['users']

def create_app():
    app = Flask(__name__)

    # Serve the home page
    @app.route('/')
    def home_page():
        loggedin = 'user_logged_in' in session
        content = render_template('index.html', loggedin=loggedin)
        response = make_response(content, 200)
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
        stored_record = users.find_one({"username":username})

        if stored_record is not None:
            stored_password = stored_record["password"]

            if(bcrypt.checkpw(password.encode('utf-8'),stored_password)):
            #if the passwords match

                # login then set session
                session['user_logged_in'] = True
                session['username'] = username

                with open("templates/index.html", "rt") as file:
                    content = file.read()
                    content = content.replace('<form type = hidden>','<form ')
                    content =  content.replace("Register:",'< form type = hidden >')
                    content = content.replace("Login:",'<form type = hidden>')
                    content = content.replace("{{username}}", username)

                file = open("templates/index.html", "w")
                file.write(content)
                file.close()



                ##### SET AUTHENTICATION #####
        return redirect(url_for('home_page'))

    @app.route('/log-out', methods=['POST'])
    def logout(request):
        with open("templates/index.html", "rt") as file:
            content = file.read()


            content= content.replace('< form type = hidden >',"Register:",)
            content = content.replace('<form type = hidden>',"Login:",)
            content = content.replace('form type = hidden', '<form >')
            file.close()
            file = open("templates/index.html", "w")
            file.write(content)
            file.close()

            ####REMOVE AUTHENTICATION#####

        return redirect(url_for('home_page'))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=8080)