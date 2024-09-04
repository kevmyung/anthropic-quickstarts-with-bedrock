# AWS Bedrock Quickstarts (Modified from Anthropic Quickstarts)

This repository is a fork of Anthropic Quickstarts, modified to use AWS Bedrock instead of the Anthropic API. Each quickstart provides a foundation that you can easily build upon and customize for your specific needs.

### Key modifications include:
- Replacing Anthropic API calls with AWS Bedrock API calls
- Adding AWS region selection functionality
- Implementing AWS credential management using .env files or server environment profiles
- Dynamically populating Knowledge Base options using ListKnowledgeBases API call and displaying them in a dropdown menu

## Getting Started

To use these quickstarts, you'll need AWS credentials with access to Bedrock. If you don't have AWS credentials yet, you can create an AWS account and set up your credentials.

## Available Quickstarts

### 1. Customer Support Agent

Our first quickstart project is a customer support agent powered by AWS Bedrock. This project demonstrates how to leverage Bedrock's natural language understanding and generation capabilities to create an AI-assisted customer support system with access to a knowledge base.

[Go to Customer Support Agent Quickstart](./customer-support-agent)

## General Usage

Each quickstart project comes with its own README and setup instructions. Generally, you'll follow these steps:

1. Clone this repository
2. Navigate to the specific quickstart directory
3. Install the required dependencies
4. Set up your AWS credentials (see below)
5. Run the quickstart application

## AWS Credentials Setup

This project supports two methods for AWS credential management:

1. Environment Variables: Create a `.env` file in the project root and add your AWS access key, secret key, and preferred region:
```AWS_ACCESS_KEY_ID=your_access_key AWS_SECRET_ACCESS_KEY=your_secret_key AWS_DEFAULT_REGION=your_preferred_region```

2. AWS CLI Profile: If you don't provide a `.env` file, the application will attempt to use the AWS credentials configured in your system's default profile.

## Region Selection

This fork includes functionality to select the AWS region for Bedrock API calls. You can specify your preferred region in the `.env` file or through the application interface.

## Explore Further

To deepen your understanding of working with AWS Bedrock, check out these resources:

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS SDK for Python (Boto3) Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

## Contributing

We welcome contributions to this AWS Bedrock Quickstarts repository! If you have ideas for new quickstart projects or improvements to existing ones, please open an issue or submit a pull request.

## Community and Support

- Join the [AWS Developer Forums](https://forums.aws.amazon.com/) for discussions and support
- Check out the [AWS Documentation](https://docs.aws.amazon.com/) for additional help

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.