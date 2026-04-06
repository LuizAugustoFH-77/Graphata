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
