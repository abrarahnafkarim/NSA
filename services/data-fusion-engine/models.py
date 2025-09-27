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

class FusionRequest(BaseModel):
    location: GeoLocation = Field(..., description="Geographic location")
    date_range: DateRange = Field(..., description="Date range for analysis")
    crop_type: Optional[str] = Field(None, description="Type of crop")
    target_pest: Optional[str] = Field(None, description="Target pest for PAOI")
    datasets: Optional[List[str]] = Field(None, description="Specific datasets to use")
    
    class Config:
        json_schema_extra = {
            "example": {
                "location": {
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "name": "Sample Farm"
                },
                "date_range": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-01-31T23:59:59Z"
                },
                "crop_type": "corn",
                "target_pest": "corn_borer"
            }
        }

class USMI(BaseModel):
    """Unified Soil Moisture Index"""
    value: float = Field(..., ge=0.0, le=1.0, description="USMI value (0-1)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    components: Dict[str, float] = Field(..., description="Component values")
    quality_flags: Dict[str, Any] = Field(..., description="Data quality indicators")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    
    def get_category(self) -> str:
        """Get USMI category based on value"""
        if self.value >= 0.8:
            return "optimal"
        elif self.value >= 0.6:
            return "good"
        elif self.value >= 0.4:
            return "moderate"
        elif self.value >= 0.2:
            return "poor"
        else:
            return "critical"

class AWLI(BaseModel):
    """Agricultural Water Level Indicator"""
    value: float = Field(..., ge=0.0, le=1.0, description="AWLI value (0-1)")
    crop_type: str = Field(..., description="Crop type")
    water_requirement_status: str = Field(..., description="Water requirement status")
    components: Dict[str, float] = Field(..., description="Component values")
    irrigation_recommendations: List[str] = Field(default_factory=list, description="Irrigation recommendations")
    
    def get_confidence(self) -> float:
        """Calculate confidence based on component consistency"""
        if not self.components:
            return 0.5
        return min(1.0, np.std(list(self.components.values())) * 2)
    
    def get_irrigation_need(self) -> str:
        """Get irrigation need level"""
        if self.value >= 0.7:
            return "low"
        elif self.value >= 0.4:
            return "moderate"
        else:
            return "high"

class PAOI(BaseModel):
    """Pesticide Application Optimization Index"""
    value: float = Field(..., ge=0.0, le=1.0, description="PAOI value (0-1)")
    crop_type: str = Field(..., description="Crop type")
    target_pest: str = Field(..., description="Target pest")
    application_window: Dict[str, Any] = Field(..., description="Optimal application window")
    components: Dict[str, float] = Field(..., description="Component values")
    environmental_impact_score: float = Field(..., ge=0.0, le=1.0, description="Environmental impact")
    recommendations: List[str] = Field(default_factory=list, description="Application recommendations")
    
    def get_confidence(self) -> float:
        """Calculate confidence based on data quality"""
        if not self.components:
            return 0.5
        return min(1.0, np.mean(list(self.components.values())))

class FusionResponse(BaseModel):
    """Complete fusion response"""
    timestamp: datetime = Field(..., description="Analysis timestamp")
    location: GeoLocation = Field(..., description="Analysis location")
    usmi: USMI = Field(..., description="Unified Soil Moisture Index")
    awli: AWLI = Field(..., description="Agricultural Water Level Indicator")
    paoi: PAOI = Field(..., description="Pesticide Application Optimization Index")
    recommendations: List[str] = Field(default_factory=list, description="Integrated recommendations")
    alerts: List[str] = Field(default_factory=list, description="Critical alerts")
    confidence_scores: Dict[str, float] = Field(..., description="Confidence scores for each metric")

class CropRecommendation(BaseModel):
    """Crop recommendation"""
    crop_name: str = Field(..., description="Crop name")
    suitability_score: float = Field(..., ge=0.0, le=1.0, description="Suitability score")
    planting_window: Dict[str, str] = Field(..., description="Optimal planting window")
    water_requirements: Dict[str, Any] = Field(..., description="Water requirements")
    expected_yield: Dict[str, Any] = Field(..., description="Expected yield estimates")
    challenges: List[str] = Field(default_factory=list, description="Potential challenges")

class MetricsHistory(BaseModel):
    """Historical metrics data"""
    date: datetime = Field(..., description="Date")
    usmi: float = Field(..., description="USMI value")
    awli: float = Field(..., description="AWLI value")
    paoi: float = Field(..., description="PAOI value")
    weather_summary: Dict[str, Any] = Field(..., description="Weather summary")
