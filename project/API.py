from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource,Api, reqparse, fields, marshal_with,abort
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import timedelta
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError

class AuthAwareApi(Api):
    def error_router(self, original_handler, error):
        if isinstance(error, (JWTExtendedException, PyJWTError)):
            return original_handler(error)
        return super().error_router(original_handler, error)

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)
jwt = JWTManager(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
api = AuthAwareApi(app)

class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')

    def __repr__(self):
        return f"User(name = {self.username}, email = {self.email})"

def get_current_user():
    identity = get_jwt_identity()

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        abort(401, message="Invalid user identity")

    user = db.session.get(UserModel, user_id)
    if user is None:
        abort(401, message="User no longer exists")

    return user


def require_admin(user):
    if user.role != "admin":
        abort(403, message="Admin access required")


def require_owner_or_admin(user, user_id):
    if user.id != user_id and user.role != "admin":
        abort(403, message="You cannot access this user")

login_args = reqparse.RequestParser()
login_args.add_argument("username", type=str, required=True)
login_args.add_argument("password", type=str, required=True)

user_args = reqparse.RequestParser()
user_args.add_argument(
    "username",
    type=str,
    required=True,
    help="Username is required and cannot be blank",
)
user_args.add_argument("email", type=str, help="Email is required", required=True)

users_fields = {
    'id': fields.Integer,
    'username': fields.String,
    'email': fields.String
}

create_user_args = user_args.copy()
create_user_args.add_argument(
    "password",
    type=str,
    required=True,
    help="Password is required and cannot be blank",
)

def validate_user_fields(args):
    username = args["username"]
    email = args["email"]

    if username is None or not username.strip():
        abort(400, message="Username cannot be blank")

    username = username.strip()
    if len(username) > 80:
        abort(400, message="Username cannot exceed 80 characters")

    if email is None:
        abort(400, message="Email is required")

    email = email.strip()
    if (
        len(email) > 120
        or email.count("@") != 1
        or any(character.isspace() for character in email)
    ):
        abort(400, message="Enter a valid email address")

    local, domain = email.split("@")
    if not local or not domain:
        abort(400, message="Enter a valid email address")

    return username, email

class User(Resource):
    @jwt_required()
    @marshal_with(users_fields)
    def get(self):
        current_user = get_current_user()
        require_admin(current_user)
        return UserModel.query.all()

    @marshal_with(users_fields)
    def post(self):
        args = create_user_args.parse_args()

        username, email = validate_user_fields(args)

        password = args["password"]
        if password is None or not 8 <= len(password) <= 128:
            abort(400, message="Password must be 8–128 characters")

        user = UserModel(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()
        return user, 201


class UserDetail(Resource):
    @jwt_required()
    @marshal_with(users_fields)
    def get(self, user_id):
        current_user = get_current_user()
        require_owner_or_admin(current_user, user_id)

        user = db.session.get(UserModel, user_id)
        if user is None:
            abort(404, message="User not found")
        return user

    @jwt_required()
    @marshal_with(users_fields)
    def put(self, user_id):
        current_user = get_current_user()
        require_owner_or_admin(current_user, user_id)

        user = db.session.get(UserModel, user_id)
        if user is None:
            abort(404, message="User not found")

        args = user_args.parse_args()
        username, email = validate_user_fields(args)

        user.username = username
        user.email = email
        db.session.commit()
        return user

    @jwt_required()
    def delete(self, user_id):
        current_user = get_current_user()
        require_admin(current_user)

        user = db.session.get(UserModel, user_id)
        if user is None:
            abort(404, message="User not found")

        db.session.delete(user)
        db.session.commit()
        return "", 204

class Login(Resource):
    def post(self):
        args = login_args.parse_args()
        user = UserModel.query.filter_by(username=args['username']).first()

        if user is None or not check_password_hash(user.password_hash, args['password']):
            return {"message": "Invalid username or password"}, 401

        token = create_access_token(identity=str(user.id))
        return {"access_token": token}, 200

api.add_resource(User, "/api/users/")
api.add_resource(UserDetail, "/api/users/<int:user_id>")
api.add_resource(Login, "/api/login/")

@app.route('/')
def home():
    return '<h1> Flask REST API </h1>'

@app.route("/api/me")
@jwt_required()
def current_user():
    user_id = get_jwt_identity()
    user = db.session.get(UserModel, int(user_id))

    if user is None:
        return {"message": "User not found"}, 404
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email
    }, 200

if __name__ == '__main__':
    with app.app_context():
        print("Database path:", db.engine.url.database)
        db.create_all()
    app.run(debug=True)
