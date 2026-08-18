"""Single-agent simulation primitives.

This module is a small platform boundary for agent/environment experiments:
agents choose dictionary-shaped actions from dictionary-shaped percepts, and
environments advance their own state by applying those actions. Hierarchical
controllers can implement ``Environment`` at each layer, treating the layer
below as their environment while exposing ``do(...)`` to the layer above.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

Percept = dict[str, Any]
Action = dict[str, Any]


class Displayable:
    """Mixin for opt-in diagnostic output controlled by display level."""

    display_level = 0

    def display(self, level: int, *values: object) -> None:
        if level <= self.display_level:
            print(*values)


class Agent(Displayable):
    """Base class for a single stateful agent."""

    def initial_action(self, percept: Percept) -> Action:
        """Return the first action for a percept.

        Agents can override this when bootstrapping differs from regular
        selection. The default keeps the common path identical to steady-state
        action selection.
        """
        return self.select_action(percept)

    def select_action(self, percept: Percept) -> Action:
        """Return the next action for a percept and update internal state."""
        raise NotImplementedError("Agent.select_action")


class Environment(Displayable):
    """Base class for a single-agent environment."""

    def initial_percept(self) -> Percept:
        """Return the first percept seen by the agent."""
        raise NotImplementedError("Environment.initial_percept")

    def do(self, action: Action) -> Percept:
        """Apply an action, update environment state, and return a percept."""
        raise NotImplementedError("Environment.do")


@dataclass(frozen=True)
class SimulationStep:
    """A completed agent/environment transition."""

    index: int
    percept: Percept
    action: Action
    next_percept: Percept


class Simulate(Displayable):
    """Run a single agent against an environment for a fixed number of steps."""

    def __init__(self, agent: Agent, environment: Environment):
        self.agent = agent
        self.env = environment
        self.percept = self.env.initial_percept()
        self.percept_history = [self.percept]
        self.action_history: list[Action] = []
        self.step_history: list[SimulationStep] = []

    def go(self, n: int) -> list[SimulationStep]:
        """Advance the simulation by ``n`` turns and return the new steps."""
        if n < 0:
            raise ValueError("simulation steps must be non-negative")

        steps: list[SimulationStep] = []
        for _ in range(n):
            index = len(self.step_history)
            current_percept = self.percept
            action = self.agent.select_action(current_percept)
            self.display(2, f"i={index} action={action}")

            next_percept = self.env.do(action)
            self.display(2, f" percept={next_percept}")

            step = SimulationStep(
                index=index,
                percept=current_percept,
                action=action,
                next_percept=next_percept,
            )
            self.percept = next_percept
            self.action_history.append(action)
            self.percept_history.append(next_percept)
            self.step_history.append(step)
            steps.append(step)

        return steps


__all__ = [
    "Action",
    "Agent",
    "Displayable",
    "Environment",
    "Percept",
    "Simulate",
    "SimulationStep",
]
