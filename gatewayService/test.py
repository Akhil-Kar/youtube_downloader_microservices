import boto3
from botocore.exceptions import NoCredentialsError

# Set your credentials manually
aws_access_key_id = 'AKIA3LWC6D43CCHIRUXS'
aws_secret_access_key = 'VnojfiwhIjanwtmoLBnwjJFnjx1rq/c697Jbg7+h'
region_name = 'ap-south-1'

# Create a session using the above credentials
# session = boto3.Session(
#     aws_access_key_id=aws_access_key_id,
#     aws_secret_access_key=aws_secret_access_key,
#     region_name=region_name
# )

# Now you can create an S3 client or resource
# s3 = session.client('s3')
s3 = boto3.client('s3')

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

def upload_file_to_s3(local_file, bucket_name, s3_file):
    try:
        # s3.upload_file(local_file, bucket_name, s3_file)
        # s3.download_file(bucket_name, s3_file, 'return.txt')
        respone = s3.list_objects_v2(Bucket=bucket_name, Prefix="media")
        # print(respone.get('Contents'))
        for content in respone.get('Contents'):
            print("b28b5e61" in content.get('Key'))
            print(content.get('Key')[15:])
        # print(f"File {local_file} uploaded successfully to {bucket_name}/{s3_file}")
    except NoCredentialsError:
        print("Credentials not available.")
    except Exception as e:
        print(f"Error: {str(e)}")

# Example usage
upload_file_to_s3('requirements.txt', 'youtubemicroservice', 'require/file.txt')
