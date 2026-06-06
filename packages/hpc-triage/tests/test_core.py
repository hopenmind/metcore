"""Tests for the hpc-triage abstraction.

No real triage tool is needed — we use minimal mock tools to verify the
cascade semantics (SOLVED stops, ESCALATE continues, BLOCKED stops,
ABORT stops, exhaustion synthesises a BLOCKED-HPC verdict).

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np
import pytest

from hpc_triage import (
    Problem,
    Tier,
    TriageTool,
    Verdict,
    VerdictStatus,
    cascade,
)


# ──────────────────────────────────────────────────────────────────────────────
#  Minimal mock tool — parameterised by the verdict it returns
# ──────────────────────────────────────────────────────────────────────────────

class _MockTool:
    def __init__(self, name: str, tier: Tier, status: VerdictStatus,
                 msg: str = "mock"):
        self.name = name
        self.tier = tier
        self._status = status
        self._msg = msg

    def evaluate(self, problem: Problem) -> Verdict:
        return Verdict(status=self._status, tier=self.tier, message=self._msg)


def _mock_problem() -> Problem:
    return Problem(
        spectral_density=lambda w: np.exp(-np.asarray(w) ** 2),
        system_hamiltonian=np.eye(2, dtype=complex),
        coupling_strength=0.1,
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Protocol satisfaction
# ──────────────────────────────────────────────────────────────────────────────

def test_mock_tool_satisfies_protocol():
    tool = _MockTool("x", Tier.LAPTOP, VerdictStatus.SOLVED)
    assert isinstance(tool, TriageTool)


def test_problem_dimension():
    p = _mock_problem()
    assert p.dimension() == 2


# ──────────────────────────────────────────────────────────────────────────────
#  Cascade behaviour
# ──────────────────────────────────────────────────────────────────────────────

def test_cascade_stops_on_solved():
    ladder = [
        _MockTool("a", Tier.LAPTOP, VerdictStatus.ESCALATE),
        _MockTool("b", Tier.LAPTOP, VerdictStatus.SOLVED, "done"),
        _MockTool("c", Tier.WORKSTATION, VerdictStatus.SOLVED, "unreached"),
    ]
    v = cascade(_mock_problem(), ladder, verbose=False)
    assert v.status == VerdictStatus.SOLVED
    assert v.message == "done"


def test_cascade_stops_on_blocked():
    ladder = [
        _MockTool("a", Tier.LAPTOP, VerdictStatus.ESCALATE),
        _MockTool("b", Tier.LAPTOP, VerdictStatus.BLOCKED, "no chance"),
        _MockTool("c", Tier.WORKSTATION, VerdictStatus.SOLVED, "unreached"),
    ]
    v = cascade(_mock_problem(), ladder, verbose=False)
    assert v.status == VerdictStatus.BLOCKED


def test_cascade_stops_on_abort():
    ladder = [
        _MockTool("a", Tier.LAPTOP, VerdictStatus.ABORT, "bad input"),
    ]
    v = cascade(_mock_problem(), ladder, verbose=False)
    assert v.status == VerdictStatus.ABORT


def test_cascade_all_escalate_confirms_hpc():
    ladder = [
        _MockTool("a", Tier.LAPTOP,      VerdictStatus.ESCALATE),
        _MockTool("b", Tier.WORKSTATION, VerdictStatus.ESCALATE),
        _MockTool("c", Tier.GPU_CLOUD,   VerdictStatus.ESCALATE),
    ]
    v = cascade(_mock_problem(), ladder, verbose=False)
    assert v.status == VerdictStatus.BLOCKED
    assert v.tier == Tier.HPC
    assert "HPC-bound" in v.message


def test_cascade_empty_ladder_confirms_hpc():
    v = cascade(_mock_problem(), [], verbose=False)
    assert v.status == VerdictStatus.BLOCKED
    assert v.tier == Tier.HPC


def test_cascade_logs_each_step(capsys):
    ladder = [
        _MockTool("alpha", Tier.LAPTOP, VerdictStatus.ESCALATE, "pass"),
        _MockTool("beta",  Tier.LAPTOP, VerdictStatus.SOLVED,   "done"),
    ]
    cascade(_mock_problem(), ladder, verbose=True)
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" in out
    assert "escalate" in out
    assert "solved" in out


def test_cascade_custom_log_sink():
    lines: list[str] = []
    ladder = [_MockTool("x", Tier.LAPTOP, VerdictStatus.SOLVED, "ok")]
    cascade(_mock_problem(), ladder, verbose=True, log=lines.append)
    assert any("x" in ln for ln in lines)


# ──────────────────────────────────────────────────────────────────────────────
#  Verdict defaults
# ──────────────────────────────────────────────────────────────────────────────

def test_verdict_defaults_are_conservative():
    v = Verdict(status=VerdictStatus.SOLVED, tier=Tier.LAPTOP, message="")
    assert v.cost_estimate_seconds is None
    assert v.memory_estimate_gb is None
    assert v.result is None
    assert v.diagnostic == {}
    assert v.next_tool is None


def test_tier_ordering_is_declared():
    # Not enforced at runtime; this test exists to pin the intended order
    # for reviewers: LAPTOP < WORKSTATION < GPU_CLOUD < HPC.
    declared = [Tier.LAPTOP, Tier.WORKSTATION, Tier.GPU_CLOUD, Tier.HPC, Tier.UNKNOWN]
    names = [t.value for t in declared]
    assert names[:4] == ["laptop", "workstation", "gpu_cloud", "hpc"]
