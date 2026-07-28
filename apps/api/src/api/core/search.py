"""Reusable graph-search primitives for agent experiments.

The API mirrors the AI Python search examples while keeping the implementation
small, typed, and suitable for backend tests. Searchers are stateful: repeated
calls to ``search()`` return successive solutions until the frontier is empty.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
import heapq
from typing import Generic, Protocol, TypeVar

from api.core.agents import Displayable


NodeT = TypeVar("NodeT")


@dataclass(frozen=True)
class Arc(Generic[NodeT]):
    """A directed transition between two problem nodes."""

    from_node: NodeT
    to_node: NodeT
    cost: float = 1
    action: str | None = None

    def __post_init__(self) -> None:
        if self.cost < 0:
            raise ValueError("arc cost must be non-negative")


class SearchProblem(Protocol[NodeT]):
    """Protocol implemented by searchable problem definitions."""

    def start_node(self) -> NodeT:
        """Return the node where search begins."""

    def is_goal(self, node: NodeT) -> bool:
        """Return whether ``node`` is a goal."""

    def neighbors(self, node: NodeT) -> Iterable[Arc[NodeT]]:
        """Return outgoing arcs for ``node``."""

    def heuristic(self, node: NodeT) -> float:
        """Return an admissible or domain-specific heuristic for ``node``."""


@dataclass(frozen=True)
class Path(Generic[NodeT]):
    """A linked path from a start node through zero or more arcs."""

    initial: Path[NodeT] | NodeT
    arc: Arc[NodeT] | None = None

    def __post_init__(self) -> None:
        if self.arc is None:
            return
        if not isinstance(self.initial, Path):
            raise TypeError("a path with an arc must extend an existing Path")
        if self.initial.end() != self.arc.from_node:
            raise ValueError("arc must start at the end of the initial path")

    @property
    def cost(self) -> float:
        """Total path cost."""
        if self.arc is None:
            return 0
        return self.initial.cost + self.arc.cost

    def end(self) -> NodeT:
        """Return the final node on the path."""
        if self.arc is None:
            return self.initial
        return self.arc.to_node

    def nodes(self) -> tuple[NodeT, ...]:
        """Return nodes in start-to-end order."""
        if self.arc is None:
            return (self.initial,)
        return (*self.initial.nodes(), self.arc.to_node)

    def initial_nodes(self) -> tuple[NodeT, ...]:
        """Return ancestor nodes before this path's final node."""
        nodes = self.nodes()
        return nodes[:-1]

    def arcs(self) -> tuple[Arc[NodeT], ...]:
        """Return arcs in start-to-end order."""
        if self.arc is None:
            return ()
        return (*self.initial.arcs(), self.arc)

    def __str__(self) -> str:
        return " --> ".join(str(node) for node in self.nodes())


class FrontierPQ(Generic[NodeT]):
    """Priority-queue frontier for best-first style searchers."""

    def __init__(self) -> None:
        self.frontier_index = 0
        self.frontierpq: list[tuple[float, int, Path[NodeT]]] = []

    def empty(self) -> bool:
        return not self.frontierpq

    def add(self, path: Path[NodeT], value: float) -> None:
        """Add a path with a priority value to minimize.

        The negative insertion index preserves the AI Python behavior: when two
        paths have the same priority, the most recently added path is expanded
        first. That makes priority search line up with depth-first tie-breaking.
        """
        self.frontier_index += 1
        heapq.heappush(self.frontierpq, (value, -self.frontier_index, path))

    def pop(self) -> Path[NodeT]:
        _, _, path = heapq.heappop(self.frontierpq)
        return path

    def count(self, value: float) -> int:
        return sum(1 for frontier_value, _, _ in self.frontierpq if frontier_value == value)

    def __len__(self) -> int:
        return len(self.frontierpq)

    def __iter__(self) -> Iterator[Path[NodeT]]:
        for _, _, path in self.frontierpq:
            yield path

    def __repr__(self) -> str:
        return str([(value, index, str(path)) for value, index, path in self.frontierpq])


