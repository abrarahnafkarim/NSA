import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
import json
import os
import httpx
from dataclasses import dataclass

from models import USMI, AWLI, PAOI, GeoLocation, DateRange, CropRecommendation, MetricsHistory

logger = logging.getLogger(__name__)

@dataclass
class CropData:
    """Crop-specific data and requirements"""
    name: str
    water_requirements: Dict[str, float]  # mm/day by growth stage
    optimal_temperature: Tuple[float, float]  # min, max in Celsius
    soil_moisture_optimal: Tuple[float, float]  # min, max
    pest_susceptibility: Dict[str, float]  # pest -> susceptibility score
    phenology_stages: Dict[str, int]  # stage -> days from planting

class AgriculturalDataFusionEngine:
    """
    Advanced fusion engine that combines multiple NASA datasets
    into actionable agricultural metrics
    """
    
    def __init__(self):
        self.nasa_ingest_url = os.getenv('NASA_DATA_INGEST_URL', 'http://nasa-data-ingest:8000')
        self.db_pool = None
        self.redis_client = None
        
        # Initialize crop databases
        self.crop_databases = self._initialize_crop_databases()
        
        # Historical data for anomaly detection
        self.climatology_data = {}
        
    async def initialize(self):
        """Initialize the fusion engine"""
        logger.info("🧠 Initializing Agricultural Data Fusion Engine...")
        
        # In production, initialize database and Redis connections
        # For now, we'll use mock data
        
        logger.info("✅ Fusion engine initialized")
    
    def _initialize_crop_databases(self) -> Dict[str, CropData]:
        """Initialize crop-specific databases"""
        return {
            "corn": CropData(
                name="Corn",
                water_requirements={"germination": 5, "vegetative": 8, "reproductive": 12, "maturity": 6},
                optimal_temperature=(18, 27),
                soil_moisture_optimal=(0.3, 0.6),
                pest_susceptibility={"corn_borer": 0.8, "aphids": 0.6, "rust": 0.4},
                phenology_stages={"emergence": 10, "vegetative": 45, "reproductive": 85, "maturity": 120}
            ),
            "wheat": CropData(
                name="Wheat",
                water_requirements={"germination": 3, "vegetative": 6, "reproductive": 8, "maturity": 4},
                optimal_temperature=(15, 25),
                soil_moisture_optimal=(0.25, 0.5),
                pest_susceptibility={"rust": 0.7, "aphids": 0.5, "weevils": 0.6},
                phenology_stages={"emergence": 7, "vegetative": 60, "reproductive": 120, "maturity": 150}
            ),
            "soybean": CropData(
                name="Soybean",
                water_requirements={"germination": 4, "vegetative": 7, "reproductive": 10, "maturity": 5},
                optimal_temperature=(20, 30),
                soil_moisture_optimal=(0.3, 0.55),
                pest_susceptibility={"aphids": 0.7, "caterpillars": 0.6, "rust": 0.5},
                phenology_stages={"emergence": 8, "vegetative": 35, "reproductive": 75, "maturity": 110}
            ),
            "rice": CropData(
                name="Rice",
                water_requirements={"germination": 8, "vegetative": 12, "reproductive": 15, "maturity": 8},
                optimal_temperature=(25, 35),
                soil_moisture_optimal=(0.4, 0.7),
                pest_susceptibility={"brown_plant_hopper": 0.8, "rice_blast": 0.7, "stem_borer": 0.6},
                phenology_stages={"emergence": 12, "vegetative": 50, "reproductive": 90, "maturity": 130}
            )
        }
    
    async def fetch_raw_data(
        self, 
        location: GeoLocation, 
        date_range: DateRange, 
        datasets: List[str]
    ) -> Dict[str, Any]:
        """Fetch raw NASA data from ingestion service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.nasa_ingest_url}/api/v1/nasa/ingest",
                    json={
                        "location": location.dict(),
                        "date_range": date_range.dict(),
                        "datasets": datasets
                    }
                )
                
                if response.status_code == 200:
                    task_response = response.json()
                    task_id = task_response["task_id"]
                    
                    # Wait for completion (in production, use async polling)
                    await asyncio.sleep(2)  # Simulate processing time
                    
                    # Fetch results
                    status_response = await client.get(
                        f"{self.nasa_ingest_url}/api/v1/nasa/status/{task_id}"
                    )
                    
                    if status_response.status_code == 200:
                        # Return mock data for now
                        return self._generate_mock_nasa_data(location, date_range, datasets)
                    else:
                        raise Exception("Failed to get ingestion status")
                else:
                    raise Exception(f"Ingestion failed: {response.status_code}")
                    
        except Exception as e:
            logger.warning(f"Failed to fetch from NASA service, using mock data: {e}")
            return self._generate_mock_nasa_data(location, date_range, datasets)
    
    def _generate_mock_nasa_data(
        self, 
        location: GeoLocation, 
        date_range: DateRange, 
        datasets: List[str]
    ) -> Dict[str, Any]:
        """Generate realistic mock NASA data"""
        mock_data = {}
        
        for dataset in datasets:
            if dataset == 'smap_l3':
                mock_data[dataset] = {
                    'surface_moisture': np.random.uniform(0.1, 0.4),
                    'quality_flag': 'good',
                    'uncertainty': np.random.uniform(0.05, 0.15)
                }
            elif dataset == 'smap_l4':
                mock_data[dataset] = {
                    'root_zone_moisture': np.random.uniform(0.15, 0.35),
                    'surface_moisture': np.random.uniform(0.12, 0.38),
                    'quality_flag': 'good'
                }
            elif dataset == 'modis_vegetation':
                mock_data[dataset] = {
                    'ndvi': np.random.uniform(0.3, 0.8),
                    'evi': np.random.uniform(0.2, 0.6),
                    'pixel_reliability': np.random.randint(0, 3)
                }
            elif dataset == 'modis_lst':
                mock_data[dataset] = {
                    'day_lst': np.random.uniform(20, 45),
                    'night_lst': np.random.uniform(5, 25),
                    'quality_flag': 'good'
                }
            elif dataset == 'gpm':
                mock_data[dataset] = {
                    'precipitation_rate': np.random.uniform(0, 10),
                    'precipitation_cal': np.random.uniform(0, 50),
                    'quality_flag': 'good'
                }
            elif dataset == 'ecostress':
                mock_data[dataset] = {
                    'et_actual': np.random.uniform(0, 8),
                    'et_potential': np.random.uniform(2, 12),
                    'land_surface_temperature': np.random.uniform(20, 40)
                }
            elif dataset == 'grace':
                mock_data[dataset] = {
                    'groundwater_anomaly': np.random.uniform(-10, 10),
                    'soil_moisture_anomaly': np.random.uniform(-5, 5),
                    'uncertainty': np.random.uniform(1, 3)
                }
            elif dataset == 'landsat':
                mock_data[dataset] = {
                    'ndvi': np.random.uniform(0.2, 0.8),
                    'ndwi': np.random.uniform(0.1, 0.6),
                    'surface_temperature': np.random.uniform(15, 35),
                    'cloud_cover': np.random.uniform(0, 30)
                }
        
        return mock_data
    
    async def compute_unified_soil_moisture_index(self, raw_data: Dict[str, Any]) -> USMI:
        """
        Compute Unified Soil Moisture Index from multiple data sources
        """
        logger.info("🌍 Computing Unified Soil Moisture Index (USMI)")
        
        # Extract and process individual components
        smap_surface = self._process_smap_surface(raw_data.get('smap_l3', {}))
        smap_root = self._process_smap_root_zone(raw_data.get('smap_l4', {}))
        precipitation = self._process_gpm_precipitation(raw_data.get('gpm', {}))
        temperature = self._process_modis_lst(raw_data.get('modis_lst', {}))
        et_data = self._process_ecostress_et(raw_data.get('ecostress', {}))
        
        # Apply spatiotemporal normalization
        normalized_components = {
            'surface_moisture': self._spatial_normalize(smap_surface, 'soil_moisture'),
            'root_zone_moisture': self._spatial_normalize(smap_root, 'soil_moisture'),
            'precipitation_factor': self._temporal_normalize(precipitation, 'precipitation', days=7),
            'temperature_stress': self._calculate_temperature_stress(temperature),
            'et_deficit': self._calculate_et_deficit(et_data, precipitation)
        }
        
        # Quality assessment and uncertainty quantification
        quality_weights = self._assess_data_quality(raw_data)
        
        # Fusion calculation with uncertainty propagation
        usmi_value = (
            normalized_components['surface_moisture'] * 0.35 * quality_weights.get('smap_l3', 1.0) +
            normalized_components['root_zone_moisture'] * 0.25 * quality_weights.get('smap_l4', 1.0) +
            normalized_components['precipitation_factor'] * 0.20 * quality_weights.get('gpm', 1.0) +
            normalized_components['temperature_stress'] * 0.15 * quality_weights.get('modis_lst', 1.0) +
            normalized_components['et_deficit'] * 0.05 * quality_weights.get('ecostress', 1.0)
        )
        
        # Calculate confidence interval
        uncertainty = self._propagate_uncertainty(normalized_components, quality_weights)
        confidence = max(0.0, 1.0 - uncertainty)
        
        # Generate recommendations
        recommendations = self._generate_usmi_recommendations(usmi_value, normalized_components)
        
        return USMI(
            value=usmi_value,
            confidence=confidence,
            components=normalized_components,
            quality_flags=self._generate_quality_flags(raw_data),
            recommendations=recommendations
        )
    
    async def compute_agricultural_water_level_indicator(
        self, 
        raw_data: Dict[str, Any], 
        crop_type: str
    ) -> AWLI:
        """
        Compute Agricultural Water Level Indicator
        """
        logger.info(f"💧 Computing Agricultural Water Level Indicator (AWLI) for {crop_type}")
        
        # Process groundwater data
        grace_data = self._process_grace_groundwater(raw_data.get('grace', {}))
        gldas_data = self._process_gldas_soil_moisture(raw_data.get('smap_l4', {}))
        
        # Process vegetation stress indicators
        ndvi_data = self._process_vegetation_indices(raw_data.get('modis_vegetation', {}))
        water_stress_index = self._calculate_vegetation_water_stress(ndvi_data, raw_data.get('modis_lst', {}))
        
        # Process precipitation anomalies
        precipitation_anomaly = self._calculate_precipitation_anomaly(
            raw_data.get('gpm', {}), 
            self._get_precipitation_climatology()
        )
        
        # Process evapotranspiration
        actual_et = raw_data.get('ecostress', {}).get('et_actual', 5.0)
        potential_et = self._calculate_potential_et(raw_data.get('modis_lst', {}), raw_data.get('gpm', {}))
        et_ratio = self._safe_divide(actual_et, potential_et)
        
        # Surface water analysis from Landsat
        surface_water = self._analyze_surface_water(raw_data.get('landsat', {}))
        
        # Crop-specific water requirements
        crop_data = self.crop_databases.get(crop_type.lower(), self.crop_databases['corn'])
        crop_water_needs = self._get_crop_water_requirements(crop_data, ndvi_data.get('phenology_stage', 'vegetative'))
        
        # Crop-specific weighting
        crop_weights = self._get_crop_water_weights(crop_type)
        
        awli_components = {
            'groundwater_anomaly': self._normalize_groundwater_anomaly(grace_data, gldas_data),
            'precipitation_anomaly': precipitation_anomaly,
            'vegetation_water_stress': water_stress_index,
            'et_ratio': et_ratio,
            'surface_water_availability': surface_water
        }
        
        awli_value = sum(
            awli_components[key] * crop_weights.get(key, 1.0) 
            for key in awli_components.keys()
        )
        
        # Determine water requirement status
        water_requirement_status = self._assess_water_requirement_status(awli_value, crop_water_needs)
        
        # Generate irrigation recommendations
        irrigation_recommendations = self._generate_irrigation_recommendations(awli_value, crop_type)
        
        return AWLI(
            value=awli_value,
            crop_type=crop_type,
            water_requirement_status=water_requirement_status,
            components=awli_components,
            irrigation_recommendations=irrigation_recommendations
        )
    
    async def compute_pesticide_application_optimization_index(
        self, 
        raw_data: Dict[str, Any], 
        crop_type: str, 
        target_pest: str
    ) -> PAOI:
        """
        Compute Pesticide Application Optimization Index
        """
        logger.info(f"🌿 Computing Pesticide Application Optimization Index (PAOI) for {crop_type} vs {target_pest}")
        
        # Vegetation stress analysis
        vegetation_data = raw_data.get('modis_vegetation', {})
        vegetation_stress = self._detect_vegetation_anomalies(vegetation_data)
        
        # Pest favorable conditions modeling
        temperature_data = raw_data.get('modis_lst', {})
        humidity_proxy = self._calculate_humidity_proxy(raw_data.get('gpm', {}), temperature_data)
        pest_conditions = self._model_pest_favorable_conditions(
            temperature_data, humidity_proxy, target_pest
        )
        
        # Weather suitability for application
        wind_data = self._extract_wind_data(raw_data.get('gpm', {}))  # Mock wind data
        precipitation_forecast = self._get_precipitation_forecast(raw_data.get('gpm', {}))
        application_weather = self._assess_application_weather_suitability(
            wind_data, precipitation_forecast, temperature_data
        )
        
        # Crop phenology stage
        phenology_stage = self._determine_phenology_stage(vegetation_data, crop_type)
        phenology_score = self._get_pesticide_timing_score(phenology_stage, target_pest)
        
        # Spray drift risk
        aerosol_data = self._mock_aerosol_data()  # Mock aerosol data
        spray_drift_risk = self._calculate_spray_drift_risk(wind_data, aerosol_data)
        
        paoi_components = {
            'vegetation_stress': vegetation_stress,
            'pest_favorable_conditions': pest_conditions,
            'weather_suitability': application_weather,
            'phenology_timing': phenology_score,
            'spray_drift_risk': 1.0 - spray_drift_risk  # Invert for optimization
        }
        
        # Weighted fusion
        paoi_value = (
            paoi_components['vegetation_stress'] * 0.30 +
            paoi_components['pest_favorable_conditions'] * 0.25 +
            paoi_components['weather_suitability'] * 0.20 +
            paoi_components['phenology_timing'] * 0.15 +
            paoi_components['spray_drift_risk'] * 0.10
        )
        
        # Calculate application window
        application_window = self._calculate_optimal_application_window(paoi_components)
        
        # Assess environmental impact
        environmental_impact_score = self._assess_environmental_impact(paoi_components)
        
        # Generate recommendations
        recommendations = self._generate_pesticide_recommendations(paoi_value, paoi_components)
        
        return PAOI(
            value=paoi_value,
            crop_type=crop_type,
            target_pest=target_pest,
            application_window=application_window,
            components=paoi_components,
            environmental_impact_score=environmental_impact_score,
            recommendations=recommendations
        )
    
    # Helper methods for data processing
    def _process_smap_surface(self, data: Dict[str, Any]) -> float:
        """Process SMAP surface moisture data"""
        return data.get('surface_moisture', 0.25)
    
    def _process_smap_root_zone(self, data: Dict[str, Any]) -> float:
        """Process SMAP root zone moisture data"""
        return data.get('root_zone_moisture', 0.30)
    
    def _process_gpm_precipitation(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Process GPM precipitation data"""
        return {
            'rate': data.get('precipitation_rate', 2.0),
            'total': data.get('precipitation_cal', 20.0),
            'probability': data.get('probability_of_precipitation', 0.3)
        }
    
    def _process_modis_lst(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Process MODIS land surface temperature data"""
        return {
            'day': data.get('day_lst', 30.0),
            'night': data.get('night_lst', 15.0),
            'average': (data.get('day_lst', 30.0) + data.get('night_lst', 15.0)) / 2
        }
    
    def _process_ecostress_et(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Process ECOSTRESS evapotranspiration data"""
        return {
            'actual': data.get('et_actual', 5.0),
            'potential': data.get('et_potential', 8.0),
            'deficit': max(0, data.get('et_potential', 8.0) - data.get('et_actual', 5.0))
        }
    
    def _spatial_normalize(self, value: float, data_type: str) -> float:
        """Spatial normalization based on data type"""
        normalization_ranges = {
            'soil_moisture': (0.0, 0.5),
            'precipitation': (0.0, 50.0),
            'temperature': (0.0, 50.0)
        }
        
        min_val, max_val = normalization_ranges.get(data_type, (0.0, 1.0))
        return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
    
    def _temporal_normalize(self, data: Dict[str, float], data_type: str, days: int = 7) -> float:
        """Temporal normalization"""
        if data_type == 'precipitation':
            total = data.get('total', 0.0)
            optimal = days * 5.0  # 5mm/day optimal
            return max(0.0, min(1.0, total / optimal))
        return 0.5  # Default
    
    def _calculate_temperature_stress(self, temperature: Dict[str, float]) -> float:
        """Calculate temperature stress factor"""
        avg_temp = temperature.get('average', 25.0)
        # Optimal temperature range: 20-30°C
        if 20 <= avg_temp <= 30:
            return 1.0
        elif avg_temp < 20:
            return max(0.0, avg_temp / 20.0)
        else:
            return max(0.0, 1.0 - (avg_temp - 30) / 20.0)
    
    def _calculate_et_deficit(self, et_data: Dict[str, float], precipitation: Dict[str, float]) -> float:
        """Calculate evapotranspiration deficit"""
        et_deficit = et_data.get('deficit', 0.0)
        precipitation_total = precipitation.get('total', 0.0)
        
        if precipitation_total > 0:
            return max(0.0, min(1.0, et_deficit / precipitation_total))
        return 0.5
    
    def _assess_data_quality(self, raw_data: Dict[str, Any]) -> Dict[str, float]:
        """Assess data quality and return weights"""
        quality_weights = {}
        
        for dataset, data in raw_data.items():
            if isinstance(data, dict) and 'quality_flag' in data:
                quality_flag = data['quality_flag']
                if quality_flag == 'good':
                    quality_weights[dataset] = 1.0
                elif quality_flag == 'marginal':
                    quality_weights[dataset] = 0.7
                else:
                    quality_weights[dataset] = 0.4
            else:
                quality_weights[dataset] = 0.8  # Default weight
        
        return quality_weights
    
    def _propagate_uncertainty(self, components: Dict[str, float], weights: Dict[str, float]) -> float:
        """Propagate uncertainty through fusion calculation"""
        # Simplified uncertainty propagation
        uncertainties = []
        for key, weight in weights.items():
            uncertainty = 1.0 - weight
            uncertainties.append(uncertainty * 0.1)  # Scale uncertainty
        
        return min(0.5, sum(uncertainties))
    
    def _generate_usmi_recommendations(self, usmi_value: float, components: Dict[str, float]) -> List[str]:
        """Generate recommendations based on USMI"""
        recommendations = []
        
        if usmi_value < 0.3:
            recommendations.extend([
                "Critical soil moisture levels detected",
                "Immediate irrigation recommended",
                "Consider soil moisture monitoring system"
            ])
        elif usmi_value < 0.5:
            recommendations.extend([
                "Below optimal soil moisture",
                "Schedule irrigation within 2-3 days",
                "Monitor soil conditions closely"
            ])
        elif usmi_value > 0.8:
            recommendations.extend([
                "Excellent soil moisture conditions",
                "No irrigation needed",
                "Continue current management practices"
            ])
        else:
            recommendations.append("Soil moisture within acceptable range")
        
        return recommendations
    
    def _generate_quality_flags(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate quality flags for the data"""
        flags = {}
        
        for dataset, data in raw_data.items():
            if isinstance(data, dict):
                flags[dataset] = {
                    'quality_flag': data.get('quality_flag', 'unknown'),
                    'data_completeness': 1.0 if data else 0.0,
                    'temporal_coverage': 'complete'
                }
            else:
                flags[dataset] = {
                    'quality_flag': 'missing',
                    'data_completeness': 0.0,
                    'temporal_coverage': 'incomplete'
                }
        
        return flags
    
    # Additional helper methods for AWLI and PAOI
    def _process_grace_groundwater(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Process GRACE groundwater data"""
        return {
            'anomaly': data.get('groundwater_anomaly', 0.0),
            'uncertainty': data.get('uncertainty', 2.0)
        }
    
    def _process_gldas_soil_moisture(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Process GLDAS soil moisture data"""
        return {
            'surface': data.get('surface_moisture', 0.25),
            'root_zone': data.get('root_zone_moisture', 0.30)
        }
    
    def _process_vegetation_indices(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Process vegetation indices"""
        return {
            'ndvi': data.get('ndvi', 0.5),
            'evi': data.get('evi', 0.3),
            'phenology_stage': 'vegetative'  # Simplified
        }
    
    def _calculate_vegetation_water_stress(self, ndvi_data: Dict[str, float], lst_data: Dict[str, Any]) -> float:
        """Calculate vegetation water stress index"""
        ndvi = ndvi_data.get('ndvi', 0.5)
        lst = lst_data.get('average', 25.0)
        
        # Simplified water stress calculation
        if ndvi > 0.6 and lst < 30:
            return 1.0  # No stress
        elif ndvi < 0.4 or lst > 35:
            return 0.0  # High stress
        else:
            return (ndvi - 0.4) / 0.2  # Linear interpolation
    
    def _calculate_precipitation_anomaly(self, gpm_data: Dict[str, Any], climatology: Dict[str, float]) -> float:
        """Calculate precipitation anomaly"""
        current_precip = gpm_data.get('precipitation_cal', 20.0)
        historical_mean = climatology.get('mean', 25.0)
        
        if historical_mean > 0:
            anomaly = (current_precip - historical_mean) / historical_mean
            return max(0.0, min(1.0, (anomaly + 1.0) / 2.0))  # Normalize to 0-1
        return 0.5
    
    def _get_precipitation_climatology(self) -> Dict[str, float]:
        """Get precipitation climatology (mock)"""
        return {'mean': 25.0, 'std': 10.0}
    
    def _calculate_potential_et(self, lst_data: Dict[str, Any], gpm_data: Dict[str, Any]) -> float:
        """Calculate potential evapotranspiration"""
        temperature = lst_data.get('average', 25.0)
        # Simplified PET calculation based on temperature
        return max(0, temperature * 0.3)
    
    def _safe_divide(self, numerator: float, denominator: float) -> float:
        """Safe division with zero handling"""
        return numerator / denominator if denominator != 0 else 0.0
    
    def _analyze_surface_water(self, landsat_data: Dict[str, Any]) -> float:
        """Analyze surface water availability from Landsat"""
        ndwi = landsat_data.get('ndwi', 0.3)
        # NDWI > 0.3 indicates surface water
        return max(0.0, min(1.0, ndwi))
    
    def _get_crop_water_requirements(self, crop_data: CropData, stage: str) -> float:
        """Get crop water requirements for growth stage"""
        return crop_data.water_requirements.get(stage, 6.0)
    
    def _get_crop_water_weights(self, crop_type: str) -> Dict[str, float]:
        """Get crop-specific weights for AWLI components"""
        return {
            'groundwater_anomaly': 0.30,
            'precipitation_anomaly': 0.25,
            'vegetation_water_stress': 0.20,
            'et_ratio': 0.15,
            'surface_water_availability': 0.10
        }
    
    def _assess_water_requirement_status(self, awli_value: float, water_needs: float) -> str:
        """Assess water requirement status"""
        if awli_value >= 0.7:
            return "adequate"
        elif awli_value >= 0.4:
            return "moderate"
        else:
            return "critical"
    
    def _generate_irrigation_recommendations(self, awli_value: float, crop_type: str) -> List[str]:
        """Generate irrigation recommendations"""
        recommendations = []
        
        if awli_value < 0.3:
            recommendations.extend([
                "Immediate irrigation required",
                f"Apply 15-20mm water for {crop_type}",
                "Monitor soil moisture closely"
            ])
        elif awli_value < 0.5:
            recommendations.extend([
                "Irrigation recommended within 2 days",
                f"Apply 10-15mm water for {crop_type}",
                "Check weather forecast before irrigation"
            ])
        else:
            recommendations.append("Water levels adequate, continue monitoring")
        
        return recommendations
    
    # PAOI helper methods
    def _detect_vegetation_anomalies(self, vegetation_data: Dict[str, Any]) -> float:
        """Detect vegetation stress anomalies"""
        ndvi = vegetation_data.get('ndvi', 0.5)
        pixel_reliability = vegetation_data.get('pixel_reliability', 0)
        
        # High NDVI and good reliability = low stress
        if ndvi > 0.6 and pixel_reliability == 0:
            return 1.0
        elif ndvi < 0.4 or pixel_reliability > 1:
            return 0.0
        else:
            return ndvi  # Use NDVI as stress indicator
    
    def _calculate_humidity_proxy(self, gpm_data: Dict[str, Any], temperature_data: Dict[str, Any]) -> float:
        """Calculate humidity proxy from precipitation and temperature"""
        precip = gpm_data.get('precipitation_cal', 20.0)
        temp = temperature_data.get('average', 25.0)
        
        # Simplified humidity proxy
        return min(1.0, precip / (temp * 2))
    
    def _model_pest_favorable_conditions(self, temperature: Dict[str, Any], humidity: float, pest: str) -> float:
        """Model pest favorable conditions"""
        temp = temperature.get('average', 25.0)
        
        # Simplified pest model
        pest_optimal_temp = {'corn_borer': 25, 'aphids': 20, 'rust': 22}.get(pest, 25)
        
        # Temperature favorability
        temp_favorability = max(0.0, 1.0 - abs(temp - pest_optimal_temp) / 10.0)
        
        # Combine with humidity
        return (temp_favorability + humidity) / 2.0
    
    def _extract_wind_data(self, gpm_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract wind data (mock implementation)"""
        return {
            'speed': np.random.uniform(2, 8),  # m/s
            'direction': np.random.uniform(0, 360)  # degrees
        }
    
    def _get_precipitation_forecast(self, gpm_data: Dict[str, Any]) -> Dict[str, float]:
        """Get precipitation forecast (mock)"""
        return {
            'next_6h': gpm_data.get('precipitation_rate', 2.0) * 6,
            'next_24h': gpm_data.get('precipitation_cal', 20.0),
            'probability': gpm_data.get('probability_of_precipitation', 0.3)
        }
    
    def _assess_application_weather_suitability(self, wind: Dict[str, float], precip: Dict[str, float], temp: Dict[str, Any]) -> float:
        """Assess weather suitability for pesticide application"""
        wind_speed = wind.get('speed', 5.0)
        precip_prob = precip.get('probability', 0.3)
        temperature = temp.get('average', 25.0)
        
        # Optimal conditions: low wind, no rain, moderate temperature
        wind_score = max(0.0, 1.0 - wind_speed / 10.0)  # Lower wind is better
        precip_score = 1.0 - precip_prob  # Lower precipitation probability is better
        temp_score = 1.0 - abs(temperature - 25) / 15.0  # 25°C is optimal
        
        return (wind_score + precip_score + temp_score) / 3.0
    
    def _determine_phenology_stage(self, vegetation_data: Dict[str, Any], crop_type: str) -> str:
        """Determine crop phenology stage"""
        ndvi = vegetation_data.get('ndvi', 0.5)
        
        # Simplified phenology determination
        if ndvi < 0.3:
            return "emergence"
        elif ndvi < 0.6:
            return "vegetative"
        elif ndvi < 0.8:
            return "reproductive"
        else:
            return "maturity"
    
    def _get_pesticide_timing_score(self, stage: str, pest: str) -> float:
        """Get pesticide timing score based on phenology and pest"""
        # Optimal timing varies by pest and crop stage
        timing_scores = {
            ('vegetative', 'corn_borer'): 0.9,
            ('reproductive', 'corn_borer'): 0.7,
            ('vegetative', 'aphids'): 0.8,
            ('reproductive', 'aphids'): 0.6,
            ('vegetative', 'rust'): 0.5,
            ('reproductive', 'rust'): 0.9
        }
        
        return timing_scores.get((stage, pest), 0.6)
    
    def _mock_aerosol_data(self) -> Dict[str, float]:
        """Mock aerosol optical depth data"""
        return {
            'aod_550': np.random.uniform(0.1, 0.5),
            'aod_865': np.random.uniform(0.05, 0.3)
        }
    
    def _calculate_spray_drift_risk(self, wind: Dict[str, float], aerosol: Dict[str, float]) -> float:
        """Calculate spray drift risk"""
        wind_speed = wind.get('speed', 5.0)
        aod = aerosol.get('aod_550', 0.3)
        
        # Higher wind speed and aerosol load increase drift risk
        wind_risk = min(1.0, wind_speed / 8.0)  # 8 m/s is high risk
        aerosol_risk = min(1.0, aod / 0.4)  # 0.4 AOD is high risk
        
        return (wind_risk + aerosol_risk) / 2.0
    
    def _calculate_optimal_application_window(self, components: Dict[str, float]) -> Dict[str, Any]:
        """Calculate optimal application window"""
        # Simplified window calculation
        base_score = np.mean(list(components.values()))
        
        return {
            'optimal_hours': max(0, int(24 * base_score)),
            'next_optimal_time': '06:00-10:00',
            'avoid_times': '14:00-18:00',
            'confidence': base_score
        }
    
    def _assess_environmental_impact(self, components: Dict[str, float]) -> float:
        """Assess environmental impact score"""
        # Lower score means higher environmental impact
        weather_suitability = components.get('weather_suitability', 0.5)
        spray_drift_risk = 1.0 - components.get('spray_drift_risk', 0.5)  # Invert risk
        
        return (weather_suitability + spray_drift_risk) / 2.0
    
    def _generate_pesticide_recommendations(self, paoi_value: float, components: Dict[str, float]) -> List[str]:
        """Generate pesticide application recommendations"""
        recommendations = []
        
        if paoi_value > 0.7:
            recommendations.extend([
                "Optimal conditions for pesticide application",
                "Proceed with planned application",
                "Monitor weather conditions during application"
            ])
        elif paoi_value > 0.4:
            recommendations.extend([
                "Moderate conditions for application",
                "Consider waiting for better conditions",
                "Use targeted application methods"
            ])
        else:
            recommendations.extend([
                "Poor conditions for pesticide application",
                "Postpone application until conditions improve",
                "Consider alternative pest management strategies"
            ])
        
        return recommendations
    
    # Additional methods for the API
    async def generate_integrated_recommendations(self, usmi: USMI, awli: AWLI, paoi: PAOI, request) -> List[str]:
        """Generate integrated recommendations across all metrics"""
        recommendations = []
        
        # Combine recommendations from all metrics
        recommendations.extend(usmi.recommendations)
        recommendations.extend(awli.irrigation_recommendations)
        recommendations.extend(paoi.recommendations)
        
        # Add integrated insights
        if usmi.value < 0.4 and awli.value < 0.4:
            recommendations.append("CRITICAL: Both soil moisture and water levels are low - immediate action required")
        elif paoi.value > 0.7 and usmi.value > 0.6:
            recommendations.append("Optimal conditions for integrated crop management")
        
        return list(set(recommendations))  # Remove duplicates
    
    async def generate_alerts(self, usmi: USMI, awli: AWLI, paoi: PAOI) -> List[str]:
        """Generate critical alerts"""
        alerts = []
        
        if usmi.value < 0.2:
            alerts.append("CRITICAL: Extremely low soil moisture detected")
        if awli.value < 0.2:
            alerts.append("CRITICAL: Critical water shortage detected")
        if paoi.value < 0.3:
            alerts.append("WARNING: Poor conditions for pest management")
        
        return alerts
    
    async def store_fusion_results(self, location: GeoLocation, response):
        """Store fusion results in database"""
        # In production, store in database
        logger.info(f"💾 Storing fusion results for location: {location.lat}, {location.lon}")
    
    async def get_metrics_history(self, location: GeoLocation, date_range: DateRange, crop_type: Optional[str]) -> List[MetricsHistory]:
        """Get historical metrics"""
        # Mock historical data
        history = []
        current_date = date_range.start
        
        while current_date <= date_range.end:
            history.append(MetricsHistory(
                date=current_date,
                usmi=np.random.uniform(0.3, 0.8),
                awli=np.random.uniform(0.4, 0.9),
                paoi=np.random.uniform(0.5, 0.9),
                weather_summary={
                    'temperature': np.random.uniform(15, 35),
                    'precipitation': np.random.uniform(0, 20),
                    'humidity': np.random.uniform(40, 90)
                }
            ))
            current_date += timedelta(days=1)
        
        return history
    
    async def get_crop_recommendations(self, location: GeoLocation) -> List[CropRecommendation]:
        """Get crop recommendations for location"""
        # Mock crop recommendations based on location
        recommendations = []
        
        # Simple location-based recommendations
        if location.lat > 40:  # Northern hemisphere
            recommendations.append(CropRecommendation(
                crop_name="Corn",
                suitability_score=0.85,
                planting_window={"start": "April 15", "end": "May 15"},
                water_requirements={"total": 500, "peak_demand": "July-August"},
                expected_yield={"low": 8, "medium": 12, "high": 16},
                challenges=["Late spring frosts", "Summer drought risk"]
            ))
            
            recommendations.append(CropRecommendation(
                crop_name="Wheat",
                suitability_score=0.78,
                planting_window={"start": "September 1", "end": "October 15"},
                water_requirements={"total": 400, "peak_demand": "March-May"},
                expected_yield={"low": 4, "medium": 6, "high": 8},
                challenges=["Winter kill risk", "Spring moisture stress"]
            ))
        
        return recommendations
