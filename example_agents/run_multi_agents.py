import argparse
import os
import random
import signal
import subprocess
import sys
from pathlib import Path
from typing import List


THIS_DIR = Path(__file__).resolve().parent


def discover_agent_scripts() -> List[Path]:
    scripts = []
    for p in THIS_DIR.iterdir():
        if not p.is_file():
            continue
        if not p.name.startswith("agent_"):
            continue
        if not p.name.endswith(".py"):
            continue
        if p.name == Path(__file__).name:
            continue
        scripts.append(p)
    return sorted(scripts)


def launch_agents(num_agents: int, extra_args: List[str] | None = None) -> None:
    if extra_args is None:
        extra_args = []

    agents = discover_agent_scripts()
    if not agents:
        print("No agent_*.py scripts found in", THIS_DIR)
        return

    print(f"Discovered {len(agents)} agent scripts:")
    for a in agents:
        print(" -", a.name)

    chosen: List[Path] = []
    for _ in range(num_agents):
        chosen.append(random.choice(agents))

    print(f"\nStarting {num_agents} agents (one OS process per agent)...")

    procs: List[subprocess.Popen] = []
    try:
        for idx, script in enumerate(chosen, start=1):
            cmd = [sys.executable, str(script), *extra_args]
            print(f"[{idx}/{num_agents}] launching: {' '.join(cmd)}")
            proc = subprocess.Popen(cmd, cwd=str(THIS_DIR))
            procs.append(proc)

        print("\nAll agents launched. Press Ctrl+C to stop them.")

        # Wait for any child to exit; keep the controller alive until then.
        # If you prefer to run for a fixed time, you can change this loop.
        while procs:
            # Remove finished processes from the list
            alive = []
            for p in procs:
                ret = p.poll()
                if ret is None:
                    alive.append(p)
            procs = alive
            if not procs:
                break
            try:
                # Small sleep to avoid busy waiting
                signal.pause()
            except AttributeError:
                # Windows: fall back to a simple blocking wait on the first process
                procs[0].wait(timeout=1)
    except KeyboardInterrupt:
        print("\nCtrl+C received, terminating agents...")
    finally:
        # Terminate any remaining children
        for p in procs:
            if p.poll() is None:
                try:
                    p.terminate()
                except Exception:
                    pass
        for p in procs:
            if p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multiple DND auction agents in parallel.")
    parser.add_argument(
        "--num",
        "-n",
        type=int,
        default=4,
        help="Number of agents to start (default: 4)",
    )
    parser.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help="Extra arguments to pass through to each agent script (optional)",
    )

    args = parser.parse_args()
    num_agents = max(1, args.num)
    extra_args = args.extra or []

    launch_agents(num_agents, extra_args)


if __name__ == "__main__":
    main()
