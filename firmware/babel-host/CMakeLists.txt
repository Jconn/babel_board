cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

# WAMR checkout (pinned to WAMR-2.4.6); override with the WAMR_PATH environment variable.
if(DEFINED ENV{WAMR_PATH})
    set(WAMR_PATH $ENV{WAMR_PATH})
else()
    set(WAMR_PATH $ENV{HOME}/projects/wamr)
endif()
list(APPEND EXTRA_COMPONENT_DIRS "${WAMR_PATH}/build-scripts/esp-idf")

project(babel_host)
