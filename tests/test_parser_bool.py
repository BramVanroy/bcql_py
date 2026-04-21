"""Tests for sequence-level boolean operators ``|``, ``&``, and (perhaps unexpectedly) ``->``.

Per ``Bcql.g4``'s ``booleanOperator`` rule, all three share the same precedence and are left-associative.
That is a parser peculiarity worth calling out because readers often expect ``&`` to bind tighter than ``|``.
Boolean operators also bind looser than sequence juxtaposition, so ``"New" "York" | "Los" "Angeles"`` is
parsed as ``("New" "York") | ("Los" "Angeles")``.
"""

from conftest import round_trip_test

from bcql_py.models.sequence import (
    GroupNode,
    NegationNode,
    RepetitionNode,
    SequenceBoolNode,
    SequenceNode,
)
from bcql_py.models.token import AnnotationConstraint, TokenQuery
from bcql_py.parser import parse


class TestSequenceUnion:
    """``|`` at the sequence level for alternative tokens or phrases."""

    def test_simple_union(self):
        """``[lemma="go"] | [lemma="come"]`` - alternative lemma queries on one token position.

        Searches for: tokens whose lemma is ``go`` OR whose lemma is ``come``.
        Interpretation: this would match forms like "go", "goes", "went", "come", "comes", "came"
        at the same token position, depending on corpus lemmatization.
        """
        node = parse('[lemma="go"] | [lemma="come"]')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, TokenQuery)
        assert isinstance(node.right, TokenQuery)
        assert isinstance(node.left.constraint, AnnotationConstraint)
        assert node.left.constraint.annotation == "lemma"
        assert node.left.constraint.value.value == "go"
        assert isinstance(node.right.constraint, AnnotationConstraint)
        assert node.right.constraint.annotation == "lemma"
        assert node.right.constraint.value.value == "come"

    def test_union_with_sequences(self):
        """``"New" "York" | "Los" "Angeles"`` keeps each place name together.

        Searches for: the two-token phrase ``New York`` OR the two-token phrase ``Los Angeles``.
        Sequence juxtaposition binds tighter than ``|``, so each place name is parsed as one phrase
        before the union is applied.

        So with parens that is the same as ``("New" "York") | ("Los" "Angeles")``
        """
        node = parse('"New" "York" | "Los" "Angeles"')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, SequenceNode)
        assert len(node.left.children) == 2
        assert isinstance(node.right, SequenceNode)
        assert len(node.right.children) == 2

    def test_three_way_union_left_assoc(self):
        """``"although" | "because" | "while"`` groups from the left.

        Searches for: any of the three discourse markers ``although``, ``because``, or ``while``.
        Parser detail: all sequence-level boolean operators are left-associative, so this builds
        ``("although" | "because") | "while"``.
        """
        node = parse('"although" | "because" | "while"')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, SequenceBoolNode)
        assert node.left.operator == "|"
        assert isinstance(node.right, TokenQuery)

    def test_round_trip_union(self):
        """Round-trip: lemma-level union preserves alternative structure."""
        round_trip_test('[lemma="go"] | [lemma="come"]')

    def test_round_trip_union_sequences(self):
        """Round-trip: multi-token alternatives preserve sequence grouping."""
        round_trip_test('"New" "York" | "Los" "Angeles"')

    def test_round_trip_three_way(self):
        """Round-trip: three-way union preserves left-associative grouping."""
        round_trip_test('"although" | "because" | "while"')


class TestSequenceIntersection:
    """``&`` at the sequence level."""

    def test_simple_intersection(self):
        """``[lemma="search"] [] & [] [pos="NOUN"]`` - intersect two sequence patterns.

        Searches for: positions satisfying BOTH sequence constraints: one side anchored by lemma
        ``search`` and the other side anchored by a noun constraint.
        Interpretation: think of two query lenses over the same region; ``&`` keeps only hits
        that survive both lenses.
        """
        node = parse('[lemma="search"] [] & [] [pos="NOUN"]')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "&"
        assert isinstance(node.left, SequenceNode)
        assert isinstance(node.right, SequenceNode)

    def test_round_trip_intersection(self):
        """Round-trip: sequence intersection preserves both sequence operands."""
        round_trip_test('[lemma="search"] [] & [] [pos="NOUN"]')


class TestSequenceImplication:
    """``->`` implication at the sequence level.

    This form is less idiomatic than constraint-level implication, but the parser accepts it and
    applies the same precedence rules as ``|`` and ``&``.
    """

    def test_simple_implication(self):
        """``[word="not"] -> [pos="ADV"]`` - if the token is ``not``, it must parse as an adverb.

        NOTE: it is my assumption that by default this holds for the same token position, but maybe that is
        not true and we need an explicit capture to enforce that?

        Searches for: a conditional constraint at sequence-bool level: if ``word="not"`` holds,
        then ``pos="ADV"`` must also hold at that position.
        Interpretation: this encodes a consistency rule for an annotation layer.
        """
        node = parse('[word="not"] -> [pos="ADV"]')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "->"
        assert isinstance(node.left, TokenQuery)
        assert isinstance(node.right, TokenQuery)

    def test_round_trip_implication(self):
        """Round-trip: sequence-level implication preserves structure."""
        round_trip_test('[word="not"] -> [pos="ADV"]')


