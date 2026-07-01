# ICARUS Re-optimization Simulator

This repository contains a cleaned research prototype for network simulation and
event-triggered re-optimization experiments. It builds on an ICARUS-style
packet-level simulator and adds research code for multi-commodity flow
re-optimization.

## What This Project Does

The codebase has two main parts:

- **Network simulator core**: builds a graph-based communication network and
  simulates packet generation, switching, queueing, link transmission, delay,
  and packet loss under configurable traffic and topology settings.
- **Re-optimization research layer**: uses the simulator output together with a
  multi-commodity flow optimizer. The research code explores how dual variables
  and congestion signals can guide path updates or re-optimization decisions.

The current refactoring effort is focused on turning earlier one-off experiment
scripts into reusable simulator and optimizer workflows.

## Current Multi-step Simulation Status

The simulator now has initial support for running simulations across multiple
discrete time steps.

Currently working:

- Saving packets that remain in port queues at the end of a step.
- Saving packets that remain in wires at the end of a step.
- Restoring saved packets into the next step's queue or wire state.
- Looking up switch ports consistently across `SimplePacketSwitch` and
  `FairPacketSwitch`.
- Running state restoration unit tests for queue, wire, timestamp, and recovered
  packet metadata behavior.

Still in progress:

- Fully stateful multi-step simulation where restored packets continue moving
  through the active SimPy processes in the next step.
- Clean separation between stateless multi-step runs and stateful continuous
  runs.
- Cross-step Packet Loss Indicator accounting that cleanly separates temporary
  time-limit packets from final packet loss.

For now, stateless multi-step simulation is the safer first target: each time
step can run independently, and packets left unfinished at the end of a step can
be counted as that step's time-limit loss without being carried forward.

## Repository Layout

- `src/simulator/`: main simulator orchestration logic.
- `src/topo/`: topology generation and topology utilities.
- `src/packet/`: packet model, generators, and sinks.
- `src/port/`: ports, wires, and transmission components.
- `src/modem/`: switch implementations.
- `src/flow/`: flow-level data structures.
- `src/optimizer/`: multi-commodity flow optimizer and re-optimization logic.
- `src/main/`: experiment entry points and legacy research scripts.
- `tests/`: unit and integration tests for simulator, optimizer, and multi-step
  behavior.
- `docs/`: technical notes and project documentation.

## Validation Status

The focused state restoration tests currently pass:

```bash
python3 -m unittest tests.test_state_restoration -v
```

Known remaining issues in the broader test suite:

- Some tests expect generated experiment outputs under `src/results/`, which are
  intentionally not included in the public repository.
- `unittest discover` currently attempts to import a helper module as a test
  module.
- Stateful multi-step recovery still needs a cleaner step lifecycle so restored
  packets are consumed by the next step's active simulation processes.

## Branches

- `main`: public repository base.
- `paper-prototype`: cleaned research simulator source and active refactoring
  work.

The draft pull request from `paper-prototype` into `main` is the current review
path for publishing the cleaned simulator code.
