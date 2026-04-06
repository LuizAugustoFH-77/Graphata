from typing import Set, List, Dict
from core.automaton import Automaton


class AutomatonMinimizer:
    """Algoritmo de Hopcroft para minimização de AFD."""

    @staticmethod
    def minimize(dfa: Automaton) -> Automaton:
        states = list(dfa.states.keys())
        final_set = {s.name for s in dfa.get_final_states()}
        non_final_set = {s for s in states if s not in final_set}
        alphabet = list(dfa.alphabet)

        # Partição inicial: {finais} e {não-finais}
        partitions: List[Set[str]] = []
        if final_set:
            partitions.append(final_set)
        if non_final_set:
            partitions.append(non_final_set)

        def get_partition_idx(state, parts):
            for i, p in enumerate(parts):
                if state in p:
                    return i
            return -1

        def transition_target(state, sym):
            for t in dfa.transitions:
                if t.source == state and t.symbol == sym:
                    return t.target
            return None

        changed = True
        while changed:
            changed = False
            new_partitions = []
            for group in partitions:
                if len(group) <= 1:
                    new_partitions.append(group)
                    continue
                # Tenta dividir o grupo
                group_list = list(group)
                sub_groups: List[Set[str]] = []
                for state in group_list:
                    placed = False
                    sig = tuple(get_partition_idx(transition_target(state, sym), partitions) for sym in alphabet)
                    for sg in sub_groups:
                        rep = list(sg)[0]
                        rep_sig = tuple(get_partition_idx(transition_target(rep, sym), partitions) for sym in alphabet)
                        if sig == rep_sig:
                            sg.add(state)
                            placed = True
                            break
                    if not placed:
                        sub_groups.append({state})
                if len(sub_groups) > 1:
                    changed = True
                new_partitions.extend(sub_groups)
            partitions = new_partitions

        # Constrói AFD minimizado
        min_dfa = Automaton("AFD")
        # Nome de cada partição = junção dos nomes dos estados originais
        def part_name(p):
            return "{" + ",".join(sorted(p)) + "}"

        initials = {s.name for s in dfa.get_initial_states()}
        finals = {s.name for s in dfa.get_final_states()}

        added = set()
        for part in partitions:
            pn = part_name(part)
            if pn in added:
                continue
            added.add(pn)
            is_init = bool(part.intersection(initials))
            is_fin = bool(part.intersection(finals))
            min_dfa.add_state(pn, is_initial=is_init, is_final=is_fin)

        # Transições
        for part in partitions:
            pn = part_name(part)
            rep = list(part)[0]
            for sym in alphabet:
                tgt = transition_target(rep, sym)
                if tgt is not None:
                    tgt_part = next(p for p in partitions if tgt in p)
                    min_dfa.add_transition(pn, sym, part_name(tgt_part))

        return min_dfa


class StringGenerator:
    """Gera strings de exemplo aceitas e rejeitadas por um autômato.

    Usa BFS direto no grafo de transições, gerando sequências de símbolos
    reais. Funciona corretamente com símbolos multi-caractere (ex: HC, HL, M200).
    """

    MAX_DEPTH = 20   # profundidade máxima de busca (n° de transições)
    MAX_VISIT = 5000  # limite de nós visitados para não travar

    @staticmethod
    def generate(automaton: Automaton, n_accepted=4, n_rejected=4):
        from collections import deque

        alphabet = sorted(automaton.alphabet)
        if not alphabet:
            return [], []

        initials = {s.name for s in automaton.get_initial_states()}
        finals   = {s.name for s in automaton.get_final_states()}
        if not initials:
            return [], []

        # Indexar transições por estado de origem para performance
        trans_from: Dict[str, list] = {}
        for t in automaton.transitions:
            trans_from.setdefault(t.source, []).append(t)

        accepted: List[str] = []
        rejected: List[str] = []
        sep = ","  # separador visual para strings multi-char

        # Para rejeitadas: tentar sequências curtas que levam a becos sem saída
        # ou que terminam em estados não-finais

        # BFS: (estado_atual ou set de estados, lista de símbolos, profundidade)
        # Cada nó: (frozenset de estados ativos, tupla de símbolos percorridos)
        start = frozenset(initials)
        queue = deque()
        queue.append((start, ()))
        visited = set()
        visited.add((start, ()))
        visit_count = 0

        while queue and (len(accepted) < n_accepted or len(rejected) < n_rejected):
            if visit_count >= StringGenerator.MAX_VISIT:
                break
            visit_count += 1

            current_states, symbols = queue.popleft()

            # Verificar se essa sequência é aceita ou rejeitada
            if symbols:  # Ignora a sequência vazia no início
                is_accepted = bool(current_states & finals)
                word = sep.join(symbols)
                if is_accepted and len(accepted) < n_accepted:
                    accepted.append(word)
                elif not is_accepted and len(rejected) < n_rejected:
                    rejected.append(word)

            # String vazia — checar se estado inicial é final
            if not symbols:
                if current_states & finals and len(accepted) < n_accepted:
                    accepted.append("ε")
                elif not (current_states & finals) and len(rejected) < n_rejected:
                    rejected.append("ε")

            if len(symbols) >= StringGenerator.MAX_DEPTH:
                continue

            # Expandir: para cada símbolo do alfabeto, calcular próximos estados
            for sym in alphabet:
                next_states = set()
                for st in current_states:
                    for t in trans_from.get(st, []):
                        if t.symbol == sym:
                            next_states.add(t.target)
                # Mesmo se next_states for vazio, pode gerar uma string rejeitada
                ns = frozenset(next_states)
                new_syms = symbols + (sym,)
                key = (ns, new_syms)
                if key not in visited:
                    visited.add(key)
                    if next_states:
                        queue.append((ns, new_syms))
                    elif len(rejected) < n_rejected:
                        # Beco sem saída → string rejeitada
                        rejected.append(sep.join(new_syms))

        return accepted, rejected
