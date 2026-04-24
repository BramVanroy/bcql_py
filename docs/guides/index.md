# Guides

These guides cover the BCQL query constructs supported by `bcql_py`, together with patterns
for integrating the library in real projects.

Much of the BCQL reference material is adapted from the official
[BlackLab query documentation](https://github.com/instituutnederlandsetaal/BlackLab/tree/dev/site/docs/guide/040_query-language).

| Guide | What you will learn |
|---|---|
| [Token queries](tokens.md) | Matching tokens, sequences, repetitions, lookaround, spans, captures |
| [Relations](relations.md) | Dependency-relation queries and root relations |
| [Parallel corpora](parallel.md) | Alignment operators for parallel-corpus search |
| [LLM workflows](llm-workflows.md) | Agentic retry loops using `BCQLSyntaxError` feedback |
| [AST & parser design](ast-design.md) | Internal architecture and the Pydantic node hierarchy |
| [BCQL cheatsheet](cheatsheet.md) | Quick-reference tables for every BCQL construct |
| [Operators & CQL compatibility](misc.md) | Operator precedence and CQL compatibility notes |
