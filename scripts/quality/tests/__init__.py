"""Pytest tests for the ESAT 4-gate quality stack.

Run with `pytest shared/scripts/quality/tests/ -v` from the workspace root.

The LLM-backed gates are exercised against a mock client (monkey-patched
into `_llm.call_haiku`) so tests run offline and free.
"""
