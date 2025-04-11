from flask import Flask, render_template
from flask_login import LoginManager
from flask_pymongo import PyMongo
from config import Config
from bson import ObjectId

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize MongoDB
mongo = PyMongo(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

# Register blueprints
from main import main as main_blueprint
app.register_blueprint(main_blueprint)

from auth import auth as auth_blueprint
app.register_blueprint(auth_blueprint, url_prefix='/auth')

from habits import habits as habits_blueprint
app.register_blueprint(habits_blueprint, url_prefix='/habits')

# Main routes
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True) 