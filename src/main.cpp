#include "mbed.h"
#include "arm_math.h"

// ———————————— I2C + LSM6DSL setup ————————————
// Define I2C pins specifically for this board
// The L4 Discovery board uses PB_11 and PB_10 for the internal I2C
I2C i2c(PB_11, PB_10); // SDA, SCL

// LSM6DSL registers and address
#define LSM6DSL_ADDR (0x6A << 1) // 0x6A shifted for 8-bit R/W
#define WHO_AM_I     0x0F
#define CTRL1_XL     0x10
#define CTRL2_G      0x11
#define CTRL3_C      0x12
#define OUTX_L_XL    0x28
#define OUTX_H_XL    0x29
#define OUTY_L_XL    0x2A
#define OUTY_H_XL    0x2B
#define OUTZ_L_XL    0x2C
#define OUTZ_H_XL    0x2D

volatile bool sampleNow = false;

// I2C communication functions
void write_register(uint8_t reg, uint8_t val) {
    char data[2] = { (char)reg, (char)val };
    i2c.write(LSM6DSL_ADDR, data, 2);
}

uint8_t read_register(uint8_t reg) {
    char r = reg, val;
    i2c.write(LSM6DSL_ADDR, &r, 1, true);
    i2c.read(LSM6DSL_ADDR, &val, 1);
    return (uint8_t)val;
}

int16_t read_16bit(uint8_t lo, uint8_t hi) {
    uint8_t l = read_register(lo);
    uint8_t h = read_register(hi);
    return (int16_t)((h << 8) | l);
}

// ———————————— Serial via USB for debug ————————————
// Match the terminal's baud rate of 9600
BufferedSerial serial_port(USBTX, USBRX, 115200);

// Override console output for printf to use USB serial
FileHandle *mbed_override_console(int fd) { return &serial_port; }

// ———————————— LEDs for indication ————————————
DigitalOut ledTremor(LED1);
DigitalOut ledDysk(LED2);
DigitalOut ledNone(LED3);


// ———————————— FFT parameters ————————————
static constexpr int FFT_SIZE = 256;
static constexpr float SAMPLE_RATE_HZ = 104.0f;
static constexpr int SAMPLE_US = int(1e6f / SAMPLE_RATE_HZ);

float32_t inputBuf[FFT_SIZE];
float32_t fftOut[FFT_SIZE];
float32_t magOut[FFT_SIZE/2];
arm_rfft_fast_instance_f32 fftInst;

// Sampling control variables
Ticker sampler;
volatile uint32_t idx = 0;
volatile bool ready = false;

// ———————————— Sample handler ————————————
void sampleHandler() {
    sampleNow = true; // Signal main thread to sample
}


// ———————————— Detection ————————————
void runDetection() {
    // 1) Apply window function to reduce spectral leakage
    for (int i = 0; i < FFT_SIZE; i++) {
        // Hann window: 0.5 * (1 - cos(2π*n/(N-1)))
        float windowCoef = 0.5f * (1.0f - cosf(2.0f * PI * i / (FFT_SIZE - 1)));
        inputBuf[i] *= windowCoef;
    }
    
    // 2) Perform FFT and calculate magnitude
    arm_rfft_fast_f32(&fftInst, inputBuf, fftOut, 0);
    arm_cmplx_mag_f32(fftOut, magOut, FFT_SIZE/2);
    
    // Scale down DC component to avoid it dominating the spectrum
    magOut[0] *= 0.1f;
    
    // 3) Find peak in 3–5 Hz range (tremor)
    uint32_t t0 = uint32_t(3.0f * FFT_SIZE / SAMPLE_RATE_HZ);
    uint32_t t1 = uint32_t(5.0f * FFT_SIZE / SAMPLE_RATE_HZ);
    float32_t maxTrem = 0;
    uint32_t idxT = 0;
    arm_max_f32(magOut + t0, t1 - t0 + 1, &maxTrem, &idxT);
    
    // 4) Find peak in 5–7 Hz range (dyskinesia)
    uint32_t d0 = uint32_t(5.0f * FFT_SIZE / SAMPLE_RATE_HZ);
    uint32_t d1 = uint32_t(7.0f * FFT_SIZE / SAMPLE_RATE_HZ);
    float32_t maxDysk = 0;
    uint32_t idxD = 0;
    arm_max_f32(magOut + d0, d1 - d0 + 1, &maxDysk, &idxD);
    
    // 5) Calculate frequencies for debug output
    float tremFreq = (t0 + idxT) * SAMPLE_RATE_HZ / FFT_SIZE;
    float dyskFreq = (d0 + idxD) * SAMPLE_RATE_HZ / FFT_SIZE;
    
    // 6) Decision logic with adaptive threshold
    float32_t baseline = 0;
    arm_mean_f32(magOut + 1, 10, &baseline); // Use low frequency bins to estimate noise floor
    float threshold = baseline * 10.0f; // Set threshold as 10x the noise floor
    
    // 7) Light LEDs based on detection
    ledTremor = ledDysk = ledNone = 0;
    
    if (maxTrem > maxDysk && maxTrem > threshold) {
        ledTremor = 1; // Tremor detected
        printf("Tremor detected at %.1f Hz (mag: %.0f)\r\n", tremFreq, maxTrem);
    } else if (maxDysk > maxTrem && maxDysk > threshold) {
        ledDysk = 1; // Dyskinesia detected
        printf("Dyskinesia detected at %.1f Hz (mag: %.0f)\r\n", dyskFreq, maxDysk);
    } else {
        ledNone = 1; // None detected
        printf("No movement disorder detected (T: %.0f, D: %.0f)\r\n", maxTrem, maxDysk);
    }
}

