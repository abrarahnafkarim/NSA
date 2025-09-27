from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class GeoLocation(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    name: Optional[str] = Field(None, description="Location name")

class DateRange(BaseModel):
    start: datetime = Field(..., description="Start date and time")
    end: datetime = Field(..., description="End date and time")

class FarmAnalysisRequest(BaseModel):
    location: GeoLocation = Field(..., description="Farm location")
    farm_details: Dict[str, Any] = Field(..., description="Farm details including crop type, size, etc.")
    date_range: DateRange = Field(..., description="Analysis date range")
    analysis_type: str = Field("comprehensive", description="Type of analysis")
    
    class Config:
        json_schema_extra = {
            "example": {
                "location": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "name": "Sample Farm"
                },
                "farm_details": {
                    "crop_type": "corn",
                    "farm_size": 100,
                    "planting_date": "2024-03-15",
                    "target_pest": "corn_borer"
                },
                "date_range": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-01-31T23:59:59Z"
                },
                "analysis_type": "comprehensive"
            }
        }

class MetricsResponse(BaseModel):
    timestamp: datetime = Field(..., description="Analysis timestamp")
    location: Dict[str, Any] = Field(..., description="Analysis location")
    metrics: Dict[str, Any] = Field(..., description="Agricultural metrics")
    confidence_scores: Dict[str, float] = Field(..., description="Confidence scores")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    alerts: List[str] = Field(default_factory=list, description="Critical alerts")

class RealtimeMonitoringRequest(BaseModel):
    location: GeoLocation = Field(..., description="Monitoring location")
    crop_type: Optional[str] = Field(None, description="Crop type")
    refresh_interval: Optional[int] = Field(3600, description="Refresh interval in seconds")

class GameScenarioRequest(BaseModel):
    scenario_id: str = Field(..., description="Unique scenario identifier")
    scenario_type: str = Field(..., description="Type of scenario (drought, optimal, pest_outbreak)")
    difficulty_level: str = Field(..., description="Difficulty level (beginner, intermediate, expert)")
    learning_objectives: List[str] = Field(default_factory=list, description="Learning objectives")

class GameActionRequest(BaseModel):
    current_farm_state: Dict[str, Any] = Field(..., description="Current farm state")
    action: Dict[str, Any] = Field(..., description="Player action")

class GameScenarioResponse(BaseModel):
    scenario_id: str = Field(..., description="Scenario identifier")
    metrics: Dict[str, Any] = Field(..., description="Game metrics")
    narrative_context: str = Field(..., description="Narrative context")
    success_criteria: List[str] = Field(default_factory=list, description="Success criteria")
    real_world_connection: List[str] = Field(default_factory=list, description="Real-world connections")

class GameActionResponse(BaseModel):
    updated_metrics: Dict[str, Any] = Field(..., description="Updated metrics after action")
    impact_explanation: str = Field(..., description="Explanation of action impact")
    real_world_equivalent: str = Field(..., description="Real-world equivalent")
    nasa_data_connection: str = Field(..., description="NASA data connection")
    next_recommended_actions: List[str] = Field(default_factory=list, description="Next recommended actions")
