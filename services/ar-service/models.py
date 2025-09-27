from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

class ARVisualizationRequest(BaseModel):
    location: Dict[str, Any] = Field(..., description="Location coordinates")
    farm_details: Dict[str, Any] = Field(..., description="Farm details")
    date_range: Dict[str, Any] = Field(..., description="Date range for analysis")
    visualization_type: str = Field("comprehensive", description="Type of AR visualization")
    
    class Config:
        json_schema_extra = {
            "example": {
                "location": {"lat": 40.7128, "lon": -74.0060},
                "farm_details": {"crop_type": "corn"},
                "date_range": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-01-31T23:59:59Z"
                },
                "visualization_type": "comprehensive"
            }
        }

class ARVisualizationResponse(BaseModel):
    location: Dict[str, Any] = Field(..., description="Visualization location")
    visualization_type: str = Field(..., description="Type of visualization")
    components: Dict[str, Any] = Field(..., description="AR visualization components")
    metadata: Dict[str, Any] = Field(..., description="Visualization metadata")
