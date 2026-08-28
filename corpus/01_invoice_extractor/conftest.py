"""Applies the Operator named by GREENWASH_MUTATION before the suite imports.

pytest loads conftest before test modules, so a test that writes
`from feature import extract` still picks up the sabotaged version.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import feature  # noqa: E402

_mutation = os.environ.get("GREENWASH_MUTATION")
if _mutation:
    from greenwash import operators as ops

    ops.get(_mutation).patch(feature)
