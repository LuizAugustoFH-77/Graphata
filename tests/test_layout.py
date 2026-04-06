from core.automaton import Automaton
from utils.layout import compute_automaton_layout


def _build_automaton(state_count, edges):
    aut = Automaton()
    for idx in range(state_count):
        aut.add_state(f"q{idx}", is_initial=(idx == 0), is_final=(idx == state_count - 1))
    for source, symbol, target in edges:
        aut.add_transition(source, symbol, target)
    return aut


def test_layout_chain_flows_left_to_right():
    aut = _build_automaton(
        4,
        [
            ("q0", "a", "q1"),
            ("q1", "b", "q2"),
            ("q2", "c", "q3"),
        ],
    )

    positions = compute_automaton_layout(
        aut.states.keys(),
        aut.transitions,
        [state.name for state in aut.get_initial_states()],
        900,
        500,
    )

    assert positions["q0"][0] < positions["q1"][0] < positions["q2"][0] < positions["q3"][0]


def test_layout_keeps_nodes_inside_canvas_and_separated():
    aut = _build_automaton(
        9,
        [
            ("q0", "a", "q1"),
            ("q0", "b", "q2"),
            ("q1", "c", "q3"),
            ("q1", "d", "q4"),
            ("q2", "e", "q5"),
            ("q2", "f", "q6"),
            ("q3", "g", "q7"),
            ("q6", "h", "q7"),
            ("q7", "i", "q8"),
            ("q4", "j", "q2"),
        ],
    )

    positions = compute_automaton_layout(
        aut.states.keys(),
        aut.transitions,
        [state.name for state in aut.get_initial_states()],
        1100,
        700,
    )

    assert len(positions) == len(aut.states)

    for x, y in positions.values():
        assert 0 <= x <= 1100
        assert 0 <= y <= 700

    rounded = {(round(x, 1), round(y, 1)) for x, y in positions.values()}
    assert len(rounded) == len(positions)


def test_layout_handles_large_automaton_without_collapsing_into_one_column():
    aut = Automaton()
    total = 36
    for idx in range(total):
        aut.add_state(f"q{idx}", is_initial=(idx == 0), is_final=(idx == total - 1))

    for idx in range(total - 1):
        aut.add_transition(f"q{idx}", "a", f"q{idx + 1}")
        if idx + 3 < total:
            aut.add_transition(f"q{idx}", "b", f"q{idx + 3}")
        if idx % 5 == 0 and idx + 7 < total:
            aut.add_transition(f"q{idx + 7}", "c", f"q{idx}")

    positions = compute_automaton_layout(
        aut.states.keys(),
        aut.transitions,
        [state.name for state in aut.get_initial_states()],
        1400,
        900,
    )

    xs = [x for x, _ in positions.values()]
    ys = [y for _, y in positions.values()]

    assert max(xs) - min(xs) > 500
    assert max(ys) - min(ys) > 250
