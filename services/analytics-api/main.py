from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv
import httpx
import jwt
from jwt.exceptions import InvalidTokenError

from models import (
    FarmAnalysisRequest,
    MetricsResponse,
    RealtimeMonitoringRequest,
    GameScenarioRequest,
    GameActionRequest,
    GameScenarioResponse,
    GameActionResponse,
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
    title="NASA Agricultural Intelligence API",
    description="Comprehensive API for NASA agricultural intelligence metrics and game integration",
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

# Security
security = HTTPBearer()
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key')

# Service URLs
FUSION_SERVICE_URL = os.getenv('FUSION_SERVICE_URL', 'http://data-fusion-engine:8000')
AR_SERVICE_URL = os.getenv('AR_SERVICE_URL', 'http://ar-service:8000')

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, farm_id: str):
        await websocket.accept()
        self.active_connections[farm_id] = websocket
        logger.info(f"WebSocket connected for farm: {farm_id}")
    
    def disconnect(self, farm_id: str):
        if farm_id in self.active_connections:
            del self.active_connections[farm_id]
            logger.info(f"WebSocket disconnected for farm: {farm_id}")
    
    async def send_personal_message(self, message: str, farm_id: str):
        if farm_id in self.active_connections:
            websocket = self.active_connections[farm_id]
            await websocket.send_text(message)

manager = ConnectionManager()

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": user_id, "username": payload.get("username")}
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Optional authentication for public endpoints
async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 NASA Agricultural Intelligence API started successfully")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "analytics-api",
        "version": "2.0.0"
    }