class Searcher(Displayable, Generic[NodeT], Iterator[Path[NodeT]]):
    """Depth-first searcher that returns one solution per ``search()`` call."""

    def __init__(self, problem: SearchProblem[NodeT]):
        self.problem = problem
        self.initialize_frontier()
        self.num_expanded = 0
        self.solution: Path[NodeT] | None = None
        self.path: Path[NodeT] | None = None
        self.add_to_frontier(Path(problem.start_node()))
        super().__init__()

    def initialize_frontier(self) -> None:
        self.frontier: list[Path[NodeT]] | deque[Path[NodeT]] | FrontierPQ[NodeT] = []

    def empty_frontier(self) -> bool:
        return len(self.frontier) == 0

    def add_to_frontier(self, path: Path[NodeT]) -> None:
        self.frontier.append(path)

    def pop_frontier(self) -> Path[NodeT]:
        return self.frontier.pop()

    def ordered_neighbors(self, arcs: Iterable[Arc[NodeT]]) -> Sequence[Arc[NodeT]]:
        """Return neighbor arcs in the order they should be added."""
        return list(reversed(list(arcs)))

    def search(self) -> Path[NodeT] | None:
        """Return the next path to a goal, or ``None`` when exhausted."""
        while not self.empty_frontier():
            self.path = self.pop_frontier()
            self.num_expanded += 1

            if self.problem.is_goal(self.path.end()):
                self.solution = self.path
                self.display(
                    1,
                    f"Solution: {self.path} (cost: {self.path.cost})",
                    self.num_expanded,
                    "paths have been expanded and",
                    len(self.frontier),
                    "paths remain in the frontier",
                )
                return self.path

            self.display(4, f"Expanding: {self.path} (cost: {self.path.cost})")
            neighbors = list(self.problem.neighbors(self.path.end()))
            self.display(2, f"Expanding: {self.path} with neighbors {neighbors}")
            for arc in self.ordered_neighbors(neighbors):
                self.add_to_frontier(Path(self.path, arc))
            self.display(3, f"New frontier: {[path.end() for path in self.frontier]}")

        self.display(0, "No (more) solutions. Total of", self.num_expanded, "paths expanded.")
        return None

    def __iter__(self) -> Searcher[NodeT]:
        return self

    def __next__(self) -> Path[NodeT]:
        path = self.search()
        if path is None:
            raise StopIteration
        return path


class BreadthFirstSearcher(Searcher[NodeT]):
    """First-in, first-out frontier searcher."""

    def initialize_frontier(self) -> None:
        self.frontier = deque()

    def pop_frontier(self) -> Path[NodeT]:
        return self.frontier.popleft()

    def ordered_neighbors(self, arcs: Iterable[Arc[NodeT]]) -> Sequence[Arc[NodeT]]:
        return list(arcs)


class PrioritySearcher(Searcher[NodeT]):
    """Base class for priority-queue searchers."""

    def initialize_frontier(self) -> None:
        self.frontier = FrontierPQ()

    def empty_frontier(self) -> bool:
        return self.frontier.empty()

    def pop_frontier(self) -> Path[NodeT]:
        return self.frontier.pop()

    def add_to_frontier(self, path: Path[NodeT]) -> None:
        self.frontier.add(path, self.priority(path))

    def priority(self, path: Path[NodeT]) -> float:
        raise NotImplementedError("PrioritySearcher.priority")


class AStarSearcher(PrioritySearcher[NodeT]):
    """A* search using path cost plus the problem heuristic."""

    def priority(self, path: Path[NodeT]) -> float:
        return path.cost + self.problem.heuristic(path.end())


class BestFirstSearcher(PrioritySearcher[NodeT]):
    """Best-first search using only the problem heuristic."""

    def priority(self, path: Path[NodeT]) -> float:
        return self.problem.heuristic(path.end())


