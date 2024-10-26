# AWS Bedrock Quickstarts (Modified from Anthropic Quickstarts)

This repository is a fork of Anthropic Quickstarts, modified to use AWS Bedrock instead of the Anthropic API. Each quickstart provides a foundation that you can easily build upon and customize for your specific needs.

### Key modifications include:
- **Replacing Anthropic API calls with AWS Bedrock API calls**
- **Adding AWS region selection functionality**
- **Implementing AWS credential management using .env files or server profiles**
- **List the available KnowledgeBase using API call (ListKnowledgeBases) and displaying them in a dropdown menu**

## Getting Started

To use these quickstarts, you'll need AWS credentials with access to Bedrock. If you don't have AWS credentials yet, you can create an AWS account and set up your credentials.

## Available Quickstarts

### Customer Support Agent

A customer support agent powered by Claude. This project demonstrates how to leverage Claude's natural language understanding and generation capabilities to create an AI-assisted customer support system with access to a knowledge base.

[Go to Customer Support Agent Quickstart](./customer-support-agent)

### Financial Data Analyst

A financial data analyst powered by Claude. This project demonstrates how to leverage Claude's capabilities with interactive data visualization to analyze financial data via chat.

[Go to Financial Data Analyst Quickstart](./financial-data-analyst)

### Computer Use Demo

An environment and tools that Claude can use to control a desktop computer. This project demonstrates how to leverage the computer use capabilities of the the new Claude 3.5 Sonnet model.

[Go to Computer Use Demo Quickstart](./computer-use-demo)

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
```
AWS_ACCESS_KEY_ID=your_access_key 
AWS_SECRET_ACCESS_KEY=your_secret_key
```

2. AWS CLI Profile: If you don't provide a `.env` file, the application will attempt to use the AWS credentials configured in your system's default profile.

## Region Selection

This fork includes functionality to select the AWS region for Bedrock API calls. You can specify your preferred region through the application interface.

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
