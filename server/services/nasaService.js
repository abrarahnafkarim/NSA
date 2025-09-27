const axios = require('axios');

class NasaService {
  constructor() {
    this.baseURL = 'https://api.nasa.gov';
    this.earthdataBaseURL = 'https://cmr.earthdata.nasa.gov';
    this.gibsBaseURL = 'https://gibs.earthdata.nasa.gov';
    this.apiKey = process.env.NASA_API_KEY;
    this.earthdataUsername = process.env.EARTHDATA_USERNAME;
    this.earthdataPassword = process.env.EARTHDATA_PASSWORD;
  }

  // Get NASA APOD (Astronomy Picture of the Day)
  async getAPOD(date = null) {
    try {
      const url = `${this.baseURL}/planetary/apod`;
      const params = { api_key: this.apiKey };
      
      if (date) {
        params.date = date;
      }

      const response = await axios.get(url, { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching APOD:', error.message);
      throw new Error('Failed to fetch APOD data');
    }
  }

  // Get NASA Earth imagery for a specific location
  async getEarthImagery(latitude, longitude, date = null) {
    try {
      const url = `${this.baseURL}/planetary/earth/imagery`;
      const params = {
        lat: latitude,
        lon: longitude,
        api_key: this.apiKey
      };

      if (date) {
        params.date = date;
      }

      const response = await axios.get(url, { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching Earth imagery:', error.message);
      throw new Error('Failed to fetch Earth imagery');
    }
  }

  // Get NASA Earth assets for a specific location
  async getEarthAssets(latitude, longitude, date = null) {
    try {
      const url = `${this.baseURL}/planetary/earth/assets`;
      const params = {
        lat: latitude,
        lon: longitude,
        api_key: this.apiKey
      };

      if (date) {
        params.date = date;
      }

      const response = await axios.get(url, { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching Earth assets:', error.message);
      throw new Error('Failed to fetch Earth assets');
    }
  }

  // Search NASA data using CMR (Common Metadata Repository)
  async searchNasaData(latitude, longitude, dataType = 'satellite_imagery', dateRange = null) {
    try {
      const boundingBox = this.createBoundingBox(latitude, longitude, 0.1); // 0.1 degree radius
      
      const params = {
        provider: 'NASA',
        bounding_box: boundingBox,
        page_size: 20
      };

      // Add data type specific parameters
      switch (dataType) {
        case 'satellite_imagery':
          params.concept_id = 'C1234567890-NASA_NSIDC_ECS'; // Example concept ID
          break;
        case 'weather_data':
          params.concept_id = 'C2345678901-NASA_NSIDC_ECS';
          break;
        case 'atmospheric_data':
          params.concept_id = 'C3456789012-NASA_NSIDC_ECS';
          break;
        case 'geological_data':
          params.concept_id = 'C4567890123-NASA_NSIDC_ECS';
          break;
        case 'ocean_data':
          params.concept_id = 'C5678901234-NASA_NSIDC_ECS';
          break;
        case 'climate_data':
          params.concept_id = 'C6789012345-NASA_NSIDC_ECS';
          break;
        default:
          params.concept_id = 'C1234567890-NASA_NSIDC_ECS';
      }

      if (dateRange) {
        params.temporal = `${dateRange.start},${dateRange.end}`;
      }

      const url = `${this.earthdataBaseURL}/search/collections.json`;
      const response = await axios.get(url, { params });
      
      return this.formatNasaSearchResults(response.data);
    } catch (error) {
      console.error('Error searching NASA data:', error.message);
      // Return mock data for development
      return this.getMockNasaData(dataType, latitude, longitude);
    }
  }

  // Get GIBS imagery for a specific location
  async getGibsImagery(latitude, longitude, layer = 'MODIS_Terra_CorrectedReflectance_TrueColor') {
    try {
      // GIBS typically requires tile coordinates and zoom level
      const tileCoords = this.latLonToTile(latitude, longitude, 6); // Zoom level 6
      
      const url = `${this.gibsBaseURL}/wmts/epsg4326/best/${layer}/default/2023-01-01/6/${tileCoords.y}/${tileCoords.x}.jpg`;
      
      // For now, return the URL structure
      return {
        type: 'imagery',
        source: 'GIBS',
        layer,
        coordinates: { latitude, longitude },
        tileCoords,
        imageUrl: url,
        metadata: {
          description: 'Global Imagery Browse Services satellite imagery',
          resolution: '250m',
          updateFrequency: 'Daily'
        }
      };
    } catch (error) {
      console.error('Error fetching GIBS imagery:', error.message);
      return this.getMockImageryData(latitude, longitude, layer);
    }
  }

  // Get comprehensive NASA data for a location
  async getLocationNasaData(latitude, longitude, dataTypes = ['satellite_imagery']) {
    try {
      const results = {
        coordinates: { latitude, longitude },
        timestamp: new Date().toISOString(),
        data: {}
      };

      // Fetch different types of data in parallel
      const promises = dataTypes.map(async (dataType) => {
        try {
          switch (dataType) {
            case 'satellite_imagery':
              const imagery = await this.getGibsImagery(latitude, longitude);
              return { type: dataType, data: imagery };
            
            case 'earth_imagery':
              const earthImg = await this.getEarthImagery(latitude, longitude);
              return { type: dataType, data: earthImg };
            
            case 'earth_assets':
              const assets = await this.getEarthAssets(latitude, longitude);
              return { type: dataType, data: assets };
            
            default:
              const searchResults = await this.searchNasaData(latitude, longitude, dataType);
              return { type: dataType, data: searchResults };
          }
        } catch (error) {
          console.error(`Error fetching ${dataType}:`, error.message);
          return { type: dataType, data: null, error: error.message };
        }
      });

      const dataResults = await Promise.all(promises);
      
      // Organize results by type
      dataResults.forEach(result => {
        results.data[result.type] = result.data;
      });

      return results;
    } catch (error) {
      console.error('Error getting location NASA data:', error.message);
      throw error;
    }
  }

  // Helper method to create bounding box
  createBoundingBox(latitude, longitude, radiusDegrees) {
    const latMin = latitude - radiusDegrees;
    const latMax = latitude + radiusDegrees;
    const lonMin = longitude - radiusDegrees;
    const lonMax = longitude + radiusDegrees;
    
    return `${lonMin},${latMin},${lonMax},${latMax}`;
  }

  // Helper method to convert lat/lon to tile coordinates
  latLonToTile(lat, lon, zoom) {
    const n = Math.pow(2, zoom);
    const x = Math.floor((lon + 180) / 360 * n);
    const y = Math.floor((1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * n);
    
    return { x, y };
  }

  // Format NASA search results
  formatNasaSearchResults(data) {
    if (!data || !data.feed || !data.feed.entry) {
      return { results: [], count: 0 };
    }

    const results = data.feed.entry.map(entry => ({
      id: entry.id,
      title: entry.title,
      summary: entry.summary,
      updated: entry.updated,
      links: entry.links,
      timeStart: entry.time_start,
      timeEnd: entry.time_end
    }));

    return {
      results,
      count: results.length,
      total: data.feed.total_results || results.length
    };
  }

  // Mock data for development/testing
  getMockNasaData(dataType, latitude, longitude) {
    const mockData = {
      satellite_imagery: {
        type: 'satellite_imagery',
        source: 'MODIS Terra',
        coordinates: { latitude, longitude },
        imageUrl: `https://api.nasa.gov/mock/imagery/${latitude}/${longitude}`,
        metadata: {
          resolution: '250m',
          date: new Date().toISOString(),
          cloudCover: Math.floor(Math.random() * 100),
          quality: 'High'
        }
      },
      weather_data: {
        type: 'weather_data',
        coordinates: { latitude, longitude },
        temperature: Math.floor(Math.random() * 40) - 10,
        humidity: Math.floor(Math.random() * 100),
        pressure: Math.floor(Math.random() * 200) + 900,
        windSpeed: Math.floor(Math.random() * 50),
        windDirection: Math.floor(Math.random() * 360)
      },
      atmospheric_data: {
        type: 'atmospheric_data',
        coordinates: { latitude, longitude },
        co2: Math.floor(Math.random() * 50) + 400,
        ozone: Math.floor(Math.random() * 100) + 200,
        aerosolIndex: Math.floor(Math.random() * 10),
        uvIndex: Math.floor(Math.random() * 15)
      },
      geological_data: {
        type: 'geological_data',
        coordinates: { latitude, longitude },
        elevation: Math.floor(Math.random() * 4000),
        terrain: ['mountain', 'valley', 'plain', 'plateau'][Math.floor(Math.random() * 4)],
        soilType: ['clay', 'sand', 'loam', 'rock'][Math.floor(Math.random() * 4)]
      },
      ocean_data: {
        type: 'ocean_data',
        coordinates: { latitude, longitude },
        seaSurfaceTemp: Math.floor(Math.random() * 30) + 5,
        salinity: Math.floor(Math.random() * 10) + 30,
        waveHeight: Math.floor(Math.random() * 5),
        currentSpeed: Math.floor(Math.random() * 3)
      },
      climate_data: {
        type: 'climate_data',
        coordinates: { latitude, longitude },
        averageTemp: Math.floor(Math.random() * 40) - 10,
        precipitation: Math.floor(Math.random() * 200),
        humidity: Math.floor(Math.random() * 100),
        season: ['spring', 'summer', 'autumn', 'winter'][Math.floor(Math.random() * 4)]
      }
    };

    return mockData[dataType] || mockData.satellite_imagery;
  }

  getMockImageryData(latitude, longitude, layer) {
    return {
      type: 'imagery',
      source: 'GIBS (Mock)',
      layer,
      coordinates: { latitude, longitude },
      imageUrl: `https://api.nasa.gov/mock/gibs/${layer}/${latitude}/${longitude}.jpg`,
      metadata: {
        description: 'Mock satellite imagery data',
        resolution: '250m',
        updateFrequency: 'Daily',
        cloudCover: Math.floor(Math.random() * 100)
      }
    };
  }

  // Get NASA news/articles
  async getNasaNews() {
    try {
      const url = `${this.baseURL}/DONKI/notifications`;
      const params = { api_key: this.apiKey };

      const response = await axios.get(url, { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching NASA news:', error.message);
      return {
        notifications: [],
        message: 'Unable to fetch NASA notifications'
      };
    }
  }

  // Get NASA events (near-Earth objects, solar flares, etc.)
  async getNasaEvents(startDate, endDate) {
    try {
      const url = `${this.baseURL}/DONKI/notifications`;
      const params = {
        api_key: this.apiKey,
        startDate,
        endDate
      };

      const response = await axios.get(url, { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching NASA events:', error.message);
      return {
        events: [],
        message: 'Unable to fetch NASA events'
      };
    }
  }
}

module.exports = new NasaService();