@app.post("/api/v1/agriculture/unified-analysis", response_model=MetricsResponse)
async def unified_agricultural_analysis(
    request: FarmAnalysisRequest, 
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Comprehensive agricultural analysis returning all three unified metrics
    """
    try:
        logger.info(f"🧮 Starting unified analysis for farm: {request.location.name}")
        
        # Parse and validate request
        location = GeoLocation(**request.location)
        date_range = DateRange(**request.date_range)
        
        # Initialize data fusion engine
        fusion_request = {
            "location": location.dict(),
            "date_range": date_range.dict(),
            "crop_type": request.farm_details.get("crop_type", "corn"),
            "target_pest": request.farm_details.get("target_pest", "general"),
            "datasets": [
                'smap_l3', 'smap_l4', 'modis_vegetation', 'modis_lst',
                'gpm', 'ecostress', 'grace', 'landsat'
            ]
        }
        
        # Call fusion engine
        async with httpx.AsyncClient() as client:
            fusion_response = await client.post(
                f"{FUSION_SERVICE_URL}/api/v1/fusion/compute-unified-metrics",
                json=fusion_request,
                timeout=60.0
            )
            
            if fusion_response.status_code != 200:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Fusion engine error: {fusion_response.text}"
                )
            
            fusion_data = fusion_response.json()
        
        # Prepare metrics response
        metrics = {
            "soil_moisture": {
                "value": fusion_data["usmi"]["value"],
                "category": fusion_data["usmi"]["get_category"]() if hasattr(fusion_data["usmi"], "get_category") else "unknown",
                "components": fusion_data["usmi"]["components"],
                "quality_flags": fusion_data["usmi"]["quality_flags"]
            },
            "water_level": {
                "value": fusion_data["awli"]["value"],
                "water_requirement_status": fusion_data["awli"]["water_requirement_status"],
                "components": fusion_data["awli"]["components"],
                "irrigation_need": fusion_data["awli"]["get_irrigation_need"]() if hasattr(fusion_data["awli"], "get_irrigation_need") else "unknown"
            },
            "pesticide_optimization": {
                "value": fusion_data["paoi"]["value"],
                "application_window": fusion_data["paoi"]["application_window"],
                "components": fusion_data["paoi"]["components"],
                "environmental_impact": fusion_data["paoi"]["environmental_impact_score"]
            }
        }
        
        confidence_scores = fusion_data["confidence_scores"]
        recommendations = fusion_data["recommendations"]
        alerts = fusion_data["alerts"]
        
        # Schedule background tasks for caching and logging
        background_tasks.add_task(
            cache_analysis_results, 
            location, date_range, metrics, confidence_scores, current_user["user_id"]
        )
        background_tasks.add_task(
            log_api_usage, 
            request, metrics, confidence_scores, current_user["user_id"]
        )
        
        return MetricsResponse(
            timestamp=datetime.now(),
            location=request.location,
            metrics=metrics,
            confidence_scores=confidence_scores,
            recommendations=recommendations,
            alerts=alerts
        )
        
    except Exception as e:
        logger.error(f"❌ Unified analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/api/v1/agriculture/realtime-monitoring")
async def realtime_monitoring(
    lat: float, 
    lon: float, 
    crop_type: Optional[str] = None,
    refresh_interval: Optional[int] = 3600,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Real-time monitoring endpoint for continuous farm monitoring
    """
    location = GeoLocation(lat=lat, lon=lon)
    
    try:
        # Call fusion engine for quick metrics
        fusion_request = {
            "location": location.dict(),
            "date_range": {
                "start": (datetime.now() - timedelta(days=1)).isoformat(),
                "end": datetime.now().isoformat()
            },
            "crop_type": crop_type or "corn",
            "datasets": ['smap_l3', 'modis_vegetation', 'gpm']  # Subset for real-time
        }
        
        async with httpx.AsyncClient() as client:
            fusion_response = await client.post(
                f"{FUSION_SERVICE_URL}/api/v1/fusion/compute-unified-metrics",
                json=fusion_request,
                timeout=30.0
            )
            
            if fusion_response.status_code == 200:
                fusion_data = fusion_response.json()
                
                # Prepare quick metrics
                quick_metrics = {
                    "soil_moisture": {
                        "value": fusion_data["usmi"]["value"],
                        "status": "normal" if fusion_data["usmi"]["value"] > 0.4 else "attention_needed"
                    },
                    "water_level": {
                        "value": fusion_data["awli"]["value"],
                        "status": "normal" if fusion_data["awli"]["value"] > 0.5 else "attention_needed"
                    },
                    "pesticide_optimization": {
                        "value": fusion_data["paoi"]["value"],
                        "status": "optimal" if fusion_data["paoi"]["value"] > 0.6 else "suboptimal"
                    }
                }
                
                monitoring_data = {
                    "timestamp": datetime.now().isoformat(),
                    "location": {"lat": lat, "lon": lon},
                    "quick_metrics": quick_metrics,
                    "status": "healthy" if all(m["status"] in ["normal", "optimal"] for m in quick_metrics.values()) else "attention_needed",
                    "next_update": (datetime.now() + timedelta(seconds=refresh_interval)).isoformat()
                }
                
                return monitoring_data
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch real-time data")
                
    except Exception as e:
        logger.error(f"❌ Real-time monitoring failed: {e}")
        raise HTTPException(status_code=500, detail=f"Real-time monitoring failed: {str(e)}")

@app.websocket("/ws/farm-monitoring/{farm_id}")
async def websocket_farm_monitoring(websocket: WebSocket, farm_id: str):
    """
    WebSocket endpoint for real-time farm data streaming
    """
    await manager.connect(websocket, farm_id)
    
    try:
        while True:
            # Send periodic updates
            await asyncio.sleep(300)  # 5 minutes
            
            # Get latest metrics for this farm
            latest_metrics = await get_latest_farm_metrics(farm_id)
            
            if latest_metrics:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "metrics_update",
                        "farm_id": farm_id,
                        "timestamp": datetime.now().isoformat(),
                        "data": latest_metrics
                    }),
                    farm_id
                )
            
            # Check for alerts
            alerts = await check_farm_alerts(farm_id, latest_metrics)
            if alerts:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "alert",
                        "farm_id": farm_id,
                        "alerts": alerts
                    }),
                    farm_id
                )
                
    except WebSocketDisconnect:
        manager.disconnect(farm_id)
    except Exception as e:
        logger.error(f"WebSocket error for farm {farm_id}: {str(e)}")
        manager.disconnect(farm_id)

