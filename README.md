# Race MCP Server

A comprehensive MCP (Model Context Protocol) server for iRacing telemetry data that provides real-time racing advice, car spotting, telemetry analysis, and conversational interaction about racing data.

## 🏁 Overview

This MCP server transforms iRacing telemetry data into actionable racing insights through:
- **Real-time telemetry streaming** with advanced analytics
- **AI-powered racing coaching** based on driving patterns
- **Intelligent car spotting** and traffic awareness
- **Detailed lap analysis** with improvement suggestions
- **Session monitoring** with performance trends
- **Conversational interface** for natural racing discussions

## 🚀 Features

### Core Capabilities
- **Live Telemetry Processing**: Real-time data from iRacing via pyirsdk
- **Advanced Analytics**: G-force calculations, racing line analysis, gear optimization
- **Racing AI Coach**: Personalized advice based on driving style and situation
- **Car Spotting System**: Traffic awareness and positioning intelligence
- **Performance Analysis**: Lap-by-lap breakdown with improvement suggestions
- **Session Tracking**: Long-term performance trends and statistics

### MCP Integration
- **5 Interactive Tools**: Direct telemetry access and analysis functions
- **3 Live Resources**: Streaming data feeds for continuous monitoring  
- **3 AI Prompts**: Specialized coaching personalities (coach, spotter, setup analyst)
- **JSON-RPC 2.0**: Standard MCP protocol compliance
- **STDIO Transport**: Ready for integration with MCP clients

## 📦 Installation

### Prerequisites
- Python 3.8+
- iRacing simulator (for live telemetry)
- Virtual environment (recommended)

### Quick Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd race-mcp

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package with dependencies
pip install -e .
```

### Manual Dependencies
If you prefer manual installation:
```bash
pip install mcp pyirsdk pydantic aiofiles
```

## 🎮 Usage

### Running the Server
```bash
# Activate virtual environment
source .venv/bin/activate

# Run the MCP server directly
python -m race_mcp_server

# Or use the convenient startup script
./start_server.sh

# Run with debug logging
./start_server.sh --debug

# Run in simulation mode (no iRacing required)
./start_server.sh --simulation
```

### Mock iRacing Data Generator
For development without the simulator, a standalone process can emit realistic iRacing-style telemetry over TCP.

```bash
# Start the mock telemetry stream on port 9000
python -m race_mcp_server.mock_iracing_stream --port 9000
```

Clients can connect to the specified host and port to receive newline-delimited JSON telemetry frames that mimic the structure of a real iRacing stream.

### Testing the Server
```bash
# Run comprehensive tests
python test_client.py

# Or use the startup script with testing
./start_server.sh --test
```

## 🛠 Available Tools

### 1. `get_telemetry`
**Purpose**: Retrieve current telemetry data with enhanced analytics
```json
{
  "name": "get_telemetry",
  "arguments": {
    "include_analytics": true,
    "format": "detailed"
  }
}
```
**Returns**: Complete telemetry data including speed, RPM, position, G-forces, and racing line analysis

### 2. `spot_cars` 
**Purpose**: Identify and analyze nearby cars for situational awareness
```json
{
  "name": "spot_cars",
  "arguments": {
    "radius_meters": 100,
    "include_predictions": true
  }
}
```
**Returns**: List of nearby cars with relative positions, speeds, and trajectory predictions

### 3. `get_racing_advice`
**Purpose**: Get AI-powered coaching advice based on current situation
```json
{
  "name": "get_racing_advice", 
  "arguments": {
    "context": "struggling with turn 3 entry speed",
    "focus_area": "cornering"
  }
}
```
**Returns**: Personalized advice with priority levels and specific recommendations

### 4. `analyze_lap`
**Purpose**: Detailed analysis of lap performance with improvement suggestions
```json
{
  "name": "analyze_lap",
  "arguments": {
    "lap_number": 5,
    "compare_to_best": true
  }
}
```
**Returns**: Sector times, racing line efficiency, consistency ratings, and specific improvement areas

### 5. `track_session`
**Purpose**: Monitor overall session progress and performance trends
```json
{
  "name": "track_session",
  "arguments": {
    "include_trends": true,
    "format": "summary"
  }
}
```
**Returns**: Session statistics, pace trends, fuel usage, and tire degradation analysis

## 📊 Live Resources

### 1. `telemetry://live-stream`
Continuous telemetry data stream with real-time updates

### 2. `session://current-info`
Current session information including track, conditions, and session type

### 3. `track://layout-info` 
Track-specific information including turn locations and racing line data

## 🤖 AI Prompts

### 1. `racing_coach`
**Personality**: Professional racing instructor
**Focus**: Technique improvement and strategic advice
**Use Case**: General racing improvement and learning

### 2. `car_spotter`
**Personality**: Experienced spotter focused on safety and positioning
**Focus**: Traffic management and situational awareness  
**Use Case**: Race situations and traffic navigation

