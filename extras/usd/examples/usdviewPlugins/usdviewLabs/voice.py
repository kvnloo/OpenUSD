#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Realtime-voice text ingress.

This module accepts an already-transcribed utterance and returns a proposal.
It never executes a UsdAction.
"""

from .intents import route_text
from .receipts import record_event
from .router import action_signature, text_fingerprint
from .shadow import schedule_shadow


def propose_transcript(transcript):
    text = str(transcript)
    decision = route_text(text, source="voice")
    decision.metadata.update({
        "source": "voice",
        "text_hash": text_fingerprint(text),
        "text_len": len(text),
    })
    return decision


def ingest_transcript(usdviewApi, transcript, shadow=True):
    """Record and route a transcript without applying the proposal."""
    text = str(transcript)
    decision = propose_transcript(text)

    record_event(usdviewApi, "voice_ingress", {
        "text_hash": text_fingerprint(text),
        "text_len": len(text),
        "matched": decision.action is not None,
        "proposed_action": action_signature(decision.action),
    })

    if shadow:
        schedule_shadow(usdviewApi, text, decision)

    return decision
