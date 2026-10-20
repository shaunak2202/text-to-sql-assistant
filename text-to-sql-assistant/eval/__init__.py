"""
Evaluation harness for the Text-to-SQL Query Assistant.

Measures *result correctness* of generated SQL against a small hand-labeled
set of (question, reference SQL) pairs, rather than comparing generated SQL
text against an expected string — two differently-written but equivalent
queries both count as correct. See eval/run_eval.py.
"""