# Game Integration Endpoints
@app.post("/api/v1/game/scenario-data", response_model=GameScenarioResponse)
async def get_game_scenario_data(scenario_request: GameScenarioRequest):
    """
    Specialized endpoint for educational game integration
    """
    try:
        scenario_type = scenario_request.scenario_type
        difficulty_level = scenario_request.difficulty_level
        learning_objectives = scenario_request.learning_objectives
        
        # Generate scenario-appropriate data
        scenario_generator = GameScenarioGenerator()
        
        base_data = await scenario_generator.create_base_scenario(
            scenario_type, difficulty_level
        )
        
        # Apply educational modifications
        educational_data = await scenario_generator.apply_educational_modifications(
            base_data, learning_objectives
        )
        
        # Generate simplified metrics for game consumption
        game_metrics = {
            'soil_health_percentage': educational_data['usmi_simplified'] * 100,
            'water_availability_percentage': educational_data['awli_simplified'] * 100,
            'pesticide_efficiency_percentage': educational_data['paoi_simplified'] * 100,
            'overall_farm_score': educational_data['overall_score'],
            'challenge_factors': educational_data['active_challenges'],
            'available_actions': educational_data['player_actions'],
            'learning_hints': educational_data['contextual_hints']
        }
        
        return GameScenarioResponse(
            scenario_id=scenario_request.scenario_id,
            metrics=game_metrics,
            narrative_context=educational_data['narrative'],
            success_criteria=educational_data['success_criteria'],
            real_world_connection=educational_data['real_world_examples']
        )
        
    except Exception as e:
        logger.error(f"❌ Game scenario generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scenario generation failed: {str(e)}")

@app.post("/api/v1/game/action-impact", response_model=GameActionResponse)
async def calculate_action_impact(action_request: GameActionRequest):
    """
    Calculate the impact of player actions on farm metrics
    """
    try:
        current_state = action_request.current_farm_state
        player_action = action_request.action
        
        # Simulate action impact using real NASA data patterns
        impact_calculator = ActionImpactCalculator()
        
        updated_metrics = await impact_calculator.simulate_action_impact(
            current_state, player_action
        )
        
        # Generate educational feedback
        feedback = await impact_calculator.generate_educational_feedback(
            current_state, updated_metrics, player_action
        )
        
        return GameActionResponse(
            updated_metrics=updated_metrics,
            impact_explanation=feedback['explanation'],
            real_world_equivalent=feedback['real_world_example'],
            nasa_data_connection=feedback['nasa_data_context'],
            next_recommended_actions=feedback['recommendations']
        )
        
    except Exception as e:
        logger.error(f"❌ Action impact calculation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Action impact calculation failed: {str(e)}")

# AR Integration Endpoints
@app.get("/api/v1/ar/visualization-data")
async def get_ar_visualization_data(
    lat: float,
    lon: float,
    visualization_type: str = "comprehensive",
    current_user: dict = Depends(get_current_user)
):
    """
    Get AR visualization data for a specific location
    """
    try:
        location = GeoLocation(lat=lat, lon=lon)
        
        # Get comprehensive analysis
        analysis_request = {
            "location": location.dict(),
            "date_range": {
                "start": (datetime.now() - timedelta(days=7)).isoformat(),
                "end": datetime.now().isoformat()
            },
            "farm_details": {"crop_type": "corn"},
            "analysis_type": "comprehensive"
        }
        
        # Call fusion engine
        async with httpx.AsyncClient() as client:
            fusion_response = await client.post(
                f"{FUSION_SERVICE_URL}/api/v1/fusion/compute-unified-metrics",
                json=analysis_request,
                timeout=30.0
            )
            
            if fusion_response.status_code == 200:
                fusion_data = fusion_response.json()
                
                # Prepare AR visualization data
                ar_data = {
                    "soil_moisture_mesh": {
                        "type": "heatmap",
                        "data": fusion_data["usmi"]["components"],
                        "value": fusion_data["usmi"]["value"],
                        "confidence": fusion_data["usmi"]["confidence"]
                    },
                    "water_level_spheres": {
                        "type": "spheres",
                        "data": fusion_data["awli"]["components"],
                        "value": fusion_data["awli"]["value"],
                        "status": fusion_data["awli"]["water_requirement_status"]
                    },
                    "pesticide_zones": {
                        "type": "zones",
                        "data": fusion_data["paoi"]["components"],
                        "value": fusion_data["paoi"]["value"],
                        "application_window": fusion_data["paoi"]["application_window"]
                    },
                    "info_panels": [
                        {
                            "title": "Soil Moisture Index",
                            "value": fusion_data["usmi"]["value"],
                            "category": "soil_health",
                            "recommendations": fusion_data["usmi"]["recommendations"][:2]
                        },
                        {
                            "title": "Water Level Indicator", 
                            "value": fusion_data["awli"]["value"],
                            "category": "water_management",
                            "recommendations": fusion_data["awli"]["irrigation_recommendations"][:2]
                        },
                        {
                            "title": "Pesticide Optimization",
                            "value": fusion_data["paoi"]["value"],
                            "category": "pest_management",
                            "recommendations": fusion_data["paoi"]["recommendations"][:2]
                        }
                    ]
                }
                
                return ar_data
            else:
                raise HTTPException(status_code=500, detail="Failed to get fusion data for AR")
                
    except Exception as e:
        logger.error(f"❌ AR visualization data failed: {e}")
        raise HTTPException(status_code=500, detail=f"AR visualization failed: {str(e)}")

