// lsm6dsl.h
#ifndef LSM6DSL_H
#define LSM6DSL_H

#include <cstdint>
#define LSM6DSL_ADDR  (0x6A << 1)
#define WHO_AM_I      0x0F
#define CTRL1_XL      0x10
#define OUTX_L_XL     0x28
#define OUTX_H_XL     0x29

void    write_register(uint8_t reg, uint8_t val);
uint8_t read_register (uint8_t reg);
int16_t read_16bit    (uint8_t lo_reg, uint8_t hi_reg);

#endif
