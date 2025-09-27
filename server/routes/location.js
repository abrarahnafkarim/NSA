const express = require('express');
const { auth } = require('../middleware/auth');
const Location = require('../models/Location');
const LocationService = require('../services/locationService');

const router = express.Router();

// @route   POST /api/location/update
// @desc    Update user's current location
// @access  Private
router.post('/update', auth, async (req, res) => {
  try {
    const {
      latitude,
      longitude,
      accuracy,
      altitude,
      altitudeAccuracy,
      heading,
      speed
    } = req.body;

    // Validate coordinates
    if (!latitude || !longitude) {
      return res.status(400).json({ message: 'Latitude and longitude are required' });
    }

    if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
      return res.status(400).json({ message: 'Invalid coordinates' });
    }

    // Generate session ID if not provided
    const sessionId = req.body.sessionId || `session_${req.user._id}_${Date.now()}`;

    // Create location record
    const location = await LocationService.createLocation(
      req.user._id,
      {
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        accuracy: accuracy ? parseFloat(accuracy) : undefined,
        altitude: altitude ? parseFloat(altitude) : undefined,
        altitudeAccuracy: altitudeAccuracy ? parseFloat(altitudeAccuracy) : undefined,
        heading: heading ? parseFloat(heading) : undefined,
        speed: speed ? parseFloat(speed) : undefined
      },
      sessionId
    );

    // Update user stats
    await LocationService.updateUserStats(req.user._id, location);

    res.json({
      message: 'Location updated successfully',
      location: {
        id: location._id,
        coordinates: location.coordinates,
        address: location.address,
        gameData: location.gameData,
        timestamp: location.timestamp
      }
    });
  } catch (error) {
    console.error('Location update error:', error);
    res.status(500).json({ message: 'Server error during location update' });
  }
});

// @route   GET /api/location/current
// @desc    Get user's current location
// @access  Private
router.get('/current', auth, async (req, res) => {
  try {
    const user = await User.findById(req.user._id);
    
    if (!user.currentLocation) {
      return res.status(404).json({ message: 'No current location found' });
    }

    res.json({
      currentLocation: user.currentLocation
    });
  } catch (error) {
    console.error('Get current location error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

// @route   GET /api/location/history
// @desc    Get user's location history
// @access  Private
router.get('/history', auth, async (req, res) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 20;
    const skip = (page - 1) * limit;

    const locations = await Location.find({ userId: req.user._id })
      .sort({ timestamp: -1 })
      .skip(skip)
      .limit(limit)
      .select('-metadata');

    const total = await Location.countDocuments({ userId: req.user._id });

    res.json({
      locations,
      pagination: {
        current: page,
        pages: Math.ceil(total / limit),
        total,
        hasNext: page < Math.ceil(total / limit),
        hasPrev: page > 1
      }
    });
  } catch (error) {
    console.error('Get location history error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

// @route   GET /api/location/nearby
// @desc    Get nearby locations
// @access  Private
router.get('/nearby', auth, async (req, res) => {
  try {
    const { latitude, longitude, radius } = req.query;

    if (!latitude || !longitude) {
      return res.status(400).json({ message: 'Latitude and longitude are required' });
    }

    const radiusKm = radius ? parseFloat(radius) : 10;
    const locations = await LocationService.getNearbyLocations(
      req.user._id,
      parseFloat(latitude),
      parseFloat(longitude),
      radiusKm
    );

    res.json({
      locations: locations.map(loc => ({
        id: loc._id,
        coordinates: loc.coordinates,
        address: loc.address,
        gameData: loc.gameData,
        timestamp: loc.timestamp
      })),
      count: locations.length,
      radius: radiusKm
    });
  } catch (error) {
    console.error('Get nearby locations error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

// @route   GET /api/location/stats
// @desc    Get location statistics for user
// @access  Private
router.get('/stats', auth, async (req, res) => {
  try {
    const stats = await Location.aggregate([
      { $match: { userId: req.user._id } },
      {
        $group: {
          _id: null,
          totalLocations: { $sum: 1 },
          uniqueEnvironments: { $addToSet: '$gameData.environment' },
          uniqueLevels: { $addToSet: '$gameData.level' },
          totalDataTypes: { $sum: { $size: '$gameData.dataTypes' } },
          averageDifficulty: { $avg: '$gameData.difficulty' },
          totalExperience: { $sum: '$gameData.experienceReward' },
          firstLocation: { $min: '$timestamp' },
          lastLocation: { $max: '$timestamp' }
        }
      }
    ]);

    const locationStats = stats[0] || {
      totalLocations: 0,
      uniqueEnvironments: [],
      uniqueLevels: [],
      totalDataTypes: 0,
      averageDifficulty: 0,
      totalExperience: 0,
      firstLocation: null,
      lastLocation: null
    };

    res.json({
      stats: {
        ...locationStats,
        environmentCount: locationStats.uniqueEnvironments.length,
        levelCount: locationStats.uniqueLevels.length
      }
    });
  } catch (error) {
    console.error('Get location stats error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

// @route   DELETE /api/location/:id
// @desc    Delete a specific location record
// @access  Private
router.delete('/:id', auth, async (req, res) => {
  try {
    const location = await Location.findOne({
      _id: req.params.id,
      userId: req.user._id
    });

    if (!location) {
      return res.status(404).json({ message: 'Location not found' });
    }

    await Location.findByIdAndUpdate(req.params.id, { isActive: false });

    res.json({ message: 'Location deleted successfully' });
  } catch (error) {
    console.error('Delete location error:', error);
    res.status(500).json({ message: 'Server error' });
  }
});

module.exports = router;
