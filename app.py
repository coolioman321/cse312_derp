from flask import Flask, send_from_directory, make_response, url_for, render_template
def create_app():

    app = Flask(__name__)


    @app.route('/')
    def home_page():
        headers ={
            "X-Content-Type-Options": "nosniff",
            "Content-Length": "5"
        }
      #sending example response from the root page
        return Flask.response_class(b'hello',status= 200,headers=headers,mimetype= "text/plain")
    return app

    @app.route('/js')
    def js_page():
        return render_template('js.html')

    return app
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True,host = "0.0.0.0", port = 8080)
