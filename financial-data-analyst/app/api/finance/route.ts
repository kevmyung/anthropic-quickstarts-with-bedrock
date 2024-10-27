// app/api/finance/route.ts
import { NextRequest } from "next/server";
import { ConverseCommand, BedrockRuntimeServiceException } from "@aws-sdk/client-bedrock-runtime";
import { createBedrockClient } from "@/app/lib/utils";
import type { ChartData } from "@/types/chart";

const region = "us-west-2"

interface ChartToolResponse extends ChartData {
}

const isValidBase64 = (str: string): boolean => {
  try {
    return btoa(atob(str)) === str;
  } catch (err) {
    return false;
  }
};

const processFileContent = (fileData: any) => {
  if (!fileData) {
    console.log("No file data provided");
    return null;
  }

  const { base64, mediaType, isText, fileName } = fileData;

  console.log("Processing file:", {
    fileName,
    mediaType,
    isText,
    base64Length: base64?.length,
  });

  if (!base64) {
    console.error("No base64 data received");
    return null;
  }

  try {
    if (isText) {
      const textContent = decodeURIComponent(escape(atob(base64)));
      console.log("Processed text file successfully");
      return {
        text: `File contents of ${fileName}:\n\n${textContent}`
      };
    }

    if (mediaType.startsWith('image/')) {
      console.log("Processing image file...");
      const format = mediaType.split('/')[1];

      if (!['png', 'jpeg', 'gif', 'webp'].includes(format)) {
        console.error("Unsupported image format:", format);
        return null;
      }

      if (!isValidBase64(base64)) {
        console.error("Invalid base64 data for image");
        return null;
      }

      const imageData = Buffer.from(base64, 'base64');
      console.log("Image data size:", imageData.length, "bytes");

      return {
        image: {
          format: format as "png" | "jpeg" | "gif" | "webp",
          source: {
            bytes: imageData
          }
        }
      };
    }

    console.warn("Unsupported file type:", mediaType);
    return null;

  } catch (error) {
    console.error("Error in processFileContent:", error);
    if (error instanceof Error) {
      console.error("Error details:", {
        name: error.name,
        message: error.message,
        stack: error.stack
      });
    }
    return null;
  }
};

const systemPrompt = `You are a financial data visualization expert. Your role is to analyze financial data and create clear, meaningful visualizations using generate_graph_data tool:

Here are the chart types available and their ideal use cases:

1. LINE CHARTS ("line")
   - Time series data showing trends
   - Financial metrics over time
   - Market performance tracking

2. BAR CHARTS ("bar")
   - Single metric comparisons
   - Period-over-period analysis
   - Category performance

3. MULTI-BAR CHARTS ("multiBar")
   - Multiple metrics comparison
   - Side-by-side performance analysis
   - Cross-category insights

4. AREA CHARTS ("area")
   - Volume or quantity over time
   - Cumulative trends
   - Market size evolution

5. STACKED AREA CHARTS ("stackedArea")
   - Component breakdowns over time
   - Portfolio composition changes
   - Market share evolution

6. PIE CHARTS ("pie")
   - Distribution analysis
   - Market share breakdown
   - Portfolio allocation

When generating visualizations:
1. Structure data correctly based on the chart type
2. Use descriptive titles and clear descriptions
3. Include trend information when relevant (percentage and direction)
4. Add contextual footer notes
5. Use proper data keys that reflect the actual metrics

Data Structure Examples:

For Time-Series (Line/Bar/Area):
{
  data: [
    { period: "Q1 2024", revenue: 1250000 },
    { period: "Q2 2024", revenue: 1450000 }
  ],
  config: {
    xAxisKey: "period",
    title: "Quarterly Revenue",
    description: "Revenue growth over time"
  },
  chartConfig: {
    revenue: { label: "Revenue ($)" }
  }
}

For Comparisons (MultiBar):
{
  data: [
    { category: "Product A", sales: 450000, costs: 280000 },
    { category: "Product B", sales: 650000, costs: 420000 }
  ],
  config: {
    xAxisKey: "category",
    title: "Product Performance",
    description: "Sales vs Costs by Product"
  },
  chartConfig: {
    sales: { label: "Sales ($)" },
    costs: { label: "Costs ($)" }
  }
}

For Distributions (Pie):
{
  data: [
    { segment: "Equities", value: 5500000 },
    { segment: "Bonds", value: 3200000 }
  ],
  config: {
    xAxisKey: "segment",
    title: "Portfolio Allocation",
    description: "Current investment distribution",
    totalLabel: "Total Assets"
  },
  chartConfig: {
    equities: { label: "Equities" },
    bonds: { label: "Bonds" }
  }
}

Always:
- Generate real, contextually appropriate data
- Use proper financial formatting
- Include relevant trends and insights
- Structure data exactly as needed for the chosen chart type
- Choose the most appropriate visualization for the data

Never:
- Use placeholder or static data
- Announce the tool usage
- Include technical implementation details in responses
- NEVER SAY you are using the generate_graph_data tool, just execute it when needed.

Focus on clear financial insights and let the visualization enhance understanding.` 


