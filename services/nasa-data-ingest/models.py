from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class GeoLocation(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    name: Optional[str] = Field(None, description="Location name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "lat": 40.7128,
                "lon": -74.0060,
                "name": "New York City"
            }
        }

class DateRange(BaseModel):
    start: datetime = Field(..., description="Start date and time")
    end: datetime = Field(..., description="End date and time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-31T23:59:59Z"
            }
        }

class DatasetStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DataIngestionRequest(BaseModel):
    location: GeoLocation = Field(..., description="Geographic location for data")
    date_range: DateRange = Field(..., description="Date range for data collection")
    datasets: List[str] = Field(..., description="List of NASA datasets to fetch")
    priority: Optional[str] = Field("normal", description="Processing priority")
    
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
                "datasets": ["smap_l3", "modis_vegetation", "gpm"]
            }
        }

class DataIngestionResponse(BaseModel):
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Status message")
    estimated_completion: datetime = Field(..., description="Estimated completion time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "ingest_40.7128_-74.0060_20240101_120000",
                "status": "started",
                "message": "Data ingestion started",
                "estimated_completion": "2024-01-01T12:05:00Z"
            }
        }

class TaskStatus(BaseModel):
    task_id: str
    status: DatasetStatus
    progress: float = Field(0.0, ge=0.0, le=100.0)
    datasets_processed: List[str] = Field(default_factory=list)
    datasets_failed: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None

# Agricultural Metrics Models
class USMI(BaseModel):
    """Unified Soil Moisture Index"""
    value: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    components: Dict[str, float]
    quality_flags: Dict[str, Any]
    recommendations: List[str]
    
class AWLI(BaseModel):
    """Agricultural Water Level Indicator"""
    value: float = Field(..., ge=0.0, le=1.0)
    crop_type: str
    water_requirement_status: str
    components: Dict[str, float]
    irrigation_recommendations: List[str]

class PAOI(BaseModel):
    """Pesticide Application Optimization Index"""
    value: float = Field(..., ge=0.0, le=1.0)
    crop_type: str
    target_pest: str
    application_window: Dict[str, Any]
    components: Dict[str, float]
    environmental_impact_score: float = Field(..., ge=0.0, le=1.0)
    recommendations: List[str]

class AgriculturalMetrics(BaseModel):
    """Complete agricultural metrics package"""
    usmi: USMI
    awli: AWLI
    paoi: PAOI
    timestamp: datetime
    location: GeoLocation
    confidence_scores: Dict[str, float]
    alerts: List[str] = Field(default_factory=list)
