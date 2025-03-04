# Pinterest Data Pipeline
----------------------------------------------------------------

## Description
This is a data pipeline that extracts data from Pinterest's API, transforms it into a usable format


## Installation
### Milestone 3: Batch Processing: Configure the EC2 Kafka client
#### Task 3: Create Kafka Topics on EC2
1. SSH into the EC2 instance
```
ssh -i <your-key-pair-name>.pem ubuntu@<your-ec2-public-ip>
```
<!-- ssh -i "68e3427bbc67-key-pair.pem" ubuntu@ec2-54-80-77-214.compute-1.amazonaws.com -->
2. Navigate to the Kafka Directory
```
cd ~/kafka
```
3. Create the Kafka Topics (pin, geo, user)
```
bin/kafka-topics --create --topic <your_UserId>.pin --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
bin/kafka-topics --create --topic <your_UserId>.geo --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
bin/kafka-topics --create --topic <your_UserId>.user --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```
4. Verify the Kafka Topics
```
bin/kafka-topics --list --bootstrap-server localhost:9092
```
5. (Optional) Describe the Topics
```
bin/kafka-topics --describe --topic <your_UserId>.pin --bootstrap-server localhost:9092
bin/kafka-topics --describe --topic <your_UserId>.geo --bootstrap-server localhost:9092
bin/kafka-topics --describe --topic <your_UserId>.user --bootstrap-server localhost:9092
```

## Usage


### License