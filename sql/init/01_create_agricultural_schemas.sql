-- Create agricultural intelligence database schemas
-- This script initializes the complete database structure for NASA agricultural intelligence

-- Enable PostGIS extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgis_raster;

-- Create main schemas
CREATE SCHEMA IF NOT EXISTS nasa_data;
CREATE SCHEMA IF NOT EXISTS agricultural_metrics;
CREATE SCHEMA IF NOT EXISTS user_management;
CREATE SCHEMA IF NOT EXISTS game_data;

-- NASA Raw Data Tables
CREATE TABLE nasa_data.ingestion_tasks (
    task_id VARCHAR(255) PRIMARY KEY,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    location GEOMETRY(POINT, 4326) NOT NULL,
    date_range_start TIMESTAMPTZ NOT NULL,
    date_range_end TIMESTAMPTZ NOT NULL,
    datasets_requested TEXT[] NOT NULL,
    datasets_completed TEXT[] DEFAULT '{}',
    datasets_failed TEXT[] DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    processing_time_seconds INTEGER
);

CREATE TABLE nasa_data.raw_dataset_cache (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) REFERENCES nasa_data.ingestion_tasks(task_id),
    dataset_id VARCHAR(100) NOT NULL,
    location GEOMETRY(POINT, 4326) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    data JSONB NOT NULL,
    metadata JSONB,
    quality_flags JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days')
);

