const express = require('express');
const { auth } = require('../middleware/auth');
const User = require('../models/User');
const Location = require('../models/Location');
const NasaService = require('../services/nasaService');
const LocationService = require('../services/locationService');

const router = express.Router();

// @route   POST /api/game/start-session
// @desc    Start a new game session
// @access  Private
router.post('/start-session', auth, async (req, res) => {
  try {
    const { latitude, longitude } = req.body;

    if (!latitude || !longitude) {
      return res.status(400).json({
        success: false,
        message: 'Location coordinates are required to start a game session'
      });
    }

    // Generate session ID
    const sessionId = `session_${req.user._id}_${Date.now()}`;

    // Create initial location record
    const location = await LocationService.createLocation(
      req.user._id,
      {
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        accuracy: 10 // Default accuracy
      },
      sessionId
    );

    // Get NASA data for this location
    const nasaData = await NasaService.getLocationNasaData(
      parseFloat(latitude),
      parseFloat(longitude),
      location.gameData.dataTypes
    );

    // Calculate session rewards
    const sessionRewards = {
      experience: location.gameData.experienceReward,
      dataPoints: location.gameData.dataTypes.length,
      level: location.gameData.level,
      environment: location.gameData.environment,
      difficulty: location.gameData.difficulty
    };

    res.json({
      success: true,
      session: {
        sessionId,
        location: {
          id: location._id,
          coordinates: location.coordinates,
          address: location.address,
          gameData: location.gameData
        },
        nasaData,
        rewards: sessionRewards,
        startTime: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('Game session start error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to start game session',
      error: error.message
    });
  }
});

// @route   POST /api/game/collect-data
// @desc    Collect NASA data at current location
// @access  Private
router.post('/collect-data', auth, async (req, res) => {
  try {
    const { latitude, longitude, dataType, sessionId } = req.body;

    if (!latitude || !longitude || !dataType) {
      return res.status(400).json({
        success: false,
        message: 'Location coordinates and data type are required'
      });
    }

    // Find or create location record
    let location = await Location.findOne({
      userId: req.user._id,
      sessionId: sessionId || `session_${req.user._id}_${Date.now()}`
    });

    if (!location) {
      location = await LocationService.createLocation(
        req.user._id,
        {
          latitude: parseFloat(latitude),
          longitude: parseFloat(longitude),
          accuracy: 10
        },
        sessionId || `session_${req.user._id}_${Date.now()}`
      );
    }

    // Verify data type is available at this location
    if (!location.gameData.dataTypes.includes(dataType)) {
      return res.status(400).json({
        success: false,
        message: `Data type '${dataType}' is not available at this location`,
        availableTypes: location.gameData.dataTypes
      });
    }

    // Collect the data
    const collectedData = await NasaService.getLocationNasaData(
      parseFloat(latitude),
      parseFloat(longitude),
      [dataType]
    );

    // Update user stats
    await LocationService.updateUserStats(req.user._id, location);

    // Check for achievements
    const user = await User.findById(req.user._id);
    const newAchievements = [];

    if (user.gameStats.nasaDataCollected >= 10 && !user.gameStats.achievements.includes('data_collector')) {
      user.gameStats.achievements.push('data_collector');
      newAchievements.push('data_collector');
    }

    if (user.gameStats.totalLocationsVisited >= 50 && !user.gameStats.achievements.includes('nasa_fan')) {
      user.gameStats.achievements.push('nasa_fan');
      newAchievements.push('nasa_fan');
    }

    await user.save();

    res.json({
      success: true,
      collectedData: {
        type: dataType,
        data: collectedData.data[dataType],
        location: {
          coordinates: location.coordinates,
          environment: location.gameData.environment,
          level: location.gameData.level
        },
        rewards: {
          experience: location.gameData.experienceReward,
          level: location.gameData.level
        },
        newAchievements,
        timestamp: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('Data collection error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to collect NASA data',
      error: error.message
    });
  }
});

// @route   GET /api/game/stats
// @desc    Get user's game statistics
// @access  Private
router.get('/stats', auth, async (req, res) => {
  try {
    const user = await User.findById(req.user._id);
    
    // Get additional stats from location data
    const locationStats = await Location.aggregate([
      { $match: { userId: req.user._id } },
      {
        $group: {
          _id: null,
          totalLocations: { $sum: 1 },
          uniqueEnvironments: { $addToSet: '$gameData.environment' },
          uniqueLevels: { $addToSet: '$gameData.level' },
          totalDataCollected: { $sum: { $size: '$gameData.dataTypes' } },
          averageDifficulty: { $avg: '$gameData.difficulty' },
          totalExperience: { $sum: '$gameData.experienceReward' }
        }
      }
    ]);

    const stats = locationStats[0] || {};

    res.json({
      success: true,
      stats: {
        user: {
          level: user.gameStats.level,
          experience: user.gameStats.experience,
          totalLocationsVisited: user.gameStats.totalLocationsVisited,
          nasaDataCollected: user.gameStats.nasaDataCollected,
          achievements: user.gameStats.achievements
        },
        locations: {
          total: stats.totalLocations || 0,
          environments: stats.uniqueEnvironments || [],
          levels: stats.uniqueLevels || [],
          dataCollected: stats.totalDataCollected || 0,
          averageDifficulty: Math.round((stats.averageDifficulty || 0) * 10) / 10,
          totalExperience: stats.totalExperience || 0
        },
        currentLocation: user.currentLocation
      }
    });
  } catch (error) {
    console.error('Game stats error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch game statistics',
      error: error.message
    });
  }
});

// @route   GET /api/game/achievements
// @desc    Get all available achievements and user progress
// @access  Private
router.get('/achievements', auth, async (req, res) => {
  try {
    const user = await User.findById(req.user._id);
    
    const allAchievements = [
      {
        id: 'first_location',
        name: 'First Steps',
        description: 'Visit your first location',
        icon: '🌍',
        requirement: 1,
        progress: Math.min(user.gameStats.totalLocationsVisited, 1),
        unlocked: user.gameStats.achievements.includes('first_location')
      },
      {
        id: 'data_collector',
        name: 'Data Collector',
        description: 'Collect NASA data from 10 different locations',
        icon: '📊',
        requirement: 10,
        progress: Math.min(user.gameStats.nasaDataCollected, 10),
        unlocked: user.gameStats.achievements.includes('data_collector')
      },
      {
        id: 'explorer',
        name: 'Explorer',
        description: 'Reach level 5',
        icon: '🚀',
        requirement: 5,
        progress: Math.min(user.gameStats.level, 5),
        unlocked: user.gameStats.achievements.includes('explorer')
      },
      {
        id: 'nasa_fan',
        name: 'NASA Fan',
        description: 'Visit 50 different locations',
        icon: '🛰️',
        requirement: 50,
        progress: Math.min(user.gameStats.totalLocationsVisited, 50),
        unlocked: user.gameStats.achievements.includes('nasa_fan')
      },
      {
        id: 'location_master',
        name: 'Location Master',
        description: 'Visit 100 different locations',
        icon: '🏆',
        requirement: 100,
        progress: Math.min(user.gameStats.totalLocationsVisited, 100),
        unlocked: user.gameStats.achievements.includes('location_master')
      },
      {
        id: 'space_explorer',
        name: 'Space Explorer',
        description: 'Collect data from space-level locations',
        icon: '🌌',
        requirement: 5,
        progress: Math.min(
          user.gameStats.achievements.includes('space_explorer') ? 5 : 0, 
          5
        ),
        unlocked: user.gameStats.achievements.includes('space_explorer')
      }
    ];

    const unlockedCount = allAchievements.filter(a => a.unlocked).length;

    res.json({
      success: true,
      achievements: {
        all: allAchievements,
        unlocked: unlockedCount,
        total: allAchievements.length,
        completionPercentage: Math.round((unlockedCount / allAchievements.length) * 100)
      }
    });
  } catch (error) {
    console.error('Achievements error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch achievements',
      error: error.message
    });
  }
});

// @route   GET /api/game/leaderboard
// @desc    Get game leaderboard
// @access  Public (with optional auth)
router.get('/leaderboard', async (req, res) => {
  try {
    const { type = 'experience', limit = 10 } = req.query;

    let sortField = 'gameStats.experience';
    switch (type) {
      case 'locations':
        sortField = 'gameStats.totalLocationsVisited';
        break;
      case 'data':
        sortField = 'gameStats.nasaDataCollected';
        break;
      case 'level':
        sortField = 'gameStats.level';
        break;
      default:
        sortField = 'gameStats.experience';
    }

    const leaderboard = await User.find({ isActive: true })
      .sort({ [sortField]: -1 })
      .limit(parseInt(limit))
      .select('username profile.firstName gameStats.level gameStats.experience gameStats.totalLocationsVisited gameStats.nasaDataCollected gameStats.achievements');

    res.json({
      success: true,
      leaderboard: {
        type,
        rankings: leaderboard.map((user, index) => ({
          rank: index + 1,
          username: user.username,
          firstName: user.profile.firstName,
          level: user.gameStats.level,
          experience: user.gameStats.experience,
          locationsVisited: user.gameStats.totalLocationsVisited,
          dataCollected: user.gameStats.nasaDataCollected,
          achievements: user.gameStats.achievements.length
        }))
      }
    });
  } catch (error) {
    console.error('Leaderboard error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch leaderboard',
      error: error.message
    });
  }
});

// @route   POST /api/game/complete-mission
// @desc    Complete a game mission/objective
// @access  Private
router.post('/complete-mission', auth, async (req, res) => {
  try {
    const { missionType, locationId, data } = req.body;

    if (!missionType) {
      return res.status(400).json({
        success: false,
        message: 'Mission type is required'
      });
    }

    const user = await User.findById(req.user._id);
    let missionReward = 0;
    let newAchievements = [];

    switch (missionType) {
      case 'collect_all_data_types':
        missionReward = 50;
        if (!user.gameStats.achievements.includes('data_collector')) {
          user.gameStats.achievements.push('data_collector');
          newAchievements.push('data_collector');
        }
        break;
      
      case 'visit_new_environment':
        missionReward = 25;
        break;
      
      case 'collect_space_data':
        missionReward = 100;
        if (!user.gameStats.achievements.includes('space_explorer')) {
          user.gameStats.achievements.push('space_explorer');
          newAchievements.push('space_explorer');
        }
        break;
      
      default:
        missionReward = 10;
    }

    // Update user stats
    user.gameStats.experience += missionReward;
    
    // Check for level up
    const newLevel = Math.floor(user.gameStats.experience / 1000) + 1;
    if (newLevel > user.gameStats.level) {
      user.gameStats.level = newLevel;
      if (!user.gameStats.achievements.includes('explorer')) {
        user.gameStats.achievements.push('explorer');
        newAchievements.push('explorer');
      }
    }

    await user.save();

    res.json({
      success: true,
      mission: {
        type: missionType,
        completed: true,
        reward: missionReward,
        newLevel: user.gameStats.level,
        newAchievements,
        timestamp: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('Mission completion error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to complete mission',
      error: error.message
    });
  }
});

module.exports = router;
