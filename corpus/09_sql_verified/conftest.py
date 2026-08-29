import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import feature  # noqa: E402

_mutation = os.environ.get("GREENWASH_MUTATION")
if _mutation:
    from greenwash import operators as ops

    ops.get(_mutation).patch(feature)