class LowestCostFirstSearcher(PrioritySearcher[NodeT]):
    """Uniform-cost search using only accumulated path cost."""

    def priority(self, path: Path[NodeT]) -> float:
        return path.cost


class DFBranchAndBound(Searcher[NodeT]):
    """Depth-first branch-and-bound searcher returning the optimal solution.

    Explores the full reachable frontier, pruning branches whose cost plus
    heuristic already meets or exceeds the current best. Each call to
    ``search()`` resets the frontier and refines ``self.bound``, so
    successive calls converge toward the optimum.
    """

    def __init__(self, problem: SearchProblem[NodeT], bound: float = float("inf")) -> None:
        super().__init__(problem)
        self.best_path: Path[NodeT] | None = None
        self.bound = bound

    def search(self) -> Path[NodeT] | None:
        """Return the optimal path with cost less than the current bound, or None."""
        self.frontier: list[Path[NodeT]] = [Path(self.problem.start_node())]
        self.num_expanded = 0
        while self.frontier:
            self.path = self.frontier.pop()
            if self.path.cost + self.problem.heuristic(self.path.end()) < self.bound:
                self.num_expanded += 1
                if self.problem.is_goal(self.path.end()):
                    self.best_path = self.path
                    self.bound = self.path.cost
                    self.display(1, f"New best path: {self.path} cost: {self.path.cost}")
                else:
                    self.display(2, f"Expanding: {self.path} (cost: {self.path.cost})")
                    for arc in reversed(list(self.problem.neighbors(self.path.end()))):
                        self.add_to_frontier(Path(self.path, arc))
                    self.display(3, f"New frontier: {[p.end() for p in self.frontier]}")
        self.path = self.best_path
        self.solution = self.best_path
        self.display(
            1,
            f"Optimal solution: {self.best_path}." if self.best_path else "No solution found.",
            f"Paths expanded: {self.num_expanded}.",
        )
        return self.best_path


class SearcherMPP(AStarSearcher[NodeT]):
    """A* searcher with multiple-path pruning."""

    def __init__(self, problem: SearchProblem[NodeT]):
        super().__init__(problem)
        self.explored: set[NodeT] = set()

    def search(self) -> Path[NodeT] | None:
        while not self.empty_frontier():
            self.path = self.pop_frontier()
            if self.path.end() in self.explored:
                continue

            self.explored.add(self.path.end())
            self.num_expanded += 1
            if self.problem.is_goal(self.path.end()):
                self.solution = self.path
                self.display(
                    1,
                    f"Solution: {self.path} (cost: {self.path.cost})",
                    self.num_expanded,
                    "paths have been expanded and",
                    len(self.frontier),
                    "paths remain in the frontier",
                )
                return self.path

            self.display(4, f"Expanding: {self.path} (cost: {self.path.cost})")
            neighbors = list(self.problem.neighbors(self.path.end()))
            self.display(2, f"Expanding: {self.path} with neighbors {neighbors}")
            for arc in self.ordered_neighbors(neighbors):
                self.add_to_frontier(Path(self.path, arc))
            self.display(3, f"New frontier: {[path.end() for path in self.frontier]}")

        self.display(0, "No (more) solutions. Total of", self.num_expanded, "paths expanded.")
        return None


class CyclePruningSearcher(Searcher[NodeT]):
    """Depth-first searcher that skips paths returning to their own ancestors."""

    def add_to_frontier(self, path: Path[NodeT]) -> None:
        if path.end() in path.initial_nodes():
            return
        super().add_to_frontier(path)


__all__ = [
    "AStarSearcher",
    "Arc",
    "BestFirstSearcher",
    "BreadthFirstSearcher",
    "CyclePruningSearcher",
    "DFBranchAndBound",
    "FrontierPQ",
    "LowestCostFirstSearcher",
    "Path",
    "PrioritySearcher",
    "SearchProblem",
    "Searcher",
    "SearcherMPP",
]
