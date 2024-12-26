import pika
import yt_dlp
import requests
import boto3
from botocore.exceptions import NoCredentialsError
import os

s3 = boto3.client('s3')

def upload_file_to_s3(local_file, bucket_name, s3_file):
    try:
        s3.upload_file(local_file, bucket_name, s3_file)
        # s3.download_file(bucket_name, s3_file, 'return.txt')
        print(f"File {local_file} uploaded successfully to {bucket_name}/{s3_file}")
    except NoCredentialsError:
        print("Credentials not available.")
    except Exception as e:
        print(f"Error: {str(e)}")

# RabbitMQ connection setup
connection_params = pika.ConnectionParameters(
    host=os.getenv('RM_HOST'),
    port=os.getenv('RM_PORT'),
    virtual_host='/',
    credentials=pika.PlainCredentials(os.getenv('RM_USER'), os.getenv('RM_PASSWORD'))
)
connection = pika.BlockingConnection(connection_params)
channel = connection.channel()

# Declare a queue
channel.queue_declare(queue='download_queue', durable=True)

status_url = f'http://{os.getenv('STATUS_URL')}:5000/update_status'

# Function to download video
def download_video_from_url(download_id, url, resolution, title):
    # Update status to "In Progress"
    requests.post(status_url, json={
        'download_id': download_id,
        'status': 'In Progress'
    })

    ydl_opts = {
        'format': f'bestvideo[height={resolution[:-1]}]+bestaudio/best[height={resolution[:-1]}]',
        'outtmpl': f'./downloads/{download_id}_{title}.%(ext)s',
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
        
        upload_file_to_s3(f'./downloads/{download_id}_{title}.webm', 'youtubemicroservice', f'media/{download_id}_{title}.mp4')
        
        # Update status to "Completed"
        requests.post(status_url, json={
            'download_id': download_id,
            'status': 'Completed'
        })
    except Exception as e:
        # Update status to "Failed" with error
        requests.post(status_url, json={
            'download_id': download_id,
            'status': 'Failed',
            'error': str(e)
        })

def callback(ch, method, properties, body):
    print(f"Received message: {body}")
    download_id, url, resolution, title = body.decode().split("_20_")
    download_video_from_url(download_id, url, resolution, title)
    ch.basic_ack(delivery_tag=method.delivery_tag)

# Start consuming messages from the queue
channel.basic_qos(prefetch_count=1)  # Limit to 1 unacknowledged message per consumer
channel.basic_consume(queue='download_queue', on_message_callback=callback)

print(' [*] Waiting for download tasks. To exit press CTRL+C')
channel.start_consuming()
