#!/bin/bash

# Install LocalStack if not already installed
echo "Checking for LocalStack installation..."
if ! command -v localstack &> /dev/null; then
    echo "LocalStack not found. Installing..."
    pip install localstack
else
    echo "LocalStack is already installed."
fi

# Install AWS CLI if not already installed
echo "Checking for AWS CLI installation..."
if ! command -v aws &> /dev/null; then
    echo "AWS CLI not found. Installing..."
    pip install awscli
else
    echo "AWS CLI is already installed."
fi

# Configure AWS CLI for LocalStack
mkdir -p ~/.aws
cat > ~/.aws/config << EOL
[default]
region = us-east-1
output = json

[profile localstack]
region = us-east-1
output = json
EOL

cat > ~/.aws/credentials << EOL
[default]
aws_access_key_id = test
aws_secret_access_key = test

[localstack]
aws_access_key_id = test
aws_secret_access_key = test
EOL

echo "AWS CLI configured for LocalStack"

# Start LocalStack
echo "Starting LocalStack..."
localstack start -d

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
until curl -s http://localhost:4566/_localstack/health | grep -q "\"kinesis\": \"available\""; do
    echo "Waiting for Kinesis to be ready..."
    sleep 2
done

# Create Kinesis streams
echo "Creating Kinesis streams..."
aws --endpoint-url=http://localhost:4566 kinesis create-stream --stream-name pin_data_geo --shard-count 1
aws --endpoint-url=http://localhost:4566 kinesis create-stream --stream-name pin_data_pin --shard-count 1
aws --endpoint-url=http://localhost:4566 kinesis create-stream --stream-name pin_data_user --shard-count 1

# List streams to verify
echo "Listing Kinesis streams:"
aws --endpoint-url=http://localhost:4566 kinesis list-streams

echo "LocalStack setup complete!"
