import boto3
import json
import time
import sys

def create_kinesis_client():
    """Create a Kinesis client that connects to LocalStack"""
    return boto3.client(
        'kinesis',
        endpoint_url='http://localhost:4566',  # LocalStack default endpoint
        region_name='us-east-1',
        aws_access_key_id='test',
        aws_secret_access_key='test'
    )

def consume_stream(stream_name):
    """Consume data from a Kinesis stream"""
    kinesis_client = create_kinesis_client()
    
    # Get shard details
    try:
        response = kinesis_client.describe_stream(StreamName=stream_name)
        shard_id = response['StreamDescription']['Shards'][0]['ShardId']
    except Exception as e:
        print(f"Error accessing stream {stream_name}: {e}")
        return
    
    # Get shard iterator
    shard_iterator = kinesis_client.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType='LATEST'
    )['ShardIterator']
    
    print(f"Starting to consume from {stream_name}. Press Ctrl+C to exit.")
    
    try:
        while True:
            # Get records from the shard
            response = kinesis_client.get_records(
                ShardIterator=shard_iterator,
                Limit=100
            )
            
            records = response['Records']
            if records:
                print(f"\nReceived {len(records)} records from {stream_name}:")
                for i, record in enumerate(records, 1):
                    data = json.loads(record['Data'].decode('utf-8'))
                    print(f"Record {i}: {json.dumps(data, indent=2)}")
            else:
                print(".", end="", flush=True)
            
            # Update shard iterator for next set of records
            shard_iterator = response['NextShardIterator']
            time.sleep(1)  # Avoid throttling
            
    except KeyboardInterrupt:
        print(f"\nStopped consuming from {stream_name}")
    except Exception as e:
        print(f"\nError consuming from {stream_name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python consumer.py <stream_name>")
        print("Available streams: pin_data_geo, pin_data_pin, pin_data_user")
        sys.exit(1)
    
    stream_name = sys.argv[1]
    consume_stream(stream_name)
