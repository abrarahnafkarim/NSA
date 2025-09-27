# NASA Agricultural Intelligence System 🌾🛰️

A comprehensive agricultural intelligence platform that integrates NASA satellite data with advanced data fusion algorithms to provide three critical metrics for modern farming operations. This system delivers real-time agricultural insights through microservices architecture, AR visualization, and educational gaming interfaces.

## 🎯 System Overview

This system transforms NASA's vast satellite data into actionable agricultural intelligence through three unified metrics:

### Core Metrics

#### 1. **Unified Soil Moisture Index (USMI)**
Combines multiple NASA datasets to provide comprehensive soil moisture assessment:
- **SMAP L3/L4** soil moisture data
- **MODIS** land surface temperature
- **GPM** precipitation data
- **ECOSTRESS** evapotranspiration data

#### 2. **Agricultural Water Level Indicator (AWLI)**
Provides water availability assessment for agricultural operations:
- **GRACE/GRACE-FO** groundwater data
- **MODIS** vegetation indices
- **GPM** precipitation analysis
- **Landsat** surface water detection

#### 3. **Pesticide Application Optimization Index (PAOI)**
Optimizes pesticide application timing and effectiveness:
- **MODIS** vegetation stress analysis
- **Landsat** crop health assessment
- **GPM** weather suitability
- **VIIRS** pest activity correlation

## 🏗️ Architecture

### Microservices Design

```yaml
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   NASA Data     │    │  Data Fusion    │    │   Analytics     │
│   Ingestion     │───▶│    Engine       │───▶│      API        │
│   Service       │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Redis       │    │   PostgreSQL    │    │  WebSocket      │
│     Cache       │    │   Database      │    │   Service       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   AR Service    │
                                              │  Visualization  │
                                              └─────────────────┘
```

### Technology Stack

**Backend Services:**
- **FastAPI** - High-performance Python web framework
- **PostgreSQL + PostGIS** - Geospatial database
- **Redis** - Caching and real-time data
- **Docker** - Containerization
- **Nginx** - Load balancing and reverse proxy

**Data Processing:**
- **NumPy/Pandas** - Data manipulation
- **Scikit-learn** - Machine learning
- **GDAL** - Geospatial data processing
- **XArray** - Multidimensional data arrays

**Frontend Integration:**
- **WebSocket** - Real-time communication
- **AR Visualization** - 3D agricultural data display
- **Game Integration** - Educational interfaces

## 🚀 Quick Start

### Prerequisites

```bash
# System Requirements
- Docker 24.0+
- Docker Compose 2.0+
- 8GB+ RAM
- 20GB+ disk space

# NASA Accounts Required
- NASA Earthdata Login: https://urs.earthdata.nasa.gov/
- NASA API Key: https://api.nasa.gov/
```

### Installation

1. **Clone and Setup**
```bash
git clone <repository-url>
cd nasa-agriculture-system
cp env.example .env
# Edit .env with your NASA credentials
```

2. **Deploy System**
```bash
chmod +x deploy.sh
./deploy.sh
```

3. **Verify Deployment**
```bash
# Check service health
curl http://localhost:8003/health

# Test unified analysis
curl -X POST http://localhost:8003/api/v1/agriculture/unified-analysis \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(echo '{"user_id": "test"}' | base64)" \
  -d '{
    "location": {"lat": 40.7128, "lon": -74.0060, "name": "Test Farm"},
    "farm_details": {"crop_type": "corn", "farm_size": 100},
    "date_range": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-31T23:59:59Z"},
    "analysis_type": "comprehensive"
  }'
```

## 📊 API Endpoints

### Core Agricultural Analysis

```bash
# Unified Agricultural Analysis
POST /api/v1/agriculture/unified-analysis
# Returns: USMI, AWLI, PAOI with recommendations

# Real-time Monitoring
GET /api/v1/agriculture/realtime-monitoring?lat=40.7128&lon=-74.0060
# Returns: Live agricultural metrics

# Historical Analysis
GET /api/v1/agriculture/metrics-history?lat=40.7128&lon=-74.0060&days=30
# Returns: Historical trend data
```

### Game Integration

```bash
# Educational Scenarios
POST /api/v1/game/scenario-data
{
  "scenario_type": "drought",
  "difficulty_level": "beginner",
  "learning_objectives": ["water_management", "sustainable_farming"]
}

# Action Impact Simulation
POST /api/v1/game/action-impact
{
  "current_farm_state": {...},
  "action": {"type": "irrigation", "amount": 25}
}
```

### AR Visualization

```bash
# AR Data Generation
GET /api/v1/ar/visualization-data?lat=40.7128&lon=-74.0060
# Returns: 3D visualization components for AR apps

# WebSocket Real-time Updates
ws://localhost:8005/ws/farm-monitoring/{farm_id}
# Provides: Live data streaming for AR applications
```

## 🎮 Educational Game Integration

### Scenario Types

1. **Drought Management**
   - Low soil moisture conditions
   - Water conservation strategies
   - Irrigation optimization

2. **Optimal Conditions**
   - Balanced agricultural metrics
   - Maintenance best practices
   - Continuous monitoring

3. **Pest Outbreak**
   - Pest detection and management
   - Pesticide optimization
   - Environmental considerations

