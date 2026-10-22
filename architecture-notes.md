# Babel architecture working notes

Updated: 2026-10-17

This is the assistant-maintained companion to [architecture.md](architecture.md).
That document and explicit user decisions are authoritative. This file records
the agreed baseline, proposed design details, and questions to resolve during
implementation. Proposals below are not accepted decisions or verified hardware
capabilities. Reconcile this file with the source document before future work.

## Agreed baseline

- Babel is a handheld, interchangeable sensor instrument.
- The main board owns the display, primary SoC, WAMR runtime, and BLE
  connection to a phone.
- One daughter board attaches at a time through a single mating port.
- Every daughter board carries nonvolatile memory (NVM) containing its own
  portable WebAssembly driver. The main board executes that driver; the code is trusted.
- WAMR replaces the original MicroPython baseline following the user's runtime
  decision. Drivers target a versioned Babel API, independent of host OS and
  processor. See [runtime-decision.md](runtime-decision.md).
- Daughter boards may contain a sensor and supporting circuitry alone, or also
  include an MCU. An MCU is not required on every daughter board.
- The connector supports sensor communication using I²C, SPI, or UART, with
  possible future interfaces. Each board uses one sensor communication interface.
- Driver NVM uses dedicated pins separate from sensor communication pins, and
  exposes a fixed, host-known read/write interface.
- Daughter boards can be programmed through the mating connector.
- Daughter boards are hot-swappable; the main board must stay running during a
  swap.
- A few hours of battery operation is sufficient for the early prototype.
- The first sensor is a short-range IR temperature proof of concept.
- A small Android proof-of-concept app receives sensor data over BLE from the
  main board.

The mechanical mating method is an architectural decision to evaluate, not a
missing user requirement. The repeated IR-board tasks in the source document are
understood as one deliverable.

## Prototype boundaries

Deliverables are architectural decisions, main-board and IR daughter-board KiCad
designs, host firmware, a daughter-board driver, and a minimal Android receiver.
PCB implementation follows the relevant electrical and component decisions.

Exact temperature range, accuracy, field of view, and measurement distance are
not specified. Choose and document provisional targets when comparing sensors;
do not imply calibrated instrument performance.

Display controls, logging, calibration persistence, phone-side programming, and
custom daughter-board screens remain unspecified. The broad use case mentions
programmability, but the Android prototype currently requires only data reception.

## Proposed responsibility split

| Component | Proposed responsibility |
| --- | --- |
| Main-board platform firmware | Attachment detection, power sequencing, NVM access, driver validation/loading, resource ownership, display and BLE services |
| Daughter-board Wasm driver | Sensor initialization, configuration, acquisition, conversion to named readings with units, and cleanup |
| Daughter-board manifest | Board identity, format/API versions, sensor interface requirements, driver location/length, and integrity metadata |
| Android app | BLE connection, sensor identity and readings, connection and sensor status |

Prefer a common measurement contract feeding both the display and BLE. Whether
drivers can define custom UI behavior is still open. An optional daughter-board
MCU does not replace the requirement for host-readable driver storage.

## Decisions to resolve

| Decision | Evaluation notes |
| --- | --- |
| Board contract and NVM format | Define discovery before driver execution, version compatibility, bounded reads, and handling of blank or corrupt storage. |
| NVM technology and protocol | Compare capacity, read/write behavior, endurance, availability, and programming recovery. “Flash” in the source TODO does not yet select a part or settle whether another NVM technology is suitable. |
| Electrical connector contract | Define voltage, current budget, ground, dedicated NVM signals, sensor signals, attachment detection, and any interrupt/reset needs. Decide whether sensor interface pins can be multiplexed. |
| Mechanical connector | Compare insertion experience, retention, orientation/keying, durability, size, sourcing, and suitability for powered insertion/removal. |
| Main SoC or module | Evaluate WAMR execution modes, BLE, display support, available pins/peripherals, RAM/flash, development tools, and power consumption together. |
| Power system | Choose battery, charging input, regulators, daughter-board power control, current limits, and power budget including display/radio peaks. |
| Driver execution and isolation | Define scheduling, timeouts, memory limits where feasible, resource cleanup, and recovery from exceptions or hangs. Trusted code can still fail. |
| BLE application protocol | Define identity, measurement schema, units, sequencing/timestamps as needed, status events, reconnect behavior, and payload framing. |
| IR sensor and display/input | Select provisional prototype targets and then suitable parts; document limitations and required supporting circuitry. |

The first researched working selections and their sources are now in
[architecture-proposal.md](architecture-proposal.md), with the draft storage,
driver, and BLE contract in [board-contract-v0.md](board-contract-v0.md).
They are proposals, not final component selections or a fabrication-ready pinout.
Remaining datasheet checks and hardware validation are recorded there.

## Proposed attachment and driver lifecycle

1. Detect attachment and establish stable daughter-board power.
2. Read a bounded manifest through the fixed NVM interface.
3. Check format/API compatibility, driver bounds, and integrity before execution.
4. Configure the required sensor interface and initialize the driver.
5. Acquire readings and publish them to the display and BLE services.
6. On removal or fault, stop acquisition, invalidate outstanding readings, release
   driver resources, and report status while preserving host operation.

Details to work out include attachment debounce, interrupted bus transactions,
removal during initialization, and late results from a previous board instance.
A board/session generation identifier is one possible way to reject stale results.

Hot swapping needs both electrical and software design. Evaluate contact order,
inrush, unpowered signal paths, bus isolation/pull-ups, and power switching before
finalizing the connector. Dedicated NVM pins alone do not address these issues.

