from core.automaton import Automaton

class AutomatonValidator:
    """Utilitários para analisar as propriedades formais de um autômato."""
    @staticmethod
    def is_deterministic(automaton: Automaton) -> bool:
        """Verifica se o autômato é determinístico (não tem transições epsilon nem ambiguidades)."""
        for state_name in automaton.states:
            seen_symbols = set()
            for t in automaton.get_transitions_from(state_name):
                if t.symbol in ("", "ε"):
                    return False
                if t.symbol in seen_symbols:
                    return False
                seen_symbols.add(t.symbol)
        # Além disso, AFD deve ter apenas 1 estado inicial.
        if len(automaton.get_initial_states()) > 1:
            return False
            
        return True
        
    @staticmethod
    def is_complete(automaton: Automaton) -> bool:
        """Verifica se há transição para todos os símbolos do alfabeto em todos os estados."""
        if not automaton.alphabet:
            return True
        for state_name in automaton.states:
            symbols = {t.symbol for t in automaton.get_transitions_from(state_name) if t.symbol not in ("", "ε")}
            if not automaton.alphabet.issubset(symbols):
                return False
        return True
