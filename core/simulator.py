from typing import List, Dict, Set
from .automaton import Automaton


class Simulator:
    """Motor de simulação de execução de strings em um Autômato."""

    def __init__(self, automaton: Automaton):
        self.automaton = automaton

    def _epsilon_closure(self, states: Set[str]) -> Set[str]:
        closure = set(states)
        stack = list(states)
        while stack:
            current = stack.pop()
            for t in self.automaton.get_transitions_from(current):
                if t.symbol in ("", "ε") and t.target not in closure:
                    closure.add(t.target)
                    stack.append(t.target)
        return closure

    def step(self, current_states: Set[str], symbol: str) -> Set[str]:
        next_states = set()
        for state in current_states:
            for t in self.automaton.get_transitions_from(state):
                if t.symbol == symbol:
                    next_states.add(t.target)
        return self._epsilon_closure(next_states)

    def tokenize(self, input_string: str) -> list | None:
        """Tokeniza a string de entrada usando os símbolos do alfabeto do autômato.

        Tenta casar greedily (símbolos mais longos primeiro).
        Também aceita separação por vírgula (ex: 'HC,H,HR').
        Retorna lista de tokens ou None se não for possível tokenizar.
        """
        # Se a entrada contém vírgulas, separar por vírgula
        if "," in input_string:
            return [t.strip() for t in input_string.split(",") if t.strip()]

        alphabet = sorted(self.automaton.alphabet, key=len, reverse=True)

        # Se todos os símbolos são de 1 caractere, tratar como string simples
        if all(len(s) == 1 for s in alphabet):
            return list(input_string)

        # Tokenização gulosa (match mais longo primeiro)
        tokens = []
        i = 0
        while i < len(input_string):
            matched = False
            for sym in alphabet:
                if input_string[i:i + len(sym)] == sym:
                    tokens.append(sym)
                    i += len(sym)
                    matched = True
                    break
            if not matched:
                return None  # Não conseguiu tokenizar
        return tokens

    def simulate(self, input_string: str) -> dict:
        initials = {s.name for s in self.automaton.get_initial_states()}
        if not initials:
            return {"accepted": False, "trace": [], "error": "Nenhum estado inicial definido."}

        current = self._epsilon_closure(initials)
        trace = [{"symbol": "", "states": list(current)}]

        # Tokenizar a entrada
        tokens = self.tokenize(input_string)
        if tokens is None:
            return {"accepted": False, "trace": trace,
                    "error": f"Não foi possível tokenizar '{input_string}' com o alfabeto {sorted(self.automaton.alphabet)}."}

        for symbol in tokens:
            current = self.step(current, symbol)
            trace.append({"symbol": symbol, "states": list(current)})
            if not current:
                break

        final_names = {s.name for s in self.automaton.get_final_states()}
        accepted = bool(current.intersection(final_names))

        # Se a simulação terminou antes de iterar todos os tokens
        if len(trace) - 1 < len(tokens):
            accepted = False

        return {"accepted": accepted, "trace": trace, "error": None}
