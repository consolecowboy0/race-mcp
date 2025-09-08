#!/bin/bash
# Race MCP Server Startup Script
# Usage: ./start_server.sh [options]

set -e

# Default values
DEBUG_MODE=false
PORT=3000
SIMULATION_MODE=false
LOG_FILE=""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_debug() {
    if [ "$DEBUG_MODE" = true ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Help function
show_help() {
    echo "Race MCP Server Startup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -d, --debug         Enable debug mode with verbose logging"
    echo "  -p, --port PORT     Set server port (default: 3000)"
    echo "  -s, --simulation    Force simulation mode (no iRacing connection)"
    echo "  -l, --log FILE      Log output to file"
    echo "  --test              Run test client after starting server"
    echo "  --check             Check system requirements and exit"
    echo ""
    echo "Examples:"
    echo "  $0                  # Start server with default settings"
    echo "  $0 -d -p 3001       # Start with debug mode on port 3001"
    echo "  $0 -s -l server.log # Start in simulation mode with logging"
    echo "  $0 --check          # Check if all requirements are met"
}

# Check system requirements
check_requirements() {
    print_status "Checking system requirements..."
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_status "Python version: $PYTHON_VERSION"
    else
        print_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
    
    # Check virtual environment
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        print_status "Virtual environment: $VIRTUAL_ENV"
    else
        print_warning "No virtual environment detected. Consider using 'source .venv/bin/activate'"
    fi
    
    # Check if package is installed
    if python3 -c "import race_mcp_server" 2>/dev/null; then
        print_status "race_mcp_server package is installed"
    else
        print_error "race_mcp_server package not found. Run 'pip install -e .' first"
        exit 1
    fi
    
    # Check dependencies
    local deps=("mcp" "pyirsdk" "pydantic" "aiofiles")
    for dep in "${deps[@]}"; do
        if python3 -c "import $dep" 2>/dev/null; then
            print_status "Dependency $dep is installed"
        else
            print_error "Missing dependency: $dep. Run 'pip install $dep'"
            exit 1
        fi
    done
    
    # Check iRacing connection (if not in simulation mode)
    if [ "$SIMULATION_MODE" = false ]; then
        print_status "Checking iRacing connection..."
        if python3 -c "
import pyirsdk
ir = pyirsdk.IRSDK()
if ir.startup():
    print('iRacing connection available')
    ir.shutdown()
else:
    print('iRacing not running or telemetry disabled')
" 2>/dev/null; then
            print_status "iRacing telemetry is available"
        else
            print_warning "iRacing not detected. Server will run in simulation mode"
            SIMULATION_MODE=true
        fi
    fi
    
    print_status "All requirements checked successfully!"
}

# Start the server
start_server() {
    print_status "Starting Race MCP Server..."
    
    # Prepare environment variables
    if [ "$DEBUG_MODE" = true ]; then
        export MCP_DEBUG=1
        print_debug "Debug mode enabled"
    fi
    
    if [ "$SIMULATION_MODE" = true ]; then
        export RACE_MCP_SIMULATION=1
        print_status "Simulation mode enabled"
    fi
    
    # Prepare command
    local cmd="python3 -m race_mcp_server"
    
    # Add logging if specified
    if [ "$LOG_FILE" != "" ]; then
        print_status "Logging to: $LOG_FILE"
        cmd="$cmd 2>&1 | tee $LOG_FILE"
    fi
    
    print_status "Server command: $cmd"
    print_status "Server starting on port $PORT..."
    print_status "Press Ctrl+C to stop the server"
    print_status ""
    
    # Execute the command
    eval $cmd
}

# Run test client
run_tests() {
    print_status "Running test client..."
    
    if [ -f "test_client.py" ]; then
        python3 test_client.py
    else
        print_error "test_client.py not found in current directory"
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--debug)
            DEBUG_MODE=true
            shift
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -s|--simulation)
            SIMULATION_MODE=true
            shift
            ;;
        -l|--log)
            LOG_FILE="$2"
            shift 2
            ;;
        --test)
            RUN_TESTS=true
            shift
            ;;
        --check)
            check_requirements
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
print_status "Race MCP Server Startup Script"
print_status "==============================="

# Always check requirements first
check_requirements

# Change to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
print_debug "Working directory: $SCRIPT_DIR"

# Set up Python path
export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"
print_debug "PYTHONPATH: $PYTHONPATH"

# Start the server
if [ "$RUN_TESTS" = true ]; then
    print_status "Starting server in background for testing..."
    start_server &
    SERVER_PID=$!
    
    # Wait a moment for server to start
    sleep 3
    
    # Run tests
    run_tests
    
    # Stop the server
    print_status "Stopping server (PID: $SERVER_PID)..."
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
    print_status "Test run complete!"
else
    start_server
fi
