#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Model-router seam for future Jev and voice experiments.

Routers are deliberately side-effect free. They may propose UsdAction objects;
only the deterministic executor in actions.py may touch usdview.
"""

from .actions import UsdAction


class RouteDecision(object):
    __slots__ = ("action", "reason", "router")

    def __init__(self, action, reason="", router="deterministic"):
        if action is not None and not isinstance(action, UsdAction):
            raise TypeError("RouteDecision.action must be UsdAction or None")
        self.action = action
        self.reason = str(reason)
        self.router = str(router)


class ShadowRouter(object):
    """Compare a candidate router with a deterministic decision without acting."""

    def __init__(self, candidate, name="shadow"):
        self._candidate = candidate
        self._name = name

    def compare(self, text, context, deterministic_decision):
        candidate = self._candidate(text, context)
        deterministic_action = _action_dict(deterministic_decision.action)
        candidate_action = _action_dict(candidate.action)
        return {
            "router": self._name,
            "text": text,
            "deterministic": deterministic_action,
            "candidate": candidate_action,
            "agree": deterministic_action == candidate_action,
            "candidate_reason": candidate.reason,
        }


def _action_dict(action):
    return action.to_dict() if action is not None else None
