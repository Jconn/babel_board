// Host pins, matching the radio (hardware/radio/gpio-map.csv) and the J2 bench wiring.
#pragma once

#define PIN_SENSOR_SCL 7  // J2.3, radio H_SENSOR_IO0
#define PIN_SENSOR_SDA 8  // J2.4, radio H_SENSOR_IO1
#define PIN_NVM_SCL    4  // J2.5
#define PIN_NVM_SDA    5  // J2.6
#define PIN_NVM_WP     6  // J2.7, high = write-protected
