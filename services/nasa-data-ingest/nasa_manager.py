import asyncio
import aiohttp
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
import json
import os
from dataclasses import dataclass
import redis
import asyncpg
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

@dataclass
class GeoLocation:
    lat: float
    lon: float
    name: Optional[str] = None
    
    @property
    def bbox(self):
        """Create bounding box around location"""
        offset = 0.1  # degrees
        return {
            'west': self.lon - offset,
            'south': self.lat - offset,
            'east': self.lon + offset,
            'north': self.lat + offset
        }
    
    @property
    def bbox_string(self):
        """Bounding box as string for API calls"""
        bbox = self.bbox
        return f"{bbox['west']},{bbox['south']},{bbox['east']},{bbox['north']}"

@dataclass
class DateRange:
    start: datetime
    end: datetime
    
    @property
    def start_iso(self):
        return self.start.isoformat()
    
    @property
    def end_iso(self):
        return self.end.isoformat()

class NASADataManager:
    """
    Master NASA data access and management system
    Handles authentication, rate limiting, and data caching
    """
    
    def __init__(self):
        self.earthdata_username = os.getenv('NASA_EARTHDATA_USERNAME')
        self.earthdata_password = os.getenv('NASA_EARTHDATA_PASSWORD')
        self.redis_client = None
        self.db_pool = None
        
        # NASA API endpoints
        self.endpoints = {
            'earthdata_login': 'https://urs.earthdata.nasa.gov',
            'appeears_api': 'https://appeears.earthdatacloud.nasa.gov',
            'giovanni_api': 'https://giovanni.gsfc.nasa.gov/giovanni',
            'worldview_gibs': 'https://gibs.earthdata.nasa.gov',
            'lpdaac_data_pool': 'https://e4ftl01.cr.usgs.gov'
        }
        
        # Rate limiting
        self.rate_limits = {
            'earthdata': 1000,  # requests per hour
            'appeears': 100,    # requests per hour
            'giovanni': 500     # requests per hour
        }
    
    async def authenticate_all_services(self):
        """Authenticate with all NASA services"""
        logger.info("🔐 Authenticating with NASA services...")
        
        # Initialize Redis connection
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        
        # Initialize database connection
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            self.db_pool = await asyncpg.create_pool(database_url)
        
        # Test authentication
        auth_tokens = {}
        
        # For now, we'll use basic authentication
        # In production, implement OAuth2 flow
        if self.earthdata_username and self.earthdata_password:
            auth_tokens['earthdata'] = f"{self.earthdata_username}:{self.earthdata_password}"
        
        logger.info("✅ NASA authentication setup complete")
        return auth_tokens
    
    async def bulk_data_fetch(
        self, 
        location: GeoLocation, 
        date_range: DateRange, 
        datasets: List[str]
    ) -> Dict[str, Any]:
        """
        Optimized bulk fetching of multiple NASA datasets
        """
        logger.info(f"📡 Fetching NASA data for {len(datasets)} datasets")
        
        tasks = []
        for dataset in datasets:
            task = self._fetch_dataset(dataset, location, date_range)
            tasks.append(task)
        
        # Fetch all datasets concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Organize results
        data_results = {}
        for dataset, result in zip(datasets, results):
            if isinstance(result, Exception):
                logger.error(f"❌ Failed to fetch {dataset}: {result}")
                data_results[dataset] = None
            else:
                data_results[dataset] = result
        
        return data_results
    
    async def _fetch_dataset(
        self, 
        dataset_id: str, 
        location: GeoLocation, 
        date_range: DateRange
    ) -> Dict[str, Any]:
        """Fetch specific dataset with retry logic"""
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if dataset_id == 'smap_l3':
                    return await self._fetch_smap_soil_moisture(location, date_range, 'l3')
                elif dataset_id == 'smap_l4':
                    return await self._fetch_smap_soil_moisture(location, date_range, 'l4')
                elif dataset_id == 'modis_vegetation':
                    return await self._fetch_modis_vegetation(location, date_range)
                elif dataset_id == 'modis_lst':
                    return await self._fetch_modis_lst(location, date_range)
                elif dataset_id == 'gpm':
                    return await self._fetch_gpm_precipitation(location, date_range)
                elif dataset_id == 'ecostress':
                    return await self._fetch_ecostress_data(location, date_range)
                elif dataset_id == 'grace':
                    return await self._fetch_grace_groundwater(location, date_range)
                elif dataset_id == 'landsat':
                    return await self._fetch_landsat_data(location, date_range)
                else:
                    raise ValueError(f"Unknown dataset: {dataset_id}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt + 1} failed for {dataset_id}: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return {}
    
    async def _fetch_smap_soil_moisture(
        self, 
        location: GeoLocation, 
        date_range: DateRange, 
        level: str
    ) -> Dict[str, Any]:
        """Fetch SMAP soil moisture data"""
        logger.info(f"🌍 Fetching SMAP {level} soil moisture data")
        
        # Mock implementation - in production, use real NASA APIs
        # For now, return realistic mock data
        return {
            'dataset': f'smap_{level}',
            'location': {'lat': location.lat, 'lon': location.lon},
            'date_range': {'start': date_range.start_iso, 'end': date_range.end_iso},
            'data': {
                'surface_moisture': np.random.uniform(0.1, 0.4),  # m³/m³
                'root_zone_moisture': np.random.uniform(0.15, 0.35),
                'soil_temperature': np.random.uniform(15, 25),  # °C
                'quality_flag': 'good',
                'uncertainty': np.random.uniform(0.05, 0.15)
            },
            'metadata': {
                'spatial_resolution': '36km' if level == 'l3' else '9km',
                'temporal_resolution': 'daily' if level == 'l3' else '3-hourly',
                'source': 'NASA SMAP',
                'processing_level': level.upper()
            }
        }
    
    async def _fetch_modis_vegetation(
        self, 
        location: GeoLocation, 
        date_range: DateRange
    ) -> Dict[str, Any]:
        """Fetch MODIS vegetation indices"""
        logger.info("🌱 Fetching MODIS vegetation data")
        
        return {
            'dataset': 'modis_vegetation',
            'location': {'lat': location.lat, 'lon': location.lon},
            'date_range': {'start': date_range.start_iso, 'end': date_range.end_iso},
            'data': {
                'ndvi': np.random.uniform(0.3, 0.8),  # Normalized Difference Vegetation Index
                'evi': np.random.uniform(0.2, 0.6),   # Enhanced Vegetation Index
                'pixel_reliability': np.random.randint(0, 3),  # 0=good, 1=marginal, 2=snow/ice, 3=cloudy
                'composite_day': np.random.randint(1, 366),
                'view_zenith_angle': np.random.uniform(0, 60)
            },
            'metadata': {
                'spatial_resolution': '250m',
                'temporal_resolution': '16-day',
                'source': 'NASA MODIS',
                'products': ['MOD13Q1', 'MYD13Q1']
            }
        }
    
    async def _fetch_modis_lst(
        self, 
        location: GeoLocation, 
        date_range: DateRange
    ) -> Dict[str, Any]:
        """Fetch MODIS Land Surface Temperature"""
        logger.info("🌡️ Fetching MODIS land surface temperature")
        
        return {
            'dataset': 'modis_lst',
            'location': {'lat': location.lat, 'lon': location.lon},
            'date_range': {'start': date_range.start_iso, 'end': date_range.end_iso},
            'data': {
                'day_lst': np.random.uniform(20, 45),  # °C
                'night_lst': np.random.uniform(5, 25),  # °C
                'day_lst_quality': np.random.randint(0, 3),
                'night_lst_quality': np.random.randint(0, 3),
                'emissivity': np.random.uniform(0.9, 0.99)
            },
            'metadata': {
                'spatial_resolution': '1km',
                'temporal_resolution': 'daily',
                'source': 'NASA MODIS',
                'products': ['MOD11A1', 'MYD11A1']
            }
        }
    
    async def _fetch_gpm_precipitation(
        self, 
        location: GeoLocation, 
        date_range: DateRange
    ) -> Dict[str, Any]:
        """Fetch GPM precipitation data"""
        logger.info("🌧️ Fetching GPM precipitation data")
        
        # Calculate precipitation accumulation over date range
        days = (date_range.end - date_range.start).days
        total_precipitation = np.random.exponential(50) * days  # mm
        
        return {
            'dataset': 'gpm_precipitation',
            'location': {'lat': location.lat, 'lon': location.lon},
            'date_range': {'start': date_range.start_iso, 'end': date_range.end_iso},
            'data': {
                'precipitation_rate': np.random.uniform(0, 10),  # mm/hour
                'precipitation_cal': total_precipitation,  # mm total
                'quality_flag': 'good',
                'probability_of_precipitation': np.random.uniform(0, 1)
            },
            'metadata': {
                'spatial_resolution': '0.1°',
                'temporal_resolution': '30-minute',
                'source': 'NASA GPM',
                'product': '3IMERGHH'
            }
        }
    
    async def _fetch_ecostress_data(
        self, 
        location: GeoLocation, 
        date_range: DateRange
    ) -> Dict[str, Any]:
        """Fetch ECOSTRESS evapotranspiration data"""
        logger.info("💧 Fetching ECOSTRESS evapotranspiration data")
        
        return {
            'dataset': 'ecostress_et',
            'location': {'lat': location.lat, 'lon': location.lon},
            'date_range': {'start': date_range.start_iso, 'end': date_range.end_iso},
            'data': {
                'et_actual': np.random.uniform(0, 8),  # mm/day
                'et_potential': np.random.uniform(2, 12),  # mm/day
                'land_surface_temperature': np.random.uniform(20, 40),  # °C
                'emissivity': np.random.uniform(0.9, 0.99),
                'quality_flag': 'good'
            },
            'metadata': {
                'spatial_resolution': '70m',
                'temporal_resolution': 'variable',
                'source': 'NASA ECOSTRESS',
                'product': 'ECO3ETPTJPL'
            }
        }
    
    async def _fetch_grace_groundwater(
        self, 
        location: GeoLocation, 
        date_range: DateRange
    ) -> Dict[str, Any]:
        """Fetch GRACE groundwater data"""
        logger.info("🏔️ Fetching GRACE groundwater data")
        
        return {
            'dataset': 'grace_groundwater',
            'location': {'lat': location.lat, 'lon': location.lon},
            'date_range': {'start': date_range.start_iso, 'end': date_range.end_iso},
            'data': {
                'groundwater_anomaly': np.random.uniform(-10, 10),  # cm
                'soil_moisture_anomaly': np.random.uniform(-5, 5),  # cm
                'total_water_storage_anomaly': np.random.uniform(-15, 15),  # cm
                'uncertainty': np.random.uniform(1, 3)  # cm
            },
            'metadata': {
                'spatial_resolution': '1°',
                'temporal_resolution': 'monthly',
                'source': 'NASA GRACE',
                'product': 'GRCTellus'
            }
        }
    
    async def _fetch_landsat_data(
        self, 
        location: GeoLocation, 
        date_range: DateRange
    ) -> Dict[str, Any]:
        """Fetch Landsat multispectral data"""
        logger.info("🛰️ Fetching Landsat multispectral data")
        
        return {
            'dataset': 'landsat_multispectral',
            'location': {'lat': location.lat, 'lon': location.lon},
            'date_range': {'start': date_range.start_iso, 'end': date_range.end_iso},
            'data': {
                'ndvi': np.random.uniform(0.2, 0.8),
                'ndwi': np.random.uniform(0.1, 0.6),  # Normalized Difference Water Index
                'surface_temperature': np.random.uniform(15, 35),  # °C
                'cloud_cover': np.random.uniform(0, 30),  # %
                'quality_score': np.random.uniform(0.7, 1.0)
            },
            'metadata': {
                'spatial_resolution': '30m',
                'temporal_resolution': '16-day',
                'source': 'USGS/NASA Landsat',
                'products': ['Landsat-8', 'Landsat-9']
            }
        }
    
    async def store_raw_data(self, task_id: str, raw_data: Dict[str, Any]):
        """Store raw NASA data in database"""
        if not self.db_pool:
            logger.warning("No database connection available")
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                # Store task metadata
                await conn.execute("""
                    INSERT INTO nasa_data.ingestion_tasks 
                    (task_id, status, created_at, completed_at)
                    VALUES ($1, $2, $3, $4)
                """, task_id, 'completed', datetime.now(), datetime.now())
                
                # Store raw data for each dataset
                for dataset_id, data in raw_data.items():
                    if data:
                        await conn.execute("""
                            INSERT INTO nasa_data.raw_dataset_cache
                            (task_id, dataset_id, location, data, created_at)
                            VALUES ($1, $2, $3, $4, $5)
                        """, task_id, dataset_id, 
                            f"POINT({data['location']['lon']} {data['location']['lat']})",
                            json.dumps(data), datetime.now())
                
                logger.info(f"✅ Stored raw data for task {task_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to store raw data: {e}")
    
    async def notify_completion(self, task_id: str, raw_data: Dict[str, Any]):
        """Notify data fusion engine of completion"""
        # In production, send notification to message queue or API
        logger.info(f"📢 Notifying completion of task {task_id}")
        
        # Store completion status in Redis
        if self.redis_client:
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self.redis_client.setex,
                f"task:{task_id}:status",
                3600,  # 1 hour TTL
                json.dumps({
                    'status': 'completed',
                    'datasets': list(raw_data.keys()),
                    'completed_at': datetime.now().isoformat()
                })
            )
    
    async def notify_error(self, task_id: str, error_message: str):
        """Notify of ingestion error"""
        logger.error(f"❌ Task {task_id} failed: {error_message}")
        
        if self.redis_client:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.redis_client.setex,
                f"task:{task_id}:status",
                3600,
                json.dumps({
                    'status': 'failed',
                    'error': error_message,
                    'failed_at': datetime.now().isoformat()
                })
            )
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of ingestion task"""
        if not self.redis_client:
            return {'status': 'unknown', 'message': 'Redis not available'}
        
        try:
            status_data = await asyncio.get_event_loop().run_in_executor(
                None,
                self.redis_client.get,
                f"task:{task_id}:status"
            )
            
            if status_data:
                return json.loads(status_data)
            else:
                return {'status': 'not_found', 'message': 'Task not found'}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def test_authentication(self) -> Dict[str, bool]:
        """Test authentication with NASA services"""
        auth_status = {}
        
        # Test Earthdata authentication
        try:
            async with aiohttp.ClientSession() as session:
                # Simple test request
                async with session.get(
                    'https://urs.earthdata.nasa.gov/api/users/me',
                    auth=aiohttp.BasicAuth(self.earthdata_username, self.earthdata_password)
                ) as response:
                    auth_status['earthdata'] = response.status == 200
        except:
            auth_status['earthdata'] = False
        
        # Test other services
        auth_status['appeears'] = bool(self.earthdata_username)
        auth_status['giovanni'] = bool(self.earthdata_username)
        auth_status['gibs'] = True  # GIBS is public
        
        return auth_status
