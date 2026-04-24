# Models overview

All AST node types inherit from [`BCQLNode`][bcql_py.models.base.BCQLNode].
Each node carries a `node_type` literal discriminator, making the full tree
serializable to/from JSON.

::: bcql_py.models
    options:
      show_root_heading: false
