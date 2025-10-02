// src/sensor.h
#pragma once
#include <cstdint>

// Initialize the IMU, return the WHO_AM_I register value
uint8_t imu_init();

// Read accel-magnitude in g
float readAccelMagnitude();
