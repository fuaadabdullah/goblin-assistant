from __future__ import annotations

from api.core.agents import Agent, Environment


class TrailWorld(Environment):
    def __init__(self):
        self.history = []

    def initial_percept(self):
        return {"events": []}

    def do(self, action):
        self.history.append(dict(action))
        return {"events": list(self.history)}


class BodyLayer(Environment):
    def __init__(self, world):
        self.world = world
        self.position = 0
        self.crashed = False

    def percept(self):
        return {"position": self.position, "crashed": self.crashed}

    def initial_percept(self):
        return self.percept()

    def do(self, action):
        if self.crashed:
            return self.percept()

        step = action["step"]
        self.position += step
        self.crashed = self.position < 0
        self.world.do({"position": self.position, "crashed": self.crashed})
        return self.percept()


class MiddleLayer(Environment):
    def __init__(self, lower):
        self.lower = lower
        self.percept = lower.initial_percept()
        self.commands_sent = 0

    def initial_percept(self):
        return {}

    def do(self, action):
        target = action["go_to"]
        timeout = action.get("timeout", -1)
        arrived = self.percept["position"] == target

        while not arrived and timeout != 0:
            direction = 1 if target > self.percept["position"] else -1
            self.percept = self.lower.do({"step": direction})
            self.commands_sent += 1
            timeout -= 1
            arrived = self.percept["position"] == target

        return {"arrived": arrived, "position": self.percept["position"]}


class TopLayer(Agent, Environment):
    def __init__(self, lower, locations, timeout=10):
        self.lower = lower
        self.locations = dict(locations)
        self.timeout = timeout
        self.visited = []

    def initial_percept(self):
        return {}

    def select_action(self, percept):
        return {"visit": percept.get("visit", [])}

    def do(self, plan):
        results = []
        for location in plan["visit"]:
            result = self.lower.do(
                {"go_to": self.locations[location], "timeout": self.timeout}
            )
            self.visited.append(location)
            results.append({"location": location, **result})
        return {"visited": list(self.visited), "results": results}


def test_hierarchical_controller_layers_are_environments_for_layers_above():
    world = TrailWorld()
    body = BodyLayer(world)
    middle = MiddleLayer(body)
    top = TopLayer(middle, {"mail": 2, "storage": 4})

    result = top.do({"visit": ["mail", "storage"]})

    assert result == {
        "visited": ["mail", "storage"],
        "results": [
            {"location": "mail", "arrived": True, "position": 2},
            {"location": "storage", "arrived": True, "position": 4},
        ],
    }
    assert body.position == 4
    assert middle.commands_sent == 4
    assert world.history == [
        {"position": 1, "crashed": False},
        {"position": 2, "crashed": False},
        {"position": 3, "crashed": False},
        {"position": 4, "crashed": False},
    ]


def test_top_layer_can_bootstrap_agent_action_from_percept():
    top = TopLayer(lower=MiddleLayer(BodyLayer(TrailWorld())), locations={"mail": 1})

    assert top.initial_action({"visit": ["mail"]}) == {"visit": ["mail"]}
