"""
Race MCP Server - Main server implementation

This module implements the MCP server for iRacing telemetry streaming,
providing tools for racing analysis, car spotting, and AI-powered coaching.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Try to import pyirsdk, but make it optional for development
try:
    import pyirsdk
    PYIRSDK_AVAILABLE = True
except ImportError:
    PYIRSDK_AVAILABLE = False
    print("Warning: pyirsdk not available. Running in simulation mode.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration from environment
TELEMETRY_INTERVAL = float(os.getenv("IRACING_TELEMETRY_INTERVAL", "1.0"))
LOG_LEVEL = os.getenv("RACE_MCP_LOG_LEVEL", "INFO")
ENABLE_SPOTTING = os.getenv("RACE_MCP_ENABLE_SPOTTING", "true").lower() == "true"

logger.setLevel(getattr(logging, LOG_LEVEL.upper()))


@dataclass
class TelemetrySnapshot:
    """Snapshot of current telemetry data"""
    timestamp: float
    session_time: float
    lap: int
    lap_time: float
    lap_distance: float
    speed: float
    rpm: float
    gear: int
    throttle: float
    brake: float
    steering: float
    track_temp: float
    air_temp: float
    fuel_level: float
    tire_temps: Dict[str, float]
    is_on_track: bool
    session_state: str
    flag_state: str


@dataclass 
class CarInfo:
    """Information about a car in the session"""
    car_idx: int
    driver_name: str
    position: int
    class_position: int
    lap: int
    distance: float
    speed: float
    relative_distance: float
    is_player: bool


@dataclass
class RacingAdvice:
    """Racing advice response structure"""
    situation: str
    advice: str
    priority: str  # "low", "medium", "high", "critical"
    category: str  # "racing_line", "car_control", "strategy", "safety"
    telemetry_basis: Dict[str, Any]


class RaceMCPServer:
    """Main Race MCP Server class"""
    
    def __init__(self):
        self.server = Server("race-mcp-server")
        self.last_telemetry: Optional[TelemetrySnapshot] = None
        self.session_cars: Dict[int, CarInfo] = {}
        self.telemetry_stream_active = False
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup MCP protocol handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            """List available racing tools"""
            return [
                types.Tool(
                    name="get_telemetry",
                    description="Get current iRacing telemetry snapshot",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    },
                    outputSchema={
                        "type": "object",
                        "properties": {
                            "timestamp": {"type": "number"},
                            "session_time": {"type": "number"},
                            "lap": {"type": "integer"},
                            "speed": {"type": "number", "description": "Speed in mph"},
                            "rpm": {"type": "number"},
                            "gear": {"type": "integer"},
                            "throttle": {"type": "number", "description": "0.0 to 1.0"},
                            "brake": {"type": "number", "description": "0.0 to 1.0"},
                            "steering": {"type": "number", "description": "-1.0 to 1.0"},
                            "fuel_level": {"type": "number"},
                            "is_on_track": {"type": "boolean"},
                            "session_state": {"type": "string"},
                            "flag_state": {"type": "string"}
                        }
                    }
                ),
                types.Tool(
                    name="spot_cars",
                    description="Get information about cars around the player",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "radius": {
                                "type": "number",
                                "description": "Distance radius to search for cars (meters)",
                                "default": 100
                            }
                        }
                    },
                    outputSchema={
                        "type": "object",
                        "properties": {
                            "cars_ahead": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "driver_name": {"type": "string"},
                                        "distance": {"type": "number"},
                                        "speed": {"type": "number"},
                                        "position": {"type": "integer"}
                                    }
                                }
                            },
                            "cars_behind": {"type": "array"},
                            "cars_alongside": {"type": "array"}
                        }
                    }
                ),
                types.Tool(
                    name="get_racing_advice", 
                    description="Get AI-powered racing advice based on current telemetry and situation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "context": {
                                "type": "string",
                                "description": "Additional context about what you're looking for advice on"
                            },
                            "focus_area": {
                                "type": "string",
                                "enum": ["racing_line", "car_control", "strategy", "safety", "general"],
                                "default": "general"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="analyze_lap",
                    description="Analyze lap performance and provide improvement suggestions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "lap_number": {
                                "type": "integer",
                                "description": "Specific lap to analyze (default: most recent)"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="track_session",
                    description="Get session information and statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            """Handle tool calls"""
            try:
                if name == "get_telemetry":
                    return await self.get_telemetry()
                elif name == "spot_cars":
                    radius = arguments.get("radius", 100)
                    return await self.spot_cars(radius)
                elif name == "get_racing_advice":
                    context = arguments.get("context", "")
                    focus_area = arguments.get("focus_area", "general")
                    return await self.get_racing_advice(context, focus_area)
                elif name == "analyze_lap":
                    lap_number = arguments.get("lap_number", None)
                    return await self.analyze_lap(lap_number)
                elif name == "track_session":
                    return await self.track_session()
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Error in tool {name}: {str(e)}")
                return {
                    "error": str(e),
                    "tool": name,
                    "timestamp": time.time()
                }
        
        @self.server.list_resources()
        async def list_resources() -> List[types.Resource]:
            """List available resources"""
            return [
                types.Resource(
                    uri="telemetry://live-stream",
                    name="Live Telemetry Stream", 
                    description="Real-time iRacing telemetry data stream",
                    mimeType="application/json"
                ),
                types.Resource(
                    uri="session://current-info",
                    name="Current Session Info",
                    description="Information about the current racing session",
                    mimeType="application/json"
                ),
                types.Resource(
                    uri="track://layout-info",
                    name="Track Layout Information",
                    description="Track layout, sectors, and characteristics",
                    mimeType="application/json" 
                )
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read resource content"""
            logger.info(f"Reading resource: {uri}")
            if uri == "telemetry://live-stream":
                telemetry = await self.get_telemetry()
                return json.dumps(telemetry, indent=2)
            elif uri == "session://current-info":
                session_info = await self.track_session()
                return json.dumps(session_info, indent=2)
            elif uri == "track://layout-info":
                track_info = await self.get_track_info()
                return json.dumps(track_info, indent=2)
            else:
                logger.error(f"Unknown resource requested: {uri}")
                return json.dumps({"error": f"Unknown resource: {uri}"}, indent=2)
        
        @self.server.list_prompts()
        async def list_prompts() -> List[types.Prompt]:
            """List available prompt templates"""
            return [
                types.Prompt(
                    name="racing_coach",
                    description="Act as an experienced racing coach providing advice",
                    arguments=[
                        types.PromptArgument(
                            name="situation", 
                            description="Current racing situation or question",
                            required=True
                        ),
                        types.PromptArgument(
                            name="telemetry_data",
                            description="Current telemetry data to analyze",
                            required=False
                        )
                    ]
                ),
                types.Prompt(
                    name="car_spotter",
                    description="Act as a racing spotter providing situational awareness",
                    arguments=[
                        types.PromptArgument(
                            name="cars_nearby",
                            description="Information about nearby cars",
                            required=True
                        )
                    ]
                ),
                types.Prompt(
                    name="setup_analyst",
                    description="Analyze car setup and suggest improvements",
                    arguments=[
                        types.PromptArgument(
                            name="telemetry_history",
                            description="Historical telemetry data for analysis",
                            required=True
                        ),
                        types.PromptArgument(
                            name="track_conditions",
                            description="Current track conditions",
                            required=False
                        )
                    ]
                )
            ]
        
        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: Dict[str, str]) -> types.GetPromptResult:
            """Generate prompt content"""
            if name == "racing_coach":
                situation = arguments["situation"]
                telemetry_data = arguments.get("telemetry_data", "")
                
                prompt_content = f"""You are an experienced racing coach with expertise in motorsports across multiple disciplines. Your role is to provide expert racing advice based on telemetry data and track situations.

Current Situation: {situation}

Telemetry Context: {telemetry_data if telemetry_data else "No telemetry data provided"}

Please provide:
1. Immediate actionable advice for the current situation
2. Explanation of the reasoning behind your advice
3. Any safety considerations
4. Long-term improvement suggestions if applicable

Keep your advice clear, concise, and focused on what the driver can implement immediately."""

                return types.GetPromptResult(
                    description=f"Racing coach advice for: {situation}",
                    messages=[
                        types.PromptMessage(
                            role="user",
                            content=types.TextContent(
                                type="text",
                                text=prompt_content
                            )
                        )
                    ]
                )
            
            elif name == "car_spotter":
                cars_nearby = arguments["cars_nearby"]
                
                prompt_content = f"""You are a professional racing spotter providing real-time situational awareness to a race car driver. Your job is to communicate clearly and concisely about nearby traffic and potential hazards.

Nearby Cars Information: {cars_nearby}

Provide a spotter call that includes:
1. Clear communication about car positions relative to the driver
2. Any immediate safety concerns or opportunities
3. Advice on racing lines or passing opportunities
4. Warnings about potential incidents

Use standard spotter terminology and be concise - the driver needs quick, actionable information."""

                return types.GetPromptResult(
                    description="Racing spotter call for current track situation",
                    messages=[
                        types.PromptMessage(
                            role="user", 
                            content=types.TextContent(
                                type="text",
                                text=prompt_content
                            )
                        )
                    ]
                )
            
            else:
                raise ValueError(f"Unknown prompt: {name}")
    
    async def get_telemetry(self) -> Dict[str, Any]:
        """Get current telemetry data"""
        if PYIRSDK_AVAILABLE and pyirsdk.is_connected:
            try:
                # Get telemetry from iRacing
                telemetry_data = pyirsdk.get_data()
                if telemetry_data:
                    snapshot = TelemetrySnapshot(
                        timestamp=time.time(),
                        session_time=telemetry_data.get('SessionTime', 0),
                        lap=telemetry_data.get('Lap', 0),
                        lap_time=telemetry_data.get('LapCurrentLapTime', 0),
                        lap_distance=telemetry_data.get('LapDist', 0),
                        speed=telemetry_data.get('Speed', 0),
                        rpm=telemetry_data.get('RPM', 0),
                        gear=telemetry_data.get('Gear', 0),
                        throttle=telemetry_data.get('Throttle', 0),
                        brake=telemetry_data.get('Brake', 0),
                        steering=telemetry_data.get('SteeringWheelAngle', 0),
                        track_temp=telemetry_data.get('TrackTemp', 0),
                        air_temp=telemetry_data.get('AirTemp', 0),
                        fuel_level=telemetry_data.get('FuelLevel', 0),
                        tire_temps={
                            'LF': telemetry_data.get('LFtempCL', 0),
                            'RF': telemetry_data.get('RFtempCL', 0),
                            'LR': telemetry_data.get('LRtempCL', 0),
                            'RR': telemetry_data.get('RRtempCL', 0)
                        },
                        is_on_track=telemetry_data.get('IsOnTrack', False),
                        session_state=str(telemetry_data.get('SessionState', 'Unknown')),
                        flag_state=str(telemetry_data.get('SessionFlags', 'Green'))
                    )
                    self.last_telemetry = snapshot
                    return asdict(snapshot)
            except Exception as e:
                logger.error(f"Error getting telemetry: {e}")
        
        # Return simulated data if not connected or error
        simulated_data = TelemetrySnapshot(
            timestamp=time.time(),
            session_time=300.5,
            lap=5,
            lap_time=85.234,
            lap_distance=0.75,
            speed=120.5,
            rpm=6500,
            gear=4,
            throttle=0.8,
            brake=0.0,
            steering=0.15,
            track_temp=85.2,
            air_temp=72.1,
            fuel_level=15.5,
            tire_temps={'LF': 180.2, 'RF': 182.1, 'LR': 175.3, 'RR': 177.8},
            is_on_track=True,
            session_state="Racing",
            flag_state="Green"
        )
        return asdict(simulated_data)
    
    async def spot_cars(self, radius: float = 100) -> Dict[str, Any]:
        """Get information about nearby cars"""
        # This would integrate with iRacing's car position data
        # For now, return simulated data
        cars_ahead = [
            {
                "driver_name": "John Doe",
                "distance": 45.2,
                "speed": 125.3,
                "position": 3,
                "relative_time": 1.2
            },
            {
                "driver_name": "Jane Smith", 
                "distance": 89.1,
                "speed": 118.7,
                "position": 2,
                "relative_time": 2.8
            }
        ]
        
        cars_behind = [
            {
                "driver_name": "Bob Wilson",
                "distance": -32.1,
                "speed": 119.8,
                "position": 5,
                "relative_time": -0.9
            }
        ]
        
        return {
            "cars_ahead": cars_ahead,
            "cars_behind": cars_behind,
            "cars_alongside": [],
            "total_cars_nearby": len(cars_ahead) + len(cars_behind),
            "search_radius": radius,
            "timestamp": time.time()
        }
    
    async def get_racing_advice(self, context: str = "", focus_area: str = "general") -> Dict[str, Any]:
        """Generate racing advice based on current situation"""
        if not self.last_telemetry:
            await self.get_telemetry()
        
        # Analyze current situation
        advice = self._generate_advice_from_telemetry(context, focus_area)
        
        return {
            "advice": advice.advice,
            "situation": advice.situation,
            "priority": advice.priority,
            "category": advice.category,
            "telemetry_basis": advice.telemetry_basis,
            "context": context,
            "focus_area": focus_area,
            "timestamp": time.time()
        }
    
    def _generate_advice_from_telemetry(self, context: str, focus_area: str) -> RacingAdvice:
        """Generate racing advice based on telemetry analysis"""
        if not self.last_telemetry:
            return RacingAdvice(
                situation="No telemetry available",
                advice="Connect to iRacing to get real-time racing advice",
                priority="low",
                category="general",
                telemetry_basis={}
            )
        
        tel = self.last_telemetry
        situation_factors = []
        advice_points = []
        priority = "low"
        
        # Analyze speed and performance
        if tel.speed < 50:
            situation_factors.append("low speed")
            advice_points.append("Consider increasing pace if safe to do so")
        
        # Analyze throttle and brake inputs
        if tel.throttle > 0.95:
            situation_factors.append("full throttle")
        if tel.brake > 0.8:
            situation_factors.append("heavy braking")
            priority = "medium"
        
        # Analyze car control
        if abs(tel.steering) > 0.5:
            situation_factors.append("significant steering input")
            if tel.speed > 100:
                advice_points.append("Be smooth with steering inputs at high speed")
                priority = "high"
        
        # Generate contextual advice
        if focus_area == "safety":
            if tel.flag_state != "Green":
                advice_points.insert(0, f"Caution: {tel.flag_state} flag condition")
                priority = "critical"
        
        situation = f"Lap {tel.lap}, {', '.join(situation_factors) if situation_factors else 'normal driving'}"
        advice = "; ".join(advice_points) if advice_points else "Continue current driving approach"
        
        if context:
            advice = f"Given your question about {context}: {advice}"
        
        return RacingAdvice(
            situation=situation,
            advice=advice,
            priority=priority,
            category=focus_area,
            telemetry_basis={
                "speed": tel.speed,
                "throttle": tel.throttle,
                "brake": tel.brake,
                "steering": tel.steering,
                "gear": tel.gear,
                "lap": tel.lap
            }
        )
    
    async def analyze_lap(self, lap_number: Optional[int] = None) -> Dict[str, Any]:
        """Analyze lap performance"""
        # This would analyze historical lap data
        # For now, return basic analysis
        return {
            "lap_analyzed": lap_number or "current",
            "lap_time": "1:23.456",
            "sectors": {
                "sector_1": "28.123",
                "sector_2": "31.456", 
                "sector_3": "23.877"
            },
            "analysis": {
                "strengths": ["Good sector 1 time", "Consistent braking points"],
                "improvement_areas": ["Can carry more speed through turn 3", "Earlier throttle application in sector 2"],
                "overall_rating": "B+",
                "compared_to_personal_best": "+0.234 seconds"
            },
            "timestamp": time.time()
        }
    
    async def track_session(self) -> Dict[str, Any]:
        """Get session information"""
        return {
            "session_type": "Practice",
            "time_remaining": "15:30",
            "total_cars": 24,
            "current_position": 8,
            "laps_completed": 12,
            "best_lap_time": "1:22.891",
            "track_name": "Road Atlanta",
            "weather": {
                "air_temp": 72.1,
                "track_temp": 85.2,
                "wind_speed": 5.2,
                "conditions": "Clear"
            },
            "timestamp": time.time()
        }
    
    async def get_track_info(self) -> Dict[str, Any]:
        """Get track layout information"""
        return {
            "track_name": "Road Atlanta",
            "length": 2.54,
            "turns": 12,
            "sectors": 3,
            "direction": "Clockwise",
            "surface": "Asphalt",
            "characteristics": [
                "High-speed track",
                "Elevation changes", 
                "Challenging turn 1",
                "Long back straight"
            ],
            "notable_corners": {
                "Turn 1": "Uphill right-hander, heavy braking zone",
                "Turn 5": "Blind crest, commitment required",
                "Turn 10a": "Chicane, good overtaking opportunity"
            }
        }
    
    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="race-mcp-server",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """Main entry point"""
    logger.info("Starting Race MCP Server...")
    
    if PYIRSDK_AVAILABLE:
        logger.info("pyirsdk available - will connect to iRacing when possible")
    else:
        logger.warning("pyirsdk not available - running in simulation mode")
    
    server = RaceMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
