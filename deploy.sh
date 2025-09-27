#!/bin/bash

# NASA Agricultural Intelligence System - Complete Deployment Script
set -e

echo "🌾 NASA Agricultural Intelligence System Deployment"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is required but not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is required but not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from example..."
        cp env.example .env
        print_warning "Please edit .env file with your NASA API credentials before continuing."
        print_warning "Required credentials:"
        print_warning "  - NASA_EARTHDATA_USERNAME"
        print_warning "  - NASA_EARTHDATA_PASSWORD"
        print_warning "  - JWT_SECRET"
        echo ""
        read -p "Press Enter after updating .env file to continue..."
    fi
    
    print_success "Prerequisites check passed"
}

# Setup directories
setup_directories() {
    print_status "Setting up directory structure..."
    
    mkdir -p data/{nasa_raw,processed,cache}
    mkdir -p logs/{nasa-ingest,fusion-engine,analytics-api,ar-service,websocket}
    mkdir -p models/{ml_models,crop_databases}
    mkdir -p ar-assets/{textures,models,shaders}
    mkdir -p monitoring/{prometheus,grafana/dashboards,grafana/datasources}
    mkdir -p nginx/ssl
    mkdir -p sql/init
    
    print_success "Directory structure created"
}

# Generate SSL certificates
generate_ssl_certs() {
    print_status "Generating SSL certificates for development..."
    
    if [ ! -f nginx/ssl/cert.pem ]; then
        openssl req -x509 -newkey rsa:4096 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem -days 365 -nodes \
            -subj "/C=US/ST=CA/L=San Francisco/O=NASA Agriculture/OU=IT Department/CN=localhost"
        print_success "SSL certificates generated"
    else
        print_status "SSL certificates already exist"
    fi
}

