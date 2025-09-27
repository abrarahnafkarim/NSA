const Location = require('../models/Location');
const User = require('../models/User');
const axios = require('axios');

class LocationService {
  // Determine game environment based on coordinates
  static async determineEnvironment(latitude, longitude) {
    try {
      // This is a simplified version - in production you'd use more sophisticated geospatial analysis
      // You could integrate with services like Google Maps API or OpenStreetMap
      
      const environments = {
        polar: { minLat: 60, maxLat: 90, minLon: -180, maxLon: 180 },
        desert: { minLat: 15, maxLat: 35, minLon: -180, maxLon: 180 },
        mountain: { minLat: 20, maxLat: 50, minLon: -180, maxLon: 180 },
        forest: { minLat: 30, maxLat: 60, minLon: -180, maxLon: 180 },
        water: { minLat: -90, maxLat: 90, minLon: -180, maxLon: 180 } // Simplified
      };

      // Check for polar regions
      if (Math.abs(latitude) > 60) {
        return 'polar';
      }

      // Check for desert regions (simplified)
      if (latitude > 15 && latitude < 35) {
        return 'desert';
      }

      // Check for mountain regions (simplified)
      if (latitude > 20 && latitude < 50) {
        return 'mountain';
      }

      // Check for forest regions (simplified)
      if (latitude > 30 && latitude < 60) {
        return 'forest';
      }

      // Default to land
      return 'land';
    } catch (error) {
      console.error('Error determining environment:', error);
      return 'land';
    }
  }

  // Determine game level based on location
  static determineGameLevel(latitude, longitude) {
    // Simple logic - in production you'd use more sophisticated analysis
    const absLat = Math.abs(latitude);
    
    if (absLat > 80) {
      return 'deep_space'; // Polar regions = deep space
    } else if (absLat > 60) {
      return 'space'; // High latitude = space
    } else {
      return 'earth'; // Normal earth regions
    }
  }

  // Determine available NASA data types
  static determineAvailableDataTypes(latitude, longitude, environment) {
    const dataTypes = [];

    // Base data types available everywhere
    dataTypes.push('satellite_imagery');

    // Environment-specific data
    switch (environment) {
      case 'water':
        dataTypes.push('ocean_data');
        dataTypes.push('weather_data');
        break;
      case 'mountain':
        dataTypes.push('geological_data');
        dataTypes.push('atmospheric_data');
        break;
      case 'desert':
        dataTypes.push('climate_data');
        dataTypes.push('atmospheric_data');
        break;
      case 'polar':
        dataTypes.push('climate_data');
        dataTypes.push('atmospheric_data');
        break;
      default:
        dataTypes.push('weather_data');
        dataTypes.push('atmospheric_data');
    }

    // Time-based data
    const hour = new Date().getHours();
    if (hour >= 6 && hour <= 18) {
      dataTypes.push('solar_data');
    } else {
      dataTypes.push('moon_data');
    }

    return dataTypes;
  }

  // Calculate experience reward based on location difficulty
  static calculateExperienceReward(environment, level, dataTypes) {
    let baseReward = 10;

    // Environment multiplier
    const environmentMultipliers = {
      land: 1,
      water: 1.2,
      mountain: 1.5,
      desert: 1.3,
      forest: 1.1,
      urban: 1.1,
      polar: 2.0
    };

    // Level multiplier
    const levelMultipliers = {
      earth: 1,
      space: 1.5,
      deep_space: 2.0
    };

    baseReward *= environmentMultipliers[environment] || 1;
    baseReward *= levelMultipliers[level] || 1;
    baseReward *= Math.min(dataTypes.length / 2, 2); // More data types = more reward

    return Math.round(baseReward);
  }

