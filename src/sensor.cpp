// src/sensor.cpp
#include "sensor.h"
#include "mbed.h"

static I2C i2c(PB_11, PB_10);
#define LSM6DSL_ADDR (0x6A << 1)

static uint8_t read_register(uint8_t reg) {
    char cmd = reg, data;
    i2c.write(LSM6DSL_ADDR, &cmd, 1, true);
    i2c.read (LSM6DSL_ADDR, &data, 1);
    return (uint8_t)data;
}

static void write_register(uint8_t reg, uint8_t val) {
    char buf[2] = { (char)reg, (char)val };
    i2c.write(LSM6DSL_ADDR, buf, 2);
}

uint8_t imu_init() {
    uint8_t who = read_register(0x0F);
    write_register(0x10, 0x40);  // accel 104 Hz, ±2 g
    write_register(0x11, 0x40);  // gyro  104 Hz, ±250 dps
    return who;
}

float readAccelMagnitude() {
    int16_t xl = (int16_t)(read_register(0x28) | (read_register(0x29) << 8));
    int16_t yl = (int16_t)(read_register(0x2A) | (read_register(0x2B) << 8));
    int16_t zl = (int16_t)(read_register(0x2C) | (read_register(0x2D) << 8));
    const float scale = 0.000061f; // 2 g scale factor
    float xg = xl * scale, yg = yl * scale, zg = zl * scale;
    return sqrtf(xg*xg + yg*yg + zg*zg);
}
