import requests
from time import sleep
import random
import sqlalchemy
from sqlalchemy import text
import yaml
from datetime import datetime

random.seed(100)  # Consistent randomness for reproducibility


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
        self.db_connector = DBConnector(db_creds_file)
        self.engine = self.db_connector.create_db_connector()

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

    def get_table_row_counts(self, tables):
        """Get row counts for multiple tables and return as dictionary"""
        counts = {}
        try:
            with self.engine.connect() as connection:
                for table in tables:
                    query = text(f"SELECT COUNT(*) FROM {table}")
                    count = connection.execute(query).scalar()
                    counts[table] = count
                    print(f"[STATUS] Table {table} has {count} rows")
        except Exception as e:
            print(f"[ERROR] Failed to get table counts: {str(e)}")
        return counts

    def get_random_indexes(self, table_name, index_column, num_records):
        """Get random indexes from specified table using correct column name"""
        try:
            with self.engine.connect() as connection:
                # Get total rows for the table
                count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                total_rows = connection.execute(count_query).scalar()

                # Ensure we don't request more rows than available
                actual_limit = min(num_records, total_rows)
                print(
                    f"[STATUS] Selecting {actual_limit} indexes (column: {index_column}) from {table_name}"
                )

                # Use parameterized column name in query
                query = text(
                    f"SELECT `{index_column}` FROM {table_name} ORDER BY RAND() LIMIT {actual_limit}"
                )
                result = connection.execute(query)
                return [row[index_column] for row in result]
        except Exception as e:
            print(f"[ERROR] Failed to get indexes from {table_name}: {str(e)}")
            return []

    def stream_data_for_table(self, table_name, topic_name, indexes, index_column):
        """Stream data for a table using pre-selected indexes and correct column name"""
        if not indexes:
            print(f"[WARNING] No indexes provided for {table_name}")
            return

        print(
            f"[STATUS] Starting stream for {table_name} (using {index_column} column) with {len(indexes)} indexes"
        )

        try:
            with self.engine.connect() as connection:
                # Use parameterized column name in WHERE clause
                query = text(
                    f"SELECT * FROM {table_name} WHERE `{index_column}` IN :indexes"
                )
                params = {"indexes": tuple(indexes)}
                result = connection.execute(query, params)

                print(f"[STATUS] Retrieved {result.rowcount} records from {table_name}")

                for row_num, row in enumerate(result):
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
                        if response.status_code not in [200, 201]:
                            print(
                                f"[ERROR] Failed to send record {row_num + 1}: {response.text}"
                            )
                    except Exception as e:
                        print(f"[ERROR] API Error: {str(e)}")

                    sleep(0.01)
        except Exception as e:
            print(f"[ERROR] Database Error for {table_name}: {str(e)}")
        finally:
            print(f"[STATUS] Completed streaming for {table_name}\n")


if __name__ == "__main__":
    DB_CREDS_FILE = "local_db_creds.yaml"
    API_CREDS_FILE = "api_creds.yaml"
    TARGET_RECORDS = 500
    TOPIC_MAPPING = {
        "pinterest_data": "808492447622.pin",
        "geolocation_data": "808492447622.geo",
        "user_data": "808492447622.user",
    }
    # Map each table to its respective index column name
    INDEX_COLUMNS = {
        "pinterest_data": "index",
        "geolocation_data": "ind",
        "user_data": "ind",
    }

    streamer = DataStreamer(DB_CREDS_FILE, API_CREDS_FILE)

    # Step 1: Get row counts for all tables
    tables = TOPIC_MAPPING.keys()
    print("\n[INFO] Getting table row counts...")
    table_counts = streamer.get_table_row_counts(tables)

    # Step 2: Determine the safe number of records to retrieve
    min_count = min(table_counts.values())
    actual_records = min(TARGET_RECORDS, min_count)
    print("\n[INFO] Safety check results:")
    print(f"- Smallest table has {min_count} rows")
    print(f"- Will retrieve {actual_records} records\n")

    # Step 3: Get indexes from the smallest table using its specific column name
    smallest_table = min(table_counts, key=table_counts.get)
    index_column = INDEX_COLUMNS[smallest_table]
    print(
        f"[INFO] Selecting indexes from smallest table ({smallest_table}) using column '{index_column}'..."
    )
    indexes = streamer.get_random_indexes(smallest_table, index_column, actual_records)

    if not indexes:
        print("[CRITICAL] No indexes retrieved. Exiting.")
        exit(1)

    # Step 4: Stream data for all tables using common indexes
    print("\n[INFO] Starting data streaming...")
    for table, topic in TOPIC_MAPPING.items():
        print(f"\n=== Processing {table} ===")
        # Get the correct index column for each table
        current_index_column = INDEX_COLUMNS[table]
        streamer.stream_data_for_table(table, topic, indexes, current_index_column)
