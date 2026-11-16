# ADR 002 Local WSL clock isolation

Accepted for local training, 2026-10-21.

During a diagnostic run, realtime stepped back 2.492 seconds while monotonic
time continued. Immediately afterwards the mission correctly aborted for
2.565 seconds of missing odometry. Waiting for initial synchronization,
disabling the GUI, removing contact recording and software rendering had
not eliminated the issue. Control timeouts remain unchanged.

The local Windows launcher invokes a fixed root wrapper in WSL. The wrapper
reads the Linux time service state, rejects transitional states, temporarily
stops an active systemd-timesyncd service, executes the fixed local launcher
as user ican, and restores the service in finally. Inactive/failed services
remain unchanged. No timezone, system timestamp, persistent service enablement,
competition interface, scene or physical model is modified.

An exclusive local file lock rejects a concurrent wrapper before service
changes. State-read or stop failures prevent the trial; restoration failure
is reported instead of claiming success. Tests cover command failure and
KeyboardInterrupt restoration. SIGTERM is translated into an interrupt; the
wrapper terminates and waits for its process group before restoring the clock
service, and the trial supervisor cleans up its owned simulator groups.
SIGKILL, host crash and WSL shutdown cannot
execute Python finally; a normal WSL boot still uses the unchanged service
enablement. This wrapper is not included in src.zip or platform run.sh.

Operational states: inspect -> isolate (if active) -> run -> restore -> exit.
An unknown/transitional state rejects before isolation. Trial exit codes
propagate; cleanup errors remain visible. No restart or retry is automatic.
