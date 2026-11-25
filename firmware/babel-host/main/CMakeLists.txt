idf_component_register(SRCS "main.c" "nvm.c" "image.c" "driver_host.c"
                       INCLUDE_DIRS "."
                       PRIV_REQUIRES wamr esp_driver_i2c esp_driver_gpio esp_driver_uart
                                     esp_timer json mbedtls pthread)
