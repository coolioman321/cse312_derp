from flask import Flask,make_response,render_template

def create_app():

    app = Flask(__name__)


    @app.route('/')
    def home_page():
        response = make_response(render_template('index.html'),200)
        response.headers["X-Content-Type-Options"] ="nosniff"
        response.headers["Content-Type"] = 'text/html'
      #sending example response from the root page
        return response

    @app.route('/images/download.jpg')
    def host_image():
        headers ={
        "X-Content-Type-Options": "nosniff"
        }
        with open('images/download.jpg', "rb") as file:
            content = file.read()
        return Flask.response_class(content,status= 200,headers=headers,mimetype= "image/jpeg")

    @app.route('/style.css')
    def  host_css():
        headers ={
            "X-Content-Type-Options": "nosniff"
        }
        with open('style.css', "rb") as file:
            content = file.read()
        return Flask.response_class(content,status= 200,headers=headers,mimetype= "text/css")

    @app.route('/app.js')
    def host_js():
        headers ={
            "X-Content-Type-Options": "nosniff"
        }
        with open('app.js', "rb") as file:
            content = file.read()
        return Flask.response_class(content,status= 200,headers=headers,mimetype= "text/javascript")

    return app

    @app.route('/js')
    def js_page():
        return render_template('js.html')

    return app
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True,host = "0.0.0.0", port = 8080)
