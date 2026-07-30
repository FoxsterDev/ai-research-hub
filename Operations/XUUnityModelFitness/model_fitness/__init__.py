"""Public deterministic fitness engine (design P2).

Bootstraps imports of the public XUUnity module libraries
(``xuunity_canonical``, ``contract_validator``, ``observation_contract``,
``reduced_stack_gate``) that this package composes. Everything here is
public-safe: no host paths, tokens, fixture prompts, or raw transcripts."""

from __future__ import annotations

import sys
from pathlib import Path

OPERATION_DIR = Path(__file__).resolve().parents[1]
AIROOT_DIR = OPERATION_DIR.parents[1]
MODULE_DIR = AIROOT_DIR / "Modules" / "XUUnity"
MODULE_SCRIPTS_DIR = MODULE_DIR / "scripts"

if str(MODULE_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_SCRIPTS_DIR))