const tools = [{
  toolSpec: {
    name: "generate_graph_data",
    description: "Generate structured JSON data for creating financial charts and graphs.",
    inputSchema: {
      json: {
        type: "object",
        properties: {
          chartType: {
            type: "string",
            enum: ["bar", "multiBar", "line", "pie", "area", "stackedArea"]
          },
          config: {
            type: "object",
            properties: {
              title: { type: "string" },
              description: { type: "string" },
              trend: {
                type: "object",
                properties: {
                  percentage: { type: "number" },
                  direction: { type: "string", enum: ["up", "down"] }
                }
              },
              footer: { type: "string" },
              totalLabel: { type: "string" },
              xAxisKey: { type: "string" }
            },
            required: ["title", "description"]
          },
          data: {
            type: "array",
            items: { type: "object" }
          },
          chartConfig: {
            type: "object",
            additionalProperties: {
              type: "object",
              properties: {
                label: { type: "string" },
                stacked: { type: "boolean" }
              }
            }
          }
        },
        required: ["chartType", "config", "data", "chartConfig"]
      }
    }
  }
}];

export async function POST(req: NextRequest) {
  try {
    const { messages, fileData, model, region } = await req.json();

    console.log("🔍 Initial Request Data:", {
      hasMessages: !!messages,
      messageCount: messages?.length,
      hasFileData: !!fileData,
      fileType: fileData?.mediaType,
      model,
      region,
    });

    // Input validation
    if (!messages || !Array.isArray(messages)) {
      return new Response(
        JSON.stringify({ error: "Messages array is required" }),
        { status: 400 }
      );
    }

    if (!model) {
      return new Response(
        JSON.stringify({ error: "Model selection is required" }),
        { status: 400 }
      );
    }

    if (!region) {
      return new Response(
        JSON.stringify({ error: "Region selection is required" }),
        { status: 400 }
      );
    }

    const bedrockClient = createBedrockClient(region);

    // Convert messages to Bedrock format
    const bedrockMessages = messages.map((msg: any) => {
      let messageContent: any[] = [];
    
      if (msg.content) {
        if (Array.isArray(msg.content)) {
          msg.content.forEach((content: any) => {
            if (content.type === 'text') {
              messageContent.push({ text: content.text });
            } else if (content.type === 'image') {
              messageContent.push({
                image: {
                  format: content.source.media_type.split('/')[1] as "png" | "jpeg" | "gif" | "webp",
                  source: {
                    bytes: Buffer.from(content.source.data, 'base64')
                  }
                }
              });
            }
          });
        } 
        else if (typeof msg.content === 'string') {
          messageContent.push({ text: msg.content });
        }
      }
    
      if (msg === messages[messages.length - 1] && fileData) {
        const fileContent = processFileContent(fileData);
        if (fileContent) {
          messageContent.push(fileContent);
        }
      }
    
      const result = {
        role: msg.role === 'assistant' ? 'assistant' : 'user',
        content: messageContent
      };
    
      console.log("Processed message:", JSON.stringify(result, null, 2));
      return result;
    });
    

    const command = new ConverseCommand({
      modelId: model,
      messages: bedrockMessages,
      system: [{ text: systemPrompt }],
      inferenceConfig: {
        maxTokens: 4096,
        temperature: 0.7,
        topP: 0.9,
      },
      toolConfig: {
        tools: tools,
        toolChoice: { auto: {} }
      }
    });

    console.log("Final API request:", JSON.stringify({
      modelId: model,
      messages: bedrockMessages.map(msg => ({
        ...msg,
        content: msg.content.map(c => 
          'image' in c ? { ...c, image: { ...c.image, source: { bytes: '[BINARY]' } }} : c
        )
      })),
      system: [{ text: systemPrompt }]
    }, null, 2));
    
    const response = await bedrockClient.send(command);
    console.log("📊 Raw Bedrock Response:", JSON.stringify(response, null, 2));

    if (!response.output?.message?.content) {
      throw new Error("Invalid response from Bedrock API");
    }

    const textContent = response.output.message.content.find(c => 'text' in c);
    const toolUseContent = response.output.message.content.find(c => 'toolUse' in c);

    const processToolResponse = (toolUseContent: any) => {
      try {
        if (!toolUseContent || !toolUseContent.toolUse || !toolUseContent.toolUse.input) {
          console.log("No valid tool use content found");
          return null;
        }

        // Get the tool input from the response
        const toolInput = toolUseContent.toolUse.input;
        console.log("Tool Input:", toolInput);

        const chartData = typeof toolInput === 'string' ? JSON.parse(toolInput) : toolInput;

        if (!chartData.chartType || !chartData.data || !Array.isArray(chartData.data)) {
          throw new Error("Invalid chart data structure");
        }

        // Transform data for pie charts
        if (chartData.chartType === "pie") {
          chartData.data = chartData.data.map((item) => {
            const valueKey = Object.keys(chartData.chartConfig)[0];
            const segmentKey = chartData.config.xAxisKey || "segment";

            return {
              segment: item[segmentKey] || item.segment || item.category || item.name,
              value: item[valueKey] || item.value,
            };
          });

          chartData.config.xAxisKey = "segment";
        }

        // Process chart config with colors
        const processedChartConfig = Object.entries(chartData.chartConfig).reduce(
          (acc, [key, config], index) => ({
            ...acc,
            [key]: {
              ...config,
              color: `hsl(var(--chart-${index + 1}))`,
            },
          }),
          {}
        );

        return {
          ...chartData,
          chartConfig: processedChartConfig,
        };
      } catch (error) {
        console.error("Error processing tool response:", error);
        return null;
      }
    };

    const processedChartData = toolUseContent ? processToolResponse(toolUseContent) : null;
    console.log("📊 Processed Chart Data:", processedChartData);

    return new Response(
      JSON.stringify({
        content: textContent?.text || "",
        hasToolUse: !!toolUseContent,
        toolUse: toolUseContent?.toolUse || null,
        chartData: processedChartData
      }),
      {
        headers: {
          "Content-Type": "application/json",
          "Cache-Control": "no-cache"
        }
      }
    );

  } catch (error) {
    console.error("❌ Finance API Error: ", error);
    console.error("Full error details:", {
      name: error instanceof Error ? error.name : "Unknown",
      message: error instanceof Error ? error.message : "Unknown error",
      stack: error instanceof Error ? error.stack : undefined,
    });

    if (error instanceof BedrockRuntimeServiceException) {
      return new Response(
        JSON.stringify({
          error: "AWS Service Error",
          details: error.message,
          code: error.$metadata.httpStatusCode
        }),
        { 
          status: error.$metadata.httpStatusCode || 500,
          headers: { "Content-Type": "application/json" }
        }
      );
    }

    return new Response(
      JSON.stringify({
        error: error instanceof Error ? error.message : "An unknown error occurred",
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}