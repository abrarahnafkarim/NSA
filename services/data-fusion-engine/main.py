from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv

from fusion_engine import AgriculturalDataFusionEngine
from models import (
    FusionRequest,
    FusionResponse,
    USMI,
    AWLI,
    PAOI,
    GeoLocation,
    DateRange
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agricultural Data Fusion Engine",
    description="Advanced fusion engine for NASA agricultural intelligence metrics",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize fusion engine
fusion_engine = AgriculturalDataFusionEngine()

@app.on_event("startup")
async def startup_event():
    """Initialize fusion engine on startup"""
    try:
        await fusion_engine.initialize()
        logger.info("🧠 Agricultural Data Fusion Engine started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize fusion engine: {e}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "data-fusion-engine",
        "version": "2.0.0"
    }

@app.post("/api/v1/fusion/compute-unified-metrics", response_model=FusionResponse)
async def compute_unified_metrics(
    request: FusionRequest,
    background_tasks: BackgroundTasks
):
    """
    Compute all three unified agricultural metrics (USMI, AWLI, PAOI)
    """
    try:
        logger.info(f"🧮 Computing unified metrics for location: {request.location}")
        
        # Fetch raw NASA data
        raw_data = await fusion_engine.fetch_raw_data(
            request.location,
            request.date_range,
            request.datasets or [
                'smap_l3', 'smap_l4', 'modis_vegetation', 'modis_lst',
                'gpm', 'ecostress', 'grace', 'landsat'
            ]
        )
        
        # Compute unified metrics concurrently
        usmi_task = fusion_engine.compute_unified_soil_moisture_index(raw_data)
        awli_task = fusion_engine.compute_agricultural_water_level_indicator(
            raw_data, request.crop_type or "corn"
        )
        paoi_task = fusion_engine.compute_pesticide_application_optimization_index(
            raw_data, request.crop_type or "corn", request.target_pest or "general"
        )
        
        usmi, awli, paoi = await asyncio.gather(usmi_task, awli_task, paoi_task)
        
        # Generate integrated recommendations
        integrated_recommendations = await fusion_engine.generate_integrated_recommendations(
            usmi, awli, paoi, request
        )
        
        # Generate alerts
        alerts = await fusion_engine.generate_alerts(usmi, awli, paoi)
        
        # Prepare response
        response = FusionResponse(
            timestamp=datetime.now(),
            location=request.location,
            usmi=usmi,
            awli=awli,
            paoi=paoi,
            recommendations=integrated_recommendations,
            alerts=alerts,
            confidence_scores={
                "usmi": usmi.confidence,
                "awli": awli.get_confidence(),
                "paoi": paoi.get_confidence()
            }
        )
        
        # Store results in background
        background_tasks.add_task(
            fusion_engine.store_fusion_results,
            request.location,
            response
        )
        
        logger.info("✅ Unified metrics computation completed")
        return response
        
    except Exception as e:
        logger.error(f"❌ Unified metrics computation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Fusion computation failed: {str(e)}")

@app.post("/api/v1/fusion/compute-usmi", response_model=USMI)
async def compute_usmi(request: FusionRequest):
    """Compute Unified Soil Moisture Index"""
    try:
        raw_data = await fusion_engine.fetch_raw_data(
            request.location,
            request.date_range,
            ['smap_l3', 'smap_l4', 'modis_lst', 'gpm', 'ecostress']
        )
        
        usmi = await fusion_engine.compute_unified_soil_moisture_index(raw_data)
        return usmi
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"USMI computation failed: {str(e)}")

@app.post("/api/v1/fusion/compute-awli", response_model=AWLI)
async def compute_awli(request: FusionRequest):
    """Compute Agricultural Water Level Indicator"""
    try:
        raw_data = await fusion_engine.fetch_raw_data(
            request.location,
            request.date_range,
            ['grace', 'modis_vegetation', 'gpm', 'ecostress', 'landsat']
        )
        
        awli = await fusion_engine.compute_agricultural_water_level_indicator(
            raw_data, request.crop_type or "corn"
        )
        return awli
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AWLI computation failed: {str(e)}")

@app.post("/api/v1/fusion/compute-paoi", response_model=PAOI)
async def compute_paoi(request: FusionRequest):
    """Compute Pesticide Application Optimization Index"""
    try:
        raw_data = await fusion_engine.fetch_raw_data(
            request.location,
            request.date_range,
            ['modis_vegetation', 'landsat', 'modis_lst', 'gpm']
        )
        
        paoi = await fusion_engine.compute_pesticide_application_optimization_index(
            raw_data, request.crop_type or "corn", request.target_pest or "general"
        )
        return paoi
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PAOI computation failed: {str(e)}")

@app.get("/api/v1/fusion/metrics-history")
async def get_metrics_history(
    lat: float,
    lon: float,
    days: int = 30,
    crop_type: Optional[str] = None
):
    """Get historical metrics for a location"""
    try:
        location = GeoLocation(lat=lat, lon=lon)
        date_range = DateRange(
            start=datetime.now() - timedelta(days=days),
            end=datetime.now()
        )
        
        history = await fusion_engine.get_metrics_history(
            location, date_range, crop_type
        )
        
        return {
            "location": location,
            "date_range": date_range,
            "metrics_history": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics history: {str(e)}")

@app.get("/api/v1/fusion/crop-recommendations")
async def get_crop_recommendations(lat: float, lon: float):
    """Get crop recommendations based on location"""
    try:
        location = GeoLocation(lat=lat, lon=lon)
        recommendations = await fusion_engine.get_crop_recommendations(location)
        
        return {
            "location": location,
            "recommended_crops": recommendations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get crop recommendations: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
