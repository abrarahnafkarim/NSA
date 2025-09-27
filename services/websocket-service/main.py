from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv
import redis
import httpx

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="WebSocket Real-time Service",
    description="Real-time WebSocket service for NASA agricultural intelligence",
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
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Redis client
redis_client = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.farm_subscriptions: Dict[str, List[str]] = {}  # farm_id -> [websocket_ids]
        self.websocket_farms: Dict[str, str] = {}  # websocket_id -> farm_id
    
    async def connect(self, websocket: WebSocket, farm_id: str):
        await websocket.accept()
        connection_id = f"{farm_id}_{datetime.now().timestamp()}"
        
        self.active_connections[connection_id] = websocket
        self.websocket_farms[connection_id] = farm_id
        
        if farm_id not in self.farm_subscriptions:
            self.farm_subscriptions[farm_id] = []
        self.farm_subscriptions[farm_id].append(connection_id)
        
        logger.info(f"WebSocket connected for farm: {farm_id} (connection: {connection_id})")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "farm_id": farm_id,
            "connection_id": connection_id,
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to NASA Agricultural Intelligence Real-time Service"
        }, connection_id)
    
    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            farm_id = self.websocket_farms.get(connection_id)
            
            # Remove from active connections
            del self.active_connections[connection_id]
            
            if connection_id in self.websocket_farms:
                del self.websocket_farms[connection_id]
            
            # Remove from farm subscriptions
            if farm_id and farm_id in self.farm_subscriptions:
                self.farm_subscriptions[farm_id].remove(connection_id)
                if not self.farm_subscriptions[farm_id]:
                    del self.farm_subscriptions[farm_id]
            
            logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def send_to_farm(self, message: Dict[str, Any], farm_id: str):
        """Send message to all connections for a specific farm"""
        if farm_id in self.farm_subscriptions:
            for connection_id in self.farm_subscriptions[farm_id]:
                await self.send_personal_message(message, connection_id)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to broadcast to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
    
    def get_farm_connection_count(self, farm_id: str) -> int:
        """Get number of connections for a specific farm"""
        return len(self.farm_subscriptions.get(farm_id, []))

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize WebSocket service on startup"""
    global redis_client
    
    try:
        # Initialize Redis connection
        redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        
        # Start background tasks
        asyncio.create_task(periodic_data_updates())
        asyncio.create_task(alert_monitoring())
        
        logger.info("🔌 WebSocket Real-time Service started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize WebSocket service: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if redis_client:
        redis_client.close()
    logger.info("WebSocket service shutdown complete")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "websocket-service",
        "version": "2.0.0",
        "active_connections": manager.get_connection_count(),
        "monitored_farms": len(manager.farm_subscriptions)
    }

@app.websocket("/ws/farm-monitoring/{farm_id}")
async def websocket_farm_monitoring(websocket: WebSocket, farm_id: str):
    """
    WebSocket endpoint for real-time farm data streaming
    """
    connection_id = await manager.connect(websocket, farm_id)
    
    try:
        # Start monitoring this farm
        await start_farm_monitoring(farm_id)
        
        while True:
            # Listen for client messages
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await handle_client_message(message, farm_id, connection_id)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling client message: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"Error processing message: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }, connection_id)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for farm: {farm_id}")
    except Exception as e:
        logger.error(f"WebSocket error for farm {farm_id}: {e}")
    finally:
        manager.disconnect(connection_id)
        await stop_farm_monitoring(farm_id)

async def handle_client_message(message: Dict[str, Any], farm_id: str, connection_id: str):
    """Handle messages from WebSocket clients"""
    message_type = message.get("type", "")
    
    if message_type == "ping":
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }, connection_id)
    
    elif message_type == "request_update":
        # Send immediate update
        latest_data = await get_latest_farm_data(farm_id)
        await manager.send_personal_message({
            "type": "immediate_update",
            "farm_id": farm_id,
            "data": latest_data,
            "timestamp": datetime.now().isoformat()
        }, connection_id)
    
    elif message_type == "subscribe_alerts":
        # Subscribe to specific alert types
        alert_types = message.get("alert_types", ["all"])
        await subscribe_to_alerts(farm_id, alert_types, connection_id)
    
    elif message_type == "update_preferences":
        # Update monitoring preferences
        preferences = message.get("preferences", {})
        await update_monitoring_preferences(farm_id, preferences, connection_id)

async def start_farm_monitoring(farm_id: str):
    """Start monitoring a farm"""
    try:
        # Store farm monitoring status in Redis
        if redis_client:
            await redis_client.setex(
                f"farm_monitoring:{farm_id}",
                3600,  # 1 hour TTL
                json.dumps({
                    "status": "active",
                    "started_at": datetime.now().isoformat(),
                    "update_interval": 300  # 5 minutes
                })
            )
        
        logger.info(f"Started monitoring farm: {farm_id}")
    except Exception as e:
        logger.error(f"Failed to start monitoring farm {farm_id}: {e}")

async def stop_farm_monitoring(farm_id: str):
    """Stop monitoring a farm"""
    try:
        # Remove farm monitoring status from Redis
        if redis_client:
            await redis_client.delete(f"farm_monitoring:{farm_id}")
        
        logger.info(f"Stopped monitoring farm: {farm_id}")
    except Exception as e:
        logger.error(f"Failed to stop monitoring farm {farm_id}: {e}")

async def get_latest_farm_data(farm_id: str) -> Dict[str, Any]:
    """Get latest data for a farm"""
    try:
        # In production, fetch from database or cache
        # For now, generate mock data
        return {
            "farm_id": farm_id,
            "soil_moisture": {
                "value": 0.65,
                "status": "good",
                "trend": "stable",
                "last_updated": datetime.now().isoformat()
            },
            "water_level": {
                "value": 0.72,
                "status": "adequate",
                "trend": "improving",
                "last_updated": datetime.now().isoformat()
            },
            "pesticide_optimization": {
                "value": 0.58,
                "status": "moderate",
                "trend": "declining",
                "last_updated": datetime.now().isoformat()
            },
            "weather": {
                "temperature": 22.5,
                "humidity": 65,
                "precipitation_probability": 0.3,
                "wind_speed": 3.2
            },
            "alerts": [],
            "recommendations": [
                "Monitor soil moisture levels",
                "Prepare for potential irrigation",
                "Check pesticide application conditions"
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get latest data for farm {farm_id}: {e}")
        return {}

async def periodic_data_updates():
    """Send periodic updates to all monitored farms"""
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutes
            
            for farm_id in manager.farm_subscriptions.keys():
                latest_data = await get_latest_farm_data(farm_id)
                
                await manager.send_to_farm({
                    "type": "metrics_update",
                    "farm_id": farm_id,
                    "data": latest_data,
                    "timestamp": datetime.now().isoformat()
                }, farm_id)
                
        except Exception as e:
            logger.error(f"Error in periodic updates: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying

async def alert_monitoring():
    """Monitor for alerts and send notifications"""
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            
            for farm_id in manager.farm_subscriptions.keys():
                alerts = await check_farm_alerts(farm_id)
                
                if alerts:
                    await manager.send_to_farm({
                        "type": "alert",
                        "farm_id": farm_id,
                        "alerts": alerts,
                        "timestamp": datetime.now().isoformat()
                    }, farm_id)
                    
        except Exception as e:
            logger.error(f"Error in alert monitoring: {e}")
            await asyncio.sleep(60)

async def check_farm_alerts(farm_id: str) -> List[Dict[str, Any]]:
    """Check for alerts for a specific farm"""
    try:
        latest_data = await get_latest_farm_data(farm_id)
        alerts = []
        
        # Check soil moisture alerts
        soil_moisture = latest_data.get("soil_moisture", {}).get("value", 1.0)
        if soil_moisture < 0.3:
            alerts.append({
                "type": "critical",
                "category": "soil_moisture",
                "message": "Critical soil moisture levels detected",
                "recommendation": "Immediate irrigation required"
            })
        
        # Check water level alerts
        water_level = latest_data.get("water_level", {}).get("value", 1.0)
        if water_level < 0.3:
            alerts.append({
                "type": "critical",
                "category": "water_level",
                "message": "Critical water shortage detected",
                "recommendation": "Emergency water management needed"
            })
        
        # Check pesticide optimization alerts
        paoi = latest_data.get("pesticide_optimization", {}).get("value", 1.0)
        if paoi < 0.3:
            alerts.append({
                "type": "warning",
                "category": "pesticide_optimization",
                "message": "Poor pesticide application conditions",
                "recommendation": "Consider postponing pesticide application"
            })
        
        return alerts
        
    except Exception as e:
        logger.error(f"Failed to check alerts for farm {farm_id}: {e}")
        return []

async def subscribe_to_alerts(farm_id: str, alert_types: List[str], connection_id: str):
    """Subscribe to specific alert types"""
    try:
        # Store alert preferences in Redis
        if redis_client:
            await redis_client.setex(
                f"alert_subscription:{farm_id}:{connection_id}",
                3600,
                json.dumps({
                    "alert_types": alert_types,
                    "subscribed_at": datetime.now().isoformat()
                })
            )
        
        await manager.send_personal_message({
            "type": "subscription_confirmed",
            "alert_types": alert_types,
            "timestamp": datetime.now().isoformat()
        }, connection_id)
        
    except Exception as e:
        logger.error(f"Failed to subscribe to alerts: {e}")

async def update_monitoring_preferences(farm_id: str, preferences: Dict[str, Any], connection_id: str):
    """Update monitoring preferences"""
    try:
        # Store preferences in Redis
        if redis_client:
            await redis_client.setex(
                f"monitoring_preferences:{farm_id}:{connection_id}",
                3600,
                json.dumps({
                    "preferences": preferences,
                    "updated_at": datetime.now().isoformat()
                })
            )
        
        await manager.send_personal_message({
            "type": "preferences_updated",
            "preferences": preferences,
            "timestamp": datetime.now().isoformat()
        }, connection_id)
        
    except Exception as e:
        logger.error(f"Failed to update preferences: {e}")

# REST endpoints for WebSocket management
@app.get("/api/v1/websocket/status")
async def get_websocket_status():
    """Get WebSocket service status"""
    return {
        "active_connections": manager.get_connection_count(),
        "monitored_farms": len(manager.farm_subscriptions),
        "farm_details": {
            farm_id: {
                "connection_count": manager.get_farm_connection_count(farm_id),
                "connections": connection_ids
            }
            for farm_id, connection_ids in manager.farm_subscriptions.items()
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/websocket/broadcast")
async def broadcast_message(message: Dict[str, Any]):
    """Broadcast message to all connected clients"""
    try:
        broadcast_msg = {
            "type": "broadcast",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.broadcast_to_all(broadcast_msg)
        
        return {
            "status": "success",
            "message": "Broadcast sent to all connected clients",
            "connection_count": manager.get_connection_count()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Broadcast failed: {str(e)}")

@app.post("/api/v1/websocket/farm/{farm_id}/notify")
async def notify_farm(farm_id: str, notification: Dict[str, Any]):
    """Send notification to specific farm"""
    try:
        notification_msg = {
            "type": "notification",
            "farm_id": farm_id,
            "notification": notification,
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.send_to_farm(notification_msg, farm_id)
        
        return {
            "status": "success",
            "message": f"Notification sent to farm {farm_id}",
            "connection_count": manager.get_farm_connection_count(farm_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Notification failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
