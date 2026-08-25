from __future__ import annotations

import pytest

from api.core.agents import Agent, Environment, Simulate


class CountingAgent(Agent):
    def __init__(self):
        self.seen = []

    def select_action(self, percept):
        self.seen.append(dict(percept))
        return {"increment": percept["target"] - percept["value"]}


class CounterEnvironment(Environment):
    def __init__(self, target=3):
        self.value = 0
        self.target = target

    def initial_percept(self):
        return {"value": self.value, "target": self.target}

    def do(self, action):
        self.value += action["increment"]
        return {"value": self.value, "target": self.target}


def test_initial_action_defaults_to_select_action():
    agent = CountingAgent()

    action = agent.initial_action({"value": 1, "target": 4})

    assert action == {"increment": 3}
    assert agent.seen == [{"value": 1, "target": 4}]


def test_environment_and_agent_abstract_methods_raise():
    with pytest.raises(NotImplementedError, match="Agent.select_action"):
        Agent().select_action({})

    with pytest.raises(NotImplementedError, match="Environment.initial_percept"):
        Environment().initial_percept()

    with pytest.raises(NotImplementedError, match="Environment.do"):
        Environment().do({})


def test_simulate_chains_agent_actions_and_environment_percepts():
    agent = CountingAgent()
    environment = CounterEnvironment(target=5)
    simulation = Simulate(agent, environment)

    steps = simulation.go(2)

    assert environment.value == 5
    assert steps[0].index == 0
    assert steps[0].percept == {"value": 0, "target": 5}
    assert steps[0].action == {"increment": 5}
    assert steps[0].next_percept == {"value": 5, "target": 5}
    assert steps[1].index == 1
    assert steps[1].action == {"increment": 0}
    assert simulation.percept == {"value": 5, "target": 5}
    assert simulation.percept_history == [
        {"value": 0, "target": 5},
        {"value": 5, "target": 5},
        {"value": 5, "target": 5},
    ]
    assert simulation.action_history == [{"increment": 5}, {"increment": 0}]
    assert simulation.step_history == steps
    assert agent.seen == [
        {"value": 0, "target": 5},
        {"value": 5, "target": 5},
    ]


def test_simulate_rejects_negative_steps():
    simulation = Simulate(CountingAgent(), CounterEnvironment())

    with pytest.raises(ValueError, match="non-negative"):
        simulation.go(-1)