# Background task functions
async def cache_analysis_results(location: GeoLocation, date_range: DateRange, metrics: Dict, confidence_scores: Dict, user_id: str):
    """Cache analysis results for future reference"""
    try:
        # In production, cache in Redis or database
        logger.info(f"💾 Caching analysis results for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Failed to cache results: {e}")

async def log_api_usage(request: FarmAnalysisRequest, metrics: Dict, confidence_scores: Dict, user_id: str):
    """Log API usage for analytics"""
    try:
        # In production, log to database or analytics service
        logger.info(f"📊 Logging API usage for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Failed to log usage: {e}")

async def get_latest_farm_metrics(farm_id: str) -> Optional[Dict]:
    """Get latest metrics for a farm"""
    try:
        # In production, fetch from database
        return {
            "soil_moisture": 0.65,
            "water_level": 0.72,
            "pesticide_optimization": 0.58,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Failed to get latest metrics for farm {farm_id}: {e}")
        return None

async def check_farm_alerts(farm_id: str, metrics: Optional[Dict]) -> List[str]:
    """Check for farm alerts"""
    alerts = []
    
    if metrics:
        if metrics.get("soil_moisture", 1.0) < 0.3:
            alerts.append("CRITICAL: Soil moisture critically low")
        if metrics.get("water_level", 1.0) < 0.3:
            alerts.append("CRITICAL: Water level critically low")
        if metrics.get("pesticide_optimization", 1.0) < 0.3:
            alerts.append("WARNING: Poor pesticide application conditions")
    
    return alerts

# Game integration classes
class GameScenarioGenerator:
    """Generate educational game scenarios"""
    
    async def create_base_scenario(self, scenario_type: str, difficulty: str) -> Dict:
        """Create base scenario data"""
        scenarios = {
            "drought": {
                "usmi_simplified": 0.2,
                "awli_simplified": 0.15,
                "paoi_simplified": 0.8,
                "overall_score": 30,
                "active_challenges": ["water_shortage", "soil_drought", "crop_stress"],
                "player_actions": ["irrigation", "mulching", "crop_rotation", "drought_resistant_varieties"],
                "contextual_hints": ["Water conservation is critical", "Soil moisture monitoring essential"]
            },
            "optimal": {
                "usmi_simplified": 0.8,
                "awli_simplified": 0.85,
                "paoi_simplified": 0.7,
                "overall_score": 85,
                "active_challenges": [],
                "player_actions": ["maintenance", "monitoring", "optimization"],
                "contextual_hints": ["Maintain current practices", "Continue monitoring"]
            },
            "pest_outbreak": {
                "usmi_simplified": 0.6,
                "awli_simplified": 0.7,
                "paoi_simplified": 0.3,
                "overall_score": 55,
                "active_challenges": ["pest_infestation", "disease_risk"],
                "player_actions": ["targeted_spraying", "biological_control", "crop_rotation"],
                "contextual_hints": ["Timing is crucial for pest control", "Consider environmental impact"]
            }
        }
        
        return scenarios.get(scenario_type, scenarios["optimal"])
    
    async def apply_educational_modifications(self, base_data: Dict, learning_objectives: List[str]) -> Dict:
        """Apply educational modifications"""
        return {
            **base_data,
            "narrative": f"Your farm is facing {base_data.get('active_challenges', ['normal conditions'])[0] if base_data.get('active_challenges') else 'optimal conditions'}. Use NASA data to make informed decisions.",
            "success_criteria": ["Improve overall farm score to 80+", "Address all active challenges", "Maintain environmental sustainability"],
            "real_world_examples": ["NASA satellites help farmers worldwide", "Precision agriculture reduces resource waste", "Data-driven decisions improve yields"]
        }

class ActionImpactCalculator:
    """Calculate impact of player actions"""
    
    async def simulate_action_impact(self, current_state: Dict, action: Dict) -> Dict:
        """Simulate the impact of a player action"""
        action_type = action.get("type", "")
        action_amount = action.get("amount", 0)
        
        updated_metrics = current_state.copy()
        
        if action_type == "irrigation":
            # Irrigation improves soil moisture and water level
            updated_metrics["soil_health_percentage"] = min(100, updated_metrics.get("soil_health_percentage", 50) + action_amount)
            updated_metrics["water_availability_percentage"] = min(100, updated_metrics.get("water_availability_percentage", 50) + action_amount * 0.8)
        elif action_type == "pesticide_application":
            # Pesticide application improves pest control
            updated_metrics["pesticide_efficiency_percentage"] = min(100, updated_metrics.get("pesticide_efficiency_percentage", 50) + action_amount)
        elif action_type == "mulching":
            # Mulching conserves soil moisture
            updated_metrics["soil_health_percentage"] = min(100, updated_metrics.get("soil_health_percentage", 50) + action_amount * 0.5)
        
        # Recalculate overall score
        updated_metrics["overall_farm_score"] = (
            updated_metrics.get("soil_health_percentage", 0) +
            updated_metrics.get("water_availability_percentage", 0) +
            updated_metrics.get("pesticide_efficiency_percentage", 0)
        ) / 3
        
        return updated_metrics
    
    async def generate_educational_feedback(self, current_state: Dict, updated_metrics: Dict, action: Dict) -> Dict:
        """Generate educational feedback for the action"""
        action_type = action.get("type", "")
        
        feedback_map = {
            "irrigation": {
                "explanation": "Irrigation adds water to the soil, improving soil moisture and plant water availability. NASA satellites help monitor soil moisture levels globally.",
                "real_world_example": "Farmers in California use NASA soil moisture data to optimize irrigation timing, reducing water usage by 20% while maintaining crop yields.",
                "nasa_data_context": "SMAP satellite provides soil moisture data that helps farmers make irrigation decisions, reducing water waste and improving crop health."
            },
            "pesticide_application": {
                "explanation": "Strategic pesticide application helps control pests while minimizing environmental impact. Weather conditions affect application effectiveness.",
                "real_world_example": "Iowa corn farmers use NASA weather data to time pesticide applications, reducing spray drift and improving pest control effectiveness.",
                "nasa_data_context": "MODIS satellites provide vegetation health data that helps identify pest-infested areas, enabling targeted pesticide application."
            },
            "mulching": {
                "explanation": "Mulching helps retain soil moisture and regulate soil temperature, reducing water evaporation and improving soil health.",
                "real_world_example": "Organic farmers use mulching techniques combined with NASA climate data to improve soil moisture retention and reduce irrigation needs.",
                "nasa_data_context": "Landsat satellites monitor vegetation cover and soil conditions, helping farmers understand the benefits of mulching and ground cover."
            }
        }
        
        return feedback_map.get(action_type, {
            "explanation": "Your action has been applied to the farm. Continue monitoring the results and adjust your strategy as needed.",
            "real_world_example": "NASA data helps farmers worldwide make informed decisions about farm management practices.",
            "nasa_data_context": "Satellite data provides valuable insights for agricultural decision-making.",
            "recommendations": ["Monitor the results of your action", "Consider additional improvements", "Check weather forecasts for planning"]
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
