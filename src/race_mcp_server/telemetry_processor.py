#!/usr/bin/env python3
"""
Race MCP Server - Enhanced telemetry processing and streaming capabilities

This module provides enhanced telemetry processing features including:
- Real-time telemetry streaming
- Historical data analysis
- Advanced car spotting algorithms
- AI-powered racing coaching

For production use with actual iRacing data, ensure pyirsdk is properly configured.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class LapAnalysis:
    """Detailed lap analysis results"""
    lap_number: int
    lap_time: float
    sector_times: List[float]
    speed_analysis: Dict[str, float]
    racing_line_efficiency: float
    consistency_rating: float
    improvement_suggestions: List[str]


@dataclass
class SessionStats:
    """Session statistics and progression"""
    total_laps: int
    best_lap: float
    worst_lap: float
    average_lap: float
    consistency: float
    pace_trend: str  # "improving", "stable", "declining"
    fuel_usage: float
    tire_degradation: Dict[str, float]


class AdvancedTelemetryProcessor:
    """Advanced telemetry processing and analysis"""
    
    def __init__(self):
        self.lap_history: List[Dict[str, Any]] = []
        self.telemetry_buffer: List[Dict[str, Any]] = []
        self.session_start_time = time.time()
        
    def process_telemetry_frame(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single telemetry frame and add analytics"""
        # Store telemetry for historical analysis
        self.telemetry_buffer.append(telemetry)
        
        # Keep buffer size manageable
        if len(self.telemetry_buffer) > 1000:
            self.telemetry_buffer = self.telemetry_buffer[-500:]
        
        # Add computed fields
        enhanced_telemetry = telemetry.copy()
        enhanced_telemetry.update({
            "g_force_lateral": self._calculate_lateral_g(telemetry),
            "g_force_longitudinal": self._calculate_longitudinal_g(telemetry),
            "racing_line_deviation": self._calculate_line_deviation(telemetry),
            "optimal_gear_suggestion": self._suggest_optimal_gear(telemetry),
            "braking_efficiency": self._analyze_braking_efficiency(telemetry),
            "throttle_smoothness": self._analyze_throttle_smoothness(telemetry)
        })
        
        return enhanced_telemetry
    
    def _calculate_lateral_g(self, telemetry: Dict[str, Any]) -> float:
        """Calculate lateral G-force based on speed and steering"""
        speed_ms = telemetry.get("speed", 0) * 0.44704  # mph to m/s
        steering_angle = abs(telemetry.get("steering", 0))
        
        # Simplified lateral G calculation
        if speed_ms > 5:  # Only calculate for meaningful speeds
            return (speed_ms * steering_angle) / 50.0  # Simplified formula
        return 0.0
    
    def _calculate_longitudinal_g(self, telemetry: Dict[str, Any]) -> float:
        """Calculate longitudinal G-force based on throttle/brake"""
        throttle = telemetry.get("throttle", 0)
        brake = telemetry.get("brake", 0)
        
        # Simplified calculation: positive for acceleration, negative for braking
        if brake > 0:
            return -brake * 2.0  # Braking G-force
        else:
            return throttle * 1.5  # Acceleration G-force
    
    def _calculate_line_deviation(self, telemetry: Dict[str, Any]) -> float:
        """Calculate deviation from optimal racing line"""
        # This would need track-specific racing line data
        # For now, return a simulated value based on steering smoothness
        steering = abs(telemetry.get("steering", 0))
        speed = telemetry.get("speed", 0)
        
        # Rough estimation: high steering at high speed = poor line
        if speed > 60:
            return steering * speed / 100.0
        return steering * 0.5
    
    def _suggest_optimal_gear(self, telemetry: Dict[str, Any]) -> int:
        """Suggest optimal gear based on RPM and speed"""
        rpm = telemetry.get("rpm", 0)
        current_gear = telemetry.get("gear", 1)
        
        # Simple gear suggestion logic
        if rpm > 7000 and current_gear < 6:
            return current_gear + 1  # Shift up
        elif rpm < 4000 and current_gear > 1:
            return current_gear - 1  # Shift down
        else:
            return current_gear  # Stay in current gear
    
    def _analyze_braking_efficiency(self, telemetry: Dict[str, Any]) -> float:
        """Analyze braking efficiency (0-1 scale)"""
        brake = telemetry.get("brake", 0)
        speed = telemetry.get("speed", 0)
        
        if brake > 0 and speed > 20:
            # Rate efficiency based on brake pressure vs speed
            optimal_pressure = min(speed / 100.0, 1.0)
            efficiency = 1.0 - abs(brake - optimal_pressure)
            return max(0.0, efficiency)
        return 1.0  # No braking or low speed
    
    def _analyze_throttle_smoothness(self, telemetry: Dict[str, Any]) -> float:
        """Analyze throttle application smoothness"""
        if len(self.telemetry_buffer) < 2:
            return 1.0
        
        # Compare current throttle to previous frames
        current_throttle = telemetry.get("throttle", 0)
        recent_frames = self.telemetry_buffer[-5:] if len(self.telemetry_buffer) >= 5 else self.telemetry_buffer
        
        if not recent_frames:
            return 1.0
        
        throttle_changes = []
        for frame in recent_frames:
            prev_throttle = frame.get("throttle", 0)
            throttle_changes.append(abs(current_throttle - prev_throttle))
        
        # Calculate smoothness (lower changes = higher smoothness)
        avg_change = sum(throttle_changes) / len(throttle_changes)
        smoothness = max(0.0, 1.0 - avg_change * 5.0)  # Scale factor
        return smoothness
    
    def analyze_lap_performance(self, lap_number: int) -> LapAnalysis:
        """Analyze performance for a specific lap"""
        # This would analyze telemetry data for the specified lap
        # For now, return simulated analysis
        return LapAnalysis(
            lap_number=lap_number,
            lap_time=85.234,
            sector_times=[28.123, 31.456, 25.655],
            speed_analysis={
                "max_speed": 142.5,
                "avg_speed": 98.7,
                "min_speed": 45.2,
                "speed_variance": 12.3
            },
            racing_line_efficiency=0.87,
            consistency_rating=0.92,
            improvement_suggestions=[
                "Carry more speed through turn 3",
                "Earlier throttle application in sector 2",
                "Optimize braking point for turn 7"
            ]
        )
    
    def get_session_statistics(self) -> SessionStats:
        """Get comprehensive session statistics"""
        # This would analyze all laps in the session
        return SessionStats(
            total_laps=len(self.lap_history),
            best_lap=82.451,
            worst_lap=87.892,
            average_lap=84.756,
            consistency=0.94,
            pace_trend="improving",
            fuel_usage=2.3,  # gallons per lap
            tire_degradation={
                "LF": 0.12,  # % degradation
                "RF": 0.15,
                "LR": 0.08,
                "RR": 0.11
            }
        )


