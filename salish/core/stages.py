"""Run pipeline stages so that one failing model cannot take down the rest."""

import time
import traceback
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageResult:
    status: str                 # "ok", "skipped", "failed" or "disabled"
    note: str = ""
    output: Any = None
    seconds: float = 0.0
    extra: dict = field(default_factory=dict)


class Skip(Exception):
    """Raise inside a stage when its inputs are missing; the stage is skipped, not failed."""


def run_stage(name, enabled, fn, *args, **kwargs):
    if not enabled:
        print(f"\n=== {name}: disabled in config ===")
        return StageResult("disabled", "disabled in config/pipeline.yaml")
    print(f"\n=== {name} ===")
    t0 = time.time()
    try:
        output = fn(*args, **kwargs)
    except Skip as e:
        print(f"[{name}] skipped: {e}")
        return StageResult("skipped", str(e), seconds=time.time() - t0)
    except Exception as e:
        traceback.print_exc()
        print(f"[{name}] FAILED: {e}")
        return StageResult("failed", f"{type(e).__name__}: {e}", seconds=time.time() - t0)
    seconds = time.time() - t0
    print(f"[{name}] done in {seconds:.0f}s")
    return StageResult("ok", output=output, seconds=seconds)
