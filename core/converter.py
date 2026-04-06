from typing import Set, Dict, Tuple, FrozenSet
from .automaton import Automaton, State

class Converter:
    """Módulo para conversões de autômatos (AFN para AFD)."""
    @staticmethod
    def _epsilon_closure(automaton: Automaton, states: Set[str]) -> FrozenSet[str]:
        closure = set(states)
        stack = list(states)
        while stack:
            current = stack.pop()
            for t in automaton.get_transitions_from(current):
                if t.symbol in ("", "ε") and t.target not in closure:
                    closure.add(t.target)
                    stack.append(t.target)
        return frozenset(closure)

    @staticmethod
    def nfa_to_dfa(nfa: Automaton) -> Automaton:
        """Converte um AFN para um AFD usando Powerset Construction."""
        dfa = Automaton(automaton_type="AFD")
        
        initial_states = {s.name for s in nfa.get_initial_states()}
        if not initial_states:
            return dfa
            
        start_closure = Converter._epsilon_closure(nfa, initial_states)
        
        # Mapeia conjuntos de estados do AFN para um único nome no AFD
        # ex: frozenset({'q0', 'q1'}) -> "q0,q1" ou nome gerado
        def get_state_name(state_set: FrozenSet[str]) -> str:
            return "{" + ",".join(sorted(state_set)) + "}"
            
        start_name = get_state_name(start_closure)
        is_final = any(nfa.states[s].is_final for s in start_closure)
        dfa.add_state(start_name, is_initial=True, is_final=is_final)
        
        unmarked = [start_closure]
        state_mapping = {start_closure: start_name}
        
        while unmarked:
            current_set = unmarked.pop(0)
            current_name = state_mapping[current_set]
            
            for symbol in nfa.alphabet:
                next_states = set()
                for state in current_set:
                    for t in nfa.get_transitions_from(state):
                        if t.symbol == symbol:
                            next_states.add(t.target)
                            
                if next_states:
                    next_closure = Converter._epsilon_closure(nfa, next_states)
                    if next_closure not in state_mapping:
                        next_name = get_state_name(next_closure)
                        is_fin = any(nfa.states[s].is_final for s in next_closure)
                        dfa.add_state(next_name, is_initial=False, is_final=is_fin)
                        state_mapping[next_closure] = next_name
                        unmarked.append(next_closure)
                        
                    next_mapped_name = state_mapping[next_closure]
                    dfa.add_transition(current_name, symbol, next_mapped_name)
                    
        return dfa
