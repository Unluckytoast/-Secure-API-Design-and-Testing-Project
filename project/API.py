from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource,Api, reqparse, fields, marshal_with,abort
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import timedelta
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)
jwt = JWTManager(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
api = Api(app)

class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"User(name = {self.username}, email = {self.email})"

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

class User(Resource):
    @marshal_with(users_fields)
    def get(self):
        users = UserModel.query.all()
        return  users

    @marshal_with(users_fields)
    def post(self):
        args = create_user_args.parse_args()

        if not args['password']:
            abort(400, message="Password is required")

        user = UserModel(username=args['username'], email=args['email'], password_hash=generate_password_hash(args['password']))
        db.session.add(user)
        db.session.commit()
        return user, 201

class UserDetail(Resource):
    @marshal_with(users_fields)
    def get(self, user_id):
        user = db.session.get(UserModel, user_id)
        if user is None:
            abort(404, message="User not found")
        return user

    @marshal_with(users_fields)
    def put(self, user_id):
        user = db.session.get(UserModel, user_id)
        if user is None:
            abort(404, message="User not found")
        args = user_args.parse_args()
        user.username = args['username']
        user.email = args['email']
        db.session.commit()
        return user

    def delete(self, user_id):
        user = db.session.get(UserModel, user_id)
        if user is None:
            abort(404, message="User not found")
        db.session.delete(user)
        db.session.commit()
        return '', 204

class Login(Resource):
    def post(self):
        args = login_args.parse_args()
        user = UserModel.query.filter_by(username=args['username']).first()

        if user is None or not check_password_hash(user.password_hash, args['password']):
            return {"message": "Invalid username or password"}, 401

        token = create_access_token(identity=user.id)
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
        db.create_all()
    app.run(debug=True)
