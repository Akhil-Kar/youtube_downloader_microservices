import pika
import yt_dlp
from flask import Flask, request, jsonify, send_file
import threading
import uuid
from flask_sqlalchemy import SQLAlchemy
import jwt
import datetime
from functools import wraps

import boto3
from botocore.exceptions import NoCredentialsError
from io import BytesIO

import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET')  # Secret key to encode JWT tokens
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class DownloadStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    download_id = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(200), nullable=False)

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
            # current_user = User.query.get(data['user_id'])
            current_user = data['user_id']
        except:
            return jsonify({'message': 'Token is invalid!'}), 403

        return f(current_user, *args, **kwargs)

    return decorated_function

download_status = {}

connection_params = pika.ConnectionParameters(
    host=os.getenv('RM_HOST'),
    port=os.getenv('RM_PORT'),
    virtual_host='/',
    credentials=pika.PlainCredentials(os.getenv('RM_USER'), os.getenv('RM_PASSWORD'))
)
connection = pika.BlockingConnection(connection_params)
channel = connection.channel()

s3 = boto3.client('s3')

# Declare a queue
channel.queue_declare(queue='download_queue', durable=True)

# Temporary directory to store downloaded videos
# DOWNLOAD_DIR = "downloads"
# os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route("/resolutions", methods=["POST"])
@token_required
def get_resolutions(username):
    data = request.get_json()
    url = data.get("url")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'format': 'best',
            'extractor_args': {
                'youtube': {
                    'skip': ['comments']  # Avoid fetching unnecessary data like comments
                }
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            resolutions = sorted(set([f"{fmt['height']}p" for fmt in formats if fmt.get('vcodec') != 'none' and fmt.get('height')]))

        return jsonify({"title": info.get('title', 'Unknown Title'), "resolutions": resolutions})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/download', methods=['POST'])
@token_required
def download_video(username):
    youtube_url = request.json.get('url')
    resolution = request.json.get('resolution')
    title = request.json.get('title')

    if not youtube_url or not resolution:
        return jsonify({"error": "URL and resolution required"}), 400

    # Generate a unique download ID
    download_id = str(uuid.uuid4()).replace("-", "")[:8]
    download_status[download_id] = {'status': 'Queued', 'url': youtube_url, 'resolution': resolution}

    # Add the download task to the RabbitMQ queue
    channel.basic_publish(exchange='',
                          routing_key='download_queue',
                          body=f"{download_id}_20_{youtube_url}_20_{resolution}_20_{title}",
                          properties=pika.BasicProperties(delivery_mode=2))

    return jsonify({"message": "Download started", "download_id": download_id}), 202

@app.route('/status/<download_id>', methods=['GET'])
@token_required
def get_status(download_id, username):
    status = download_status.get(download_id)
    if status:
        return jsonify(status)
    else:
        return jsonify({"error": "Download ID not found"}), 404

@app.route('/status', methods=['GET'])
@token_required
def get_all_statuses(username):
    """Get the status of all downloads"""
    if download_status:
        return jsonify(download_status)
    else:
        return jsonify({"error": "No download tasks available"}), 404

@app.route('/update_status', methods=['POST'])
# @token_required
def update_status():
    download_id = request.json.get('download_id')
    status = request.json.get('status')
    error = request.json.get('error')

    if not download_id or not status:
        return jsonify({"error": "Download ID and status required"}), 400

    if download_id in download_status:
        download_status[download_id]['status'] = status
        if error:
            download_status[download_id]['error'] = error
        return jsonify({"message": "Status updated successfully"})
    else:
        return jsonify({"error": "Download ID not found"}), 404

def get_s3_file(bucket_name, s3_file_key):
    try:
        # Retrieve the file from S3 as a stream (without saving it locally)
        response = s3.get_object(Bucket=bucket_name, Key=s3_file_key)
        
        # Extract the file content as a stream
        file_stream = response['Body']
        return file_stream
    except Exception as e:
        print(f"Error retrieving file from S3: {str(e)}")
        return None

@app.route('/download/<status_id>', methods=['POST'])
@token_required
def download_file(username, status_id):
    bucket_name = 'youtubemicroservice'
    
    key = '';
    respone = s3.list_objects_v2(Bucket=bucket_name, Prefix="media")
    for content in respone.get('Contents'):
        if status_id in content.get('Key'):
            key = content.get('Key')

    # Get the file stream from S3
    file_stream = get_s3_file(bucket_name, key)
    
    if file_stream:
        # Send the file as a response, stream the content to the client
        return send_file(
            file_stream,
            mimetype='application/octet-stream',  # You can set the correct MIME type if needed
            as_attachment=True,
            download_name=key[15:]  # This is the name the file will have when downloaded
        )
    else:
        return "Error retrieving file", 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
