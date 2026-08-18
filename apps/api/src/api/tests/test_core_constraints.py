from __future__ import annotations

import operator

import pytest

from api.core.constraints import (
    CSP,
    BacktrackingSolver,
    Constraint,
    Variable,
    all_solutions,
    solve,
)


def build_ordered_example() -> tuple[CSP, Variable, Variable, Variable]:
    a = Variable("A", [1, 2, 3, 4], position=(0.2, 0.9))
    b = Variable("B", [1, 2, 3, 4], position=(0.8, 0.9))
    c = Variable("C", [1, 2, 3, 4], position=(1.0, 0.3))

    problem = CSP(
        "ordered",
        [a, b, c],
        [
            Constraint([a, b], operator.lt, "A < B"),
            Constraint([b], lambda value: value != 2, "B != 2"),
            Constraint([b, c], operator.lt, "B < C"),
        ],
    )
    return problem, a, b, c


def test_variable_preserves_domain_order_and_identity() -> None:
    first = Variable("X", ["low", "medium", "high"])
    second = Variable("X", ["low", "medium", "high"])

    assert first.domain == ("low", "medium", "high")
    assert first.size == 3
    assert first != second
    assert repr(first) == "X"


def test_constraint_evaluates_only_when_scope_is_assigned() -> None:
    x = Variable("X", [1, 2, 3])
    y = Variable("Y", [1, 2, 3])
    constraint = Constraint([x, y], operator.lt, "X < Y")

    assert not constraint.can_evaluate({x: 1})
    assert constraint.can_evaluate({x: 1, y: 2})
    assert constraint.holds({x: 1, y: 2})
    assert not constraint.holds({x: 3, y: 2})


def test_csp_consistency_ignores_constraints_not_ready_to_evaluate() -> None:
    problem, a, b, c = build_ordered_example()

    assert problem.consistent({a: 1})
    assert problem.consistent({a: 1, b: 3})
    assert not problem.consistent({a: 3, b: 2})
    assert not problem.consistent({a: 2, b: 3, c: 1})


def test_legal_values_apply_unary_and_binary_constraints() -> None:
    problem, a, b, c = build_ordered_example()

    assert problem.legal_values(b, {a: 1}) == (3, 4)
    assert problem.legal_values(c, {a: 1, b: 3}) == (4,)

    with pytest.raises(ValueError, match="not part"):
        problem.legal_values(Variable("Z", [1]))


def test_default_solver_returns_a_complete_consistent_solution() -> None:
    problem, a, b, c = build_ordered_example()

    solution = solve(problem)

    assert solution is not None
    assert problem.complete(solution)
    assert problem.consistent(solution)
    assert solution in ({a: 1, b: 3, c: 4}, {a: 2, b: 3, c: 4})


def test_solver_enumerates_all_solutions_and_honors_limit() -> None:
    problem, a, b, c = build_ordered_example()

    solutions = all_solutions(problem)

    assert solutions == ({a: 1, b: 3, c: 4}, {a: 2, b: 3, c: 4})
    assert all_solutions(problem, limit=1) == ({a: 1, b: 3, c: 4},)


def test_solver_returns_none_for_unsatisfiable_problem() -> None:
    x = Variable("X", [1])
    problem = CSP(
        "unsatisfiable",
        [x],
        [
            Constraint([x], lambda value: value == 1, "X == 1"),
            Constraint([x], lambda value: value != 1, "X != 1"),
        ],
    )

    assert solve(problem) is None
    assert all_solutions(problem) == ()


def test_solver_accepts_partial_assignments() -> None:
    problem, a, b, c = build_ordered_example()
    solver = BacktrackingSolver(problem)

    solution = solver.solve({a: 2})

    assert solution == {a: 2, b: 3, c: 4}
    assert solver.num_expanded > 0


def test_csp_rejects_constraints_outside_the_problem() -> None:
    x = Variable("X", [1, 2])
    y = Variable("Y", [1, 2])

    with pytest.raises(ValueError, match="outside the CSP"):
        CSP("invalid", [x], [Constraint([x, y], operator.ne)])


def test_csp_builds_n_queens_with_fewer_pairwise_constraints() -> None:
    problem, rows = build_n_queens(4)

    solution = solve(problem)

    assert solution is not None
    assert problem.consistent(solution)
    assert sorted(solution[row] for row in rows) == [0, 1, 2, 3]
    assert len(problem.constraints) == 6


def build_n_queens(size: int) -> tuple[CSP, tuple[Variable, ...]]:
    rows = tuple(Variable(f"R{row}", range(size)) for row in range(size))
    constraints = [
        Constraint(
            [rows[left], rows[right]],
            non_attacking_rows(left, right),
            f"Q{left} safe from Q{right}",
        )
        for left in range(size)
        for right in range(left + 1, size)
    ]
    return CSP(f"{size}-queens", rows, constraints), rows


def non_attacking_rows(left_column: int, right_column: int):
    def no_attack(left_row: int, right_row: int) -> bool:
        return left_row != right_row and abs(left_row - right_row) != abs(
            left_column - right_column
        )

    return no_attack
