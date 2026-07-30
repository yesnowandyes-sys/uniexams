"""Tests for the chemistry stoichiometry gate."""

from __future__ import annotations

import chem_stoich_check as cs  # type: ignore


def test_balanced_combustion():
    result = cs.check({"worked_solution": "CH4 + 2O2 → CO2 + 2H2O"})
    assert result["pass"]
    assert result["score"] == 1.0
    assert result["equations_checked"] == 1


def test_balanced_synthesis():
    result = cs.check({"worked_solution": "N2 + 3H2 → 2NH3"})
    assert result["pass"]


def test_unbalanced_simple():
    result = cs.check({"worked_solution": "H2 + O2 → H2O"})
    assert not result["pass"]
    assert result["score"] == 0.0


def test_unbalanced_complex():
    result = cs.check({"worked_solution": "Fe + O2 → Fe2O3"})
    assert not result["pass"]


def test_no_equations_unsolvable():
    result = cs.check({"worked_solution": "The answer is 42."})
    assert result["pass"]
    assert result["score"] == 0.5
    assert result["equations_checked"] == 0


def test_empty_solution_unsolvable():
    result = cs.check({"worked_solution": ""})
    assert result["pass"]
    assert result["score"] == 0.5


def test_backend_reported():
    """Gate must report which backend (rdkit / fallback) was used."""
    result = cs.check({"worked_solution": "CH4 + 2O2 → CO2 + 2H2O"})
    assert result["backend"] in {"rdkit", "fallback"}
