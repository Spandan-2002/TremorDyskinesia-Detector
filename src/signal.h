#pragma once
#include <cstdint>

void signal_init(uint32_t fft_size, float sampling_freq);
void process_window(const float *buffer, float *tremor_power, float *dysk_power);