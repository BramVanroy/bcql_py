"""Using ``bcql_py`` in an LLM agentic workflow.

The recommended pattern for LLM-driven BCQL generation is:

  1. Ask the LLM to produce a BCQL query in free-form text.
  2. Validate the output with ``parse()``.
  3. If validation fails, send ``str(error)`` back to the LLM as feedback.
  4. Retry until the query is valid (or a max-attempt limit is reached).

``BCQLSyntaxError`` reports the exact character position of the problem and
includes a visual caret so the LLM can see precisely where it went wrong and
hopefully fix the issue.

This example is not an actual LLM integration (we do not want to clutter the
project dependencies) but it should give you an idea of how the code can be
used with LLMs. At the bottom, pseudocode is given to show potential
"real-world" usage.
"""

from __future__ import annotations

from bcql_py import BCQLSyntaxError, parse


SECTION_SEPARATOR = "=" * 70


def print_section(title: str) -> None:
    """Print a clearly delimited section header.

    Args:
        title: The title to display.
    """
    print(f"\n{SECTION_SEPARATOR}\n{title}\n{SECTION_SEPARATOR}")


def validate_with_feedback(attempts: list[str]) -> None:
    """Simulate asking an LLM, catching errors, and reprompting.

    In a real system ``attempts`` would be produced by successive LLM calls,
    each informed by the previous error message. Here we supply them up front
    to keep the example self-contained.

    Args:
        attempts: The sequence of candidate BCQL queries to try in order.
    """
    for idx, query in enumerate(attempts, 1):
        print(f"\n--- Attempt {idx} ---")
        print(f"LLM output: {query!r}")
        try:
            ast = parse(query)
            print(f"Valid BCQL: {ast.to_bcql()}")
            return
        except BCQLSyntaxError as err:
            print("Validation failed. Feedback for LLM:")
            # str(err) is what you append to the next LLM prompt. It contains
            # the error description, the original query, and a caret pointing
            # to the failure position. Note that you have to use str(err) to
            # get the formatted message; just printing the exception object
            # won't include the query or caret!
            print(str(err))

    print("\nAll attempts exhausted without a valid query.")


print_section("1. Recovering from bracket / paren mismatches")

syntax_attempts = [
    # Attempt 1: unclosed bracket
    '[word="baker"',
    # Attempt 2: LLM overcorrects but adds a stray paren
    '[word="baker")',
    # Attempt 3: valid
    '[word="baker"]',
]
validate_with_feedback(syntax_attempts)


"""
# Pseudocode for integrating with any OpenAI-compatible LLM API:

    from openai import OpenAI
    MAX_ATTEMPTS = 5

    client = OpenAI(...)
    messages = [
        {"role": "system", "content": "Generate a BCQL query for the following user query."},
        {"role": "user",   "content": user_request},
    ]

    for attempt in range(MAX_ATTEMPTS):
        response = client.chat.completions.create(
            model="your-model",
            messages=messages,
        )
        query = response.choices[0].message.content.strip()
        try:
            ast = parse(query)
            break  # success
        except BCQLSyntaxError as err:
            messages.append({"role": "assistant", "content": query})
            messages.append({
                "role": "user",
                "content": (
                    f"That query is invalid:\n\n{err}\n\n"
                    "Please fix it and output only the corrected BCQL query."
                ),
            })
    else:
        raise RuntimeError(f"LLM could not produce a valid BCQL query after {MAX_ATTEMPTS} attempts.")
"""
