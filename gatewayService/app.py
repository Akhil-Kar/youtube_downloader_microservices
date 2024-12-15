import pika
import yt_dlp
from flask import Flask, request, jsonify
import threading
import uuid

app = Flask(__name__)

download_status = {}

connection_params = pika.ConnectionParameters(
    host='localhost',
    port=5672,
    virtual_host='/',
    credentials=pika.PlainCredentials('root', 'root')
)
connection = pika.BlockingConnection(connection_params)
channel = connection.channel()

# Declare a queue
channel.queue_declare(queue='download_queue', durable=True)

# Temporary directory to store downloaded videos
# DOWNLOAD_DIR = "downloads"
# os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route("/resolutions", methods=["POST"])
def get_resolutions():
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
def download_video():
    youtube_url = request.json.get('url')
    resolution = request.json.get('resolution')

    if not youtube_url or not resolution:
        return jsonify({"error": "URL and resolution required"}), 400

    # Generate a unique download ID
    download_id = str(uuid.uuid4())
    download_status[download_id] = {'status': 'Queued', 'url': youtube_url, 'resolution': resolution}

    # Add the download task to the RabbitMQ queue
    channel.basic_publish(exchange='',
                          routing_key='download_queue',
                          body=f"{download_id}_20_{youtube_url}_20_{resolution}",
                          properties=pika.BasicProperties(delivery_mode=2))

    return jsonify({"message": "Download started", "download_id": download_id}), 202

@app.route('/status/<download_id>', methods=['GET'])
def get_status(download_id):
    status = download_status.get(download_id)
    if status:
        return jsonify(status)
    else:
        return jsonify({"error": "Download ID not found"}), 404

@app.route('/status', methods=['GET'])
def get_all_statuses():
    """Get the status of all downloads"""
    if download_status:
        return jsonify(download_status)
    else:
        return jsonify({"error": "No download tasks available"}), 404

@app.route('/update_status', methods=['POST'])
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
