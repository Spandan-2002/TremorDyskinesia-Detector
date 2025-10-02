#include "signal.h"
#include "arm_math.h"
#include "lsm6dsl.h"

static arm_rfft_fast_instance_f32 fft_inst;
static uint32_t N;
static float fs;

void signal_init(uint32_t fft_size, float sampling_freq) {
    N  = fft_size;
    fs = sampling_freq;
    arm_rfft_fast_init_f32(&fft_inst, N);
}

void process_window(const float *buf,
                    float *tremor_power,
                    float *dysk_power) {
    static float spectrum[512];
    static float mags[257];

    arm_rfft_fast_f32(&fft_inst, (float*)buf, spectrum, 0);
    arm_cmplx_mag_f32(spectrum, mags, N/2 + 1);

    float bin_width = fs / N;
    uint32_t t_lo = (uint32_t)ceil(3.0f / bin_width);
    uint32_t t_hi = (uint32_t)floor(5.0f / bin_width);
    uint32_t d_lo = (uint32_t)ceil(5.0f / bin_width);
    uint32_t d_hi = (uint32_t)floor(7.0f / bin_width);

    float tp = 0, dp = 0;
    for (uint32_t i = t_lo; i <= t_hi; ++i) tp += mags[i];
    for (uint32_t i = d_lo; i <= d_hi; ++i) dp += mags[i];

    *tremor_power = tp;
    *dysk_power   = dp;
}
