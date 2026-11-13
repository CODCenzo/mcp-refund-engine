import asyncio
import os
import json
from datetime import datetime
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from google import genai

client = genai.Client()
MODEL_ID = "gemini-4-hydrogen" 

async def run_refund_agent():
    server_params = StdioServerParameters(
        command="python3",
        args=["src/server.py"]
    )

    print("[DEBUG] 1. Starting local MCP server connection...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("[DEBUG] 2. Initializing MCP session...")
            await session.initialize()
            
            print("[DEBUG] 3. Fetching tools from SQLite server...")
            mcp_tools = await session.list_tools()
            
            # Convert MCP tools to the new Interactions API dictionary format
            gemini_tools = []
            for tool in mcp_tools.tools:
                gemini_tools.append({
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "transaction_id": {
                                "type": "string"
                            }
                        },
                        "required": ["transaction_id"],
                    }
                })

            today_date = datetime.today().strftime('%Y-%m-%d')

            system_instruction = (
                f"You are a fintech support agent. Today's date is {today_date}. "
                "Use the provided tools to look up transactions. "
                "Compare the transaction age (from created_at to today) to the max_refund_days policy. "
                "Output a final decision: APPROVE or REJECT, along with a brief explanation.\n\n"
            )

            user_prompt = "User: A customer wants a refund for transaction TX-001. Can you process this?"
            print(f"\n{user_prompt}\n")
            
            print(f"[DEBUG] 4. Connecting to Gemini API (Model: {MODEL_ID})...")
            
            # Prepend system instruction for the first turn
            user_input = system_instruction + user_prompt
            previous_id = None

            # Stateful loop to handle multi-step function calling
            while True:
                print("[DEBUG] 5. Sending request to Gemini Interactions API...")
                
                # Execute in thread to avoid blocking the async event loop
                interaction = await asyncio.to_thread(
                    client.interactions.create,
                    model=MODEL_ID,
                    input=user_input,
                    tools=gemini_tools,
                    previous_interaction_id=previous_id
                )

                function_results = []
                
                # Process each step in the interaction for tool requests
                for step in interaction.steps:
                    if step.type == "function_call":
                        print(f"[DEBUG] <- Gemini requested tool: {step.name} | args: {step.arguments}")
                        
                        print("[DEBUG] -> Executing MCP tool against SQLite database...")
                        tool_result = await session.call_tool(
                            step.name,
                            arguments=step.arguments
                        )
                        
                        result_text = tool_result.content[0].text
                        print(f"[DEBUG] <- Database returned: {result_text}")
                        
                        # Append the formatted result
                        function_results.append({
                            "type": "function_result",
                            "name": step.name,
                            "call_id": step.id,
                            "result": [{"type": "text", "text": result_text}],
                        })

                # If no functions were called, the model provided its final answer
                if not function_results:
                    print(f"\nAI Agent Decision:\n{interaction.output_text}")
                    break

                # Prepare state for the next turn to send the results back to Gemini
                print("[DEBUG] -> Sending database JSON back to Gemini...")
                user_input = function_results
                previous_id = interaction.id

if __name__ == "__main__":
    asyncio.run(run_refund_agent())