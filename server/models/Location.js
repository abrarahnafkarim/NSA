const mongoose = require('mongoose');

const locationSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  coordinates: {
    latitude: {
      type: Number,
      required: true,
      min: -90,
      max: 90
    },
    longitude: {
      type: Number,
      required: true,
      min: -180,
      max: 180
    },
    accuracy: {
      type: Number,
      default: 0
    },
    altitude: Number,
    altitudeAccuracy: Number,
    heading: Number,
    speed: Number
  },
  address: {
    street: String,
    city: String,
    state: String,
    country: String,
    postalCode: String,
    formatted: String
  },
  gameData: {
    level: {
      type: String,
      enum: ['earth', 'space', 'deep_space'],
      default: 'earth'
    },
    environment: {
      type: String,
      enum: ['land', 'water', 'mountain', 'desert', 'forest', 'urban', 'polar'],
      default: 'land'
    },
    nasaDataAvailable: {
      type: Boolean,
      default: false
    },
    dataTypes: [{
      type: String,
      enum: [
        'satellite_imagery',
        'weather_data',
        'atmospheric_data',
        'geological_data',
        'ocean_data',
        'climate_data',
        'asteroid_data',
        'solar_data',
        'moon_data'
      ]
    }],
    difficulty: {
      type: Number,
      min: 1,
      max: 10,
      default: 1
    },
    experienceReward: {
      type: Number,
      default: 10
    }
  },
  timestamp: {
    type: Date,
    default: Date.now
  },
  sessionId: {
    type: String,
    required: true
  },
  isActive: {
    type: Boolean,
    default: true
  },
  metadata: {
    deviceInfo: {
      type: String,
      userAgent: String,
      platform: String
    },
    networkInfo: {
      connectionType: String,
      effectiveType: String
    }
  }
}, {
  timestamps: true
});

// Index for efficient queries
locationSchema.index({ userId: 1, timestamp: -1 });
locationSchema.index({ 'coordinates.latitude': 1, 'coordinates.longitude': 1 });
locationSchema.index({ sessionId: 1 });
locationSchema.index({ timestamp: -1 });

// Virtual for distance calculation (if needed)
locationSchema.virtual('coordinateString').get(function() {
  return `${this.coordinates.latitude},${this.coordinates.longitude}`;
});

// Method to calculate distance between two locations
locationSchema.methods.calculateDistance = function(otherLocation) {
  const R = 6371e3; // Earth's radius in meters
  const φ1 = this.coordinates.latitude * Math.PI / 180;
  const φ2 = otherLocation.coordinates.latitude * Math.PI / 180;
  const Δφ = (otherLocation.coordinates.latitude - this.coordinates.latitude) * Math.PI / 180;
  const Δλ = (otherLocation.coordinates.longitude - this.coordinates.longitude) * Math.PI / 180;

  const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
          Math.cos(φ1) * Math.cos(φ2) *
          Math.sin(Δλ/2) * Math.sin(Δλ/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

  return R * c; // Distance in meters
};

module.exports = mongoose.model('Location', locationSchema);
