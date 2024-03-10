from flask import Flask, render_template


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

    @app.route('/css')
    def css_page():
        headers = {
            "X-Content-Type-Options": "nosniff",
            "Content-Length": "5"
        }

        return render_template('css.html', headers=headers)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True,host = "0.0.0.0", port = 8080)
