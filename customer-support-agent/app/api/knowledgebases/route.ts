import { NextRequest, NextResponse } from 'next/server';
import { BedrockAgentClient, ListKnowledgeBasesCommand } from "@aws-sdk/client-bedrock-agent";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const region = searchParams.get('region');

  if (!region) {
    return NextResponse.json({ error: "Region is required" }, { status: 400 });
  }

  try {
    const client = new BedrockAgentClient({ region });
    const command = new ListKnowledgeBasesCommand({});

    console.log("Sending request to AWS...");
    const response = await client.send(command);

    const knowledgeBases = response.knowledgeBaseSummaries?.map(kb => ({
      id: kb.knowledgeBaseId,
      name: kb.name,
      description: kb.description,
      status: kb.status,
      updatedAt: kb.updatedAt?.toISOString()
    })) || [];

    return NextResponse.json(knowledgeBases);
  } catch (error) {
    console.error("Error fetching knowledge bases:", error);
    if (error instanceof Error) {
      console.error("Error name:", error.name);
      console.error("Error message:", error.message);
      console.error("Error stack:", error.stack);
    }
    return NextResponse.json({ error: "Failed to fetch knowledge bases" }, { status: 500 });
  }
}