class TestMixedBoolOperators:
    """Mixed ``&``, ``|``, ``->`` at the same precedence level.

    The important parser behaviour is that there is no built-in precedence priority between these
    three operators. Grouping is driven solely by left-associativity unless parentheses intervene.
    """

    def test_union_then_intersection(self):
        """``[pos="NN"] | [pos="NNS"] & [lemma="analysis"]`` groups as written from the left.

        Searches for: the intersection of ``([pos="NN"] | [pos="NNS"])`` with ``[lemma="analysis"]``.
        In plain language: first allow singular OR plural noun tags, then require lemma
        ``analysis`` as well.
        NOTE: in other languages we might expect ``&`` to bind tighter than ``|``, but BCQL keeps them
        at the same precedence, so grouping is left-to-right.
        """
        node = parse('[pos="NN"] | [pos="NNS"] & [lemma="analysis"]')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "&"
        assert isinstance(node.left, SequenceBoolNode)
        assert node.left.operator == "|"
        assert isinstance(node.right, TokenQuery)

    def test_intersection_then_union(self):
        """``[lemma="be"] & [pos="V"] | [word="is"]`` keeps the left intersection together.

        Searches for: ``([lemma="be"] & [pos="V"])`` OR ``[word="is"]``.
        In plain language: either a token that is both a verb and has lemma ``be``, or a token
        that is literally ``is``.
        """
        node = parse('[lemma="be"] & [pos="V"] | [word="is"]')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, SequenceBoolNode)
        assert node.left.operator == "&"

    def test_implication_mixed(self):
        """``[word="not"] -> [pos="ADV"] | [word="never"]`` groups implication first.

        Searches for: ``([word="not"] -> [pos="ADV"])`` OR ``[word="never"]``.
        Interpretation: enforce a conditional for ``not``, while also allowing ``never`` as an
        alternative branch.
        Because ``->`` shares precedence with ``|``, left-to-right grouping yields exactly that AST.
        With parentheses that is the same as ``([word="not"] -> [pos="ADV"]) | [word="never"]``.
        """
        node = parse('[word="not"] -> [pos="ADV"] | [word="never"]')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, SequenceBoolNode)
        assert node.left.operator == "->"

    def test_round_trip_mixed_union_intersection(self):
        """Round-trip: mixed ``|`` and ``&`` preserves left-associative grouping."""
        round_trip_test('[pos="NN"] | [pos="NNS"] & [lemma="analysis"]')

    def test_round_trip_mixed_implication(self):
        """Round-trip: mixed ``->`` and ``|`` preserves left-associative grouping."""
        round_trip_test('[word="not"] -> [pos="ADV"] | [word="never"]')


class TestBoolWithGroups:
    """Boolean operators interacting with groups, negation, and repetition."""

    def test_group_overrides_precedence(self):
        """``[lemma="go"] | ([pos="V"] & [word="went"])`` uses parentheses to force grouping.

        Searches for: [a form with lemma ``go``] OR [the intersection ``&`` of a token that is a
        verb AND is the word ``went``].
        Interpretation: "tokens lemmatized as go OR tokens simultaneously tagged as verbs and surface-form ``went``".
        Without parentheses the parser would group left-to-right; here the grouped right branch is
        preserved as a ``GroupNode``.
        """
        node = parse('[lemma="go"] | ([pos="V"] & [word="went"])')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, TokenQuery)
        assert isinstance(node.right, GroupNode)
        inner = node.right.child
        assert isinstance(inner, SequenceBoolNode)
        assert inner.operator == "&"

    def test_union_with_bracket_tokens(self):
        """``[word="however"] | [word="therefore"]`` - explicit annotation syntax on both sides.

        Searches for: tokens whose ``word`` annotation is either ``however`` or ``therefore``.
        Interpretation: find either of two discourse connectors in running text.
        This is the same sequence-level union as a bare-string alternative, but with explicit
        annotation names.
        """
        node = parse('[word="however"] | [word="therefore"]')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        left = node.left
        assert isinstance(left, TokenQuery)
        assert isinstance(left.constraint, AnnotationConstraint)
        assert left.constraint.annotation == "word"

    def test_negation_inside_union(self):
        """``![pos="DET"] | [word="the"]`` shows that negation binds tighter than ``|``.

        Searches for: tokens that are NOT determiners, OR tokens whose word is exactly ``the``.
        Interpretation: this broad branch demonstrates precedence, not a typical search strategy.
        The parser reads this as ``(![pos="DET"]) | [word="the"]``, not as negation of the whole
        union.
        """
        node = parse('![pos="DET"] | [word="the"]')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, NegationNode)
        assert isinstance(node.right, TokenQuery)

    def test_repetition_inside_union(self):
        """``[pos="ADJ"]+ | [pos="ADV"]*`` keeps each quantifier attached to its own operand.

        Searches for: one-or-more adjectives OR zero-or-more adverbs.
        Interpretation: the left branch can match adjective runs like "big green" (if tagged
        ADJ ADJ), while the right branch can match optional adverb stretches.
        Repetition applies before the boolean union, so both branches arrive as
        ``RepetitionNode`` operands.
        """
        node = parse('[pos="ADJ"]+ | [pos="ADV"]*')
        assert isinstance(node, SequenceBoolNode)
        assert node.operator == "|"
        assert isinstance(node.left, RepetitionNode)
        assert isinstance(node.right, RepetitionNode)

    def test_round_trip_group_overrides(self):
        """Round-trip: parentheses preserve explicit grouping inside boolean expressions."""
        round_trip_test('[lemma="go"] | ([pos="V"] & [word="went"])')

    def test_round_trip_bracket_union(self):
        """Round-trip: annotation-based union preserves explicit token constraints."""
        round_trip_test('[word="however"] | [word="therefore"]')

    def test_round_trip_negation_in_union(self):
        """Round-trip: negation-in-union preserves span-level precedence."""
        round_trip_test('![pos="DET"] | [word="the"]')

    def test_round_trip_repetition_in_union(self):
        """Round-trip: repetition-in-union preserves quantified operands."""
        round_trip_test('[pos="ADJ"]+ | [pos="ADV"]*')
