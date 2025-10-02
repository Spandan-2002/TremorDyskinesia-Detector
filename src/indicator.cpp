#include "indicator.h"
#include "mbed.h"

static DigitalOut led1(LED1);
static DigitalOut led3(LED3);

// Calibrated thresholds (tweak after testing)
static const float TremorThresh = 1.5f;
static const float DyskThresh  = 1.5f;

void indicator_init() {
    led1 = 0;
    led3 = 0;
}

static void blink_led(DigitalOut &led,
                      uint32_t times,
                      uint32_t delay_ms) {
    for (uint32_t i = 0; i < times; ++i) {
        led = !led;
        thread_sleep_for(delay_ms);
        led = !led;
        thread_sleep_for(delay_ms);
    }
}

void indicate_tremor(float power) {
    if (power > TremorThresh) {
        uint32_t rate = (uint32_t)((power - TremorThresh) * 2);
        blink_led(led1, 1, 500 / rate);
    }
}

void indicate_dysk(float power) {
    if (power > DyskThresh) {
        uint32_t rate = (uint32_t)((power - DyskThresh) * 2);
        blink_led(led3, 1, 500 / rate);
    }
}