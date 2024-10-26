# AWS Bedrock Quickstarts (Modified from Anthropic Quickstarts)

This repository is a fork of Anthropic Quickstarts, modified to use AWS Bedrock instead of the Anthropic API. The core structure and functionality remain similar to the original Anthropic quickstarts, but we've adapted the API calls to work with AWS Bedrock.

### Key modifications include:
- **Replacing Anthropic API calls with AWS Bedrock API calls**
- **Adding AWS region selection functionality**
- **Implementing AWS credential management using .env files or server profiles**
- **List the available KnowledgeBase using API call (ListKnowledgeBases) and displaying them in a dropdown menu**

## Key Features

-  AI-powered chat using Claude model on Amazon Bedrock
-  Amazong Bedrock integration for contextual knowledge retrieval
-  Real-time thinking & debug information display
-  Knowledge base source visualization
-  User mood detection & appropriate agent redirection
-  Highly customizable UI with shadcn/ui components

## General Usage

Each quickstart project comes with its own README and setup instructions. Generally, you'll follow these steps:

1. Clone this repository
2. Navigate to the specific quickstart directory
3. Install the required dependencies
4. Set up your AWS credentials (see below)
5. Run the quickstart application

## ⚙️ Configuration

This project supports two methods for AWS credential management:

1. AWS Profile: If you don't provide a `.env` file, the application will attempt to use the AWS credentials configured in your system's default profile.

2. Environment Variables: Create a `.env` file in the project root and add your AWS access key, secret key:
```
AWS_ACCESS_KEY_ID=your_access_key 
AWS_SECRET_ACCESS_KEY=your_secret_key
```

##  AWS Bedrock RAG Integration

This project utilizes Amazon Bedrock for Retrieval-Augmented Generation (RAG). To set up:

1. Ensure you have an AWS account with Bedrock access.
2. Create a Bedrock knowledge base in your desired AWS region.
3. Index your documents/sources in the knowledge base. For more info on that, check the "How to Create Your Own Knowledge Base" section.

The application will use these knowledge bases for context retrieval during conversations.

### How to Create Your Own Knowledge Base

To create your own knowledge base:

1. Go to your AWS Console and select Amazon Bedrock.
2. In the left side menu, click on "Knowledge base" under "More".

3. Click on "Create knowledge base".
   ![Create Knowledge Base](tutorial/create-knowledge-base.png)
4. Give your knowledge base a name. You can leave "Create a new service role".
5. Choose a source for your knowledge base. In this example, we'll use Amazon S3 storage service.
   ![Choose Source](tutorial/choose-source.png)

   Note: If you're using the S3 storage service, you'll need to create a bucket first where you will upload your files. Alternatively, you can also upload your files after the creation of a knowledge base.

6. Click "Next".
7. Choose a location for your knowledge base. This can be S3 buckets, folders, or even single documents.
8. Click "Next".
9. Select your preferred embedding model. In this case, we'll use Titan Text Embeddings 2.
10. Select "Quick create a new vector store".
11. Confirm and create your knowledge base.
12. Once you have done this, get your knowledge base ID from the knowledge base overview.


##  Switching Models

This project supports multiple Claude models. To switch between models:

1. In `ChatArea.tsx`, the `models` array defines available models:

```typescript
const models: Model[] = [
  { id: "claude-3-haiku-20240307", name: "Claude 3 Haiku" },
  { id: "claude-3-5-sonnet-20240620", name: "Claude 3.5 Sonnet" },
  // Add more models as needed
];
```

2. The `selectedModel` state variable controls the currently selected model:

```typescript
const [selectedModel, setSelectedModel] = useState("claude-3-haiku-20240307");
```

3. To implement model switching in the UI, a dropdown component is used that updates the `selectedModel`.


##  Customization

This project leverages shadcn/ui components, offering a high degree of customization:

* Modify the UI components in the `components/ui` directory
* Adjust the theme in `app/globals.css`
* Customize the layout and functionality in individual component files
* Modify the theme colors and styles by editing the `styles/themes.js` file:

