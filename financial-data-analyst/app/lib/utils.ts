import { BedrockRuntimeClient } from "@aws-sdk/client-bedrock-runtime";

console.log("🔑 Have AWS AccessKey?", !!process.env.BAWS_ACCESS_KEY_ID);
console.log("🔑 Have AWS Secret?", !!process.env.BAWS_SECRET_ACCESS_KEY);

export function createBedrockClient(region: string) {
    return new BedrockRuntimeClient({
      region: region,
      credentials: process.env.BAWS_ACCESS_KEY_ID && process.env.BAWS_SECRET_ACCESS_KEY
        ? {
            accessKeyId: process.env.BAWS_ACCESS_KEY_ID,
            secretAccessKey: process.env.BAWS_SECRET_ACCESS_KEY,
          }
        : undefined,
    });
  }
  