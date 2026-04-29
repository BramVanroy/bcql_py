# LLM agentic workflows

[`BCQLSyntaxError`][bcql_py.exceptions.BCQLSyntaxError] is deliberately shaped for agentic retry loops:
its string form carries the offending query, a caret under the failure position, and a
short human-readable message. That makes it trivially forwardable to any LLM for
self-correction.

```
┌──────────────┐   BCQL string   ┌────────────┐  valid?
│    LLM       │ ──────────────► │   parse()  │───────► return valid BCQL
│  (any API)   │                 └─────┬──────┘
└──────┬───────┘                       │
       │                         │ error?
       └ ◄─────── str(error) ──────────┘
           (re-prompt with feedback)
```

---

## What the error looks like

```python
from bcql_py import parse, BCQLSyntaxError

try:
    parse('[pos=NOUN]')        # value is an identifier, not a string
except BCQLSyntaxError as err:
    print(err)
```

```
Expected a string value after 'pos'=, got IDENTIFIER ('NOUN')
  [pos=NOUN]
       ^
```

The error exposes structured attributes so callers can build custom prompts, highlights,
or JSON responses:

| Attribute | Description |
|---|---|
| `str(err)` | Full human-readable message including the caret-annotated source |
| `err.message` | Just the human-readable part, without the source line |
| `err.query` | The original BCQL query string |
| `err.position` | 0-based character offset of the problem |

---

## A minimal retry loop

The basic example below shows how a retry loop with an LLM might be implemented. The important bits are
that each failure adds `str(err)` to the prompt and the loop stops as soon as `parse()`
returns without raising.

```python
from bcql_py import parse, BCQLSyntaxError


def call_llm(prompt: str) -> str:
    """Replace with a real LLM call. Must return a BCQL query string."""
    raise NotImplementedError


def generate_bcql(user_query: str, max_attempts: int = 5) -> str:
    prompt = (
        "Generate a BCQL query for the following request. "
        "Respond with ONLY the query, no explanations.\n\n"
        f"Request: {user_query}"
    )

    for attempt in range(max_attempts):
        query = call_llm(prompt).strip()
        try:
            ast = parse(query)
            return ast.to_bcql()
        except BCQLSyntaxError as err:
            prompt += (
                f"\n\nPrevious attempt ({attempt + 1}): {query}\n"
                f"That query is invalid:\n{err}\n"
                "Output only the corrected BCQL query."
            )

    raise RuntimeError(f"Could not produce a valid BCQL query in {max_attempts} attempts.")
```