// ———————————— Main function ————————————
int main() {
    // Initialize all LEDs off
    ledTremor = ledDysk = ledNone = 0;
    
    // Short delay to allow peripherals to initialize
    ThisThread::sleep_for(100ms);
    
    // Print startup message
    printf("\r\n\r\n------------------------------------\r\n");
    printf("Tremor/Dyskinesia Detection System\r\n");
    printf("------------------------------------\r\n");
    
    // Set up I2C at standard speed (100kHz) - this board only supports 100kHz, 400kHz, or 1MHz
    i2c.frequency(100000);
    
    // Longer delay to ensure I2C is fully ready
    ThisThread::sleep_for(300ms);
    
    // Test LSM6DSL connectivity
    printf("Testing sensor connectivity...\r\n");
    uint8_t who = read_register(WHO_AM_I);
    printf("WHO_AM_I = 0x%02X (expect 0x6A)\r\n", who);
    
    if (who != 0x6A) {
        printf("ERROR: Sensor not found or not responding!\r\n");
        printf("Check connections and restart.\r\n");
        
        // Error indication - blink all LEDs
        while (true) {
            ledTremor = !ledTremor;
            ledDysk = !ledDysk;
            ledNone = !ledNone;
            ThisThread::sleep_for(200ms);
        }
    }
    
    // Configure sensor control register first
    printf("Configuring sensor control register...\r\n");
    write_register(CTRL3_C, 0x04);  // Enable Block Data Update (BDU)
    ThisThread::sleep_for(100ms);   // Wait for configuration to apply
    
    // Configure accelerometer: 104 Hz, ±2g (lowest noise setting)
    printf("Configuring accelerometer: 104 Hz, ±2g\r\n");
    write_register(CTRL1_XL, 0x40);  // 0x40 = 01000000b: ODR_XL=104Hz, FS_XL=±2g
    
    // Initialize FFT instance
    arm_rfft_fast_init_f32(&fftInst, FFT_SIZE);
    
    // Ready indication - blink sequence
    printf("System ready. Starting measurements...\r\n");
    for (int i = 0; i < 3; i++) {
        ledNone = 1;
        ThisThread::sleep_for(200ms);
        ledNone = 0;
        ThisThread::sleep_for(200ms);
    }
    ledNone = 1;  // Default state is "no detection"
    
    // Main detection loop
    while (true) {
        // Reset buffer
        idx = 0;
        ready = false;
        
        // Start sampling with ticker
        printf("Collecting samples...\r\n");
        idx = 0;
        sampler.attach_us(&sampleHandler, SAMPLE_US);

        while (idx < FFT_SIZE) {
            if (sampleNow) {
                sampleNow = false;

                int16_t raw = read_16bit(OUTX_L_XL, OUTX_H_XL);
                inputBuf[idx++] = float32_t(raw);
            }
            ThisThread::sleep_for(1ms); // Reduce CPU usage
        }

        sampler.detach();

        
        // Run detection algorithm
        printf("Analyzing data...\r\n");
        runDetection();
        
        // Wait before next measurement cycle
        ThisThread::sleep_for(1s);
    }
}