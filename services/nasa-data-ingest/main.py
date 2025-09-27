from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv

from nasa_manager import NASADataManager
from models import (
    DataIngestionRequest, 
    DataIngestionResponse,
    DatasetStatus,
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
    title="NASA Data Ingestion Service",
    description="Service for ingesting NASA satellite and Earth observation data",
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

# Initialize NASA Data Manager
nasa_manager = NASADataManager()

@app.on_event("startup")
async def startup_event():
    """Initialize NASA authentication and services on startup"""
    try:
        await nasa_manager.authenticate_all_services()
        logger.info("🚀 NASA Data Ingestion Service started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize NASA services: {e}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "nasa-data-ingest",
        "version": "2.0.0"
    }

@app.post("/api/v1/nasa/ingest", response_model=DataIngestionResponse)
async def ingest_nasa_data(
    request: DataIngestionRequest,
    background_tasks: BackgroundTasks
):
    """
    Ingest NASA data for a specific location and time range
    """
    try:
        logger.info(f"📡 Starting NASA data ingestion for location: {request.location}")
        
        # Validate request
        if not request.datasets:
            raise HTTPException(status_code=400, detail="No datasets specified")
        
        # Start background ingestion task
        task_id = f"ingest_{request.location.lat}_{request.location.lon}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            process_data_ingestion,
            task_id,
            request
        )
        
        return DataIngestionResponse(
            task_id=task_id,
            status="started",
            message="Data ingestion started",
            estimated_completion=datetime.now() + timedelta(minutes=5)
        )
        
    except Exception as e:
        logger.error(f"❌ Data ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Data ingestion failed: {str(e)}")

async def process_data_ingestion(task_id: str, request: DataIngestionRequest):
    """Background task for processing data ingestion"""
    try:
        logger.info(f"🔄 Processing data ingestion task: {task_id}")
        
        # Fetch data from NASA APIs
        raw_data = await nasa_manager.bulk_data_fetch(
            request.location,
            request.date_range,
            request.datasets
        )
        
        # Store raw data
        await nasa_manager.store_raw_data(task_id, raw_data)
        
        # Notify completion
        await nasa_manager.notify_completion(task_id, raw_data)
        
        logger.info(f"✅ Data ingestion completed: {task_id}")
        
    except Exception as e:
        logger.error(f"❌ Data ingestion task failed {task_id}: {e}")
        await nasa_manager.notify_error(task_id, str(e))

@app.get("/api/v1/nasa/status/{task_id}")
async def get_ingestion_status(task_id: str):
    """Get status of data ingestion task"""
    try:
        status = await nasa_manager.get_task_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

@app.get("/api/v1/nasa/datasets")
async def get_available_datasets():
    """Get list of available NASA datasets"""
    return {
        "datasets": [
            {
                "id": "smap_l3",
                "name": "SMAP L3 Radiometer Global Daily 36 km EASE-Grid Soil Moisture",
                "description": "Surface soil moisture from SMAP radiometer",
                "spatial_resolution": "36km",
                "temporal_resolution": "Daily",
                "data_format": "NetCDF4"
            },
            {
                "id": "smap_l4",
                "name": "SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture",
                "description": "Surface and root zone soil moisture from SMAP",
                "spatial_resolution": "9km",
                "temporal_resolution": "3-hourly",
                "data_format": "NetCDF4"
            },
            {
                "id": "modis_vegetation",
                "name": "MODIS Terra/Aqua Combined Vegetation Indices",
                "description": "NDVI and EVI vegetation indices",
                "spatial_resolution": "250m",
                "temporal_resolution": "16-day",
                "data_format": "HDF5"
            },
            {
                "id": "modis_lst",
                "name": "MODIS Land Surface Temperature",
                "description": "Day and night land surface temperature",
                "spatial_resolution": "1km",
                "temporal_resolution": "Daily",
                "data_format": "HDF5"
            },
            {
                "id": "gpm",
                "name": "GPM IMERG Final Precipitation L3 Half Hourly",
                "description": "Global precipitation estimates",
                "spatial_resolution": "0.1°",
                "temporal_resolution": "30-minute",
                "data_format": "NetCDF4"
            },
            {
                "id": "ecostress",
                "name": "ECOSTRESS Land Surface Temperature and Emissivity",
                "description": "High-resolution thermal data",
                "spatial_resolution": "70m",
                "temporal_resolution": "Variable",
                "data_format": "HDF5"
            },
            {
                "id": "grace",
                "name": "GRACE/GRACE-FO Groundwater and Soil Moisture Conditions",
                "description": "Terrestrial water storage anomalies",
                "spatial_resolution": "1°",
                "temporal_resolution": "Monthly",
                "data_format": "NetCDF4"
            },
            {
                "id": "landsat",
                "name": "Landsat 8/9 Multispectral Analysis",
                "description": "High-resolution multispectral imagery",
                "spatial_resolution": "30m",
                "temporal_resolution": "16-day",
                "data_format": "GeoTIFF"
            }
        ]
    }

@app.get("/api/v1/nasa/test-auth")
async def test_nasa_authentication():
    """Test NASA API authentication"""
    try:
        auth_status = await nasa_manager.test_authentication()
        return {
            "authentication_status": "success",
            "services": auth_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
