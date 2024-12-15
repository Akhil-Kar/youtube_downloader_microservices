import pika
import yt_dlp
import requests

# RabbitMQ connection setup
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

# Function to download video
def download_video_from_url(download_id, url, resolution):
    # Update status to "In Progress"
    requests.post('http://localhost:5000/update_status', json={
        'download_id': download_id,
        'status': 'In Progress'
    })

    ydl_opts = {
        'format': f'bestvideo[height={resolution[:-1]}]+bestaudio/best[height={resolution[:-1]}]',
        'outtmpl': f'./downloads/{download_id}.%(ext)s',
        'quiet': True,
    }

    # ydl_opts = {
    #         'quiet': True,
    #         'format': f'bestvideo[height={resolution[:-1]}]+bestaudio/best[height={resolution[:-1]}]',
    #         'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
    #     }

    #     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    #         info = ydl.extract_info(url, download=True)
    #         file_path = ydl.prepare_filename(info)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Update status to "Completed"
        requests.post('http://localhost:5000/update_status', json={
            'download_id': download_id,
            'status': 'Completed'
        })
    except Exception as e:
        # Update status to "Failed" with error
        requests.post('http://localhost:5000/update_status', json={
            'download_id': download_id,
            'status': 'Failed',
            'error': str(e)
        })

def callback(ch, method, properties, body):
    print(f"Received message: {body}")
    download_id, url, resolution = body.decode().split("_20_")
    download_video_from_url(download_id, url, resolution)
    ch.basic_ack(delivery_tag=method.delivery_tag)

# Start consuming messages from the queue
channel.basic_qos(prefetch_count=1)  # Limit to 1 unacknowledged message per consumer
channel.basic_consume(queue='download_queue', on_message_callback=callback)

print(' [*] Waiting for download tasks. To exit press CTRL+C')
channel.start_consuming()
