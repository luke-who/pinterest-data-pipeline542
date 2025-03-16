# Pinterest Data Pipeline
----------------------------------------------------------------

## Description
This is a data pipeline that extracts data from Pinterest's API, store it in MySQL database using either Amazon RDS/DBeaver, stream the data using Amazon API Gateway send to Kafka REST Proxy service on a Kafka Server which are hosted on an Amazon EC2 and act as Integration Request Endpoint. The data is stored as topics on the Kafka server, then being sent to Amazon S3 via kafka connect service. After that, the topics in S3 are read in Databricks and transforms it into a usable format. Finally, Amazon Kinesis and Managed Workflow for Apache Airflow are also integrated for the pipeline (Managed Workflow for Apache Airflow -> Databricks, Amazon API Gateway -> Amazon Kinesis -> Databricks).


## Installation
Follow the instruction in `user_posting_emulation.py` for setup and running the notebook
- Milestone 1: Set up the environment
- Milestone 2: Get Started
- Milestone 3: Batch Processing: Configure the EC2 Kafka client
- Milestone 4: Batch Processing: Configuring an API in API Gateway
- Milestone 5: Batch Processing: Databricks
- Milestone 6: Batch Processing: Spark on Databricks
- Milestone 7: Batch Processing: AWS MWAA
- Milestone 8: Stream Processing: AWS Kinesis

## Usage


### License