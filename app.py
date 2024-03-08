from flask import Flask, send_from_directory
import os

def create_app():

    app = Flask(__name__)

    # serve the index.html file
    @app.route('/')
    def home_page():

        build_dir = os.getcwd() + f"/client/build"
        print(f"\n\n\npath: {build_dir}\n\n\n")
        return send_from_directory(build_dir, path="index.html")
    
    #serve the CSS and JS to the server
    @app.route('/static/<folder>/<file>')
    def serve_js_css(folder, file):
        path = folder + '/' + file
        directory = os.getcwd() + f'/client/build/static'
        return send_from_directory(directory, path)
    
    #serving manifest_json
    @app.route("/manifest.json")
    def serve_manifest_json():
        json_path_dir = os.getcwd() + f"/client/build"
        return send_from_directory(json_path_dir,path = "manifest.json")
    
    @app.route("/logo192.png")
    def serve_logo():
        logo_path_dir = os.getcwd() + f"/client/build"
        return send_from_directory(logo_path_dir, path = "logo192.png")
    
    @app.route("/favicon.ico")
    def serve_favicon():
        favicon_path_dir = os.getcwd() + f"/client/build"
        return send_from_directory(favicon_path_dir, path = "favicon.ico")
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True,host = "0.0.0.0", port = 8080)
