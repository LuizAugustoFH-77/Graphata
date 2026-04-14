from dataclasses import dataclass, field
import re
from typing import Set, Dict, List, Optional

@dataclass(frozen=True)
class State:
    name: str
    is_initial: bool = False
    is_final: bool = False

    def __repr__(self):
        return f"State({self.name})"

@dataclass(frozen=True)
class Transition:
    source: str
    symbol: str
    target: str

    def __repr__(self):
        return f"({self.source} --{self.symbol}--> {self.target})"

class Automaton:
    """Implementação base de um autômato genérico (AFD/AFN)."""
    def __init__(self, automaton_type: str = "AFD"):
        self.type = automaton_type
        self.states: Dict[str, State] = {}
        self.transitions: List[Transition] = []
        self.alphabet: Set[str] = set()
        
    def add_state(self, name: str, is_initial: bool = False, is_final: bool = False):
        if name not in self.states:
            self.states[name] = State(name, is_initial, is_final)
            
    def set_initial(self, name: str, is_initial: bool = True):
        seq = self.states.get(name)
        if seq:
            self.states[name] = State(seq.name, is_initial, seq.is_final)
            
    def set_final(self, name: str, is_final: bool = True):
        seq = self.states.get(name)
        if seq:
            self.states[name] = State(seq.name, seq.is_initial, is_final)

    def remove_state(self, name: str):
        if name in self.states:
            del self.states[name]
        self.transitions = [t for t in self.transitions if t.source != name and t.target != name]
        self.alphabet = {t.symbol for t in self.transitions if t.symbol not in ("", "Îµ")}

    def add_transition(self, source: str, symbol: str, target: str):
        if source in self.states and target in self.states:
            t = Transition(source, symbol, target)
            # Impedir transições duplicadas (mesmo source, symbol, target)
            if t not in self.transitions:
                self.transitions.append(t)
                if symbol not in ("", "ε"):
                    self.alphabet.add(symbol)
                
    def get_initial_states(self) -> List[State]:
        return [s for s in self.states.values() if s.is_initial]
        
    def get_final_states(self) -> List[State]:
        return [s for s in self.states.values() if s.is_final]
        
    def get_transitions_from(self, state_name: str) -> List[Transition]:
        return [t for t in self.transitions if t.source == state_name]
        
    def clear(self):
        self.states.clear()
        self.transitions.clear()
        self.alphabet.clear()

    def next_state_name(self, prefix: str = "q") -> str:
        """Retorna o menor nome sequencial livre no formato <prefix><n>."""
        pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
        used_indexes = {
            int(match.group(1))
            for name in self.states
            if (match := pattern.match(name))
        }
        next_index = 0
        while next_index in used_indexes:
            next_index += 1
        return f"{prefix}{next_index}"

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "states": [
                {"name": s.name, "is_initial": s.is_initial, "is_final": s.is_final}
                for s in self.states.values()
            ],
            "transitions": [
                {"source": t.source, "symbol": t.symbol, "target": t.target}
                for t in self.transitions
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Automaton':
        aut = cls(automaton_type=data.get("type", "AFD"))
        for s in data.get("states", []):
            aut.add_state(s["name"], is_initial=s.get("is_initial", False), is_final=s.get("is_final", False))
        for t in data.get("transitions", []):
            aut.add_transition(t["source"], t["symbol"], t["target"])
        return aut
