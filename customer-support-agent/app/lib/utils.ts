import {
  BedrockAgentRuntimeClient,
  RetrieveCommand,
  RetrieveCommandInput,
} from "@aws-sdk/client-bedrock-agent-runtime";
import { BedrockRuntimeClient } from "@aws-sdk/client-bedrock-runtime";
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

console.log("🔑 Have AWS AccessKey?", !!process.env.BAWS_ACCESS_KEY_ID);
console.log("🔑 Have AWS Secret?", !!process.env.BAWS_SECRET_ACCESS_KEY);

export function createBedrockAgentClient(region: string) {
  return new BedrockAgentRuntimeClient({
    region: region,
    credentials: process.env.BAWS_ACCESS_KEY_ID && process.env.BAWS_SECRET_ACCESS_KEY
      ? {
          accessKeyId: process.env.BAWS_ACCESS_KEY_ID,
          secretAccessKey: process.env.BAWS_SECRET_ACCESS_KEY,
        }
      : undefined,
  });
}

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

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface RAGSource {
  id: string;
  fileName: string;
  snippet: string;
  score: number;
}


export async function retrieveContext(
  query: string,
  knowledgeBaseId: string,
  n: number = 3,
  bedrockClient: BedrockAgentRuntimeClient
): Promise<{
  context: string;
  isRagWorking: boolean;
  ragSources: RAGSource[];
}> {
  try {
    if (!knowledgeBaseId) {
      console.error("knowledgeBaseId is not provided");
      return {
        context: "",
        isRagWorking: false,
        ragSources: [],
      };
    }

    console.log(`🔍 Querying knowledge base: ${knowledgeBaseId} with query: "${query}"`);

    const input: RetrieveCommandInput = {
      knowledgeBaseId: knowledgeBaseId,
      retrievalQuery: { text: query },
      retrievalConfiguration: {
        vectorSearchConfiguration: { numberOfResults: n },
      },
    };

    const command = new RetrieveCommand(input);
    const response = await bedrockClient.send(command);

    // Parse results
    const rawResults = response?.retrievalResults || [];

    if (rawResults.length === 0) {
      console.log("⚠️ No results returned from Bedrock");
      return {
        context: "",
        isRagWorking: true,  // The RAG system is working, just no results
        ragSources: [],
      };
    }

    const ragSources: RAGSource[] = rawResults
      .filter((res: any) => res.content && res.content.text)
      .map((result: any, index: number) => {
        const uri = result?.location?.s3Location?.uri || "";
        const fileName = uri.split("/").pop() || `Source-${index}.txt`;

        return {
          id:
            result.metadata?.["x-amz-bedrock-kb-chunk-id"] || `chunk-${index}`,
          fileName: fileName.replace(/_/g, " ").replace(".txt", ""),
          snippet: result.content?.text || "",
          score: result.score || 0,
        };
      });

    console.log("🔍 Parsed RAG Sources:", ragSources);

    const context = rawResults
      .filter((res: any) => res.content && res.content.text)
      .map((res: any) => res.content.text)
      .join("\n\n");

    console.log("📄 Retrieved Context:", context);

    return {
      context,
      isRagWorking: true,
      ragSources,
    };
  } catch (error) {
    console.error("RAG Error:", error);
    if (error instanceof Error) {
      console.error("Error message:", error.message);
      console.error("Error stack:", error.stack);
    }
    return { context: "", isRagWorking: false, ragSources: [] };
  }
}