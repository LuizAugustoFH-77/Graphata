import json
from core.automaton import Automaton

class AutomatonSerializer:
    """Importa e Exporta definições de autômatos em JSON."""
    @staticmethod
    def to_json(automaton: Automaton, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(automaton.to_dict(), f, indent=4, ensure_ascii=False)
            
    @staticmethod
    def from_json(filepath: str) -> Automaton:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Automaton.from_dict(data)
