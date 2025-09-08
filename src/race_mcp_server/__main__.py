#!/usr/bin/env python3
"""
Race MCP Server CLI Entry Point
"""

import sys
import asyncio

from race_mcp_server.main import main


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down Race MCP Server...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
