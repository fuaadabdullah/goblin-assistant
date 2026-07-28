from __future__ import annotations

import pytest

from api.core.search import (
    AStarSearcher,
    Arc,
    BestFirstSearcher,
    BreadthFirstSearcher,
    CyclePruningSearcher,
    DFBranchAndBound,
    FrontierPQ,
    LowestCostFirstSearcher,
    Path,
    Searcher,
    SearcherMPP,
)


class WeightedGraphProblem:
    def __init__(
        self,
        edges: dict[str, list[tuple[str, float]]],
        *,
        start: str = "A",
        goals: set[str] | None = None,
        heuristic: dict[str, float] | None = None,
    ):
        self.edges = edges
        self.start = start
        self.goals = goals or {"G"}
        self.heuristics = heuristic or {}

    def start_node(self) -> str:
        return self.start

    def is_goal(self, node: str) -> bool:
        return node in self.goals

    def neighbors(self, node: str) -> list[Arc[str]]:
        return [Arc(node, to_node, cost) for to_node, cost in self.edges.get(node, [])]

    def heuristic(self, node: str) -> float:
        return self.heuristics.get(node, 0)


def solution_nodes(searcher_class, problem: WeightedGraphProblem) -> tuple[str, ...]:
    path = searcher_class(problem).search()
    assert path is not None
    return path.nodes()


def test_depth_first_search_expands_first_neighbor_first() -> None:
    problem = WeightedGraphProblem(
        {
            "A": [("B", 2), ("C", 1)],
            "B": [("G", 2)],
            "C": [("D", 1)],
            "D": [("G", 1)],
        }
    )

    assert solution_nodes(Searcher, problem) == ("A", "B", "G")


def test_breadth_first_search_uses_fifo_frontier() -> None:
    problem = WeightedGraphProblem(
        {
            "A": [("B", 1), ("C", 1)],
            "B": [("D", 1)],
            "C": [("E", 1)],
            "E": [("F", 1)],
            "F": [("G", 1)],
            "D": [("G", 1)],
        }
    )

    path = BreadthFirstSearcher(problem).search()

    assert path is not None
    assert path.nodes() == ("A", "B", "D", "G")


def test_priority_search_variants_use_their_own_cost_functions() -> None:
    problem = WeightedGraphProblem(
        {
            "A": [("B", 2), ("C", 1)],
            "B": [("G", 2)],
            "C": [("D", 1)],
            "D": [("G", 1)],
        },
        heuristic={"A": 3, "B": 2, "C": 1, "D": 1, "G": 0},
    )

    assert solution_nodes(BestFirstSearcher, problem) == ("A", "C", "D", "G")
    assert solution_nodes(LowestCostFirstSearcher, problem) == ("A", "C", "D", "G")
    assert solution_nodes(AStarSearcher, problem) == ("A", "C", "D", "G")


def test_searcher_iterates_over_multiple_solutions_until_exhausted() -> None:
    problem = WeightedGraphProblem(
        {
            "A": [("B", 1), ("C", 1)],
            "B": [("G1", 1)],
            "C": [("G2", 1)],
        },
        goals={"G1", "G2"},
    )

    searcher = Searcher(problem)

    assert [path.nodes() for path in searcher] == [("A", "B", "G1"), ("A", "C", "G2")]
    assert searcher.search() is None


def test_multiple_path_pruning_expands_duplicate_nodes_once() -> None:
    problem = WeightedGraphProblem(
        {
            "A": [("B", 1), ("C", 1)],
            "B": [("D", 2)],
            "C": [("D", 1)],
            "D": [("G", 1)],
        },
        heuristic={"A": 2, "B": 2, "C": 1, "D": 1, "G": 0},
    )

    searcher = SearcherMPP(problem)
    path = searcher.search()

    assert path is not None
    assert path.nodes() == ("A", "C", "D", "G")
    assert searcher.explored == {"A", "C", "D", "G"}


def test_cycle_pruning_skips_paths_back_to_ancestors() -> None:
    problem = WeightedGraphProblem(
        {
            "A": [("B", 1)],
            "B": [("A", 1), ("G", 1)],
        }
    )

    path = CyclePruningSearcher(problem).search()

    assert path is not None
    assert path.nodes() == ("A", "B", "G")


def test_priority_frontier_does_not_compare_paths_on_ties() -> None:
    first = Path("A")
    second = Path("B")
    frontier: FrontierPQ[str] = FrontierPQ()

    frontier.add(first, 1)
    frontier.add(second, 1)

    assert frontier.pop() is second
    assert frontier.pop() is first


def test_branch_and_bound_returns_optimal_path() -> None:
    # DFS would find A->B->G (cost 4); B&B should find the cheaper A->C->D->G (cost 3)
    problem = WeightedGraphProblem(
        {
            "A": [("B", 2), ("C", 1)],
            "B": [("G", 2)],
            "C": [("D", 1)],
            "D": [("G", 1)],
        }
    )

    searcher = DFBranchAndBound(problem)
    path = searcher.search()

    assert path is not None
    assert path.nodes() == ("A", "C", "D", "G")
    assert path.cost == 3


def test_branch_and_bound_prunes_with_initial_bound() -> None:
    problem = WeightedGraphProblem(
        {
            "A": [("B", 2), ("C", 1)],
            "B": [("G", 2)],
            "C": [("D", 1)],
            "D": [("G", 1)],
        }
    )

    # bound tighter than any solution path — nothing found
    searcher = DFBranchAndBound(problem, bound=2.0)
    path = searcher.search()

    assert path is None


def test_branch_and_bound_refines_bound_on_repeated_search() -> None:
    # First search finds A->B->G (cost 3), tightens bound to 3.
    # Second search can't improve (no path costs < 3), so it retains best_path
    # and expands fewer nodes because paths meeting the bound are pruned.
    problem = WeightedGraphProblem(
        {
            "A": [("G", 5), ("B", 1)],
            "B": [("G", 2)],
        }
    )

    searcher = DFBranchAndBound(problem)
    first = searcher.search()

    assert first is not None
    assert first.cost == 3  # A->B->G
    assert searcher.bound == 3
    first_expanded = searcher.num_expanded

    second = searcher.search()

    # best_path is retained from the first call; no new improvement found
    assert second is first
    # fewer nodes expanded because paths with cost >= bound are pruned
    assert searcher.num_expanded < first_expanded


def test_branch_and_bound_uses_heuristic_for_pruning() -> None:
    # Heuristic overestimates enough to prune the long path early
    problem = WeightedGraphProblem(
        {
            "A": [("B", 1), ("G", 10)],
            "B": [("G", 1)],
        },
        heuristic={"A": 0, "B": 0, "G": 0},
    )

    searcher = DFBranchAndBound(problem)
    path = searcher.search()

    assert path is not None
    assert path.nodes() == ("A", "B", "G")
    assert path.cost == 2


def test_path_rejects_invalid_arcs_and_negative_costs() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        Arc("A", "B", -1)

    with pytest.raises(ValueError, match="arc must start"):
        Path(Path("A"), Arc("B", "C"))
