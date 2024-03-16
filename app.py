from flask import Flask, make_response, render_template, send_from_directory

def create_app():
    app = Flask(__name__)

    # Serve the home page
    @app.route('/')
    def home_page():
        response = make_response(render_template('index.html'), 200)
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

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=8080)