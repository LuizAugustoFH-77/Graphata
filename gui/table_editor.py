import tkinter as tk
import customtkinter as ctk
import re
from typing import Callable
from core.automaton import Automaton

class TransitionTableEditor(ctk.CTkToplevel):
    """Popup editor for Automaton states and transitions."""
    def __init__(self, master, current_automaton: Automaton, on_save: Callable):
        super().__init__(master)
        self.title("Editar Tabela de Transições")
        self.geometry("800x500")
        self.minsize(600, 400)
        self.transient(master)
        self.grab_set()

        self.current_automaton = current_automaton
        self.on_save = on_save
        self._loading = True

        # Data structures to track UI elements
        self.alphabet = sorted(list(self.current_automaton.alphabet))
        if not self.alphabet:
            self.alphabet = ["a", "b"]
            
        self.state_rows = []
        
        self._build_ui()
        self._populate_initial_data()

    def _build_ui(self):
        # Top toolbar
        self.toolbar = ctk.CTkFrame(self)
        self.toolbar.pack(side="top", fill="x", padx=10, pady=10)
        
        ctk.CTkButton(self.toolbar, text="+ Linha (Estado)", command=self._add_state_row,
                      fg_color="#1d4ed8", hover_color="#1e40af").pack(side="left", padx=5)
        ctk.CTkButton(self.toolbar, text="+ Coluna (Símbolo)", command=self._add_symbol_col,
                      fg_color="#166534", hover_color="#14532d").pack(side="left", padx=5)
        
        # Grid frame (Scrollable)
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Bottom Actions
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        
        ctk.CTkButton(self.action_frame, text="Salvar", command=self._save_and_close,
                      fg_color="#059669", hover_color="#047857").pack(side="right", padx=5)
        ctk.CTkButton(self.action_frame, text="Cancelar", command=self.destroy,
                      fg_color="#b91c1c", hover_color="#991b1b").pack(side="right", padx=5)

        self._render_headers()

    def _render_headers(self):
        for widget in self.scroll_frame.grid_slaves(row=0):
            widget.destroy()

        headers = ["", "Estado", "Inicial", "Final"]
        for col_idx, text in enumerate(headers):
            lbl = ctk.CTkLabel(self.scroll_frame, text=text, font=ctk.CTkFont(weight="bold"))
            lbl.grid(row=0, column=col_idx, padx=5, pady=5)

        for idx, sym in enumerate(self.alphabet):
            col_idx = 4 + idx
            frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            frame.grid(row=0, column=col_idx, padx=5, pady=5)
            
            lbl = ctk.CTkLabel(frame, text=sym, font=ctk.CTkFont(weight="bold"))
            lbl.pack(side="left")
            
            btn = ctk.CTkButton(frame, text="X", width=20, height=20, fg_color="#b91c1c", hover_color="#991b1b",
                                command=lambda s=sym: self._delete_symbol_col(s))
            btn.pack(side="left", padx=(5, 0))

    def _delete_symbol_col(self, symbol):
        if symbol in self.alphabet:
            self.alphabet.remove(symbol)
        self._render_headers()
        
        for row_data in self.state_rows:
            if symbol in row_data["transitions"]:
                menu_widget = row_data["transitions"][symbol]
                menu_widget.destroy()
                row_data["widgets"].remove(menu_widget)
                del row_data["transitions"][symbol]
                
        # Re-grid remaining columns
        for idx, sym in enumerate(self.alphabet):
            col_idx = 4 + idx
            for row_data in self.state_rows:
                if sym in row_data["transitions"]:
                    row_data["transitions"][sym].grid(row=row_data["row_idx"], column=col_idx)

    def _delete_state_row(self, row_data):
        for widget in row_data["widgets"]:
            widget.destroy()
        self.state_rows.remove(row_data)
        self._reflow_rows()
        self._update_all_dropdowns()

    def _state_sort_key(self, name):
        match = re.fullmatch(r"q(\d+)", name)
        if match:
            return (0, int(match.group(1)), name)
        return (1, name.lower(), name)

    def _next_state_name(self):
        used_indexes = set()
        for row_data in self.state_rows:
            name = row_data["name_var"].get().strip() if row_data["name_var"] else ""
            match = re.fullmatch(r"q(\d+)", name)
            if match:
                used_indexes.add(int(match.group(1)))

        next_index = 0
        while next_index in used_indexes:
            next_index += 1
        return f"q{next_index}"

    def _reflow_rows(self):
        ordered_rows = sorted(self.state_rows, key=lambda row: self._state_sort_key(row["name_var"].get().strip()))
        self.state_rows = ordered_rows
        for row_idx, row_data in enumerate(self.state_rows, start=1):
            row_data["row_idx"] = row_idx
            row_data["widgets"][0].grid(row=row_idx, column=0, padx=2, pady=2)
            row_data["widgets"][1].grid(row=row_idx, column=1, padx=2, pady=2)
            row_data["widgets"][2].grid(row=row_idx, column=2, padx=2, pady=2)
            row_data["widgets"][3].grid(row=row_idx, column=3, padx=2, pady=2)
            for idx, sym in enumerate(self.alphabet, start=4):
                widget = row_data["transitions"].get(sym)
                if widget:
                    widget.grid(row=row_idx, column=idx, padx=2, pady=2)

    def _get_current_state_names(self):
        names = [r["name_var"].get().strip() for r in self.state_rows]
        names = [n for n in names if n]
        if not names:
            return [""]
        return [""] + names
        
    def _update_all_dropdowns(self, *args):
        if self._loading:
            return
        opts = self._get_current_state_names()
        for row_data in self.state_rows:
            for sym, menu in row_data["transitions"].items():
                curr = menu.get()
                menu.configure(values=opts)
                if curr in opts:
                    menu.set(curr)
                else:
                    menu.set("")

    def _add_symbol_col(self):
        dialog = ctk.CTkInputDialog(text="Novo símbolo:", title="Adicionar Símbolo")
        symbol = dialog.get_input()
        if symbol and symbol not in self.alphabet:
            self.alphabet.append(symbol)
            self._render_headers()
            
            col_idx = 3 + len(self.alphabet)
            opts = self._get_current_state_names()
            
            for row_data in self.state_rows:
                menu = ctk.CTkOptionMenu(self.scroll_frame, values=opts, width=80)
                menu.set("")
                menu.grid(row=row_data["row_idx"], column=col_idx, padx=2, pady=2)
                row_data["transitions"][symbol] = menu
                row_data["widgets"].append(menu)

    def _add_state_row(self, name="", is_initial=False, is_final=False, transitions_data=None):
        row_idx = len(self.state_rows) + 1
        
        if transitions_data is None:
            transitions_data = {}
            
        if not name:
            name = self._next_state_name()

        row_data = {
            "name_var": None,
            "init_var": None,
            "final_var": None,
            "transitions": {},
            "widgets": [],
            "row_idx": row_idx
        }

        # Delete button (Col 0)
        del_btn = ctk.CTkButton(self.scroll_frame, text="X", width=24, fg_color="#b91c1c", hover_color="#991b1b",
                                command=lambda: self._delete_state_row(row_data))
        del_btn.grid(row=row_idx, column=0, padx=2, pady=2)
        row_data["widgets"].append(del_btn)

        # State Name (Col 1)
        name_var = tk.StringVar(value=name)
        name_var.trace_add("write", self._on_state_name_changed)
        name_entry = ctk.CTkEntry(self.scroll_frame, textvariable=name_var, width=80)
        name_entry.grid(row=row_idx, column=1, padx=2, pady=2)
        row_data["name_var"] = name_var
        row_data["widgets"].append(name_entry)
        
        # Init Checkbox (Col 2)
        init_var = tk.BooleanVar(value=is_initial)
        init_cb = ctk.CTkCheckBox(
            self.scroll_frame,
            text="",
            variable=init_var,
            width=20,
            command=lambda var=init_var: self._ensure_single_initial(var)
        )
        init_cb.grid(row=row_idx, column=2, padx=2, pady=2)
        row_data["init_var"] = init_var
        row_data["widgets"].append(init_cb)
        
        # Final Checkbox (Col 3)
        final_var = tk.BooleanVar(value=is_final)
        final_cb = ctk.CTkCheckBox(self.scroll_frame, text="", variable=final_var, width=20)
        final_cb.grid(row=row_idx, column=3, padx=2, pady=2)
        row_data["final_var"] = final_var
        row_data["widgets"].append(final_cb)
        
        opts = self._get_current_state_names()
        
        # Transitions (Col 4+)
        for col_idx, symbol in enumerate(self.alphabet, start=4):
            tr_val = transitions_data.get(symbol, "")
            
            menu = ctk.CTkOptionMenu(self.scroll_frame, values=opts, width=80)
            if tr_val:
                menu.set(tr_val)
            else:
                menu.set("")
                
            menu.grid(row=row_idx, column=col_idx, padx=2, pady=2)
            row_data["transitions"][symbol] = menu
            row_data["widgets"].append(menu)

        self.state_rows.append(row_data)
        self._reflow_rows()
        self._update_all_dropdowns()

    def _on_state_name_changed(self, *args):
        if self._loading:
            return
        self._reflow_rows()
        self._update_all_dropdowns()

    def _ensure_single_initial(self, changed_var):
        if not changed_var.get():
            return
        for row_data in self.state_rows:
            if row_data["init_var"] is not changed_var:
                row_data["init_var"].set(False)

    def _populate_initial_data(self):
        states = self.current_automaton.states
        
        for t in self.current_automaton.transitions:
            if t.symbol not in self.alphabet:
                self.alphabet.append(t.symbol)
                
        self._render_headers()

        trans_map = {s: {sym: [] for sym in self.alphabet} for s in states}
        for t in self.current_automaton.transitions:
            trans_map[t.source][t.symbol].append(t.target)

        for s_name, state in states.items():
            t_data = {sym: targets[0] if targets else "" for sym, targets in trans_map[s_name].items()}
            self._add_state_row(name=s_name, is_initial=state.is_initial, is_final=state.is_final, transitions_data=t_data)
            
        if not states:
            self._add_state_row()
            
        self._loading = False
        self._reflow_rows()
        self._update_all_dropdowns()

    def _save_and_close(self):
        parsed_states = []
        parsed_transitions = []
        
        for r in self.state_rows:
            s_name = r["name_var"].get().strip()
            if not s_name:
                continue
                
            parsed_states.append({
                "name": s_name,
                "is_initial": r["init_var"].get(),
                "is_final": r["final_var"].get()
            })
            
            for sym, menu in r["transitions"].items():
                target = menu.get().strip()
                if target:
                    parsed_transitions.append({
                        "source": s_name,
                        "symbol": sym,
                        "target": target
                    })

        self.on_save(parsed_states, parsed_transitions)
        self.destroy()
