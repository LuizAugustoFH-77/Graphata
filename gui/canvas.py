import tkinter as tk
import tkinter.simpledialog as sd
import tkinter.messagebox as mb
import math
from core.automaton import Automaton, Transition
from utils.layout import compute_automaton_layout


class AutomatonCanvas(tk.Canvas):
    """Canvas interativo para visualização e edição de autômatos."""

    NODE_COLOR = "#ffffff"
    NODE_OUTLINE_NORMAL = "#1e293b"
    NODE_OUTLINE_FINAL = "#ef4444"
    EDGE_COLOR = "#3498db"
    EDGE_SELECTED = "#f39c12"
    HIGHLIGHT_ACTIVE = "#22c55e"
    HIGHLIGHT_VISITED = "#a3e635"

    def __init__(self, master, automaton: Automaton, on_change=None):
        super().__init__(master, bg="#2b2b2b", highlightthickness=0, takefocus=1)
        self.automaton = automaton
        self.on_change = on_change  # callback chamado quando o autômato muda

        self.nodes = {}          # name -> {item, text, x, y}
        self.state_counter = 0
        self.radius = 25
        self.link_start = None

        # Drag de nó
        self.drag_data = {"item": None, "x": 0, "y": 0}

        # Pan do canvas
        self.pan_data = {"active": False, "x": 0, "y": 0}

        # Aresta selecionada para deleção: (source, target, symbol)
        self.selected_edge = None

        # Pontos customizados para curvas de arestas: {(source, target): (dx, dy)}
        # dx/dy = offset perpendicular ao segmento, salvo em canvas coords
        self.edge_control_points = {}
        self.edge_tag_to_pair = {}

        # Drag de ponto de controle de aresta
        self.edge_drag_data = {"active": False, "pair": None, "item": None}

        # Histórico para Ctrl+Z
        self._history = []

        # Zoom
        self._zoom = 1.0
        self._layout_profile = "auto"

        # Bindings
        self.bind("<Double-Button-1>",    self.on_double_click)
        self.bind("<Button-3>",           self.on_right_click)
        self.bind("<Control-Button-3>",   self.on_ctrl_right_click)
        self.bind("<ButtonPress-1>",      self.on_press)
        self.bind("<B1-Motion>",          self.on_drag)
        self.bind("<ButtonRelease-1>",    self.on_drop)
        # Pan com clique do meio
        self.bind("<ButtonPress-2>",      self.on_pan_start)
        self.bind("<B2-Motion>",          self.on_pan_drag)
        # Zoom com scroll
        self.bind("<MouseWheel>",         self.on_zoom)       # Windows/macOS
        self.bind("<Button-4>",           self.on_zoom)       # Linux scroll up
        self.bind("<Button-5>",           self.on_zoom)       # Linux scroll down
        # Delete para remover aresta/estado selecionado
        self.bind("<Delete>",             self.on_delete_key)
        self.bind("<BackSpace>",          self.on_delete_key)
        self.bind("<Control-z>",          self.undo)

    # ─── Histórico ──────────────────────────────────────────────────────────

    def _snapshot(self):
        """Salva o estado atual do autômato, posições e control points no histórico."""
        snap_aut = self.automaton.to_dict()
        snap_pos = {name: (nd["x"], nd["y"]) for name, nd in self.nodes.items()}
        snap_edges = dict(self.edge_control_points)
        self._history.append((snap_aut, snap_pos, snap_edges))
        if len(self._history) > 30:
            self._history.pop(0)

    def undo(self, event=None):
        if not self._history:
            return
        snap_aut, snap_pos, snap_edges = self._history.pop()
        restored = Automaton.from_dict(snap_aut)
        self.automaton.__dict__.update(restored.__dict__)
        self.edge_control_points = snap_edges
        self.clear_ui(reset_counter=False)
        for name, (x, y) in snap_pos.items():
            if name in self.automaton.states:
                self.draw_node(name, x, y)
        self.refresh_edges()
        self._sync_state_counter()
        if self.on_change:
            self.on_change()

    # ─── Utilitários UI ─────────────────────────────────────────────────────

    def clear_ui(self, reset_counter=True):
        self.delete("all")
        self.nodes.clear()
        self.selected_edge = None
        self.edge_drag_data = {"active": False, "pair": None, "item": None}
        self.edge_tag_to_pair.clear()
        if reset_counter:
            self.state_counter = 0
            self.edge_control_points.clear()

    def _scaled_node_radius(self):
        return max(10, self.radius * self._zoom)

    def _node_font(self):
        return ("Arial", max(7, int(11 * self._zoom)), "bold")

    def _edge_font(self):
        return ("Arial", max(7, int(12 * self._zoom)), "bold")

    def _edge_arrowshape(self):
        scale = max(0.7, self._zoom)
        return (
            max(10, int(14 * scale)),
            max(12, int(18 * scale)),
            max(4, int(6 * scale)),
        )

    def _redraw_scene(self, preserve_selection=True):
        positions = {name: (nd["x"], nd["y"]) for name, nd in self.nodes.items()}
        selected = self.selected_edge if preserve_selection else None
        self.delete("all")
        self.nodes.clear()
        self.edge_tag_to_pair.clear()

        for name in self.automaton.states.keys():
            x, y = positions.get(name, (100, 100))
            self.draw_node(name, x, y)

        self.selected_edge = selected
        self.refresh_edges()

    def load_from_automaton(self):
        self.clear_ui()
        n = len(self.automaton.states)
        if n == 0:
            return
        w = int(self.winfo_width()) or 700
        h = int(self.winfo_height()) or 500
        cx, cy = w // 2, h // 2
        radius = min(min(w, h) // 2 - 60, max(80, 50 * n // 2))
        angle_step = 2 * math.pi / n
        for i, name in enumerate(self.automaton.states.keys()):
            x = cx + radius * math.cos(i * angle_step - math.pi / 2)
            y = cy + radius * math.sin(i * angle_step - math.pi / 2)
            self.draw_node(name, x, y)
        self.refresh_edges()
        self._sync_state_counter()
        if self.on_change:
            self.on_change()

    def organize_layout(self):
        """Reorganiza o canvas com layout híbrido em camadas + relaxamento local."""
        names = list(self.nodes.keys())
        n = len(names)
        if n < 2:
            return

        self._snapshot()

        w = int(self.winfo_width()) or 700
        h = int(self.winfo_height()) or 500
        initial_states = [state.name for state in self.automaton.get_initial_states()]
        self._layout_profile = "dense" if self._is_dense_graph() else "layered"
        pos = compute_automaton_layout(
            names,
            self.automaton.transitions,
            initial_states,
            w,
            h,
            self.radius,
        )

        # Aplicar posições calculadas ao canvas
        for name in names:
            nd = self.nodes[name]
            new_x, new_y = pos.get(name, (nd["x"], nd["y"]))
            dx = new_x - nd["x"]
            dy = new_y - nd["y"]
            self.move(name, dx, dy)
            nd["x"] = new_x
            nd["y"] = new_y

        self.refresh_edges()
        self._notify()

    def _notify(self):
        if self.on_change:
            self.on_change()

    def _is_dense_graph(self):
        n = max(1, len(self.automaton.states))
        unique_pairs = {(t.source, t.target) for t in self.automaton.transitions}
        avg_out = len(unique_pairs) / n
        indegree = {}
        outdegree = {}
        for source, target in unique_pairs:
            outdegree[source] = outdegree.get(source, 0) + 1
            indegree[target] = indegree.get(target, 0) + 1
        max_in = max(indegree.values(), default=0)
        max_out = max(outdegree.values(), default=0)
        return len(self.automaton.states) >= 10 and (
            avg_out >= 2.6 or max_in >= max(6, n // 3) or max_out >= max(6, n // 3)
        )

    def _safe_pos(self, x, y):
        """Garante que o novo estado não fique exatamente em cima de outro."""
        for nd in self.nodes.values():
            if math.hypot(nd["x"] - x, nd["y"] - y) < self.radius * 2.5:
                x += self.radius * 3
        return x, y

    def _sync_state_counter(self):
        next_name = self.automaton.next_state_name()
        self.state_counter = int(next_name[1:]) if next_name.startswith("q") and next_name[1:].isdigit() else 0

    # ─── Nós ────────────────────────────────────────────────────────────────

    def on_double_click(self, event):
        # Verifica se clicou em estado existente → renomear
        item = self.find_withtag("current")
        if item:
            tags = self.gettags(item[0])
            if "node" in tags or "node_text" in tags:
                self._rename_state(tags[1])
                return
        # Clique no vazio → criar estado
        x, y = self._safe_pos(event.x, event.y)
        name = self.automaton.next_state_name()
        self._snapshot()
        self.automaton.add_state(name)
        self._sync_state_counter()
        if len(self.automaton.states) == 1:
            self.automaton.set_initial(name)
        self.draw_node(name, x, y)
        self._notify()

    def _rename_state(self, old_name):
        new_name = sd.askstring("Renomear Estado", f"Novo nome para '{old_name}':", initialvalue=old_name)
        if not new_name or new_name == old_name:
            return
        if new_name in self.automaton.states:
            mb.showerror("Erro", f"Estado '{new_name}' já existe.")
            return
        self._snapshot()
        # Atualiza no autômato
        old_state = self.automaton.states[old_name]
        self.automaton.states[new_name] = type(old_state)(new_name, old_state.is_initial, old_state.is_final)
        del self.automaton.states[old_name]
        # Atualiza transições
        new_transitions = []
        for t in self.automaton.transitions:
            src = new_name if t.source == old_name else t.source
            tgt = new_name if t.target == old_name else t.target
            new_transitions.append(Transition(src, t.symbol, tgt))
        self.automaton.transitions = new_transitions
        # Atualiza canvas preservando a posição do estado renomeado
        nd = self.nodes.pop(old_name)
        self.nodes[new_name] = nd
        self._sync_state_counter()
        self._redraw_scene()
        self._notify()

    def draw_node(self, name, x, y):
        state = self.automaton.states[name]
        r = self._scaled_node_radius()
        outline = self.NODE_OUTLINE_FINAL if state.is_final else self.NODE_OUTLINE_NORMAL
        width = max(2, int((4 if state.is_final else 2) * max(0.8, self._zoom)))
        item = self.create_oval(
            x - r, y - r, x + r, y + r,
            fill=self.NODE_COLOR, outline=outline, width=width, tags=("node", name)
        )
        # Desenha um contorno limpo para o texto e evita distorção ao redesenhar no zoom.
        s = max(1.0, round(1.2 * self._zoom, 1))
        font_bold = self._node_font()
        offsets = [
            (-s, 0), (s, 0), (0, -s), (0, s),
            (-s, -s), (s, -s), (-s, s), (s, s),
        ]
        for dx, dy in offsets:
            self.create_text(x + dx, y + dy, text=name, font=font_bold,
                             fill="#000000", tags=("node_text_outline", name, f"text_{name}", f"label_{name}"))
        text = self.create_text(x, y, text=name, font=font_bold,
                                fill="#b45309", tags=("node_text", name, f"text_{name}", f"label_{name}"))
        self.nodes[name] = {"item": item, "text": text, "x": x, "y": y}
        self.draw_init_arrow(name, x, y, state.is_initial)
        self.tag_raise(name)
        self.tag_raise(f"text_{name}")

    def draw_init_arrow(self, name, x, y, is_initial):
        self.delete(f"init_arrow_{name}")
        if is_initial:
            r = self._scaled_node_radius()
            arrow_w = max(10, int(11 * max(0.8, self._zoom)))
            arrow_gap = max(16, int(22 * max(0.8, self._zoom)))
            self.create_polygon(
                x - r - arrow_gap, y,
                x - r - 2, y - arrow_w,
                x - r - 2, y + arrow_w,
                fill="#f1c40f", tags=(f"init_arrow_{name}", name)
            )
            self.tag_lower(f"init_arrow_{name}")

    def redraw_node(self, name):
        if name not in self.nodes:
            return
        nd = self.nodes[name]
        state = self.automaton.states[name]
        outline = self.NODE_OUTLINE_FINAL if state.is_final else self.NODE_OUTLINE_NORMAL
        width = max(2, int((4 if state.is_final else 2) * max(0.8, self._zoom)))
        self.itemconfig(nd["item"], outline=outline, width=width, fill=self.NODE_COLOR)
        self.draw_init_arrow(name, nd["x"], nd["y"], state.is_initial)

    # ─── Highlight de Simulação ─────────────────────────────────────────────

    def highlight_states(self, active_states, visited_states=None):
        """Colore os nós ativos (verde) e visitados (amarelo) para a simulação."""
        # Resetar todos para cor normal
        for name, nd in self.nodes.items():
            state = self.automaton.states[name]
            outline = self.NODE_OUTLINE_FINAL if state.is_final else self.NODE_OUTLINE_NORMAL
            self.itemconfig(nd["item"], fill=self.NODE_COLOR, outline=outline)
        # Colorir visitados
        if visited_states:
            for name in visited_states:
                if name in self.nodes:
                    self.itemconfig(self.nodes[name]["item"], fill="#fef08a")
        # Colorir ativos
        for name in active_states:
            if name in self.nodes:
                self.itemconfig(self.nodes[name]["item"], fill=self.HIGHLIGHT_ACTIVE)

    def reset_highlight(self):
        self.highlight_states([])

    # ─── Cliques ────────────────────────────────────────────────────────────

    def on_right_click(self, event):
        self.focus_set()
        item = self.find_withtag("current")
        if item:
            tags = self.gettags(item[0])
            if "node" in tags or "node_text" in tags:
                self._show_context_menu(event, tags[1])
                return
            if {"edge", "edge_text", "edge_label_bg", "edge_label_callout"} & set(tags):
                # Selecionar aresta
                self._select_edge_at(event.x, event.y)

    def _show_context_menu(self, event, name):
        menu = tk.Menu(self, tearoff=0, bg="#1e293b", fg="white",
                       activebackground="#3498db", activeforeground="white",
                       font=("Arial", 11))
        state = self.automaton.states[name]
        menu.add_command(label=f"✏️  Renomear '{name}'",   command=lambda: self._rename_state(name))
        if state.is_final:
            menu.add_command(label="⭕  Remover marcação Final",  command=lambda: self._toggle_final(name))
        else:
            menu.add_command(label="⭕  Marcar como Final",       command=lambda: self._toggle_final(name))
        if state.is_initial:
            menu.add_command(label="▶️  Remover marcação Inicial", command=lambda: self._toggle_initial(name))
        else:
            menu.add_command(label="▶️  Marcar como Inicial",     command=lambda: self._toggle_initial(name))
        menu.add_separator()
        menu.add_command(label="🗑️  Apagar Estado",            command=lambda: self._delete_state(name))
        menu.tk_popup(event.x_root, event.y_root)

    def _toggle_final(self, name):
        self._snapshot()
        state = self.automaton.states[name]
        self.automaton.set_final(name, not state.is_final)
        self.redraw_node(name)
        self._notify()

    def _toggle_initial(self, name):
        self._snapshot()
        state = self.automaton.states[name]
        self.automaton.set_initial(name, not state.is_initial)
        self.redraw_node(name)
        self._notify()

    def _delete_state(self, name):
        self._snapshot()
        self.automaton.remove_state(name)
        if self.selected_edge and name in (self.selected_edge.source, self.selected_edge.target):
            self.selected_edge = None
        # Limpar control points das arestas conectadas
        pairs_to_remove = [p for p in self.edge_control_points if name in p]
        for p in pairs_to_remove:
            del self.edge_control_points[p]
        self.delete(name)
        del self.nodes[name]
        self._sync_state_counter()
        self.refresh_edges()
        self._notify()

    def on_ctrl_right_click(self, event):
        # Mantido para compatibilidade com o atalho antigo
        item = self.find_withtag("current")
        if item:
            tags = self.gettags(item[0])
            if "node" in tags or "node_text" in tags:
                self._delete_state(tags[1])

    # ─── Seleção de Aresta ──────────────────────────────────────────────────

    def _select_edge_at(self, x, y):
        """Identifica a transição mais próxima do clique e a seleciona."""
        self.focus_set()
        current_pair = self._edge_pair_from_current_item()
        if current_pair:
            for t in self.automaton.transitions:
                if (t.source, t.target) == current_pair:
                    self.selected_edge = t
                    self.refresh_edges()
                    return
        best = None
        best_dist = 18  # pixels de tolerância
        for t in self.automaton.transitions:
            if t.source not in self.nodes or t.target not in self.nodes:
                continue
            sx, sy = self.nodes[t.source]["x"], self.nodes[t.source]["y"]
            tx, ty = self.nodes[t.target]["x"], self.nodes[t.target]["y"]
            # Ponto médio como proxy
            mx, my = (sx + tx) / 2, (sy + ty) / 2
            d = math.hypot(x - mx, y - my)
            if d < best_dist:
                best_dist = d
                best = t
        self.selected_edge = best
        self.refresh_edges()

    def on_delete_key(self, event=None):
        if self.selected_edge:
            self._snapshot()
            t = self.selected_edge
            self.automaton.transitions = [tr for tr in self.automaton.transitions if tr != t]
            self.automaton.alphabet = {tr.symbol for tr in self.automaton.transitions if tr.symbol not in ("", "ε")}
            # Limpar control point se for a única transição desse par
            pair = (t.source, t.target)
            has_remaining = any(tr.source == t.source and tr.target == t.target for tr in self.automaton.transitions)
            if not has_remaining and pair in self.edge_control_points:
                del self.edge_control_points[pair]
            self.selected_edge = None
            self.refresh_edges()
            self._notify()
            return "break"

    # ─── Pressionar / Arrastar ──────────────────────────────────────────────

    def on_press(self, event):
        item = self.find_withtag("current")
        if item:
            tags = self.gettags(item[0])
            if "node" in tags or "node_text" in tags:
                # Limpa seleção de aresta ao clicar num nó
                self.selected_edge = None
                name = tags[1]
                if event.state & 0x0001:  # Shift
                    self.link_start = name
                else:
                    self.drag_data["item"] = name
                    self.drag_data["x"] = event.x
                    self.drag_data["y"] = event.y
            elif {"edge", "edge_text", "edge_label_bg", "edge_label_callout"} & set(tags):
                self._select_edge_at(event.x, event.y)
                self.on_edge_drag_start(event)
        else:
            # Inicia pan com botão esquerdo se clicar no vazio
            self.selected_edge = None
            self.on_pan_start(event)

    def on_drag(self, event):
        if self.edge_drag_data["active"]:
            self.on_edge_drag_motion(event)
        elif self.link_start:
            self.delete("temp_line")
            nx = self.nodes[self.link_start]["x"]
            ny = self.nodes[self.link_start]["y"]
            self.create_line(nx, ny, event.x, event.y, arrow=tk.LAST, fill="#f39c12", width=2, tags="temp_line")
        elif self.drag_data["item"]:
            name = self.drag_data["item"]
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            self.move(name, dx, dy)
            self.nodes[name]["x"] = event.x
            self.nodes[name]["y"] = event.y
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            # Mover control points das arestas conectadas
            self._adjust_edge_control_points(name, dx, dy)
            self.refresh_edges()
        elif self.pan_data["active"]:
            # Executa pan se iniciado pelo botão esquerdo
            self.on_pan_drag(event)

    def on_drop(self, event):
        if self.edge_drag_data["active"]:
            self.on_edge_drag_release(event)
        if self.link_start:
            self.delete("temp_line")
            item = self.find_closest(event.x, event.y)
            if item:
                tags = self.gettags(item[0])
                if "node" in tags or "node_text" in tags:
                    target_name = tags[1]
                    sym = sd.askstring("Transição", f"Símbolo ({self.link_start} → {target_name}):")
                    if sym is not None:
                        # Verificar se já existe transição idêntica
                        existing = any(
                            t.source == self.link_start and t.symbol == sym and t.target == target_name
                            for t in self.automaton.transitions
                        )
                        if existing:
                            mb.showwarning(
                                "Transição Duplicada",
                                f"Já existe uma transição '{sym}' de '{self.link_start}' para '{target_name}'.",
                            )
                        else:
                            self._snapshot()
                            self.automaton.add_transition(self.link_start, sym, target_name)
                            self.refresh_edges()
                            self._notify()
            self.link_start = None
        self.drag_data["item"] = None
        self.pan_data["active"] = False
        self.config(cursor="")

    # ─── Pan & Zoom ─────────────────────────────────────────────────────────

    def on_pan_start(self, event):
        self.pan_data = {"active": True, "x": event.x, "y": event.y}
        self.config(cursor="fleur")

    def on_pan_drag(self, event):
        if self.pan_data["active"]:
            dx = event.x - self.pan_data["x"]
            dy = event.y - self.pan_data["y"]
            self.move("all", dx, dy)
            for name in self.nodes:
                self.nodes[name]["x"] += dx
                self.nodes[name]["y"] += dy
            # Mover também os control points
            for pair, (cpx, cpy) in self.edge_control_points.items():
                self.edge_control_points[pair] = (cpx + dx, cpy + dy)
            self.pan_data["x"] = event.x
            self.pan_data["y"] = event.y
            self.config(cursor="fleur")

    def on_zoom(self, event):
        # Detecta direção
        if event.num == 4 or event.delta > 0:
            factor = 1.1
        else:
            factor = 0.9
        self._zoom *= factor
        self._zoom = max(0.3, min(self._zoom, 3.0))
        cx, cy = event.x, event.y
        # Atualiza posições lógicas dos nós e redesenha a cena inteira.
        for name in self.nodes:
            nx = (self.nodes[name]["x"] - cx) * factor + cx
            ny = (self.nodes[name]["y"] - cy) * factor + cy
            self.nodes[name]["x"] = nx
            self.nodes[name]["y"] = ny
        # Escalar também os control points de arestas customizadas
        for pair, (cpx, cpy) in self.edge_control_points.items():
            ncx = (cpx - cx) * factor + cx
            ncy = (cpy - cy) * factor + cy
            self.edge_control_points[pair] = (ncx, ncy)
        self._redraw_scene()

    # ─── Arestas ────────────────────────────────────────────────────────────

    def refresh_edges(self):
        self.delete("edge")
        self.delete("edge_text")
        self.delete("edge_label_bg")
        self.delete("edge_label_callout")
        self.edge_tag_to_pair.clear()
        r = self._scaled_node_radius()

        # Agrupar transições por par
        edge_groups: dict[tuple, list] = {}
        for t in self.automaton.transitions:
            pair = (t.source, t.target)
            if pair not in edge_groups:
                edge_groups[pair] = []
            if t.symbol not in edge_groups[pair]:
                edge_groups[pair].append(t.symbol)

        dense_mode = self._layout_profile == "dense" or self._is_dense_graph()
        pair_order = self._pair_orderings(edge_groups)
        hub_targets, hub_sources = self._hub_nodes(edge_groups)

        for idx, ((source, target), symbols) in enumerate(edge_groups.items()):
            if source not in self.nodes or target not in self.nodes:
                continue
            pair_tag = f"edge_pair_{idx}"
            self.edge_tag_to_pair[pair_tag] = (source, target)
            sx, sy = self.nodes[source]["x"], self.nodes[source]["y"]
            tx, ty = self.nodes[target]["x"], self.nodes[target]["y"]
            symbols_str = ", ".join(symbols)

            # Verificar se é aresta selecionada
            is_selected = self.selected_edge and (
                self.selected_edge.source == source and self.selected_edge.target == target
            )
            color = self.EDGE_SELECTED if is_selected else self.EDGE_COLOR

            if source == target:  # self-loop
                loop_w = max(14, int(15 * max(0.9, self._zoom)))
                loop_h = max(20, int(30 * max(0.9, self._zoom)))
                self.create_oval(sx - loop_w, sy - r - loop_h, sx + loop_w, sy - r,
                                 outline=color, width=2, tags=("edge", pair_tag))
                label_y = sy - r - loop_h - max(12, int(14 * self._zoom))
                self._draw_edge_label(
                    sx,
                    label_y,
                    symbols_str,
                    color,
                    self._edge_font(),
                    pair_tag=pair_tag,
                )
            else:
                dx = tx - sx
                dy = ty - sy
                dist = math.hypot(dx, dy)
                if dist == 0:
                    continue
                nx = dx / dist
                ny = dy / dist
                start_x = sx + nx * r
                start_y = sy + ny * r
                end_x = tx - nx * r
                end_y = ty - ny * r

                has_reverse = (target, source) in edge_groups
                edge_font = self._edge_font()
                arrowshape = self._edge_arrowshape()
                has_cp = (source, target) in self.edge_control_points
                if has_cp:
                    # Controle manual do usuário sobrepõe qualquer modo automático
                    cp_x, cp_y = self.edge_control_points[(source, target)]
                    self.create_line(start_x, start_y, cp_x, cp_y, end_x, end_y,
                                     smooth=True, arrow=tk.LAST, fill=color, width=2,
                                     arrowshape=arrowshape, tags=("edge", pair_tag))
                    lane2 = pair_order.get((source, target), 0)
                    label_x2, label_y2, anchor_x2, anchor_y2 = self._segment_label_position(
                        start_x, start_y, cp_x, cp_y, lane2, t=0.42, offset=18
                    )
                    self._draw_edge_label(label_x2, label_y2, symbols_str, color, edge_font, anchor_x2, anchor_y2, pair_tag)
                elif dense_mode and target in hub_targets:
                    self._draw_hub_edge(
                        source, target,
                        start_x, start_y, end_x, end_y,
                        symbols_str, color, edge_font,
                        pair_order.get((source, target), 0),
                        pair_tag=pair_tag,
                    )
                elif dense_mode and source in hub_sources:
                    self._draw_hub_edge(
                        source, target,
                        start_x, start_y, end_x, end_y,
                        symbols_str, color, edge_font,
                        pair_order.get((source, target), 0),
                        source_is_hub=True,
                        pair_tag=pair_tag,
                    )
                elif has_reverse:
                    px, py = -ny, nx
                    offset = max(28, int(40 * max(0.9, self._zoom)))
                    mid_x = (sx + tx) / 2 + px * offset
                    mid_y = (sy + ty) / 2 + py * offset
                    for vec, pt in [((mid_x - sx, mid_y - sy), "s"), ((mid_x - tx, mid_y - ty), "t")]:
                        d = math.hypot(*vec)
                        if d != 0:
                            if pt == "s":
                                start_x = sx + (vec[0] / d) * r
                                start_y = sy + (vec[1] / d) * r
                            else:
                                end_x = tx + (vec[0] / d) * r
                                end_y = ty + (vec[1] / d) * r
                    self.create_line(start_x, start_y, mid_x, mid_y, end_x, end_y,
                                     smooth=True, arrow=tk.LAST, fill=color, width=2,
                                     arrowshape=arrowshape, tags=("edge", pair_tag))
                    lane = pair_order.get((source, target), 0)
                    label_x, label_y, anchor_x, anchor_y = self._segment_label_position(
                        start_x, start_y, mid_x, mid_y, lane, t=0.42, offset=20
                    )
                    self._draw_edge_label(label_x, label_y, symbols_str, color, edge_font, anchor_x, anchor_y, pair_tag)
                elif dense_mode and dist > 180:
                    px, py = -ny, nx
                    offset = min(90, 22 + dist * 0.12)
                    direction = -1 if sy <= ty else 1
                    mid_x = (sx + tx) / 2 + px * offset * direction
                    mid_y = (sy + ty) / 2 + py * offset * direction
                    self.create_line(
                        start_x, start_y, mid_x, mid_y, end_x, end_y,
                        smooth=True, arrow=tk.LAST, fill=color, width=2,
                        arrowshape=arrowshape, tags=("edge", pair_tag)
                    )
                    lane = pair_order.get((source, target), 0)
                    label_x, label_y, anchor_x, anchor_y = self._segment_label_position(
                        start_x, start_y, mid_x, mid_y, lane * direction, t=0.42, offset=20
                    )
                    self._draw_edge_label(label_x, label_y, symbols_str, color, edge_font, anchor_x, anchor_y, pair_tag)
                else:
                    self.create_line(start_x, start_y, end_x, end_y,
                                     arrow=tk.LAST, fill=color, width=2,
                                     arrowshape=arrowshape, tags=("edge", pair_tag))
                    lane = pair_order.get((source, target), 0)
                    label_x, label_y, anchor_x, anchor_y = self._segment_label_position(
                        start_x, start_y, end_x, end_y, lane, t=0.34, offset=20
                    )
                    self._draw_edge_label(label_x, label_y, symbols_str, color, edge_font, anchor_x, anchor_y, pair_tag)

        self.tag_lower("edge")
        self.tag_raise("edge_label_bg")
        self.tag_raise("edge_label_callout")
        self.tag_raise("edge_text")
        # Garantir que nós ficam acima das arestas
        for name in self.nodes:
            self.tag_raise(name)
            self.tag_raise(f"text_{name}")

    def _pair_orderings(self, edge_groups):
        incoming = {}
        outgoing = {}
        for source, target in edge_groups:
            incoming.setdefault(target, []).append(source)
            outgoing.setdefault(source, []).append(target)

        order = {}
        for target, sources in incoming.items():
            ordered = sorted(sources, key=lambda name: self.nodes.get(name, {}).get("y", 0))
            for idx, source in enumerate(ordered):
                order[(source, target)] = idx - (len(ordered) - 1) / 2

        for source, targets in outgoing.items():
            ordered = sorted(targets, key=lambda name: self.nodes.get(name, {}).get("y", 0))
            for idx, target in enumerate(ordered):
                order.setdefault((source, target), idx - (len(ordered) - 1) / 2)

        return order

    def _hub_nodes(self, edge_groups):
        incoming = {}
        outgoing = {}
        limit = max(6, len(self.nodes) // 3)
        for source, target in edge_groups:
            incoming[target] = incoming.get(target, 0) + 1
            outgoing[source] = outgoing.get(source, 0) + 1
        hub_targets = {name for name, count in incoming.items() if count >= limit}
        hub_sources = {name for name, count in outgoing.items() if count >= limit}
        return hub_targets, hub_sources

    def _draw_hub_edge(self, source, target, start_x, start_y, end_x, end_y, symbols_str, color, edge_font, lane_index, source_is_hub=False, pair_tag=None):
        width = int(self.winfo_width()) or 700
        height = int(self.winfo_height()) or 500
        spread = max(7, int(9 * self._zoom))

        if source_is_hub:
            start_x, start_y = self._hub_port(source, lane_index, side="right")
            outlet_x = min(width - 30, start_x + max(30, int(38 * self._zoom)) + abs(lane_index) * 10)
            outlet_y = start_y + lane_index * spread
            mid_x = (outlet_x + end_x) / 2
            mid_y = (outlet_y + end_y) / 2
            points = (start_x, start_y, outlet_x, outlet_y, mid_x, mid_y, end_x, end_y)
            label_x, label_y, anchor_x, anchor_y = self._segment_label_position(
                start_x, start_y, outlet_x, outlet_y, lane_index, t=0.58, offset=16
            )
        else:
            end_x, end_y = self._hub_port(target, lane_index, side="left")
            inlet_x = max(26, end_x - max(34, int(44 * self._zoom)) - abs(lane_index) * 10)
            inlet_y = end_y + lane_index * spread
            mid_x = (start_x + inlet_x) / 2
            mid_y = (start_y + inlet_y) / 2
            points = (start_x, start_y, mid_x, mid_y, inlet_x, inlet_y, end_x, end_y)
            label_x, label_y, anchor_x, anchor_y = self._segment_label_position(
                start_x, start_y, mid_x, mid_y, lane_index, t=0.38, offset=16
            )

        self.create_line(
            *points,
            smooth=True,
            arrow=tk.LAST,
            fill=color,
            width=2,
            arrowshape=self._edge_arrowshape(),
            tags=("edge", pair_tag) if pair_tag else "edge",
        )
        self._draw_edge_label(label_x, label_y, symbols_str, color, edge_font, anchor_x, anchor_y, pair_tag)

    def _hub_port(self, name, lane_index, side="right"):
        nd = self.nodes[name]
        cx, cy = nd["x"], nd["y"]
        r = self._scaled_node_radius()
        step = max(7, int(8 * self._zoom))
        y_offset = lane_index * step
        max_y = r * 0.72
        if y_offset > max_y:
            y_offset = max_y
        if y_offset < -max_y:
            y_offset = -max_y
        x_offset = max(4, math.sqrt(max(r * r - y_offset * y_offset, 0)))
        if side == "right":
            return cx + x_offset, cy + y_offset
        return cx - x_offset, cy + y_offset

    def _segment_label_position(self, x1, y1, x2, y2, lane_index=0, t=0.34, offset=18):
        px = x1 + (x2 - x1) * t
        py = y1 + (y2 - y1) * t
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist == 0:
            return px, py, px, py

        nx = -dy / dist
        ny = dx / dist
        if lane_index == 0:
            lane_sign = 1 if ny >= 0 else -1
        else:
            lane_sign = 1 if lane_index > 0 else -1

        lane_strength = abs(lane_index)
        normal_offset = offset + lane_strength * max(8, int(10 * self._zoom))
        along_offset = lane_sign * lane_strength * max(4, int(5 * self._zoom))

        label_x = px + nx * normal_offset + (dx / dist) * along_offset
        label_y = py + ny * normal_offset + (dy / dist) * along_offset
        return label_x, label_y, px, py

    def _draw_edge_label(self, x, y, text, color, font, anchor_x=None, anchor_y=None, pair_tag=None):
        text_tags = ("edge_text", pair_tag) if pair_tag else "edge_text"
        text_item = self.create_text(
            x,
            y,
            text=text,
            fill="#f8fafc",
            font=font,
            tags=text_tags,
        )
        x1, y1, x2, y2 = self.bbox(text_item)
        pad_x = max(5, int(6 * self._zoom))
        pad_y = max(2, int(3 * self._zoom))
        bg = self.create_rectangle(
            x1 - pad_x,
            y1 - pad_y,
            x2 + pad_x,
            y2 + pad_y,
            fill="#111827",
            outline=color,
            width=max(1, int(1.2 * max(0.9, self._zoom))),
            tags=("edge_label_bg", pair_tag) if pair_tag else "edge_label_bg",
        )
        self.tag_raise(text_item, bg)

        if anchor_x is not None and anchor_y is not None:
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            dx = anchor_x - cx
            dy = anchor_y - cy
            dist = math.hypot(dx, dy)
            if dist > max(18, int(22 * self._zoom)):
                self.create_line(
                    cx,
                    cy,
                    anchor_x,
                    anchor_y,
                    fill=color,
                    width=max(1, int(1.1 * max(0.9, self._zoom))),
                    dash=(3, 2),
                    tags=("edge_label_callout", pair_tag) if pair_tag else "edge_label_callout",
                )

    # Aresta customizada (arraste direto) ────────────────────────────────

    def on_edge_drag_start(self, event):
        """Inicia o arraste de uma aresta — cria control point se não existir."""
        pair = self._edge_pair_from_current_item() or self._find_edge_at(event.x, event.y)
        if pair is None:
            return
        self._snapshot()
        self.edge_drag_data = {"active": True, "pair": pair, "item": None}
        # Se ainda não tem control point, cria no ponto médio perpendicular
        if pair not in self.edge_control_points:
            sx, sy = self.nodes[pair[0]]["x"], self.nodes[pair[0]]["y"]
            tx, ty = self.nodes[pair[1]]["x"], self.nodes[pair[1]]["y"]
            mx, my = (sx + tx) / 2, (sy + ty) / 2
            dx, dy = tx - sx, ty - sy
            dist = math.hypot(dx, dy)
            if dist > 0:
                # offset perpendicular: (-dy, dx)
                px, py = -dy / dist, dx / dist
                offset = max(30, int(50 * self._zoom))
                cp_x = mx + px * offset
                cp_y = my + py * offset
                self.edge_control_points[pair] = (cp_x, cp_y)
        self.refresh_edges()
        self.config(cursor="hand2")

    def on_edge_drag_motion(self, event):
        """Mover o ponto de controle enquanto arrasta."""
        if not self.edge_drag_data["active"]:
            return
        pair = self.edge_drag_data["pair"]
        if pair is None:
            return
        # Atualizar o control point para a posição do mouse
        self.edge_control_points[pair] = (event.x, event.y)
        self.refresh_edges()

    def on_edge_drag_release(self, event):
        """Finaliza o arraste — se arrastou pouco, reseta."""
        if not self.edge_drag_data["active"]:
            return
        pair = self.edge_drag_data["pair"]
        # Se o control point ficou muito perto do segmento, remove
        if pair and pair in self.edge_control_points:
            sx, sy = self.nodes[pair[0]]["x"], self.nodes[pair[0]]["y"]
            tx, ty = self.nodes[pair[1]]["x"], self.nodes[pair[1]]["y"]
            cp_x, cp_y = self.edge_control_points[pair]
            dist_to_segment = self._distance_to_segment(sx, sy, tx, ty, cp_x, cp_y)
            if dist_to_segment < 10:
                del self.edge_control_points[pair]
        self.edge_drag_data = {"active": False, "pair": None, "item": None}
        self.config(cursor="")
        self.refresh_edges()
        self._notify()

    def _edge_pair_from_current_item(self):
        item = self.find_withtag("current")
        if not item:
            return None
        for tag in self.gettags(item[0]):
            pair = self.edge_tag_to_pair.get(tag)
            if pair:
                return pair
        return None

    def _find_edge_at(self, x, y):
        """Encontra o par (source, target) da aresta mais próxima do ponto."""
        best = None
        best_dist = 22  # tolerância em pixels
        seen_pairs = set()
        for t in self.automaton.transitions:
            pair = (t.source, t.target)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            if t.source not in self.nodes or t.target not in self.nodes:
                continue
            sx, sy = self.nodes[t.source]["x"], self.nodes[t.source]["y"]
            tx, ty = self.nodes[t.target]["x"], self.nodes[t.target]["y"]
            if pair[0] == pair[1]:
                r = self._scaled_node_radius()
                loop_w = max(14, int(15 * max(0.9, self._zoom)))
                loop_h = max(20, int(30 * max(0.9, self._zoom)))
                segments = [
                    (sx - loop_w, sy - r - loop_h, sx + loop_w, sy - r - loop_h),
                    (sx - loop_w, sy - r - loop_h, sx - loop_w, sy - r),
                    (sx + loop_w, sy - r - loop_h, sx + loop_w, sy - r),
                ]
                d = min(self._distance_to_segment(x1, y1, x2, y2, x, y) for x1, y1, x2, y2 in segments)
            elif pair in self.edge_control_points:
                cp_x, cp_y = self.edge_control_points[pair]
                d = min(
                    self._distance_to_segment(sx, sy, cp_x, cp_y, x, y),
                    self._distance_to_segment(cp_x, cp_y, tx, ty, x, y),
                )
            else:
                d = self._distance_to_segment(sx, sy, tx, ty, x, y)
            if d < best_dist:
                best_dist = d
                best = pair
        return best

    def _distance_to_segment(self, x1, y1, x2, y2, px, py):
        """Distância de um ponto px,py ao segmento x1,y1-x2,y2."""
        dx, dy = x2 - x1, y2 - y1
        length_sq = dx*dx + dy*dy
        if length_sq == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0, min(1, ((px - x1)*dx + (py - y1)*dy) / length_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(px - proj_x, py - proj_y)

    def _adjust_edge_control_points(self, moved_name, dx, dy):
        """Ajusta os control points quando um nó é arrastado.
        Se só uma ponta moveu, o control point segue a posição relativa.
        Se as duas pontas moveram (pan do canvas), o control point segue junto.
        """
        for pair, (cpx, cpy) in self.edge_control_points.items():
            if pair[0] == moved_name and pair[1] == moved_name:
                # self-loop: control point move junto
                self.edge_control_points[pair] = (cpx + dx, cpy + dy)
            elif pair[0] == moved_name:
                # só a origem moveu — ajusta proporcionalmente
                if pair[1] in self.nodes:
                    old_sx = self.nodes[pair[0]]["x"] - dx
                    old_sy = self.nodes[pair[0]]["y"] - dy
                    sx, sy = self.nodes[pair[0]]["x"], self.nodes[pair[0]]["y"]
                    tx, ty = self.nodes[pair[1]]["x"], self.nodes[pair[1]]["y"]
                    # recalcular o control point relativo ao novo segmento
                    # mantém a mesma fração perpendicular
                    old_dx = tx - old_sx
                    old_dy = ty - old_sy
                    old_dist = math.hypot(old_dx, old_dy)
                    new_dx = tx - sx
                    new_dy = ty - sy
                    new_dist = math.hypot(new_dx, new_dy)
                    if old_dist > 0 and new_dist > 0:
                        # fração t do proj no segmento antigo
                        t = max(0, min(1, ((cpx - old_sx)*old_dx + (cpy - old_sy)*old_dy) / (old_dist*old_dist)))
                        new_proj_x = sx + t * new_dx
                        new_proj_y = sy + t * new_dy
                        # distância perpendicular
                        old_nx, old_ny = -old_dy/old_dist, old_dx/old_dist
                        perp_dist = (cpx - old_sx)*old_nx + (cpy - old_sy)*old_ny
                        new_nx, new_ny = -new_dy/new_dist, new_dx/new_dist
                        new_cpx = new_proj_x + new_nx * perp_dist
                        new_cpy = new_proj_y + new_ny * perp_dist
                        self.edge_control_points[pair] = (new_cpx, new_cpy)
            elif pair[1] == moved_name:
                # só o destino moveu — mesma lógica
                if pair[0] in self.nodes:
                    old_tx = self.nodes[pair[1]]["x"] - dx
                    old_ty = self.nodes[pair[1]]["y"] - dy
                    sx, sy = self.nodes[pair[0]]["x"], self.nodes[pair[0]]["y"]
                    tx, ty = self.nodes[pair[1]]["x"], self.nodes[pair[1]]["y"]
                    old_dx = old_tx - sx
                    old_dy = old_ty - sy
                    old_dist = math.hypot(old_dx, old_dy)
                    new_dx = tx - sx
                    new_dy = ty - sy
                    new_dist = math.hypot(new_dx, new_dy)
                    if old_dist > 0 and new_dist > 0:
                        t = max(0, min(1, ((cpx - sx)*old_dx + (cpy - sy)*old_dy) / (old_dist*old_dist)))
                        new_proj_x = sx + t * new_dx
                        new_proj_y = sy + t * new_dy
                        old_nx, old_ny = -old_dy/old_dist, old_dx/old_dist
                        perp_dist = (cpx - sx)*old_nx + (cpy - sy)*old_ny
                        new_nx, new_ny = -new_dy/new_dist, new_dx/new_dist
                        new_cpx = new_proj_x + new_nx * perp_dist
                        new_cpy = new_proj_y + new_ny * perp_dist
                        self.edge_control_points[pair] = (new_cpx, new_cpy)

    def reset_edge_curve(self, source, target):
        """Reseta uma aresta customizada pra curva automática."""
        pair = (source, target)
        if pair in self.edge_control_points:
            self._snapshot()
            del self.edge_control_points[pair]
            self.refresh_edges()
            self._notify()
