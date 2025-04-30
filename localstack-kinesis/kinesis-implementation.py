import requests
from time import sleep
import random
from multiprocessing import Process
import boto3
import json
import sqlalchemy
from sqlalchemy import text
from threading import Thread


random.seed(100)


class AWSDBConnector:
    def __init__(self):
        self.HOST = "localhost"
        self.USER = 'luke'
        self.PASSWORD = '314159luke'
        self.DATABASE = 'pinterest_data'
        self.PORT = 5432
        
    def create_db_connector(self):
        engine = sqlalchemy.create_engine(f"postgresql+psycopg2://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DATABASE}")
        return engine


def create_kinesis_client():
    """Create a Kinesis client that connects to LocalStack"""
    return boto3.client(
        'kinesis',
        endpoint_url='http://localhost:4566',  # LocalStack default endpoint
        region_name='us-east-1',
        aws_access_key_id='test',
        aws_secret_access_key='test'
    )


def create_streams_if_not_exist(stream_names, kinesis_client):
    """Create Kinesis streams if they don't exist yet"""
    existing_streams = kinesis_client.list_streams()['StreamNames']
    
    for stream_name in stream_names:
        if stream_name not in existing_streams:
            print(f"Creating stream: {stream_name}")
            kinesis_client.create_stream(
                StreamName=stream_name,
                ShardCount=1
            )
            # Wait for stream to become active
            waiter = kinesis_client.get_waiter('stream_exists')
            waiter.wait(StreamName=stream_name)
    
    print("Streams are ready")


def run_infinite_post_data_loop():
    """Main loop for extracting data and sending to Kinesis"""
    # Create a Kinesis client
    kinesis_client = create_kinesis_client()
    
    # Define stream names for different data types
    stream_names = ['pin_data_geo', 'pin_data_pin', 'pin_data_user']
    
    # Create streams if they don't exist
    create_streams_if_not_exist(stream_names, kinesis_client)
    
    # Database connector
    new_connector = AWSDBConnector()
    
    while True:
        sleep(random.randrange(0, 2))
        random_row = random.randint(0, 11000)
        engine = new_connector.create_db_connector()

        with engine.connect() as connection:
            # Query Pinterest data
            pin_string = text(f"SELECT * FROM pinterest_data LIMIT 1 OFFSET {random_row}")
            pin_selected_row = connection.execute(pin_string)
            
            for row in pin_selected_row:
                pin_result = dict(row._mapping)

            # Query geolocation data
            geo_string = text(f"SELECT * FROM geolocation_data LIMIT 1 OFFSET {random_row}")
            geo_selected_row = connection.execute(geo_string)
            
            for row in geo_selected_row:
                geo_result = dict(row._mapping)

            # Query user data
            user_string = text(f"SELECT * FROM user_data LIMIT 1 OFFSET {random_row}")
            user_selected_row = connection.execute(user_string)
            
            for row in user_selected_row:
                user_result = dict(row._mapping)
            
            # Send data to Kinesis streams
            try:
                # Convert dictionaries to strings for Kinesis
                geo_data = json.dumps(geo_result, default=str).encode('utf-8')
                pin_data = json.dumps(pin_result, default=str).encode('utf-8')
                user_data = json.dumps(user_result, default=str).encode('utf-8')
                
                # Put records into respective streams
                kinesis_client.put_record(
                    StreamName='pin_data_geo',
                    Data=geo_data,
                    PartitionKey='partition_key'
                )
                
                kinesis_client.put_record(
                    StreamName='pin_data_pin',
                    Data=pin_data,
                    PartitionKey='partition_key'
                )
                
                kinesis_client.put_record(
                    StreamName='pin_data_user',
                    Data=user_data,
                    PartitionKey='partition_key'
                )
                
                print("Data sent to Kinesis successfully")
                
            except Exception as e:
                print(f"Error sending data to Kinesis: {e}")


def consume_kinesis_stream(stream_name):
    """Consumer function to read data from a Kinesis stream"""
    kinesis_client = create_kinesis_client()
    
    # Get shard iterator
    response = kinesis_client.describe_stream(StreamName=stream_name)
    shard_id = response['StreamDescription']['Shards'][0]['ShardId']
    
    shard_iterator = kinesis_client.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType='LATEST'
    )['ShardIterator']
    
    print(f"Starting to consume from {stream_name}")
    
    while True:
        response = kinesis_client.get_records(
            ShardIterator=shard_iterator,
            Limit=100
        )
        
        records = response['Records']
        if records:
            for record in records:
                data = json.loads(record['Data'].decode('utf-8'))
                print(f"{stream_name} received data: {data}")
        
        # Get the next shard iterator
        shard_iterator = response['NextShardIterator']
        sleep(1)  # Avoid throttling


if __name__ == "__main__":
    # Start consumer threads for each stream
    consumer_threads = [
        Thread(target=consume_kinesis_stream, args=('pin_data_geo',), daemon=True),
        Thread(target=consume_kinesis_stream, args=('pin_data_pin',), daemon=True),
        Thread(target=consume_kinesis_stream, args=('pin_data_user',), daemon=True)
    ]
    
    for thread in consumer_threads:
        thread.start()
    
    # Start the producer loop
    run_infinite_post_data_loop()