Keeping the host alive during swaps is agreed. Keeping display/BLE responsive
during an arbitrary driver hang is an additional reliability target still to
resolve. Wasm memory isolation does not establish execution deadlines or safe
cancellation of native bus operations. Qualify both on the chosen host.

## Programming and storage notes

- Proposed: make blank-board provisioning possible through the host's fixed NVM
  access path without first needing a working daughter-board driver.
- Define a programming mode that prevents execution of a driver while its stored
  image is being changed.
- Choose an interrupted-write strategy: for example, mark an image invalid until
  verification completes, or retain a previous valid image if storage allows.
- Integrity checking is intended to detect corruption; trusted-code execution
  does not itself require a signing infrastructure.
- Decide whether calibration and user settings belong on the board or host, and
  whether driver updates preserve them.
- If a daughter board contains an MCU, distinguish updating its firmware from
  updating the host-executed Wasm driver. MCU flashing is not yet specified.

## Suggested order of work

1. Draft the driver/manifest contract and provisional connector signal budget.
2. Compare the IR sensor, NVM, host SoC/module, display, and connector candidates;
   refine the contract and power budget around the resulting constraints.
3. Demonstrate NVM loading, sensor acquisition, and BLE reception with development
   hardware where practical before committing custom boards.
4. Finalize electrical/mechanical interfaces and produce both KiCad designs.
5. Integrate the firmware and Android app, then validate swaps and battery life.

These steps may iterate; component constraints can change early proposals.

## Prototype acceptance checks to carry forward

- A valid attached IR board supplies its driver from NVM and produces readings on
  both the display and Android app.
- Removal and reinsertion leave the main board running; stale readings are not
  presented as current measurements.
- Blank, corrupt, or incompatible driver storage produces a recoverable status.
- Programming through the mating interface works, and an interrupted update has
  a documented recovery path.
- Sensor errors and driver exceptions are reported; behavior for a stuck driver
  follows the isolation/recovery decision rather than an assumed guarantee.
- Phone disconnect/reconnect does not prevent standalone sensor use.
- Measured battery life is checked with stated display brightness, acquisition
  rate, and BLE activity.

## Maintenance

The user selected ESP32-S3-WROOM-1-N8R8 for the radio/main board after considering
STM32N6 plus BLE; Alif is excluded by user direction. The nine-sheet rev D schematic is
in [hardware/radio](hardware/radio/README.md), with PDF, BOM, GPIO allocation,
ERC and independent critical-net checks. It covers the host, USB, protected-pack
power path, regulator and daughter interface. Supporting component choices remain
engineering proposals. The user selected the Jauch 251555 protected 1000 mAh
pouch pack and Adafruit 4741 1.5-inch 128x128 grayscale OLED over SPI. See the
radio README for exact variants and outstanding integration work. All radio
footprints are assigned; custom geometry and physical fit remain unqualified.
User committed to USB-C: the implementation
requires advertised 1.5 A or 3 A and a data-capable C-to-C connection for programming;
legacy/default-current sources are intentionally unsupported. Hardware gates power
and data before firmware starts. BQ24079 targets 4.1 V, with an external hardware
temperature window and a longer enabled safety timer. Charging remains disabled
in the initial assembly until physical qualification. Prototype sensor isolation
is grouped, not per-interface; firmware must leave unused pins high impedance. There is
no routed board or hardware/runtime qualification yet.

2026-10-19 charging decision: the user explicitly restored onboard charging
after the external-charging-only rev C work was interrupted. Rev D restores
the BQ24079 4.1 V / 166 mA charger, independent hardware NTC window and enabled
timers. It retains the new footprints, USB input switch, fuse and TVS. R90 stays
DNP until qualification. This preserves pack thermistor supervision and avoids
making routine pack disconnection/external charging the prototype workflow;
it does not remove pouch-cell puncture, heat or enclosure risks. The historical
review and interrupted rev C snapshot remain under hardware/ for traceability.

Prototype connector: MEC1-110-02-L-D-NP-A, twenty usable contacts. The polarized
variant sacrifices contacts required by our contract. External mechanical keying
and retention must precede user operation; equal-length contacts require power-off
module changes until hot-swap testing. Procurement and assembled fit remain open.

IR daughter-board revision B schematic is now in
[hardware/ir-daughter](hardware/ir-daughter/README.md), with a native KiCad
project, PDF, review BOM, and netlist verification. Per the user's direction,
the draft adapts Adafruit's MLX90632 circuit with provisional 24LC256 storage
and a card-edge interface. The MLX90614 draft is archived; see the hardware
ADAPTATION.md for upstream provenance and CC BY-SA 3.0 attribution.
Native PCB seeds now exist for both boards. The 60 x 80 mm four-layer radio and
30 x 35 mm two-layer daughter have fixed interface anchors, mounting holes,
mechanical envelopes and checked netlist imports. Critical custom footprints,
charger package correction, PS/SYNC protection and sixteen radio test points are
complete. See hardware/LAYOUT-PLAN.md for the placement/routing contract.
Keyed-carrier CAD is defined but unprinted; assembled fit, specialist hard-gold
fabrication approval, final layout DRC, Wasm capacity and bench qualification
remain open. Ready to begin layout does not mean ready to fabricate or charge.

When a decision is made, record its choice, rationale, evidence, and consequences
here and distinguish it from remaining proposals. Ask the user for missing product
constraints only when they materially affect a choice; evaluate engineering
options as part of the architectural work.