  // Get reverse geocoding information
  static async getAddressFromCoordinates(latitude, longitude) {
    try {
      // In production, you'd use a real geocoding service like Google Maps or OpenStreetMap
      // For now, we'll return a placeholder
      return {
        formatted: `Location at ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`,
        city: 'Unknown',
        country: 'Unknown'
      };
    } catch (error) {
      console.error('Error getting address:', error);
      return {
        formatted: `Location at ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`,
        city: 'Unknown',
        country: 'Unknown'
      };
    }
  }

  // Create a new location record
  static async createLocation(userId, locationData, sessionId) {
    try {
      const { latitude, longitude, accuracy, altitude, altitudeAccuracy, heading, speed } = locationData;

      // Determine game characteristics
      const environment = await this.determineEnvironment(latitude, longitude);
      const level = this.determineGameLevel(latitude, longitude);
      const dataTypes = this.determineAvailableDataTypes(latitude, longitude, environment);
      const experienceReward = this.calculateExperienceReward(environment, level, dataTypes);
      const address = await this.getAddressFromCoordinates(latitude, longitude);

      // Calculate difficulty based on environment and level
      let difficulty = 1;
      if (level === 'space') difficulty = 3;
      else if (level === 'deep_space') difficulty = 5;
      if (environment === 'polar' || environment === 'mountain') difficulty += 2;

      const location = new Location({
        userId,
        coordinates: {
          latitude,
          longitude,
          accuracy,
          altitude,
          altitudeAccuracy,
          heading,
          speed
        },
        address,
        gameData: {
          level,
          environment,
          nasaDataAvailable: dataTypes.length > 0,
          dataTypes,
          difficulty: Math.min(difficulty, 10),
          experienceReward
        },
        sessionId
      });

      await location.save();

      // Update user's current location
      await User.findByIdAndUpdate(userId, {
        currentLocation: {
          latitude,
          longitude,
          timestamp: new Date(),
          accuracy
        }
      });

      return location;
    } catch (error) {
      console.error('Error creating location:', error);
      throw error;
    }
  }

  // Get nearby locations for the user
  static async getNearbyLocations(userId, latitude, longitude, radiusKm = 10) {
    try {
      // Convert radius to degrees (approximate)
      const radiusDegrees = radiusKm / 111; // 1 degree ≈ 111 km

      const locations = await Location.find({
        userId,
        'coordinates.latitude': {
          $gte: latitude - radiusDegrees,
          $lte: latitude + radiusDegrees
        },
        'coordinates.longitude': {
          $gte: longitude - radiusDegrees,
          $lte: longitude + radiusDegrees
        },
        isActive: true
      }).sort({ timestamp: -1 }).limit(50);

      return locations;
    } catch (error) {
      console.error('Error getting nearby locations:', error);
      throw error;
    }
  }

  // Update user stats based on location visit
  static async updateUserStats(userId, location) {
    try {
      const user = await User.findById(userId);
      if (!user) return;

      // Update stats
      user.gameStats.totalLocationsVisited += 1;
      user.gameStats.nasaDataCollected += location.gameData.dataTypes.length;
      user.gameStats.experience += location.gameData.experienceReward;

      // Check for level up
      const newLevel = Math.floor(user.gameStats.experience / 1000) + 1;
      if (newLevel > user.gameStats.level) {
        user.gameStats.level = newLevel;
        // Add achievement for leveling up
        if (!user.gameStats.achievements.includes('explorer')) {
          user.gameStats.achievements.push('explorer');
        }
      }

      // Check for achievements
      if (user.gameStats.totalLocationsVisited === 1 && !user.gameStats.achievements.includes('first_location')) {
        user.gameStats.achievements.push('first_location');
      }

      if (user.gameStats.nasaDataCollected >= 50 && !user.gameStats.achievements.includes('data_collector')) {
        user.gameStats.achievements.push('data_collector');
      }

      if (user.gameStats.totalLocationsVisited >= 100 && !user.gameStats.achievements.includes('location_master')) {
        user.gameStats.achievements.push('location_master');
      }

      await user.save();
    } catch (error) {
      console.error('Error updating user stats:', error);
      throw error;
    }
  }
}

module.exports = LocationService;
