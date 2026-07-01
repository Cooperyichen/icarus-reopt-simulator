# ICARUS Simulation Tests

This directory contains unit tests for the ICARUS simulation project.

## Test Structure

```
tests/
├── __init__.py                    # Makes tests a Python package
├── test_time_conversion.py        # Tests time conversion logic
├── test_packets_in_transit.py     # Tests packet in transit detection
├── test_simulator.py              # Tests Simulator class functionality
├── fixtures/                      # Test data and configurations
│   ├── __init__.py
│   └── test_config_short_sim.yaml # Short simulation time test config
└── utils/                         # Test utility functions
    ├── __init__.py
    └── test_helpers.py            # Test helper functions
```

## Running Tests

### Prerequisites

Ensure all project dependencies are installed. The tests require:
- Python 3.10+
- simpy
- networkx
- Other dependencies listed in `dependencies.txt`

### Run All Tests

```bash
# From project root directory
python3 -m unittest discover tests -v
```

### Run Specific Test File

```bash
# Test time conversion
python3 -m unittest tests.test_time_conversion -v

# Test packets in transit
python3 -m unittest tests.test_packets_in_transit -v

# Test simulator
python3 -m unittest tests.test_simulator -v
```

## Test Descriptions

### test_time_conversion.py

Tests that `simulation_time` and `generation_finish_time` are correctly converted from milliseconds to seconds based on the `time_unit` configuration.

**Key Tests:**
- `test_simulation_time_ms_conversion`: Verifies ms to seconds conversion
- `test_simulation_time_s_no_conversion`: Verifies no conversion when time_unit is 's'
- `test_short_simulation_time`: Tests with very short simulation times

### test_packets_in_transit.py

Tests detection of packets still in transit (in wires/interlinks) when simulation ends.

**Key Tests:**
- `test_detect_packets_in_wire`: Verifies packets in wire stores are detected
- `test_packet_delivered_after_delay`: Verifies packets are delivered after delay
- `test_multiple_packets_in_transit`: Tests detection of multiple packets

### test_simulator.py

Tests the Simulator class, focusing on time conversion and short simulation scenarios.

**Key Tests:**
- `test_simulator_time_conversion_ms`: Verifies Simulator converts time correctly
- `test_simulator_short_simulation_time`: Tests with short simulation times
- `test_simulator_time_consistency`: Verifies consistency between simulation_time and generation_finish_time

## Fix Applied

### Issue Fixed: simulation_time Conversion

**Problem:** The `simulation_time` parameter was not being converted from milliseconds to seconds before being passed to SimPy's `env.run()`, causing simulations to run for incorrect durations.

**Solution:** Added time conversion logic in `src/simulator/simulator.py` (lines 954-961):

```python
# Convert simulation_time from ms to seconds (simpy uses seconds)
# Check time_unit to determine if conversion is needed
time_unit = self.scenario_config.get('system', {}).get('time_unit', 'ms')
if time_unit == 'ms':
    simulation_time_seconds = simulation_time / 1000.0  # Convert ms to seconds
else:
    simulation_time_seconds = simulation_time  # Already in seconds

# Run the simulation
self.env.run(until=simulation_time_seconds)
```

This ensures that when `time_unit='ms'` and `simulation_time=300`, the simulation actually runs for 0.3 seconds instead of 300 seconds.

## Notes

- Tests use Python's standard `unittest` framework
- Test fixtures are stored in `fixtures/` directory
- Helper functions are in `utils/test_helpers.py`
- Some tests may require full project dependencies to be installed