-- SMAP Soil Moisture Data
CREATE TABLE nasa_data.smap_soil_moisture (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(POINT, 4326) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    surface_moisture FLOAT,
    root_zone_moisture FLOAT,
    soil_temperature FLOAT,
    quality_flag VARCHAR(20),
    uncertainty FLOAT,
    data_source VARCHAR(50) DEFAULT 'SMAP',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- MODIS Vegetation Data
CREATE TABLE nasa_data.modis_vegetation (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(POINT, 4326) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    ndvi FLOAT,
    evi FLOAT,
    pixel_reliability INTEGER,
    composite_day INTEGER,
    view_zenith_angle FLOAT,
    data_source VARCHAR(50) DEFAULT 'MODIS',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- GPM Precipitation Data
CREATE TABLE nasa_data.gpm_precipitation (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(POINT, 4326) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    precipitation_rate FLOAT,
    precipitation_cal FLOAT,
    probability_of_precipitation FLOAT,
    quality_flag VARCHAR(20),
    data_source VARCHAR(50) DEFAULT 'GPM',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ECOSTRESS Evapotranspiration Data
CREATE TABLE nasa_data.ecostress_et (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(POINT, 4326) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    et_actual FLOAT,
    et_potential FLOAT,
    land_surface_temperature FLOAT,
    emissivity FLOAT,
    quality_flag VARCHAR(20),
    data_source VARCHAR(50) DEFAULT 'ECOSTRESS',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- GRACE Groundwater Data
CREATE TABLE nasa_data.grace_groundwater (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(POINT, 4326) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    groundwater_anomaly FLOAT,
    soil_moisture_anomaly FLOAT,
    total_water_storage_anomaly FLOAT,
    uncertainty FLOAT,
    data_source VARCHAR(50) DEFAULT 'GRACE',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Landsat Multispectral Data
CREATE TABLE nasa_data.landsat_multispectral (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(POINT, 4326) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    ndvi FLOAT,
    ndwi FLOAT,
    surface_temperature FLOAT,
    cloud_cover FLOAT,
    quality_score FLOAT,
    data_source VARCHAR(50) DEFAULT 'Landsat',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agricultural Metrics Tables
CREATE TABLE agricultural_metrics.unified_soil_moisture_index (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(POINT, 4326) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    usmi_value FLOAT NOT NULL CHECK (usmi_value >= 0 AND usmi_value <= 1),
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    
    -- Component values
    surface_moisture_component FLOAT,
    root_zone_component FLOAT,
    precipitation_component FLOAT,
    temperature_component FLOAT,
    et_component FLOAT,
    
    -- Quality and recommendations
    quality_flags JSONB,
    recommendations TEXT[],
    data_sources TEXT[],
    
    -- Metadata
    analysis_type VARCHAR(50) DEFAULT 'standard',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agricultural_metrics.agricultural_water_level_indicator (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(POINT, 4326) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    awli_value FLOAT NOT NULL CHECK (awli_value >= 0 AND awli_value <= 1),
    crop_type VARCHAR(50) NOT NULL,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    
    -- Component values
    groundwater_component FLOAT,
    precipitation_component FLOAT,
    vegetation_stress_component FLOAT,
    et_ratio_component FLOAT,
    surface_water_component FLOAT,
    
    -- Assessment and recommendations
    water_requirement_status VARCHAR(20),
    irrigation_recommendations TEXT[],
    data_sources TEXT[],
    
    -- Metadata
    analysis_type VARCHAR(50) DEFAULT 'standard',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agricultural_metrics.pesticide_application_optimization_index (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(POINT, 4326) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    paoi_value FLOAT NOT NULL CHECK (paoi_value >= 0 AND paoi_value <= 1),
    crop_type VARCHAR(50) NOT NULL,
    target_pest VARCHAR(50) NOT NULL,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    
    -- Component values
    vegetation_stress_component FLOAT,
    pest_conditions_component FLOAT,
    weather_suitability_component FLOAT,
    phenology_component FLOAT,
    spray_drift_component FLOAT,
    
    -- Application window and impact
    application_window JSONB,
    environmental_impact_score FLOAT CHECK (environmental_impact_score >= 0 AND environmental_impact_score <= 1),
    recommendations TEXT[],
    data_sources TEXT[],
    
    -- Metadata
    analysis_type VARCHAR(50) DEFAULT 'standard',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comprehensive Analysis Results
CREATE TABLE agricultural_metrics.comprehensive_analysis (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(POINT, 4326) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- All three metrics
    usmi_value FLOAT,
    awli_value FLOAT,
    paoi_value FLOAT,
    
    -- Overall assessment
    overall_farm_health_score FLOAT,
    critical_alerts TEXT[],
    integrated_recommendations TEXT[],
    
    -- Context
    crop_type VARCHAR(50),
    farm_size_hectares FLOAT,
    analysis_scope VARCHAR(50) DEFAULT 'comprehensive',
    
    -- Metadata
    confidence_scores JSONB,
    data_quality_summary JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Management Tables
CREATE TABLE user_management.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Profile information
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    organization VARCHAR(255),
    role VARCHAR(50) DEFAULT 'farmer',
    
    -- Preferences
    units_preference VARCHAR(10) DEFAULT 'metric',
    notification_preferences JSONB DEFAULT '{"email": true, "push": true}',
    
    -- Account status
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_management.farms (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user_management.users(id),
    farm_name VARCHAR(255) NOT NULL,
    location GEOMETRY(POLYGON, 4326) NOT NULL,
    center_point GEOMETRY(POINT, 4326) NOT NULL,
    
    -- Farm details
    total_area_hectares FLOAT,
    primary_crop_type VARCHAR(50),
    soil_type VARCHAR(100),
    irrigation_system VARCHAR(100),
    
    -- Management
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_management.analysis_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user_management.users(id),
    farm_id INTEGER REFERENCES user_management.farms(id),
    request_type VARCHAR(50) NOT NULL,
    
    -- Request parameters
    location GEOMETRY(POINT, 4326) NOT NULL,
    date_range_start TIMESTAMPTZ,
    date_range_end TIMESTAMPTZ,
    crop_type VARCHAR(50),
    target_pest VARCHAR(50),
    
    -- Results
    analysis_id INTEGER, -- Links to comprehensive_analysis
    status VARCHAR(50) DEFAULT 'pending',
    results JSONB,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Game Data Tables
CREATE TABLE game_data.game_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user_management.users(id),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    game_type VARCHAR(50) DEFAULT 'educational',
    
    -- Session details
    location GEOMETRY(POINT, 4326) NOT NULL,
    crop_type VARCHAR(50),
    difficulty_level VARCHAR(20) DEFAULT 'beginner',
    
    -- Progress tracking
    current_level INTEGER DEFAULT 1,
    experience_points INTEGER DEFAULT 0,
    data_points_collected INTEGER DEFAULT 0,
    achievements_unlocked TEXT[] DEFAULT '{}',
    
    -- Session management
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE game_data.player_actions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES game_data.game_sessions(session_id),
    action_type VARCHAR(50) NOT NULL,
    action_data JSONB NOT NULL,
    
    -- Impact tracking
    metrics_before JSONB,
    metrics_after JSONB,
    impact_score FLOAT,
    
    -- Educational feedback
    learning_objectives TEXT[],
    real_world_connection TEXT,
    nasa_data_context TEXT,
    
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE game_data.achievements (
    id SERIAL PRIMARY KEY,
    achievement_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    icon VARCHAR(100),
    category VARCHAR(50),
    
    -- Requirements
    requirements JSONB NOT NULL,
    points INTEGER DEFAULT 10,
    
    -- Metadata
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE game_data.user_achievements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user_management.users(id),
    achievement_id VARCHAR(50) REFERENCES game_data.achievements(achievement_id),
    unlocked_at TIMESTAMPTZ DEFAULT NOW(),
    progress_data JSONB
);

-- Create spatial indexes for performance
CREATE INDEX idx_ingestion_tasks_location ON nasa_data.ingestion_tasks USING GIST(location);
CREATE INDEX idx_raw_dataset_cache_location_time ON nasa_data.raw_dataset_cache USING GIST(location, timestamp);
CREATE INDEX idx_smap_location_time ON nasa_data.smap_soil_moisture USING GIST(location, timestamp);
CREATE INDEX idx_modis_veg_location_time ON nasa_data.modis_vegetation USING GIST(location, timestamp);
CREATE INDEX idx_gpm_location_time ON nasa_data.gpm_precipitation USING GIST(location, timestamp);
CREATE INDEX idx_ecostress_location_time ON nasa_data.ecostress_et USING GIST(location, timestamp);
CREATE INDEX idx_grace_location_time ON nasa_data.grace_groundwater USING GIST(location, timestamp);
CREATE INDEX idx_landsat_location_time ON nasa_data.landsat_multispectral USING GIST(location, timestamp);

CREATE INDEX idx_usmi_location_time ON agricultural_metrics.unified_soil_moisture_index USING GIST(location, timestamp);
CREATE INDEX idx_awli_location_time ON agricultural_metrics.agricultural_water_level_indicator USING GIST(location, timestamp);
CREATE INDEX idx_paoi_location_time ON agricultural_metrics.pesticide_application_optimization_index USING GIST(location, timestamp);
CREATE INDEX idx_comprehensive_location_time ON agricultural_metrics.comprehensive_analysis USING GIST(location, timestamp);

CREATE INDEX idx_farms_location ON user_management.farms USING GIST(location);
CREATE INDEX idx_farms_center_point ON user_management.farms USING GIST(center_point);
CREATE INDEX idx_analysis_requests_location ON user_management.analysis_requests USING GIST(location);
CREATE INDEX idx_game_sessions_location ON game_data.game_sessions USING GIST(location);

-- Create time-based indexes
CREATE INDEX idx_raw_dataset_cache_timestamp ON nasa_data.raw_dataset_cache (timestamp DESC);
CREATE INDEX idx_usmi_timestamp ON agricultural_metrics.unified_soil_moisture_index (timestamp DESC);
CREATE INDEX idx_awli_timestamp ON agricultural_metrics.agricultural_water_level_indicator (timestamp DESC);
CREATE INDEX idx_paoi_timestamp ON agricultural_metrics.pesticide_application_optimization_index (timestamp DESC);
CREATE INDEX idx_comprehensive_timestamp ON agricultural_metrics.comprehensive_analysis (timestamp DESC);

-- Create composite indexes for common queries
CREATE INDEX idx_usmi_location_crop ON agricultural_metrics.unified_soil_moisture_index (location, timestamp DESC);
CREATE INDEX idx_awli_location_crop ON agricultural_metrics.agricultural_water_level_indicator (location, crop_type, timestamp DESC);
CREATE INDEX idx_paoi_location_crop_pest ON agricultural_metrics.pesticide_application_optimization_index (location, crop_type, target_pest, timestamp DESC);

-- Insert default achievements
INSERT INTO game_data.achievements (achievement_id, name, description, icon, category, requirements, points) VALUES
('first_analysis', 'First Analysis', 'Complete your first agricultural analysis', '🌍', 'milestone', '{"analyses_completed": 1}', 10),
('data_collector', 'Data Collector', 'Collect data from 10 different locations', '📊', 'exploration', '{"locations_visited": 10}', 25),
('soil_expert', 'Soil Expert', 'Achieve 100 soil moisture analyses', '🌱', 'expertise', '{"soil_analyses": 100}', 50),
('water_manager', 'Water Manager', 'Complete 50 water level assessments', '💧', 'management', '{"water_assessments": 50}', 40),
('pest_controller', 'Pest Controller', 'Optimize 25 pesticide applications', '🐛', 'optimization', '{"pesticide_optimizations": 25}', 35),
('nasa_explorer', 'NASA Explorer', 'Use 5 different NASA datasets', '🛰️', 'exploration', '{"datasets_used": 5}', 30),
('precision_farmer', 'Precision Farmer', 'Achieve 90% accuracy in 20 predictions', '🎯', 'precision', '{"accuracy_threshold": 0.9, "predictions": 20}', 75),
('sustainability_champion', 'Sustainability Champion', 'Complete 100 environmentally-friendly recommendations', '🌿', 'sustainability', '{"eco_recommendations": 100}', 60);

-- Create views for common queries
CREATE VIEW agricultural_metrics.latest_metrics AS
SELECT 
    location,
    timestamp,
    usmi_value,
    awli_value,
    paoi_value,
    overall_farm_health_score,
    crop_type,
    critical_alerts,
    integrated_recommendations
FROM agricultural_metrics.comprehensive_analysis
WHERE timestamp >= NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;

CREATE VIEW agricultural_metrics.location_summary AS
SELECT 
    ST_AsText(location) as location_text,
    COUNT(*) as total_analyses,
    AVG(usmi_value) as avg_usmi,
    AVG(awli_value) as avg_awli,
    AVG(paoi_value) as avg_paoi,
    MAX(timestamp) as latest_analysis,
    COUNT(DISTINCT crop_type) as crops_analyzed
FROM agricultural_metrics.comprehensive_analysis
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY location;

-- Create functions for data cleanup and maintenance
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Clean up old raw data cache (older than 30 days)
    DELETE FROM nasa_data.raw_dataset_cache 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Clean up old analysis requests (older than 90 days)
    DELETE FROM user_management.analysis_requests 
    WHERE created_at < NOW() - INTERVAL '90 days' 
    AND status = 'completed';
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function for spatial queries
CREATE OR REPLACE FUNCTION get_nearby_analyses(
    point_lat FLOAT,
    point_lon FLOAT,
    radius_km FLOAT DEFAULT 10.0,
    days_back INTEGER DEFAULT 7
)
RETURNS TABLE (
    distance_km FLOAT,
    usmi_value FLOAT,
    awli_value FLOAT,
    paoi_value FLOAT,
    analysis_date TIMESTAMPTZ,
    crop_type VARCHAR(50)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ST_Distance(
            ST_Transform(ST_SetSRID(ST_Point(point_lon, point_lat), 4326), 3857),
            ST_Transform(location, 3857)
        ) / 1000.0 as distance_km,
        ca.usmi_value,
        ca.awli_value,
        ca.paoi_value,
        ca.timestamp as analysis_date,
        ca.crop_type
    FROM agricultural_metrics.comprehensive_analysis ca
    WHERE ST_DWithin(
        ST_Transform(ST_SetSRID(ST_Point(point_lon, point_lat), 4326), 3857),
        ST_Transform(ca.location, 3857),
        radius_km * 1000.0
    )
    AND ca.timestamp >= NOW() - (days_back || ' days')::INTERVAL
    ORDER BY distance_km;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed for your security requirements)
GRANT USAGE ON SCHEMA nasa_data TO agri_user;
GRANT USAGE ON SCHEMA agricultural_metrics TO agri_user;
GRANT USAGE ON SCHEMA user_management TO agri_user;
GRANT USAGE ON SCHEMA game_data TO agri_user;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA nasa_data TO agri_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA agricultural_metrics TO agri_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA user_management TO agri_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA game_data TO agri_user;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA nasa_data TO agri_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA agricultural_metrics TO agri_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA user_management TO agri_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA game_data TO agri_user;
