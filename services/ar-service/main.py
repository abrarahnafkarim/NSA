from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv
import httpx
import numpy as np

from models import ARVisualizationRequest, ARVisualizationResponse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AR Visualization Service",
    description="Service for generating AR visualization data for NASA agricultural intelligence",
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

# Service URLs
ANALYTICS_API_URL = os.getenv('ANALYTICS_API_URL', 'http://analytics-api:8000')

@app.on_event("startup")
async def startup_event():
    """Initialize AR service on startup"""
    logger.info("🥽 AR Visualization Service started successfully")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ar-visualization",
        "version": "2.0.0"
    }

@app.post("/api/v1/ar/visualization-data", response_model=ARVisualizationResponse)
async def get_ar_visualization_data(request: ARVisualizationRequest):
    """
    Generate comprehensive AR visualization data for agricultural metrics
    """
    try:
        logger.info(f"🥽 Generating AR visualization for location: {request.location}")
        
        # Get analysis data from analytics API
        async with httpx.AsyncClient() as client:
            analysis_response = await client.post(
                f"{ANALYTICS_API_URL}/api/v1/agriculture/unified-analysis",
                json={
                    "location": request.location,
                    "farm_details": request.farm_details,
                    "date_range": request.date_range,
                    "analysis_type": "comprehensive"
                },
                timeout=60.0
            )
            
            if analysis_response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get analysis data: {analysis_response.text}"
                )
            
            analysis_data = analysis_response.json()
        
        # Generate AR visualization components
        ar_components = await generate_ar_components(analysis_data, request.visualization_type)
        
        return ARVisualizationResponse(
            location=request.location,
            visualization_type=request.visualization_type,
            components=ar_components,
            metadata={
                "generated_at": datetime.now().isoformat(),
                "data_sources": ["NASA SMAP", "NASA MODIS", "NASA GPM", "NASA ECOSTRESS"],
                "confidence": analysis_data.get("confidence_scores", {}),
                "alerts": analysis_data.get("alerts", [])
            }
        )
        
    except Exception as e:
        logger.error(f"❌ AR visualization generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"AR visualization failed: {str(e)}")

@app.get("/ar/visualization-data")
async def get_ar_visualization_data_simple(
    lat: float,
    lon: float,
    visualization_type: str = "comprehensive"
):
    """
    Simplified AR visualization endpoint for direct access
    """
    try:
        request = ARVisualizationRequest(
            location={"lat": lat, "lon": lon},
            farm_details={"crop_type": "corn"},
            date_range={
                "start": datetime.now().isoformat(),
                "end": datetime.now().isoformat()
            },
            visualization_type=visualization_type
        )
        
        response = await get_ar_visualization_data(request)
        return response.dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def generate_ar_components(analysis_data: Dict[str, Any], viz_type: str) -> Dict[str, Any]:
    """Generate AR visualization components"""
    
    metrics = analysis_data.get("metrics", {})
    
    # Soil Moisture Visualization
    soil_moisture_component = generate_soil_moisture_visualization(
        metrics.get("soil_moisture", {})
    )
    
    # Water Level Visualization
    water_level_component = generate_water_level_visualization(
        metrics.get("water_level", {})
    )
    
    # Pesticide Optimization Visualization
    pesticide_component = generate_pesticide_visualization(
        metrics.get("pesticide_optimization", {})
    )
    
    # 3D Scene Configuration
    scene_config = generate_scene_configuration(analysis_data)
    
    return {
        "soil_moisture_mesh": soil_moisture_component,
        "water_level_spheres": water_level_component,
        "pesticide_zones": pesticide_component,
        "scene_configuration": scene_config,
        "interactive_elements": generate_interactive_elements(analysis_data),
        "information_panels": generate_information_panels(metrics)
    }

def generate_soil_moisture_visualization(soil_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate 3D soil moisture visualization"""
    
    moisture_value = soil_data.get("value", 0.5)
    components = soil_data.get("components", {})
    
    # Generate mesh data for soil moisture
    mesh_data = {
        "type": "heatmap_mesh",
        "geometry": {
            "width": 100,
            "height": 100,
            "segments": 50
        },
        "material": {
            "type": "shader_material",
            "uniforms": {
                "moisture_data": {
                    "type": "texture",
                    "data": generate_moisture_texture_data(components)
                },
                "color_scale": {
                    "type": "texture",
                    "data": generate_moisture_color_scale()
                }
            },
            "vertex_shader": """
                uniform sampler2D moisture_data;
                varying vec2 vUv;
                varying float vElevation;
                
                void main() {
                    vUv = uv;
                    vec4 moisture = texture2D(moisture_data, uv);
                    vElevation = moisture.r * 5.0;
                    
                    vec3 pos = position;
                    pos.z += vElevation;
                    
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
                }
            """,
            "fragment_shader": """
                uniform sampler2D color_scale;
                varying vec2 vUv;
                varying float vElevation;
                
                void main() {
                    float colorIndex = vElevation / 5.0;
                    vec4 color = texture2D(color_scale, vec2(colorIndex, 0.5));
                    gl_FragColor = vec4(color.rgb, 0.8);
                }
            """
        },
        "position": {"x": 0, "y": 0, "z": 0},
        "rotation": {"x": -90, "y": 0, "z": 0},
        "metadata": {
            "moisture_level": moisture_value,
            "category": categorize_moisture_level(moisture_value),
            "recommendations": soil_data.get("recommendations", [])
        }
    }
    
    return mesh_data

def generate_water_level_visualization(water_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate 3D water level visualization"""
    
    water_value = water_data.get("value", 0.5)
    components = water_data.get("components", {})
    
    # Generate sphere data for water availability
    spheres_data = {
        "type": "water_spheres",
        "spheres": []
    }
    
    # Create multiple spheres representing different water sources
    water_points = [
        {"x": -20, "z": -20, "source": "groundwater", "value": components.get("groundwater_component", 0.5)},
        {"x": 20, "z": -20, "source": "precipitation", "value": components.get("precipitation_component", 0.5)},
        {"x": 0, "z": 20, "source": "surface_water", "value": components.get("surface_water_component", 0.5)},
        {"x": 0, "z": 0, "source": "overall", "value": water_value}
    ]
    
    for point in water_points:
        sphere = {
            "geometry": {
                "type": "sphere",
                "radius": 2,
                "segments": 32
            },
            "material": {
                "type": "shader_material",
                "uniforms": {
                    "water_level": {"type": "float", "value": point["value"]},
                    "time": {"type": "float", "value": 0.0},
                    "opacity": {"type": "float", "value": 0.7}
                },
                "vertex_shader": """
                    uniform float time;
                    varying vec3 vPosition;
                    
                    void main() {
                        vPosition = position;
                        vec3 pos = position;
                        pos.y += sin(time + position.x * 2.0) * 0.1;
                        gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
                    }
                """,
                "fragment_shader": """
                    uniform float water_level;
                    uniform float opacity;
                    varying vec3 vPosition;
                    
                    void main() {
                        vec3 lowWaterColor = vec3(0.8, 0.4, 0.2);
                        vec3 highWaterColor = vec3(0.2, 0.4, 0.8);
                        vec3 color = mix(lowWaterColor, highWaterColor, water_level);
                        gl_FragColor = vec4(color, opacity);
                    }
                """,
                "transparent": True
            },
            "position": {
                "x": point["x"],
                "y": point["value"] * 3,
                "z": point["z"]
            },
            "scale": {
                "x": point["value"],
                "y": point["value"],
                "z": point["value"]
            },
            "metadata": {
                "source": point["source"],
                "water_level": point["value"],
                "status": categorize_water_level(point["value"])
            }
        }
        spheres_data["spheres"].append(sphere)
    
    return spheres_data

def generate_pesticide_visualization(pesticide_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate pesticide application zone visualization"""
    
    paoi_value = pesticide_data.get("value", 0.5)
    components = pesticide_data.get("components", {})
    application_window = pesticide_data.get("application_window", {})
    
    # Generate zone data
    zones_data = {
        "type": "application_zones",
        "zones": []
    }
    
    # Create application zones based on optimization score
    zone_configs = [
        {"x": -15, "z": -15, "type": "optimal", "threshold": 0.7},
        {"x": 15, "z": -15, "type": "moderate", "threshold": 0.4},
        {"x": 0, "z": 15, "type": "poor", "threshold": 0.0}
    ]
    
    for zone_config in zone_configs:
        zone_value = max(0.0, paoi_value - zone_config["threshold"])
        
        zone = {
            "geometry": {
                "type": "ring",
                "inner_radius": 5,
                "outer_radius": 15,
                "segments": 8
            },
            "material": {
                "type": "shader_material",
                "uniforms": {
                    "application_score": {"type": "float", "value": zone_value},
                    "time": {"type": "float", "value": 0.0},
                    "risk_level": {"type": "float", "value": pesticide_data.get("environmental_impact_score", 0.5)}
                },
                "vertex_shader": """
                    uniform float time;
                    varying vec2 vUv;
                    
                    void main() {
                        vUv = uv;
                        vec3 pos = position;
                        pos.z += sin(time * 2.0) * 0.1;
                        gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
                    }
                """,
                "fragment_shader": """
                    uniform float application_score;
                    uniform float risk_level;
                    varying vec2 vUv;
                    
                    void main() {
                        vec3 lowOptimalColor = vec3(1.0, 0.3, 0.3);
                        vec3 highOptimalColor = vec3(0.3, 1.0, 0.3);
                        vec3 baseColor = mix(lowOptimalColor, highOptimalColor, application_score);
                        
                        float riskAlpha = 1.0 - risk_level;
                        gl_FragColor = vec4(baseColor, riskAlpha * 0.6);
                    }
                """,
                "transparent": True,
                "side": "double"
            },
            "position": {
                "x": zone_config["x"],
                "y": 0.1,
                "z": zone_config["z"]
            },
            "rotation": {"x": -90, "y": 0, "z": 0},
            "metadata": {
                "zone_type": zone_config["type"],
                "optimization_score": zone_value,
                "application_window": application_window,
                "recommendations": pesticide_data.get("recommendations", [])
            }
        }
        zones_data["zones"].append(zone)
    
    return zones_data

def generate_scene_configuration(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate 3D scene configuration"""
    
    return {
        "camera": {
            "position": {"x": 0, "y": 20, "z": 30},
            "target": {"x": 0, "y": 0, "z": 0},
            "fov": 75
        },
        "lighting": {
            "ambient_light": {"color": "#404040", "intensity": 0.4},
            "directional_light": {
                "color": "#ffffff",
                "intensity": 0.8,
                "position": {"x": 50, "y": 50, "z": 50}
            }
        },
        "environment": {
            "background_color": "#87CEEB",
            "fog": {
                "enabled": True,
                "color": "#87CEEB",
                "near": 50,
                "far": 200
            }
        },
        "controls": {
            "enable_rotation": True,
            "enable_zoom": True,
            "enable_pan": True
        }
    }

def generate_interactive_elements(analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate interactive AR elements"""
    
    elements = []
    
    # Data point markers
    metrics = analysis_data.get("metrics", {})
    
    for metric_name, metric_data in metrics.items():
        element = {
            "type": "data_marker",
            "id": f"{metric_name}_marker",
            "position": {"x": 0, "y": 2, "z": 0},
            "data": {
                "metric_name": metric_name,
                "value": metric_data.get("value", 0),
                "category": get_metric_category(metric_name, metric_data.get("value", 0)),
                "recommendations": metric_data.get("recommendations", [])
            },
            "interaction": {
                "on_tap": f"show_{metric_name}_details",
                "on_hover": f"highlight_{metric_name}"
            }
        }
        elements.append(element)
    
    return elements

def generate_information_panels(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate AR information panels"""
    
    panels = []
    
    for metric_name, metric_data in metrics.items():
        panel = {
            "id": f"{metric_name}_panel",
            "title": get_metric_display_name(metric_name),
            "position": {"x": 0, "y": 8, "z": 0},
            "size": {"width": 8, "height": 4},
            "content": {
                "primary_value": metric_data.get("value", 0),
                "unit": "%",
                "category": get_metric_category(metric_name, metric_data.get("value", 0)),
                "status": get_metric_status(metric_name, metric_data.get("value", 0)),
                "recommendations": metric_data.get("recommendations", [])[:2]
            },
            "style": {
                "background_color": get_panel_color(metric_name, metric_data.get("value", 0)),
                "text_color": "#ffffff",
                "opacity": 0.9
            }
        }
        panels.append(panel)
    
    return panels

# Helper functions
def categorize_moisture_level(value: float) -> str:
    """Categorize soil moisture level"""
    if value >= 0.8:
        return "optimal"
    elif value >= 0.6:
        return "good"
    elif value >= 0.4:
        return "moderate"
    elif value >= 0.2:
        return "poor"
    else:
        return "critical"

def categorize_water_level(value: float) -> str:
    """Categorize water level"""
    if value >= 0.7:
        return "adequate"
    elif value >= 0.4:
        return "moderate"
    else:
        return "critical"

def generate_moisture_texture_data(components: Dict[str, Any]) -> List[List[float]]:
    """Generate texture data for moisture visualization"""
    # Simplified texture generation
    texture_data = []
    for i in range(64):
        row = []
        for j in range(64):
            # Create gradient pattern based on components
            value = (components.get("surface_moisture", 0.5) + 
                    components.get("root_zone_moisture", 0.5)) / 2
            row.append([value, value, value, 1.0])
        texture_data.append(row)
    return texture_data

def generate_moisture_color_scale() -> List[List[float]]:
    """Generate color scale for moisture visualization"""
    # Brown (dry) to Blue (wet) gradient
    return [
        [0.6, 0.4, 0.2, 1.0],  # Brown
        [0.7, 0.5, 0.3, 1.0],  # Light brown
        [0.5, 0.6, 0.4, 1.0],  # Yellow-green
        [0.3, 0.7, 0.5, 1.0],  # Green
        [0.2, 0.6, 0.8, 1.0]   # Blue
    ]

def get_metric_category(metric_name: str, value: float) -> str:
    """Get category for metric value"""
    if metric_name == "soil_moisture":
        return categorize_moisture_level(value)
    elif metric_name == "water_level":
        return categorize_water_level(value)
    elif metric_name == "pesticide_optimization":
        if value >= 0.7:
            return "optimal"
        elif value >= 0.4:
            return "moderate"
        else:
            return "poor"
    return "unknown"

def get_metric_status(metric_name: str, value: float) -> str:
    """Get status for metric value"""
    if value >= 0.7:
        return "excellent"
    elif value >= 0.5:
        return "good"
    elif value >= 0.3:
        return "fair"
    else:
        return "poor"

def get_metric_display_name(metric_name: str) -> str:
    """Get display name for metric"""
    names = {
        "soil_moisture": "Soil Moisture Index",
        "water_level": "Water Level Indicator",
        "pesticide_optimization": "Pesticide Optimization"
    }
    return names.get(metric_name, metric_name.title())

def get_panel_color(metric_name: str, value: float) -> str:
    """Get panel color based on metric value"""
    if value >= 0.7:
        return "#4CAF50"  # Green
    elif value >= 0.4:
        return "#FF9800"  # Orange
    else:
        return "#F44336"  # Red

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
