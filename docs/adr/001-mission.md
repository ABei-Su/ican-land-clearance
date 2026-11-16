# ADR 001: deterministic mission and fail-closed execution

Accepted 2026-10-16 under the approved design.

The mission core owns the phase, point and monotonically increasing generation.
The current adapter awaits futures in one sequential flow; ROS callbacks only
update observations and never advance the core. Future callback-driven adapters
must submit events with their originating generation. Stale events and
illegal transitions have no effects. Each accepted event atomically updates core
state before the adapter executes effects. Single-threaded callback execution is
required by the adapter. No domain state is restored across process restarts.

INIT is initial; DONE/ABORTED are terminal. Timeouts, cancellation, uncertainty and
failure terminate with cancel and stop effects. Perception and alignment guards
belong to the adapter and are tested separately. A shot spawn is recorded only as
spawn, never as a hit or score. The first implementation aborts rather than retries
ambiguous external effects. Future bounded retries must have explicit transitions.

Simulation restarts require a new run identifier. JSONL logs are diagnostic,
versioned evidence, not an authoritative replay mechanism.
