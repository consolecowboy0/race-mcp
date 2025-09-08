#!/usr/bin/env python3
"""
Simple test client for Race MCP Server

This script demonstrates how to connect to and interact with the Race MCP Server.
"""

import asyncio
import json
import sys
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def test_race_mcp_server():
    """Test the Race MCP Server functionality"""
    print("🏁 Testing Race MCP Server...")
    
    # Connect to the server
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "race_mcp_server"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            print("✅ Connected to Race MCP Server")
            
            # Test 1: List available tools
            print("\n🔧 Available Tools:")
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Test 2: Get telemetry data
            print("\n📊 Getting Telemetry:")
            telemetry_result = await session.call_tool("get_telemetry", {})
            telemetry_data = telemetry_result.content[0].text if telemetry_result.content else "No data"
            print(f"  Telemetry: {telemetry_data[:200]}...")
            
            # Test 3: Spot cars
            print("\n👀 Spotting Cars:")
            spot_result = await session.call_tool("spot_cars", {"radius": 100})
            spot_data = spot_result.content[0].text if spot_result.content else "No data"
            print(f"  Car spotting: {spot_data[:200]}...")
            
            # Test 4: Get racing advice
            print("\n🏎️ Getting Racing Advice:")
            advice_result = await session.call_tool("get_racing_advice", {
                "context": "I'm struggling with turn 3 at Road Atlanta",
                "focus_area": "racing_line"
            })
            advice_data = advice_result.content[0].text if advice_result.content else "No data"
            print(f"  Advice: {advice_data[:200]}...")
            
            # Test 5: List resources
            print("\n📚 Available Resources:")
            resources = await session.list_resources()
            for resource in resources.resources:
                print(f"  - {resource.name}: {resource.description}")
            
            # Test 6: Read a resource
            print("\n📖 Reading Live Telemetry Stream:")
            telemetry_stream = await session.read_resource("telemetry://live-stream")
            stream_data = telemetry_stream.contents[0].text if telemetry_stream.contents else "No data"
            print(f"  Stream data: {stream_data[:200]}...")
            
            # Test 7: List prompts
            print("\n💬 Available Prompts:")
            prompts = await session.list_prompts()
            for prompt in prompts.prompts:
                print(f"  - {prompt.name}: {prompt.description}")
            
            # Test 8: Get a prompt
            print("\n🎯 Getting Racing Coach Prompt:")
            coach_prompt = await session.get_prompt("racing_coach", {
                "situation": "I'm 2 seconds off the pace and losing time in the esses",
                "telemetry_data": json.dumps({"speed": 85, "throttle": 0.6, "brake": 0.3})
            })
            prompt_content = coach_prompt.messages[0].content.text if coach_prompt.messages else "No prompt"
            print(f"  Prompt: {prompt_content[:200]}...")
            
            print("\n🏆 All tests completed successfully!")


async def main():
    """Main entry point"""
    try:
        await test_race_mcp_server()
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