### Learning Objectives

- **Water Management**: Understanding irrigation efficiency
- **Soil Health**: Monitoring and improving soil conditions
- **Pest Control**: Optimizing pesticide applications
- **Sustainability**: Balancing productivity with environmental impact
- **Data-Driven Decisions**: Using NASA satellite data for farming

## 🥽 AR Visualization Features

### 3D Agricultural Data Display

1. **Soil Moisture Heatmaps**
   - Interactive 3D terrain visualization
   - Real-time moisture level mapping
   - Color-coded health indicators

2. **Water Level Spheres**
   - Animated water availability indicators
   - Multiple water source tracking
   - Irrigation zone recommendations

3. **Pesticide Application Zones**
   - Optimal application timing visualization
   - Environmental impact assessment
   - Weather suitability indicators

4. **Interactive Information Panels**
   - Real-time metric displays
   - Educational content integration
   - NASA data source attribution

## 📈 Data Fusion Algorithms

### USMI Calculation
```python
USMI = (
    (SMAP_surface_moisture * 0.35) +
    (SMAP_root_zone_moisture * 0.25) +
    (precipitation_accumulation_7day / optimal_crop_water * 0.20) +
    (soil_temperature_stress_factor * 0.15) +
    (evapotranspiration_deficit * 0.05)
)
```

### AWLI Calculation
```python
AWLI = (
    (groundwater_anomaly_normalized * 0.30) +
    (precipitation_vs_historical_mean * 0.25) +
    (vegetation_water_stress_indicator * 0.20) +
    (actual_vs_potential_ET * 0.15) +
    (surface_water_availability * 0.10)
)
```

### PAOI Calculation
```python
PAOI = (
    (vegetation_stress_anomaly * 0.30) +
    (pest_favorable_conditions * 0.25) +
    (application_weather_suitability * 0.20) +
    (crop_phenology_stage * 0.15) +
    (wind_speed_spray_drift_risk * 0.10)
)
```

## 🗄️ Database Schema

### Core Tables

- **nasa_data.*** - Raw NASA satellite data storage
- **agricultural_metrics.*** - Processed agricultural metrics
- **user_management.*** - User accounts and farm management
- **game_data.*** - Educational game data and achievements

### Key Features

- **Spatial Indexing** - Optimized geographic queries
- **Time-series Data** - Historical trend analysis
- **Data Quality Tracking** - Confidence scores and uncertainty
- **Real-time Updates** - Live data streaming support

## 🔧 Development

### Local Development Setup

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Run tests
python -m pytest tests/ -v

# Code formatting
black services/
flake8 services/

# Database migrations
alembic upgrade head
```

### Adding New NASA Datasets

1. **Extend Data Ingestion Service**
```python
async def fetch_new_dataset(self, location, date_range):
    # Implement dataset-specific fetching logic
    return processed_data
```

2. **Update Fusion Engine**
```python
def _process_new_dataset(self, data):
    # Add data processing logic
    return normalized_data
```

3. **Update Database Schema**
```sql
CREATE TABLE nasa_data.new_dataset (
    -- Define schema for new dataset
);
```

## 📊 Monitoring & Observability

### Prometheus Metrics

- **API Request Rates** - Endpoint performance tracking
- **Data Fusion Processing Time** - Algorithm performance
- **NASA API Success Rate** - External service health
- **Active WebSocket Connections** - Real-time usage

### Grafana Dashboards

- **System Overview** - Service health and performance
- **Agricultural Metrics** - USMI, AWLI, PAOI trends
- **User Engagement** - Game and AR usage analytics
- **Data Quality** - NASA API reliability and data freshness

## 🌍 Production Deployment

### Kubernetes Deployment

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Scale services
kubectl scale deployment analytics-api --replicas=3

# Monitor deployment
kubectl get pods -n nasa-agriculture
```

### Environment Configuration

```bash
# Production environment variables
export NASA_EARTHDATA_USERNAME=production_username
export NASA_EARTHDATA_PASSWORD=production_password
export JWT_SECRET=production_secret_key
export DATABASE_URL=postgresql://user:pass@prod-db:5432/agri_data
```

## 🤝 Contributing

### Development Workflow

1. **Fork Repository**
2. **Create Feature Branch**
3. **Implement Changes**
4. **Add Tests**
5. **Submit Pull Request**

### Code Standards

- **Python**: PEP 8 compliance, type hints
- **API**: OpenAPI 3.0 specification
- **Database**: Migration scripts for schema changes
- **Testing**: >90% code coverage requirement

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **NASA** for providing open access to satellite and Earth observation data
- **NASA GIBS** for satellite imagery services
- **OpenStreetMap** for map tile services
- **Agricultural Research Community** for domain expertise

## 🔗 Resources

- [NASA Open Data Portal](https://data.nasa.gov/)
- [NASA API Documentation](https://api.nasa.gov/)
- [NASA GIBS Services](https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs)
- [Earthdata Login](https://earthdata.nasa.gov/)
- [PostGIS Documentation](https://postgis.net/)

## 📞 Support

For questions, issues, or contributions:
- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check the `/docs` directory
- **Email**: Contact the development team
- **Discord**: Join our community server

---

**Built with ❤️ for agricultural intelligence and space exploration**