# Create Nginx configuration
create_nginx_config() {
    print_status "Creating Nginx configuration..."
    
    cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream analytics_api {
        server analytics-api:8000;
    }
    
    upstream ar_service {
        server ar-service:8000;
    }
    
    upstream websocket_service {
        server websocket-service:8000;
    }
    
    map $http_upgrade $connection_upgrade {
        default upgrade;
        '' close;
    }
    
    server {
        listen 80;
        server_name localhost api.nasa-agriculture.local;
        
        # API Routes
        location /api/ {
            proxy_pass http://analytics_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # CORS headers
            add_header 'Access-Control-Allow-Origin' '*' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
            
            if ($request_method = 'OPTIONS') {
                add_header 'Access-Control-Allow-Origin' '*';
                add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS';
                add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization';
                add_header 'Access-Control-Max-Age' 1728000;
                add_header 'Content-Type' 'text/plain; charset=utf-8';
                add_header 'Content-Length' 0;
                return 204;
            }
        }
        
        # AR Service Routes
        location /ar/ {
            proxy_pass http://ar_service/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
        
        # WebSocket Routes
        location /ws/ {
            proxy_pass http://websocket_service;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_cache_bypass $http_upgrade;
        }
        
        # Static files for AR assets
        location /assets/ {
            alias /app/ar-assets/;
            expires 1d;
            add_header Cache-Control "public, no-transform";
        }
        
        # Health check endpoint
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
EOF
    
    print_success "Nginx configuration created"
}

# Create Prometheus configuration
create_prometheus_config() {
    print_status "Creating Prometheus configuration..."
    
    cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'nasa-agriculture-services'
    static_configs:
      - targets: 
        - 'nasa-data-ingest:8000'
        - 'data-fusion-engine:8000'
        - 'analytics-api:8000'
        - 'ar-service:8000'
        - 'websocket-service:8000'
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'postgresql'
    static_configs:
      - targets: ['postgresql:5432']
EOF
    
    print_success "Prometheus configuration created"
}

# Build and start services
deploy_services() {
    print_status "Building and starting services..."
    
    # Build all services
    print_status "Building Docker images..."
    docker-compose build --no-cache
    
    # Start infrastructure services first
    print_status "Starting infrastructure services..."
    docker-compose up -d postgresql redis
    
    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    sleep 30
    
    # Start core application services
    print_status "Starting core application services..."
    docker-compose up -d nasa-data-ingest data-fusion-engine
    
    # Wait for core services
    print_status "Waiting for core services..."
    sleep 20
    
    # Start API and frontend services
    print_status "Starting API and frontend services..."
    docker-compose up -d analytics-api ar-service websocket-service nginx
    
    # Wait for API services
    print_status "Waiting for API services..."
    sleep 15
    
    # Start monitoring
    print_status "Starting monitoring services..."
    docker-compose up -d prometheus grafana
    
    print_success "All services started successfully"
}

# Health checks
run_health_checks() {
    print_status "Running health checks..."
    
    services=("nasa-data-ingest:8001" "data-fusion-engine:8002" "analytics-api:8003" "ar-service:8004" "websocket-service:8005")
    
    for service in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service"
        print_status "Checking $name on port $port..."
        
        max_attempts=30
        attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if curl -f http://localhost:$port/health >/dev/null 2>&1; then
                print_success "$name is healthy"
                break
            fi
            
            if [ $attempt -eq $max_attempts ]; then
                print_error "$name failed health check"
                print_error "Service logs:"
                docker-compose logs $name
                exit 1
            fi
            
            sleep 2
            attempt=$((attempt + 1))
        done
    done
    
    print_success "All health checks passed"
}

# Setup sample data
setup_sample_data() {
    print_status "Setting up sample data..."
    
    # Wait a bit for services to fully initialize
    sleep 10
    
    # Test the unified analysis endpoint
    print_status "Testing unified analysis endpoint..."
    
    curl -X POST http://localhost:8003/api/v1/agriculture/unified-analysis \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $(echo '{"user_id": "test_user", "username": "test"}' | base64)" \
        -d '{
            "location": {"lat": 40.7128, "lon": -74.0060, "name": "Sample Farm NYC"},
            "farm_details": {"crop_type": "corn", "farm_size": 100, "planting_date": "2024-03-15"},
            "date_range": {"start": "2024-03-01T00:00:00Z", "end": "2024-03-31T23:59:59Z"},
            "analysis_type": "comprehensive"
        }' || print_warning "Sample data request failed (this is normal during initial setup)"
    
    print_success "Sample data setup complete"
}

# Display deployment information
display_deployment_info() {
    echo ""
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "📡 Service URLs:"
    echo "   • Analytics API: http://localhost:8003"
    echo "   • NASA Data Ingestion: http://localhost:8001"
    echo "   • Data Fusion Engine: http://localhost:8002"
    echo "   • AR Service: http://localhost:8004"
    echo "   • WebSocket Service: ws://localhost:8005"
    echo "   • Main API (via Nginx): http://localhost"
    echo ""
    echo "📊 Monitoring:"
    echo "   • Prometheus: http://localhost:9090"
    echo "   • Grafana: http://localhost:3000 (admin/admin_password)"
    echo ""
    echo "🗄️ Database:"
    echo "   • PostgreSQL: localhost:5432 (agri_user/secure_password)"
    echo "   • Redis: localhost:6379"
    echo ""
    echo "📖 API Documentation:"
    echo "   • Analytics API Swagger: http://localhost:8003/docs"
    echo "   • Data Fusion API Swagger: http://localhost:8002/docs"
    echo ""
    echo "🧪 Test the system:"
    echo "   curl -X GET 'http://localhost:8003/api/v1/agriculture/realtime-monitoring?lat=40.7128&lon=-74.0060'"
    echo ""
    echo "🎮 Game Integration:"
    echo "   curl -X POST 'http://localhost:8003/api/v1/game/scenario-data' \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"scenario_id\": \"test_drought\", \"scenario_type\": \"drought\", \"difficulty_level\": \"beginner\"}'"
    echo ""
    echo "🛰️ AR Visualization:"
    echo "   curl -X GET 'http://localhost:8004/ar/visualization-data?lat=40.7128&lon=-74.0060'"
    echo ""
    echo "📋 Useful Commands:"
    echo "   • View logs: docker-compose logs -f [service_name]"
    echo "   • Scale services: docker-compose up -d --scale analytics-api=3"
    echo "   • Stop all services: docker-compose down"
    echo "   • Restart services: docker-compose restart"
    echo ""
}

# Main deployment function
main() {
    print_status "Starting NASA Agricultural Intelligence System deployment..."
    
    check_prerequisites
    setup_directories
    generate_ssl_certs
    create_nginx_config
    create_prometheus_config
    deploy_services
    run_health_checks
    setup_sample_data
    display_deployment_info
}

# Run deployment
main "$@"
