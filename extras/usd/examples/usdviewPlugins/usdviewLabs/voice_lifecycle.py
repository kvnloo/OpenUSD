#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Thread-safe utterance generation gate for realtime voice."""

import threading


class GenerationGate(object):
    """Reject stale generations and make cancellation dominate acceptance."""

    def __init__(self):
        self._lock = threading.Lock()
        self._latest = -1
        self._cancelled = False

    def observe(self, message):
        generation = int(message["generation"])
        op = str(message["op"])

        with self._lock:
            if generation < self._latest:
                return False

            if generation > self._latest:
                self._latest = generation
                self._cancelled = (op == "cancel")
                return True

            # Same-generation messages can advance to cancellation, but a
            # cancelled generation cannot be resurrected by a replayed start
            # or final message.
            if op == "cancel":
                self._cancelled = True

            return True

    def can_execute(self, generation):
        with self._lock:
            return (
                int(generation) == self._latest and
                not self._cancelled)

    def is_cancelled(self, generation):
        with self._lock:
            return (
                int(generation) == self._latest and
                self._cancelled)

    def latest(self):
        with self._lock:
            return self._latest