```javascript
// styles/themes.js
export const themes = {
  neutral: {
    light: {
      // Light mode colors for neutral theme
    },
    dark: {
      // Dark mode colors for neutral theme
    }
  },
  // Add more themes here
};
```
You can add new themes or modify existing ones by adjusting the color values in this file.

##  Deploy with AWS Amplify

To deploy this application using AWS Amplify, follow these steps:

1. Go to your AWS Console and select Amplify.
2. Click on "Create new app" (image link to be added later).
3. Select GitHub (or your preferred provider) as the source.
4. Choose this repository.
5. Edit the YAML file to contain:

   ```yaml
    version: 1
    frontend:
      phases:
        preBuild:
          commands:
            - npm ci --cache .npm --prefer-offline
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: .next
        files:
          - "**/*"
      cache:
        paths:
          - .next/cache/**/*
          - .npm/**/*
   ```

6. Choose to create a new service role or use an existing one. Refer to the "Service Role" section for more information.
7. Click "Save and deploy" to start the deployment process.

Your application will now be deployed using AWS Amplify.


### Service Role

Once your application is deployed, if you selected to create a new service role:

1. Go to your deployments page
2. Select the deployment you just created
3. Click on "App settings"
4. Copy the Service role ARN
5. Go to the IAM console and find this role
6. Attach the "AmazonBedrockFullAccess" policy to the role

This ensures that your Amplify app has the necessary permissions to interact with Amazon Bedrock.

##  Customized Deployment and Development
This project now supports flexible deployment and development configurations, allowing you to include or exclude specific components (left sidebar, right sidebar) based on your needs.
Configuration
The inclusion of sidebars is controlled by a config.ts file, which uses environment variables to set the configuration:
```typescript
typescriptCopytype Config = {
  includeLeftSidebar: boolean;
  includeRightSidebar: boolean;
};

const config: Config = {
  includeLeftSidebar: process.env.NEXT_PUBLIC_INCLUDE_LEFT_SIDEBAR === "true",
  includeRightSidebar: process.env.NEXT_PUBLIC_INCLUDE_RIGHT_SIDEBAR === "true",
};

export default config;
```

This configuration uses two environment variables:

NEXT_PUBLIC_INCLUDE_LEFT_SIDEBAR: Set to "true" to include the left sidebar
NEXT_PUBLIC_INCLUDE_RIGHT_SIDEBAR: Set to "true" to include the right sidebar

## NPM Scripts
The package.json includes several new scripts for different configurations:

```bash
npm run dev: Runs the full app with both sidebars (default)
npm run build: Builds the full app with both sidebars (default)
npm run dev:full: Same as npm run dev
npm run dev:left: Runs the app with only the left sidebar
npm run dev:right: Runs the app with only the right sidebar
npm run dev:chat: Runs the app with just the chat area (no sidebars)
npm run build:full: Same as npm run build
npm run build:left: Builds the app with only the left sidebar
npm run build:right: Builds the app with only the right sidebar
npm run build:chat: Builds the app with just the chat area (no sidebars)
```

Usage
To use a specific configuration:

For development: Run the desired script (e.g., npm run dev:left)
For production: Build with the desired script (e.g., npm run build:right)

These scripts set the appropriate environment variables before running or building the application, allowing you to easily switch between different configurations.
This flexibility allows you to tailor the application's layout to your specific needs, whether for testing, development, or production deployment.

## Appendix

This project is a prototype and is provided on an "as-is" basis. It is not intended for production use and may contain bugs, errors, or inconsistencies. By using this prototype, you acknowledge and agree that:
- The software is provided in a pre-release, beta, or trial form.
- It may not be suitable for production or mission-critical environments.
- The developers are not responsible for any issues, data loss, or damages resulting from its use.
- No warranties or guarantees of any kind are provided, either expressed or implied.
- Support for this prototype may be limited or unavailable.
- Use of this prototype is at your own risk. We encourage you to report any issues or provide feedback to help improve future versions.