### 3. `setup_analyst`
**Personality**: Technical setup engineer
**Focus**: Vehicle setup optimization and handling analysis
**Use Case**: Car setup tuning and technical adjustments

## 🧪 Testing

### Run the Test Client
The test client provides a comprehensive way to interact with all server functionality:

```bash
# Test all server functionality
python test_client.py

# Use the startup script for automated testing
./start_server.sh --test
```

### Test Client Features
- **Tool Testing**: Tests all 5 MCP tools with realistic parameters
- **Resource Access**: Validates all 3 live resources  
- **Prompt Testing**: Exercises all 3 AI coaching prompts
- **Error Handling**: Tests server resilience and error responses
- **Performance**: Shows response times and data validation

### Manual Server Testing
```bash
# Start server manually and test with direct JSON-RPC calls
python -m race_mcp_server

# In another terminal, you can send JSON-RPC messages via stdin
# (Advanced usage - test_client.py is much easier)
```

## 🔧 Configuration

### Environment Variables
```bash
# Enable debug logging
export MCP_DEBUG=1

# Force simulation mode
export RACE_MCP_SIMULATION=1

# Set custom iRacing data path (if needed)
export IRSDK_PATH=/path/to/irsdk
```

### Server Configuration
Modify settings in `src/race_mcp_server/main.py`:
- Telemetry update intervals
- Simulation mode parameters
- Logging levels
- Analysis parameters

### Startup Script Options
```bash
./start_server.sh --help    # Show all available options
./start_server.sh --check   # Verify system requirements
```

## 🔍 Troubleshooting

### Common Issues

1. **"pyirsdk connection failed"**
   - Ensure iRacing is running and in a session
   - Check that iRacing telemetry output is enabled
   - The server will run in simulation mode if iRacing isn't available

2. **"Tool execution failed"**
   - Check server logs for detailed error messages
   - Verify the tool arguments match the expected schema
   - Try restarting the server

3. **"Resource access failed"**
   - Resources return simulated data when iRacing isn't running
   - Check that the server started without errors
   - Verify the resource URIs are correct

### Debug Mode
```bash
# Enable verbose logging
python -m race_mcp_server --debug

# View detailed telemetry processing
export MCP_DEBUG=1 python -m race_mcp_server
```

### Log Files
- Server logs: Written to console (redirect to file if needed)
- iRacing connection status: Logged at startup
- Tool execution: Logged for each request

## 🏗 Development

### Project Structure
```
race-mcp/
├── src/race_mcp_server/
│   ├── __init__.py              # Package initialization
│   ├── __main__.py              # CLI entry point  
│   ├── main.py                  # Core MCP server (580+ lines)
│   └── telemetry_processor.py   # Advanced analytics engine
├── start_server.sh              # Convenient startup script
├── pyproject.toml               # Project configuration
├── test_client.py               # Comprehensive test suite
└── README.md                    # This file
```

### Adding New Features
1. **New Tools**: Add methods to `RaceMCPServer` class in `main.py`
2. **New Resources**: Extend the resource handlers
3. **Enhanced Analytics**: Modify `telemetry_processor.py`
4. **New Prompts**: Add prompt templates to the prompts section

### Testing New Features
```bash
# Test after making changes
python test_client.py

# Test with debug output
./start_server.sh --debug --test
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request with detailed description

## 📋 Requirements

### Core Dependencies
```toml
mcp = ">=1.0.0"          # Model Context Protocol framework
pyirsdk = ">=1.3.0"      # iRacing SDK integration
pydantic = ">=2.0.0"     # Data validation and serialization
aiofiles = ">=0.8.0"     # Async file operations
```

### System Requirements
- **OS**: Windows, macOS, or Linux
- **Python**: 3.8+ (tested with 3.10.12)
- **Memory**: 100MB+ available
- **iRacing**: Any recent version with telemetry enabled (optional - server runs in simulation mode without it)

### Optional Dependencies
- **pytest**: For running extended test suites
- **MCP Client**: Any MCP-compatible client for integration

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🏆 Acknowledgments

- **iRacing**: For providing the comprehensive telemetry API
- **MCP Community**: For the excellent Model Context Protocol framework
- **Racing Community**: For feedback and feature suggestions

---

**Ready to improve your lap times? Start the server and run the test client to see it in action! 🏎️💨**

## Configuration

The server can be configured via environment variables:

- `IRACING_TELEMETRY_INTERVAL` - Telemetry update interval in seconds (default: 1.0)
- `RACE_MCP_LOG_LEVEL` - Logging level (default: INFO)
- `RACE_MCP_ENABLE_SPOTTING` - Enable car spotting features (default: true)

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   iRacing Sim   │───▶│  pyirsdk Stream │───▶│   MCP Server    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Claude/AI     │◀───│  MCP Protocol   │◀───│  Tool Handlers  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Development

```bash
# Run tests
pytest

# Format code
black src/
isort src/

# Type checking
mypy src/
```

## License

MIT License
