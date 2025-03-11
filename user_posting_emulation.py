import requests
from time import sleep
import random
import sqlalchemy
from sqlalchemy import text
import yaml
from datetime import datetime

random.seed(100)


class DBConnector:
    def __init__(self, creds_file):
        with open(creds_file, "r") as file:
            db_creds = yaml.safe_load(file)
        self.HOST = db_creds["RDS_HOST"]
        self.USER = db_creds["RDS_USER"]
        self.PASSWORD = db_creds["RDS_PASSWORD"]
        self.DATABASE = db_creds["RDS_DATABASE"]
        self.PORT = db_creds["RDS_PORT"]

    def create_db_connector(self):
        return sqlalchemy.create_engine(
            f"mysql+pymysql://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DATABASE}?charset=utf8mb4"
        )


class DataStreamer:
    def __init__(self, db_creds_file, api_creds_file):
        # Load database credentials
        self.db_connector = DBConnector(db_creds_file)
        self.engine = self.db_connector.create_db_connector()

        # Load API credentials
        with open(api_creds_file, "r") as file:
            api_creds = yaml.safe_load(file)
        self.api_url = api_creds["API_INVOKE_URL"]
        self.headers = {
            "Content-Type": "application/vnd.kafka.json.v2+json",
            "Accept": "application/vnd.kafka.v2+json",
        }

    def _serialize_datetime(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    def stream_table_data(self, table_name, topic_name, num_records=500):
        print(
            f"[DEBUG] Starting to stream data from table: {table_name} to topic: {topic_name}"
        )

        try:
            with self.engine.connect() as connection:
                # Get total rows
                count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                total_records = connection.execute(count_query).scalar()
                print(f"[DEBUG] Total records in {table_name}: {total_records}")

                # Calculate a random offset to fetch 500 records
                offset = random.randint(0, max(0, total_records - num_records))
                query = text(
                    f"SELECT * FROM {table_name} LIMIT {num_records} OFFSET {offset}"
                )
                result = connection.execute(query)
                print(f"[DEBUG] Fetching {num_records} records from offset {offset}")

                for row_num, row in enumerate(result):
                    # Convert row to dict and handle datetime serialization
                    record = {
                        str(key): self._serialize_datetime(value)
                        for key, value in row._mapping.items()
                    }

                    payload = {"records": [{"value": record}]}

                    try:
                        response = requests.post(
                            f"{self.api_url}/topics/{topic_name}",
                            json=payload,
                            headers=self.headers,
                        )
                        if response.status_code in [200, 201]:
                            print(
                                f"[DEBUG] Successfully sent record {row_num + 1} to {topic_name}"
                            )
                        else:
                            print(
                                f"[ERROR] Failed to send record {row_num + 1} to {topic_name}: {response.text}"
                            )
                    except Exception as e:
                        print(f"[ERROR] API Error for {topic_name}: {str(e)}")

                    sleep(0.01)  # Brief pause between requests

        except Exception as e:
            print(f"[ERROR] Database Error for {table_name}: {str(e)}")
        finally:
            print(f"[DEBUG] Finished streaming data from {table_name} to {topic_name}")


if __name__ == "__main__":
    # Configuration - Update these values as needed
    DB_CREDS_FILE = "local_db_creds.yaml"  # or "aws_db_creds.yaml" for production
    API_CREDS_FILE = "api_creds.yaml"

    # Table to Kafka topic mapping based on your sample data
    TOPIC_MAPPING = {
        "pinterest_data": "808492447622.pin",
        "geolocation_data": "808492447622.geo",
        "user_data": "808492447622.user",
    }

    # Create a DataStreamer instance
    streamer = DataStreamer(DB_CREDS_FILE, API_CREDS_FILE)

    # Stream data for each table sequentially
    for table, topic in TOPIC_MAPPING.items():
        print(f"[INFO] Starting streamer for table: {table} -> topic: {topic}")
        streamer.stream_table_data(table, topic)
        print(f"[INFO] Completed streamer for table: {table} -> topic: {topic}")
