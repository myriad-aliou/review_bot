from flask import Flask
from api.endpoints import api

def create_app():
    """Factory pattern pour créer l'application Flask"""
    app = Flask(__name__)
    api.init_app(app)
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)