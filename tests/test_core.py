from core.automaton import Automaton
from core.simulator import Simulator
from core.converter import Converter

def test_automaton_creation():
    aut = Automaton()
    aut.add_state("q0", is_initial=True)
    aut.add_state("q1", is_final=True)
    aut.add_transition("q0", "a", "q1")
    
    assert len(aut.states) == 2
    assert len(aut.transitions) == 1
    assert "a" in aut.alphabet

def test_simulator_accepted():
    aut = Automaton()
    aut.add_state("q0", is_initial=True)
    aut.add_state("q1", is_final=True)
    aut.add_transition("q0", "a", "q0")
    aut.add_transition("q0", "b", "q1")
    
    sim = Simulator(aut)
    assert sim.simulate("aab")["accepted"] == True
    
def test_simulator_rejected():
    aut = Automaton()
    aut.add_state("q0", is_initial=True)
    aut.add_state("q1", is_final=True)
    aut.add_transition("q0", "a", "q0")
    aut.add_transition("q0", "b", "q1")
    
    sim = Simulator(aut)
    assert sim.simulate("aaa")["accepted"] == False

def test_nfa_to_dfa_converter():
    aut = Automaton("AFN")
    aut.add_state("q0", is_initial=True)
    aut.add_state("q1", is_final=True)
    # NFA transition
    aut.add_transition("q0", "a", "q0")
    aut.add_transition("q0", "a", "q1")

    dfa = Converter.nfa_to_dfa(aut)
    # Em DFA, lendo 'a', deve ir para {q0, q1}
    assert len(dfa.states) >= 1
    # Verifica determinismo usando o validador
    from utils.validator import AutomatonValidator
    assert AutomatonValidator.is_deterministic(dfa) == True


def test_next_state_name_reuses_first_available_gap():
    aut = Automaton()
    for name in ("q0", "q1", "q2", "q3"):
        aut.add_state(name)

    aut.remove_state("q2")
    assert aut.next_state_name() == "q2"

    aut.remove_state("q1")
    assert aut.next_state_name() == "q1"


def test_next_state_name_ignores_non_matching_names():
    aut = Automaton()
    for name in ("q0", "q2", "foo", "q10x", "Q1"):
        aut.add_state(name)

    assert aut.next_state_name() == "q1"


def test_remove_state_rebuilds_alphabet_from_remaining_transitions():
    aut = Automaton()
    aut.add_state("q0", is_initial=True)
    aut.add_state("q1")
    aut.add_state("q2", is_final=True)
    aut.add_transition("q0", "a", "q1")
    aut.add_transition("q1", "b", "q2")

    aut.remove_state("q1")

    assert aut.transitions == []
    assert aut.alphabet == set()
