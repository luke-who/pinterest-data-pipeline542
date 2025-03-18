# Pinterest Data Pipeline

<img src="img/Pinterest_Data_Pipeline_local_DB_Airflow.drawio.svg" alt="Pinterest Data Pipeline Architecture" width="100%">


## Overview
This project implements a sophisticated data pipeline that processes Pinterest-like data through various AWS services, combining both batch and stream processing capabilities. The pipeline demonstrates modern data engineering practices by integrating multiple AWS services and open-source tools to create a robust, scalable data processing solution.

## Architecture
The pipeline consists of several components working together:

1. **Data Ingestion**
   - Extracts data from a MySQL database (local/RDS)
   - Processes three main data types:
     - Pinterest post data
     - Geolocation data
     - User data

2. **Data Processing Paths**
   - **Batch Processing Path**:
     - Kafka REST Proxy on EC2 for data ingestion
     - S3 storage via Kafka Connect
     - Databricks for data transformation
   - **Streaming Path**:
     - Amazon Kinesis for real-time data streaming
     - Direct integration with Databricks

3. **Orchestration**
   - Apache Airflow (MWAA) for workflow management
   - Integration between Airflow and Databricks

## Components

### Core Scripts
- `user_posting_emulation.py`: Handles batch processing via Kafka
- `user_posting_emulation_streaming.py`: Manages real-time data streaming via Kinesis
- `Pinterest Data Pipeline.ipynb`: Jupyter notebook containing pipeline development and testing

### Infrastructure
- Amazon RDS/Local MySQL for data storage
- Amazon EC2 for Kafka broker hosting
- Amazon API Gateway for REST endpoints
- Amazon S3 for data lake storage
- Amazon Kinesis for stream processing
- Amazon MWAA (Managed Workflows for Apache Airflow)
- Databricks for data transformation and analysis

## Setup and Installation

### Prerequisites
- AWS Account with appropriate permissions
- Python 3.x
- MySQL database
- Apache Kafka
- Databricks workspace
- Required Python packages (see `requirements.txt`)

### Configuration Files
1. `api_creds.yaml`: API Gateway credentials
2. `aws_db_creds.yaml`: AWS RDS credentials
3. `local_db_creds.yaml`: Local database credentials

### Setup Steps
1. **Environment Setup**
   ```bash
   pip install -r requirements.txt
   ```

2. **Database Configuration**
   - Configure MySQL database using `pinterest_data_db.sql`
   - Set up credentials in appropriate YAML files

3. **AWS Services Setup**
   - Configure EC2 instance for Kafka
   - Set up API Gateway endpoints
   - Configure S3 buckets
   - Set up Kinesis streams
   - Configure MWAA environment

## Usage

### Batch Processing
1. Start the Kafka services on EC2
2. Run the batch processing script:
   ```bash
   python user_posting_emulation.py
   ```

### Stream Processing
1. Ensure Kinesis streams are configured
2. Run the streaming script:
   ```bash
   python user_posting_emulation_streaming.py
   ```

### Airflow DAGs
The `airflow/dags` directory contains the workflow definitions for orchestrating the pipeline tasks.

## Project Structure
```
├── .databricks/
│   └── commit_outputs
├── airflow/
│   ├── dags/
│   ├── 808492447622.py
│   └── requirements.txt
├── dbc/
│   └── pinterest_data_pipeline.ipynb
├── user_posting_emulation.py
├── user_posting_emulation_streaming.py
├── pinterest_data_pipeline.ipynb
├── pinterest_data_db.sql
└── various configuration files (.yaml)
```

## Security Notes
- API keys and credentials should be stored securely
- Use appropriate IAM roles and permissions
- Never commit sensitive credentials to version control

## License
[Your chosen license]

## Contributing
[Your contribution guidelines]