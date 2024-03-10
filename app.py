from flask import Flask, send_from_directory, after_this_request
import os

def create_app():
    app = Flask(__name__)

    def add_security_headers(response):
        """
        Adds security headers to the response to ensure that files
        are served with the correct MIME type and with the
        'X-Content-Type-Options: nosniff' header.
        """
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.route('/')
    def home_page():
        build_dir = os.getcwd() + "/client/build"
        print(f"\n\n\npath: {build_dir}\n\n\n")

        @after_this_request
        def set_header(response):
            return add_security_headers(response)

        return send_from_directory(build_dir, "index.html")
    
    @app.route('/static/<folder>/<file>')
    def serve_js_css(folder, file):
        path = folder + '/' + file
        directory = os.getcwd() + '/client/build/static'

        @after_this_request
        def set_header(response):
            return add_security_headers(response)

        return send_from_directory(directory, path)
    
    @app.route("/manifest.json")
    def serve_manifest_json():
        json_path_dir = os.getcwd() + "/client/build"

        @after_this_request
        def set_header(response):
            return add_security_headers(response)

        return send_from_directory(json_path_dir, "manifest.json")
    
    @app.route("/logo192.png")
    def serve_logo():
        logo_path_dir = os.getcwd() + "/client/build"

        @after_this_request
        def set_header(response):
            return add_security_headers(response)

        return send_from_directory(logo_path_dir, "logo192.png")
    
    @app.route("/favicon.ico")
    def serve_favicon():
        favicon_path_dir = os.getcwd() + "/client/build"

        @after_this_request
        def set_header(response):
            return add_security_headers(response)

        return send_from_directory(favicon_path_dir, "favicon.ico")
    
    @app.route ("/cat.jpg")
    def serve_cat():
        cat_path_dir = os.getcwd() + "/client/build"

        @after_this_request
        def set_header(response):
            return add_security_headers(response)

        return send_from_directory(cat_path_dir, "cat.jpg")
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=8080)
