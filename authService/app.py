from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
import jwt
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Initialize Flask app and database
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_jwt_secret_key'  # Secret key to encode JWT tokens
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User model for storing user data
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Function to verify the JWT token
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Check if token is passed in the headers
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 403

        try:
            # Decode the token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
        except:
            return jsonify({'message': 'Token is invalid!'}), 403

        return f(current_user, *args, **kwargs)

    return decorated_function

# Validate Token Function (for use by other microservices)
def validate_token(token):
    try:
        # Decode the token
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        current_user = User.query.get(data['user_id'])
        
        if current_user is None:
            return False, {'message': 'User not found!'}
        
        return True, current_user  # Return user object if token is valid
    except jwt.ExpiredSignatureError:
        return False, {'message': 'Token has expired!'}
    except jwt.InvalidTokenError:
        return False, {'message': 'Token is invalid!'}

# Register User Route
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Username and password are required!'}), 400

    # Check if user already exists
    existing_user = User.query.filter_by(username=data['username']).first()
    if existing_user:
        return jsonify({'message': 'User already exists!'}), 409

    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')

    # Create new user
    new_user = User(username=data['username'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully!'}), 201

# Login User Route (JWT Token Generation)
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Username and password are required!'}), 400

    # Check if user exists
    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials!'}), 401

    # Generate JWT token
    token = jwt.encode(
        {'user_id': user.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
        app.config['SECRET_KEY'], algorithm='HS256'
    )

    return jsonify({'token': token}), 200

# Protected Route (requires a valid token)
@app.route('/api/protected', methods=['GET'])
@token_required
def protected(current_user):
    return jsonify({'message': f'Hello, {current_user.username}'}), 200

# Example endpoint to show how another microservice can validate the token
@app.route('/api/validate', methods=['POST'])
def validate():
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({'message': 'Token is required!'}), 400

    valid, response = validate_token(token)

    if not valid:
        return jsonify(response), 403  # Invalid token

    return jsonify({'message': 'Token is valid!', 'user': response.username}), 200

# Run the application
if __name__ == '__main__':
    with app.app_context():
        db.create_all()    # Create the SQLite database tables if they don't exist
    app.run(debug=True, port=5001)
