usecase:
babel is a handheld swiss army knife of electronic sensors. The main babel board has a display and wireless connection for a user to interact with, and sensor daughterboards can be plugged into the main board and the user can use the sensor connected to that daughter board. For instance, an IR temperature sensor can be plugged in the user can check the temperature of whatever they want. Or a pressure sensor can be plugged in and the user can check the weight of a device. The user can also check use their phone to interact with babel for added programmability or nuanced data 


babel architecture:
The main board carries display, radio, primary SoC. Daughter boards carry sensors. Every daughter board needs some NVM to carry it's own device driver.
Daughter boards will need an interface to be programmable
the mating interface between daughter and main board needs to be smoothe
the main board needs to support simple serial interfaces for the daughter boards. This means i2c, spi, uart, possibly others. The mating interface should have enough pins to support this. The daughter board is assumed to use a single interface only, not multiple
the daughter board can be programmed through the mating interface 
WAMR WebAssembly runtime on device
pcb hosts the main board with display, radio connectivity
daughter boards plug into main board and load device driver code. 
daughter boards are sensors (temperature sensor, flex sensor, etc.)
few hours of battery life is sufficient for early prototype
hot swappable daughter boards. main board should stay running through the hotswap 
daughter board contains a portable WebAssembly driver in its NVM, the main board runs it using WAMR and drives the radio and display
all daughter board code is assumed to be trusted; hardware access goes through a versioned Babel host API
driver binaries should remain usable across main board revisions that implement the required API and capabilities
timing-sensitive operations require host-specific timing qualification; WAMR alone does not guarantee deadlines
only a single mating port between the daughter board and main board
the daughter board can contain as much as a small MCU and the sensor, or just the sensor and the main board drives the daughter board directly.
interface for the daughter board should be considered fixed, so the main board will have an assumed method of read/write for all daughter boards implicitly
the pins for interfacing with the NVM are separate from the pins for interfacing with the sensor on the daught board and connecting into the mating interface
the phone connection will use ble to stream sensor data from the daughter board   



TODO architectural decisions:
-decide on physical mating interface between main and daughter board
-kicad implementation of main board pcb
-kicad implementation of daughter board pcb
-decide on best main board SoC 
-main board SoC baseline selected: ESP32-S3-WROOM-1-N8R8; use this for the radio-board schematic
-decide on flash for daughter boards
-decide on power strategy
-decide on WAMR execution mode, resource limits, isolation, and timing qualification on the main board
-contract between main and daughter board
-ble application comms scheme



current tasks:
-resolve architectural decisions
-create the main board 
-create an IR temp sensor daughter board
-create a single IR temperature sensor daughter board, short range proof of concept only
-base the IR daughter board on Adafruit's MLX90632 breakout circuit, adapted for our card-edge interface and separate driver EEPROM
-create a small poc android app on phone that receives daughter board data from the main baord