class RacingAICoach:
    """AI-powered racing coach providing intelligent advice"""
    
    def __init__(self):
        self.telemetry_processor = AdvancedTelemetryProcessor()
        self.coaching_history: List[Dict[str, Any]] = []
    
    def analyze_driving_style(self, telemetry_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze driver's style based on telemetry history"""
        if not telemetry_data:
            return {"style": "insufficient_data", "characteristics": []}
        
        # Analyze patterns in the data
        avg_throttle = sum(t.get("throttle", 0) for t in telemetry_data) / len(telemetry_data)
        avg_brake = sum(t.get("brake", 0) for t in telemetry_data) / len(telemetry_data)
        steering_aggression = sum(abs(t.get("steering", 0)) for t in telemetry_data) / len(telemetry_data)
        
        characteristics = []
        style = "balanced"
        
        if avg_throttle > 0.8:
            characteristics.append("aggressive_acceleration")
            style = "aggressive"
        elif avg_throttle < 0.6:
            characteristics.append("conservative_acceleration")
            style = "conservative"
        
        if avg_brake > 0.6:
            characteristics.append("late_braking")
        elif avg_brake < 0.3:
            characteristics.append("early_braking")
        
        if steering_aggression > 0.3:
            characteristics.append("aggressive_steering")
        elif steering_aggression < 0.1:
            characteristics.append("smooth_steering")
        
        return {
            "style": style,
            "characteristics": characteristics,
            "aggression_level": (avg_throttle + steering_aggression) / 2,
            "smoothness_level": 1.0 - steering_aggression,
            "confidence_level": avg_throttle
        }
    
    def provide_situational_advice(self, current_situation: Dict[str, Any], 
                                 context: str = "") -> Dict[str, Any]:
        """Provide advice based on current racing situation"""
        telemetry = current_situation.get("telemetry", {})
        track_position = current_situation.get("track_position", "unknown")
        nearby_cars = current_situation.get("nearby_cars", [])
        
        advice_points = []
        priority = "medium"
        category = "general"
        
        # Analyze current telemetry for immediate advice
        speed = telemetry.get("speed", 0)
        throttle = telemetry.get("throttle", 0)
        brake = telemetry.get("brake", 0)
        gear = telemetry.get("gear", 1)
        rpm = telemetry.get("rpm", 0)
        
        # Speed and performance advice
        if speed < 30 and throttle < 0.5:
            advice_points.append("Consider increasing pace - you have room for more speed")
            priority = "high"
            category = "performance"
        
        # RPM and shifting advice
        if rpm > 7500:
            advice_points.append("Shift up - RPM is in the red zone")
            priority = "high"
            category = "car_control"
        elif rpm < 3000 and gear > 2:
            advice_points.append("Consider downshifting for better acceleration")
            priority = "medium"
            category = "car_control"
        
        # Braking analysis
        if brake > 0.9 and speed > 100:
            advice_points.append("Heavy braking at high speed - ensure you're on the racing line")
            priority = "high"
            category = "safety"
        
        # Traffic management
        if len(nearby_cars) > 0:
            cars_ahead = [car for car in nearby_cars if car.get("relative_distance", 0) > 0]
            cars_behind = [car for car in nearby_cars if car.get("relative_distance", 0) < 0]
            
            if cars_ahead:
                closest_ahead = min(cars_ahead, key=lambda x: x.get("relative_distance", float('inf')))
                if closest_ahead.get("relative_distance", 0) < 50:
                    advice_points.append(f"Car ahead: {closest_ahead.get('driver_name', 'Unknown')} - prepare for possible overtake")
                    priority = "high"
                    category = "strategy"
            
            if cars_behind:
                closest_behind = max(cars_behind, key=lambda x: x.get("relative_distance", float('-inf')))
                if abs(closest_behind.get("relative_distance", 0)) < 30:
                    advice_points.append(f"Car behind: {closest_behind.get('driver_name', 'Unknown')} - defend your position")
                    priority = "medium"
                    category = "strategy"
        
        # Contextual advice based on user's question
        if context:
            if "turn" in context.lower() or "corner" in context.lower():
                advice_points.append("For corner improvement: focus on entry speed, apex positioning, and exit acceleration")
                category = "racing_line"
            elif "setup" in context.lower():
                advice_points.append("Car setup concerns: monitor tire temps and adjust suspension/aero based on handling balance")
                category = "setup"
            elif "pace" in context.lower() or "speed" in context.lower():
                advice_points.append("To improve pace: analyze your braking points and acceleration zones")
                category = "performance"
        
        if not advice_points:
            advice_points.append("Maintain current approach - driving looks good")
        
        return {
            "advice": "; ".join(advice_points),
            "priority": priority,
            "category": category,
            "situation_analysis": {
                "speed_ok": 50 < speed < 150,
                "rpm_ok": 3000 < rpm < 7000,
                "traffic_density": len(nearby_cars),
                "immediate_threats": len([c for c in nearby_cars if abs(c.get("relative_distance", 100)) < 25])
            },
            "recommendations": {
                "immediate": advice_points[:2] if len(advice_points) > 2 else advice_points,
                "strategic": advice_points[2:] if len(advice_points) > 2 else []
            }
        }
