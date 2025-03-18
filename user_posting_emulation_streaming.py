import requests
import json
import yaml
import random
import sqlalchemy
from time import sleep
from datetime import datetime
from sqlalchemy import text

# Load database credentials
with open("local_db_creds.yaml", "r") as f:
    db_creds = yaml.safe_load(f)

# Load API configuration
with open("api_creds.yaml", "r") as f:
    api_creds = yaml.safe_load(f)

API_INVOKE_URL = api_creds["API_INVOKE_URL"]
HEADERS = {"Content-Type": "application/json"}


class KinesisStreamer:
    def __init__(self, batch_mode=False):
        """
        Initialize the KinesisStreamer class.
        :param batch_mode: If True, use 'records' API; otherwise, use 'record' API.
        """
        self.stream_name = "Kinesis-Prod-Stream"
        self.batch_mode = batch_mode
        self.invoke_url = f"{API_INVOKE_URL}/streams/{self.stream_name}/{'records' if batch_mode else 'record'}"
        self.max_batch_size = 500  # Maximum batch size for 'records' mode, Kinesis limit per PutRecords call

    def send_to_kinesis(self, data, partition_key):
        """
        Send a single record to Kinesis (non-batch mode).
        """
        payload = {
            "StreamName": self.stream_name,
            "Data": json.dumps(data),  # Convert to JSON string
            "PartitionKey": partition_key,
        }

        try:
            response = requests.put(
                self.invoke_url,
                headers=HEADERS,
                json=payload,
            )

            if response.status_code == 200:
                print(f"Successfully sent record to partition: {partition_key}")
            else:
                print(
                    f"Failed to send record: {response.status_code} - {response.text}"
                )
        except Exception as e:
            print(f"API Error: {str(e)}")

    def send_batch_to_kinesis(self, records, partition_key):
        """
        Send multiple records in a single batch request to Kinesis (batch mode).
        """
        payload = {
            "records": [
                {"data": json.dumps(record), "partition-key": partition_key}
                for record in records
            ]
        }

        try:
            response = requests.put(
                self.invoke_url,
                headers=HEADERS,
                json=payload,
            )

            if response.status_code == 200:
                print(f"Successfully sent {len(records)} records to {partition_key}")
            else:
                print(f"Failed to send batch: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"API Error: {str(e)}")


class DatabaseStreamer:
    def __init__(self, batch_mode=False):
        """
        Initialize the DatabaseStreamer class.
        :param batch_mode: If True, use batch processing for Kinesis.
        """
        self.kinesis = KinesisStreamer(batch_mode=batch_mode)
        self.batch_mode = batch_mode
        self.table_config = {
            "pinterest_data": {"index_col": "index"},
            "geolocation_data": {"index_col": "ind"},
            "user_data": {"index_col": "ind"},
        }

    def _get_db_connection(self):
        engine = sqlalchemy.create_engine(
            f"mysql+pymysql://{db_creds['RDS_USER']}:{db_creds['RDS_PASSWORD']}"
            f"@{db_creds['RDS_HOST']}:{db_creds['RDS_PORT']}/{db_creds['RDS_DATABASE']}"
        )
        return engine.connect()

    def _get_common_indexes(self, num_records=500):
        """Get common random indexes valid for all tables."""
        with self._get_db_connection() as conn:
            table_counts = {
                table: conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                for table in self.table_config
            }
            min_count = min(table_counts.values())
            sample_size = min(num_records, min_count)

            smallest_table = min(table_counts, key=table_counts.get)
            index_col = self.table_config[smallest_table]["index_col"]
            result = conn.execute(
                text(
                    f"SELECT `{index_col}` FROM {smallest_table} ORDER BY RAND() LIMIT :limit"
                ),
                {"limit": sample_size},
            )

            return [row[index_col] for row in result]

    def stream_data(self):
        """Stream data from the database to Kinesis."""
        print("Starting data streaming to Kinesis...")
        common_indexes = self._get_common_indexes()

        with self._get_db_connection() as conn:
            for table, config in self.table_config.items():
                print(f"Streaming from {table}...")
                index_col = config["index_col"]
                query = text(f"SELECT * FROM {table} WHERE `{index_col}` IN :indexes")
                result = conn.execute(query, {"indexes": tuple(common_indexes)})

                batch = []
                for row in result:
                    record = dict(row)
                    for key, value in record.items():
                        if isinstance(value, datetime):
                            record[key] = value.isoformat()

                    if self.batch_mode:
                        batch.append(record)
                        if len(batch) >= self.kinesis.max_batch_size:
                            self.kinesis.send_batch_to_kinesis(batch, table)
                            batch = []
                            sleep(0.1)
                    else:
                        self.kinesis.send_to_kinesis(record, table)
                        sleep(0.1)

                if self.batch_mode and batch:
                    self.kinesis.send_batch_to_kinesis(batch, table)
                    sleep(0.1)


if __name__ == "__main__":
    batch_mode = True  # Change to False to use single record mode
    streamer = DatabaseStreamer(batch_mode=batch_mode)
    streamer.stream_data()
