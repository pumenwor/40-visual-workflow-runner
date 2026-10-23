# Demo script (3-5 minutes)

Before starting: app running with ENABLE_DEMO_NODE=true, seed script already run.

1. **Intro (20s):** "This app turns a dependency graph into a recorded run.
   It validates first and never runs user-provided code."
2. **Success workflow (60s):** Open "Success demo". Two emit_json nodes feed one
   combine_inputs node. Arrows mean "must finish before".
3. **Validate and run (60s):** Click Validate, show the order. Click Run, open
   the run, show both source outputs and the combined output.
4. **Graph safety (30s):** Add a connection that makes a cycle, click Validate,
   read out the error. Remove the connection.
5. **Retry (60s):** Open "Retry demo". Run it. Show attempt 1 failed,
   attempt 2 succeeded, run succeeded.
6. **Failure (30s):** Open "Failure demo". Run it. Show the failed task and the
   downstream task marked skipped.
7. **Close (20s):** Single worker, no login, no arbitrary code, sequential runs.
   Next: durable queue, parallel nodes, authentication.

Backup plan: if the hosted app is slow, switch to the local copy.
Rehearse twice with a timer.