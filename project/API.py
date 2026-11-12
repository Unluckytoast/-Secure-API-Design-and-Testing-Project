from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource,Api, reqparse, fields, marshal_with,abort

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
api = Api(app)

class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f"User(name = {self.username}, email = {self.email})"

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

class User(Resource):
    @marshal_with(users_fields)
    def get(self):
        users = UserModel.query.all()
        return  users

    @marshal_with(users_fields)
    def post(self):
        args = user_args.parse_args()
        user = UserModel(username=args['username'], email=args['email'])
        db.session.add(user)
        db.session.commit()
        users = UserModel.query.all()
        return users, 201

api.add_resource(User, "/api/users/")

@app.route('/')
def home():
    return '<h1> Flask REST API <h1>'

if __name__ == '__main__':
    app.run(debug=True)
