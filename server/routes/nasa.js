const express = require('express');
const { auth, optionalAuth } = require('../middleware/auth');
const NasaService = require('../services/nasaService');

const router = express.Router();

// @route   GET /api/nasa/apod
// @desc    Get NASA Astronomy Picture of the Day
// @access  Public
router.get('/apod', optionalAuth, async (req, res) => {
  try {
    const { date } = req.query;
    const apod = await NasaService.getAPOD(date);
    
    res.json({
      success: true,
      data: apod
    });
  } catch (error) {
    console.error('APOD fetch error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch APOD data',
      error: error.message
    });
  }
});

// @route   GET /api/nasa/earth-imagery
// @desc    Get NASA Earth imagery for coordinates
// @access  Private
router.get('/earth-imagery', auth, async (req, res) => {
  try {
    const { latitude, longitude, date } = req.query;

    if (!latitude || !longitude) {
      return res.status(400).json({
        success: false,
        message: 'Latitude and longitude are required'
      });
    }

    const imagery = await NasaService.getEarthImagery(
      parseFloat(latitude),
      parseFloat(longitude),
      date
    );

    res.json({
      success: true,
      data: imagery
    });
  } catch (error) {
    console.error('Earth imagery fetch error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch Earth imagery',
      error: error.message
    });
  }
});

// @route   GET /api/nasa/earth-assets
// @desc    Get NASA Earth assets for coordinates
// @access  Private
router.get('/earth-assets', auth, async (req, res) => {
  try {
    const { latitude, longitude, date } = req.query;

    if (!latitude || !longitude) {
      return res.status(400).json({
        success: false,
        message: 'Latitude and longitude are required'
      });
    }

    const assets = await NasaService.getEarthAssets(
      parseFloat(latitude),
      parseFloat(longitude),
      date
    );

    res.json({
      success: true,
      data: assets
    });
  } catch (error) {
    console.error('Earth assets fetch error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch Earth assets',
      error: error.message
    });
  }
});

// @route   POST /api/nasa/location-data
// @desc    Get comprehensive NASA data for user's location
// @access  Private
router.post('/location-data', auth, async (req, res) => {
  try {
    const { latitude, longitude, dataTypes } = req.body;

    if (!latitude || !longitude) {
      return res.status(400).json({
        success: false,
        message: 'Latitude and longitude are required'
      });
    }

    // Default data types if none provided
    const types = dataTypes || [
      'satellite_imagery',
      'weather_data',
      'atmospheric_data'
    ];

    const nasaData = await NasaService.getLocationNasaData(
      parseFloat(latitude),
      parseFloat(longitude),
      types
    );

    res.json({
      success: true,
      data: nasaData
    });
  } catch (error) {
    console.error('Location NASA data fetch error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch NASA data for location',
      error: error.message
    });
  }
});

// @route   GET /api/nasa/search
// @desc    Search NASA data collections
// @access  Private
router.get('/search', auth, async (req, res) => {
  try {
    const { latitude, longitude, dataType, startDate, endDate } = req.query;

    if (!latitude || !longitude) {
      return res.status(400).json({
        success: false,
        message: 'Latitude and longitude are required'
      });
    }

    const dateRange = startDate && endDate ? { start: startDate, end: endDate } : null;
    
    const searchResults = await NasaService.searchNasaData(
      parseFloat(latitude),
      parseFloat(longitude),
      dataType,
      dateRange
    );

    res.json({
      success: true,
      data: searchResults
    });
  } catch (error) {
    console.error('NASA search error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to search NASA data',
      error: error.message
    });
  }
});

// @route   GET /api/nasa/gibs-imagery
// @desc    Get GIBS imagery for coordinates
// @access  Private
router.get('/gibs-imagery', auth, async (req, res) => {
  try {
    const { latitude, longitude, layer } = req.query;

    if (!latitude || !longitude) {
      return res.status(400).json({
        success: false,
        message: 'Latitude and longitude are required'
      });
    }

    const imagery = await NasaService.getGibsImagery(
      parseFloat(latitude),
      parseFloat(longitude),
      layer
    );

    res.json({
      success: true,
      data: imagery
    });
  } catch (error) {
    console.error('GIBS imagery fetch error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch GIBS imagery',
      error: error.message
    });
  }
});

// @route   GET /api/nasa/news
// @desc    Get NASA news and notifications
// @access  Public
router.get('/news', optionalAuth, async (req, res) => {
  try {
    const news = await NasaService.getNasaNews();
    
    res.json({
      success: true,
      data: news
    });
  } catch (error) {
    console.error('NASA news fetch error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch NASA news',
      error: error.message
    });
  }
});

// @route   GET /api/nasa/events
// @desc    Get NASA events (space weather, near-Earth objects, etc.)
// @access  Public
router.get('/events', optionalAuth, async (req, res) => {
  try {
    const { startDate, endDate } = req.query;
    
    // Default to last 7 days if no dates provided
    const end = endDate || new Date().toISOString().split('T')[0];
    const start = startDate || new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    const events = await NasaService.getNasaEvents(start, end);

    res.json({
      success: true,
      data: events
    });
  } catch (error) {
    console.error('NASA events fetch error:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch NASA events',
      error: error.message
    });
  }
});

// @route   GET /api/nasa/data-types
// @desc    Get available NASA data types
// @access  Public
router.get('/data-types', (req, res) => {
  const dataTypes = [
    {
      id: 'satellite_imagery',
      name: 'Satellite Imagery',
      description: 'High-resolution satellite images of Earth',
      category: 'Imagery',
      updateFrequency: 'Daily'
    },
    {
      id: 'weather_data',
      name: 'Weather Data',
      description: 'Atmospheric and weather information',
      category: 'Atmosphere',
      updateFrequency: 'Hourly'
    },
    {
      id: 'atmospheric_data',
      name: 'Atmospheric Data',
      description: 'Air quality, ozone, and atmospheric composition',
      category: 'Atmosphere',
      updateFrequency: 'Daily'
    },
    {
      id: 'geological_data',
      name: 'Geological Data',
      description: 'Earth surface and geological information',
      category: 'Geology',
      updateFrequency: 'Monthly'
    },
    {
      id: 'ocean_data',
      name: 'Ocean Data',
      description: 'Sea surface temperature, salinity, and currents',
      category: 'Ocean',
      updateFrequency: 'Daily'
    },
    {
      id: 'climate_data',
      name: 'Climate Data',
      description: 'Long-term climate and environmental data',
      category: 'Climate',
      updateFrequency: 'Monthly'
    },
    {
      id: 'asteroid_data',
      name: 'Asteroid Data',
      description: 'Near-Earth object tracking and information',
      category: 'Space',
      updateFrequency: 'Daily'
    },
    {
      id: 'solar_data',
      name: 'Solar Data',
      description: 'Solar activity, flares, and space weather',
      category: 'Space',
      updateFrequency: 'Real-time'
    },
    {
      id: 'moon_data',
      name: 'Moon Data',
      description: 'Lunar phases, position, and surface data',
      category: 'Space',
      updateFrequency: 'Daily'
    }
  ];

  res.json({
    success: true,
    data: {
      dataTypes,
      total: dataTypes.length
    }
  });
});

module.exports = router;
