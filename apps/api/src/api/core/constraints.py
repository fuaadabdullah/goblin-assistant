"""Constraint satisfaction primitives for small deterministic reasoning tasks.

The core API models a CSP as variables with ordered domains plus constraints
over variable scopes. Solvers return assignments keyed by the original
``Variable`` objects, which keeps callers free to use display names that are not
globally unique while still supporting readable diagnostics.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, eq=False)
class Variable:
    """A named CSP variable with an ordered domain."""

    name: str
    domain: tuple[Any, ...]
    position: tuple[float, float] | None = None

    def __init__(
        self,
        name: str,
        domain: Iterable[Any],
        position: tuple[float, float] | None = None,
    ) -> None:
        domain_values = tuple(domain)
        if not name:
            raise ValueError("variable name must not be empty")
        if not domain_values:
            raise ValueError("variable domain must not be empty")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "domain", domain_values)
        object.__setattr__(self, "position", position)

    @property
    def size(self) -> int:
        return len(self.domain)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name


Assignment = Mapping[Variable, Any]


@dataclass(frozen=True)
class Constraint:
    """A Boolean predicate over one or more variables."""

    scope: tuple[Variable, ...]
    condition: Callable[..., bool]
    name: str | None = None
    position: tuple[float, float] | None = None

    def __init__(
        self,
        scope: Iterable[Variable],
        condition: Callable[..., bool],
        name: str | None = None,
        position: tuple[float, float] | None = None,
    ) -> None:
        scope_values = tuple(scope)
        if not scope_values:
            raise ValueError("constraint scope must not be empty")
        object.__setattr__(self, "scope", scope_values)
        object.__setattr__(self, "condition", condition)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "position", position)

    def can_evaluate(self, assignment: Assignment) -> bool:
        """Return whether every scoped variable is assigned."""
        return all(variable in assignment for variable in self.scope)

    def holds(self, assignment: Assignment) -> bool:
        """Return whether the constraint accepts the assigned scoped values."""
        return bool(self.condition(*(assignment[variable] for variable in self.scope)))

    def __repr__(self) -> str:
        if self.name:
            return self.name
        return f"Constraint({', '.join(variable.name for variable in self.scope)})"


@dataclass(frozen=True)
class CSP:
    """A constraint satisfaction problem."""

    title: str
    variables: tuple[Variable, ...]
    constraints: tuple[Constraint, ...]
    var_to_constraints: Mapping[Variable, tuple[Constraint, ...]] = field(init=False)

    def __init__(
        self,
        title: str,
        variables: Iterable[Variable],
        constraints: Iterable[Constraint],
    ) -> None:
        variable_values = tuple(variables)
        constraint_values = tuple(constraints)
        if not title:
            raise ValueError("CSP title must not be empty")
        if not variable_values:
            raise ValueError("CSP must define at least one variable")

        variable_set = set(variable_values)
        for constraint in constraint_values:
            unknown = [variable for variable in constraint.scope if variable not in variable_set]
            if unknown:
                names = ", ".join(variable.name for variable in unknown)
                raise ValueError(f"constraint references variables outside the CSP: {names}")

        buckets: dict[Variable, list[Constraint]] = {
            variable: [] for variable in variable_values
        }
        for constraint in constraint_values:
            for variable in constraint.scope:
                buckets[variable].append(constraint)

        object.__setattr__(self, "title", title)
        object.__setattr__(self, "variables", variable_values)
        object.__setattr__(self, "constraints", constraint_values)
        object.__setattr__(
            self,
            "var_to_constraints",
            {
                variable: tuple(variable_constraints)
                for variable, variable_constraints in buckets.items()
            },
        )

    def __str__(self) -> str:
        return self.title

    def __repr__(self) -> str:
        return f"CSP({self.title}, {list(self.variables)}, {list(self.constraints)})"

    def consistent(self, assignment: Assignment) -> bool:
        """Return whether all evaluable constraints hold for ``assignment``."""
        return all(
            constraint.holds(assignment)
            for constraint in self.constraints
            if constraint.can_evaluate(assignment)
        )

    def complete(self, assignment: Assignment) -> bool:
        """Return whether every variable has an assigned value."""
        return all(variable in assignment for variable in self.variables)

    def unassigned_variables(self, assignment: Assignment) -> tuple[Variable, ...]:
        """Return variables missing from ``assignment`` in problem order."""
        return tuple(variable for variable in self.variables if variable not in assignment)

    def legal_values(
        self,
        variable: Variable,
        assignment: Assignment | None = None,
    ) -> tuple[Any, ...]:
        """Return domain values that keep currently evaluable constraints valid."""
        if variable not in self.var_to_constraints:
            raise ValueError(f"variable {variable.name!r} is not part of this CSP")

        assignment_dict = dict(assignment or {})
        values: list[Any] = []
        for value in variable.domain:
            trial = {**assignment_dict, variable: value}
            if all(
                constraint.holds(trial)
                for constraint in self.var_to_constraints[variable]
                if constraint.can_evaluate(trial)
            ):
                values.append(value)
        return tuple(values)


class BacktrackingSolver:
    """Depth-first CSP solver with minimum-remaining-values variable choice."""

    def __init__(self, csp: CSP):
        self.csp = csp
        self.num_expanded = 0

    def solve(self, assignment: Assignment | None = None) -> dict[Variable, Any] | None:
        """Return one complete solution, or ``None`` when no solution exists."""
        return next(self.solutions(assignment=assignment, limit=1), None)

    def solutions(
        self,
        assignment: Assignment | None = None,
        *,
        limit: int | None = None,
    ) -> Iterator[dict[Variable, Any]]:
        """Yield complete solutions, preserving each variable's domain order."""
        if limit is not None and limit < 1:
            raise ValueError("solution limit must be positive")

        yielded = 0
        start = dict(assignment or {})
        if not self.csp.consistent(start):
            return

        for solution in self._search(start):
            yield solution
            yielded += 1
            if limit is not None and yielded >= limit:
                return

    def _search(self, assignment: dict[Variable, Any]) -> Iterator[dict[Variable, Any]]:
        if self.csp.complete(assignment):
            yield dict(assignment)
            return

        variable = self._select_unassigned_variable(assignment)
        for value in self.csp.legal_values(variable, assignment):
            self.num_expanded += 1
            trial = {**assignment, variable: value}
            if self._has_legal_continuation(trial):
                yield from self._search(trial)

    def _select_unassigned_variable(self, assignment: Assignment) -> Variable:
        unassigned = self.csp.unassigned_variables(assignment)
        return min(
            unassigned,
            key=lambda variable: (len(self.csp.legal_values(variable, assignment)), variable.size),
        )

    def _has_legal_continuation(self, assignment: Assignment) -> bool:
        return all(
            self.csp.legal_values(variable, assignment)
            for variable in self.csp.unassigned_variables(assignment)
        )


def solve(csp: CSP, assignment: Assignment | None = None) -> dict[Variable, Any] | None:
    """Return one solution for ``csp`` using the default solver."""
    return BacktrackingSolver(csp).solve(assignment=assignment)


def all_solutions(
    csp: CSP,
    assignment: Assignment | None = None,
    *,
    limit: int | None = None,
) -> tuple[dict[Variable, Any], ...]:
    """Return every solution for ``csp`` up to ``limit``."""
    return tuple(BacktrackingSolver(csp).solutions(assignment=assignment, limit=limit))


__all__ = [
    "Assignment",
    "BacktrackingSolver",
    "CSP",
    "Constraint",
    "Variable",
    "all_solutions",
    "solve",
]
