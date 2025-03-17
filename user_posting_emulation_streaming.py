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
    def __init__(self):
        self.stream_name = "Kinesis-Prod-Stream"
        self.invoke_url = f"{API_INVOKE_URL}/streams/{self.stream_name}/record"

    def send_to_kinesis(self, data, partition_key):
        """Match the structure from your working test code"""
        payload = json.dumps(
            {
                "StreamName": self.stream_name,
                "Data": data,  # Direct JSON object (no base64 encoding)
                "PartitionKey": partition_key,
            }
        )

        try:
            # Use PUT method instead of POST
            response = requests.put(
                self.invoke_url,
                headers=HEADERS,
                data=payload,  # Use 'data' instead of 'json' parameter
            )

            if response.status_code == 200:
                print(
                    f"Successfully sent record to partition: {partition_key}, response.status_code: {response.status_code}"
                )
                print(response.content)
            else:
                print(
                    f"Failed to send record: {response.status_code} - {response.text}"
                )

        except Exception as e:
            print(f"API Error: {str(e)}")


class DatabaseStreamer:
    def __init__(self):
        self.kinesis = KinesisStreamer()
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
        """Get common random indexes valid for all tables"""
        with self._get_db_connection() as conn:
            # Get table counts
            table_counts = {}
            for table in self.table_config:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                table_counts[table] = count
                print(f"{table} has {count} records")

            # Determine safe sample size
            min_count = min(table_counts.values())
            sample_size = min(num_records, min_count)
            print(f"Using common sample size of {sample_size}")

            # Get indexes from smallest table
            smallest_table = min(table_counts, key=table_counts.get)
            index_col = self.table_config[smallest_table]["index_col"]

            # Get random indexes (with backticks)
            result = conn.execute(
                text(
                    f"SELECT `{index_col}` FROM {smallest_table} "  # Backticks added
                    "ORDER BY RAND() LIMIT :limit"
                ),
                {"limit": sample_size},
            )

            return [row[index_col] for row in result]

    def stream_data(self):
        print("Starting data streaming to Kinesis...")
        common_indexes = self._get_common_indexes()

        with self._get_db_connection() as conn:
            for table, config in self.table_config.items():
                print(f"Streaming from {table}...")
                index_col = config["index_col"]

                # Fetch records using common indexes
                query = text(
                    f"SELECT * FROM {table} WHERE `{index_col}` IN :indexes"
                )  # Add backticks
                result = conn.execute(query, {"indexes": tuple(common_indexes)})

                # Stream records
                for row in result:
                    record = dict(row)
                    # Convert datetime objects
                    for key, value in record.items():
                        if isinstance(value, datetime):
                            record[key] = value.isoformat()

                    self.kinesis.send_to_kinesis(data=record, partition_key=table)
                    sleep(0.1)


if __name__ == "__main__":
    streamer = DatabaseStreamer()
    streamer.stream_data()
