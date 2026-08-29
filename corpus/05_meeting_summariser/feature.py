"""Meeting summarisation — the feature under test.

The output is prose, which makes this the case where wording changes actually
show up. Every other Corpus Case returns structured data that comes back
identical however you ask for it.
"""

from __future__ import annotations

from pathlib import Path

from greenwash.modelclient import complete

PROMPT = """Summarise the meeting transcript below in a short paragraph.
Include what was decided, who owns each action, and any dates.

Transcript:
{text}

Summary:"""


# The same instruction, worded differently — see `prompt.reword`.
PROMPT_VARIANT = """Write a short paragraph summarising the meeting transcript
below. Cover the decisions that were made, the owner of each action, and any
dates mentioned.

Transcript:
{text}

Summary:"""


def read_transcript(name: str) -> str:
    return (Path(__file__).parent / "transcripts" / name).read_text()


def summarise(name: str) -> str:
    """Return a short prose summary of the meeting."""
    return complete(PROMPT.format(text=read_transcript(name))).strip()
