import customtkinter as ctk
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from gui.canvas import AutomatonCanvas
from core.automaton import Automaton
from core.simulator import Simulator
from core.converter import Converter
from core.minimizer import AutomatonMinimizer, StringGenerator
from utils.serializer import AutomatonSerializer
from utils.validator import AutomatonValidator

SIDEBAR_W = 270
BG_DARK   = "#0f172a"
BG_PANEL  = "#1e293b"
BG_BTN    = "#334155"
BG_BTN_HV = "#475569"


class App(ctk.CTk):
    """Janela principal do Graphata."""

    def __init__(self):
        super().__init__()
        self.title("Graphata")
        self.geometry("1280x720")
        self.minsize(960, 600)
        self.configure(fg_color=BG_DARK)

        self.automaton = Automaton()

        # ── Layout usando pack (mais confiável para sidebar fixa + canvas expansível) ──
        self._build_topbar()
        self._build_statusbar()   # statusbar no bottom ANTES do body

        # Container central: sidebar | canvas
        self._body = tk.Frame(self, bg=BG_DARK)
        self._body.pack(side="top", fill="both", expand=True)

        self._build_sidebar()
        self._build_canvas_area()

        # Bindings globais
        self.bind("<Control-s>", lambda e: self.export_automaton())
        self.bind("<Control-o>", lambda e: self.import_automaton())
        self.bind("<Control-z>", lambda e: self.canvas.undo())

        # Estado simulação passo a passo
        self._sim_trace   = []
        self._sim_step    = 0
        self._sim_visited = []

        self._update_status()

    # ──────────────────────────── Build UI ────────────────────────────────────

    def _build_topbar(self):
        self.topbar = tk.Frame(self, bg="#1e293b", height=48)
        self.topbar.pack(side="top", fill="x")
        self.topbar.pack_propagate(False)

        tk.Label(self.topbar, text="  Graphata",
                 font=("Arial", 14, "bold"), bg="#1e293b", fg="#f1f5f9"
                  ).pack(side="left", padx=12)

        btns = [
            ("📂 Importar",          self.import_automaton,  "#1d4ed8"),
            ("💾 Exportar",          self.export_automaton,  "#047857"),
            ("🔄 Converter AFN→AFD", self.convert_to_dfa,    "#7c3aed"),
            ("✂️ Minimizar AFD",     self.minimize_dfa,      "#b45309"),
            ("📐 Organizar",         self.organize_automaton, "#0e7490"),
            ("🗑️ Limpar",           self.clear_automaton,   "#991b1b"),
        ]
        for txt, cmd, color in btns:
            b = tk.Button(self.topbar, text=txt, command=cmd,
                          bg=color, fg="white", relief="flat",
                          padx=10, pady=4, cursor="hand2",
                          font=("Arial", 11, "bold"), bd=0,
                          activebackground=BG_BTN_HV, activeforeground="white")
            b.pack(side="left", padx=4, pady=8)

    def _build_statusbar(self):
        self.statusbar = tk.Frame(self, bg="#0a0f1e", height=26)
        self.statusbar.pack(side="bottom", fill="x")
        self.statusbar.pack_propagate(False)
        self.status_label = tk.Label(self.statusbar, text="",
                                     font=("Arial", 10), bg="#0a0f1e", fg="#64748b")
        self.status_label.pack(side="left", padx=12, pady=4)

    def _build_sidebar(self):
        # Frame externo com tamanho fixo
        outer = tk.Frame(self._body, bg=BG_PANEL, width=SIDEBAR_W)
        outer.pack(side="left", fill="y")
        outer.pack_propagate(False)

        # ScrollableFrame interno usando CTkScrollableFrame passando outer como master
        sb = ctk.CTkScrollableFrame(outer, fg_color=BG_PANEL, width=SIDEBAR_W - 20)
        sb.pack(fill="both", expand=True)

        def section(text):
            ctk.CTkLabel(sb, text=text,
                         font=ctk.CTkFont(size=13, weight="bold")
                         ).pack(anchor="w", padx=14, pady=(12, 2))

        def sep():
            tk.Frame(sb, bg="#334155", height=1).pack(fill="x", padx=10, pady=6)

        def btn(text, cmd, color="#334155", hover="#475569"):
            ctk.CTkButton(sb, text=text, command=cmd, height=32,
                          fg_color=color, hover_color=hover,
                          font=ctk.CTkFont(size=12)
                          ).pack(fill="x", padx=12, pady=3)

        # ── Controles ──
        section("Controles do Canvas")
        hints = (
            "🖱 Duplo Clique → Criar estado\n"
            "🖱 Dbl-clique no nó → Renomear\n"
            "🖱 Botão Dir. no nó → Menu\n"
            "⇧ Shift+Arrastar → Transição\n"
            "🖱 Clique aresta + Del → Remover\n"
            "  Ctrl+Dir → Apagar estado\n"
            "🖱 Botão Meio → Pan\n"
            "🖱 Scroll → Zoom\n"
            "⌨ Ctrl+Z → Desfazer"
        )
        ctk.CTkLabel(sb, text=hints, justify="left",
                     font=ctk.CTkFont(size=10), text_color="#94a3b8"
                     ).pack(anchor="w", padx=14, pady=(0, 6))

        sep()

        # ── Simulação ──
        section("Simulação")
        self.test_input = ctk.CTkEntry(sb, placeholder_text="String de teste", height=34)
        self.test_input.pack(fill="x", padx=12, pady=4)

        row_frame = tk.Frame(sb, bg=BG_PANEL)
        row_frame.pack(fill="x", padx=12, pady=2)
        for txt, cmd in [("▶ Rápido", self.run_simulation),
                         ("⏭ Passo",  self.step_simulation),
                         ("⏹ Reset",  self.reset_simulation)]:
            ctk.CTkButton(row_frame, text=txt, command=cmd, height=30, width=72,
                          font=ctk.CTkFont(size=11)
                          ).pack(side="left", padx=2)

        self.result_label = ctk.CTkLabel(sb, text="",
                                         font=ctk.CTkFont(size=12, weight="bold"))
        self.result_label.pack(pady=(4, 0))

        self.trace_box = ctk.CTkTextbox(sb, height=110,
                                        font=ctk.CTkFont(family="Courier", size=10))
        self.trace_box.pack(fill="x", padx=12, pady=4)

        sep()

        # ── Ferramentas ──
        section("Ferramentas")
        btn("✅ Validar Autômato",     self.validate_automaton,      "#14532d", "#166534")
        btn("📊 Tabela de Transições", self.show_transition_table,   "#1e40af", "#1d4ed8")

        sep()

        # ── Teste em Lote ──
        section("Teste em Lote")
        ctk.CTkLabel(sb, text="(uma string por linha)",
                     font=ctk.CTkFont(size=10), text_color="#64748b"
                     ).pack(anchor="w", padx=14)
        self.batch_input = ctk.CTkTextbox(sb, height=80,
                                          font=ctk.CTkFont(family="Courier", size=10))
        self.batch_input.pack(fill="x", padx=12, pady=4)
        btn("🧪 Testar Lote",   self.run_batch_test,  "#7c3aed", "#6d28d9")
        btn("💡 Sugerir Strings", self.suggest_strings, "#b45309", "#92400e")

    def _build_canvas_area(self):
        canvas_outer = tk.Frame(self._body, bg="#1a1a2e")
        canvas_outer.pack(side="left", fill="both", expand=True)

        self.canvas = AutomatonCanvas(canvas_outer, self.automaton,
                                      on_change=self._update_status)
        self.canvas.pack(fill="both", expand=True)

    # ──────────────────────────── Helpers ─────────────────────────────────────

    def _update_status(self):
        n_s = len(self.automaton.states)
        n_t = len(self.automaton.transitions)
        det = "Determinístico" if AutomatonValidator.is_deterministic(self.automaton) else "Não-Determinístico"
        alph = sorted(self.automaton.alphabet)
        self.status_label.configure(
            text=f"  {self.automaton.type}  |  {det}  |  {n_s} estados  |  {n_t} transições  |  Σ = {alph}"
        )

    # ──────────────────────────── I/O ─────────────────────────────────────────

    def import_automaton(self):
        fp = fd.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not fp:
            return
        try:
            aut = AutomatonSerializer.from_json(fp)
            self.automaton = aut
            self.canvas.automaton = aut
            self.canvas.load_from_automaton()
            self.result_label.configure(text="✅ Importado!", text_color="#22c55e")
            self._update_status()
        except Exception as e:
            print(f"[ERRO] {e}")
            mb.showerror("Erro ao importar", str(e))

    def export_automaton(self):
        fp = fd.asksaveasfilename(defaultextension=".json",
                                  filetypes=[("JSON Files", "*.json")])
        if not fp:
            return
        try:
            AutomatonSerializer.to_json(self.automaton, fp)
            self.result_label.configure(text="💾 Exportado!", text_color="#22c55e")
        except Exception as e:
            mb.showerror("Erro ao exportar", str(e))

    def clear_automaton(self):
        self.canvas._snapshot()
        self.automaton.clear()
        self.canvas.clear_ui()
        self.result_label.configure(text="")
        self.trace_box.delete("1.0", "end")
        self._sim_trace = []
        self._sim_step  = 0
        self._update_status()

    # ──────────────────────────── Conversão ───────────────────────────────────

    def convert_to_dfa(self):
        if AutomatonValidator.is_deterministic(self.automaton):
            mb.showinfo("Converter", "O autômato já é determinístico.")
            return
        self.canvas._snapshot()
        afd = Converter.nfa_to_dfa(self.automaton)
        self.automaton = afd
        self.canvas.automaton = afd
        self.canvas.load_from_automaton()
        self.result_label.configure(text="✅ Convertido para AFD!", text_color="#22c55e")
        self._update_status()

    def minimize_dfa(self):
        if not AutomatonValidator.is_deterministic(self.automaton):
            mb.showwarning("Minimizar", "Converta para AFD primeiro.")
            return
        self.canvas._snapshot()
        min_dfa = AutomatonMinimizer.minimize(self.automaton)
        if len(min_dfa.states) >= len(self.automaton.states):
            mb.showinfo("Minimizar", "O autômato já está minimizado.")
            return
        self.automaton = min_dfa
        self.canvas.automaton = min_dfa
        self.canvas.load_from_automaton()
        self.result_label.configure(text="✅ Minimizado!", text_color="#22c55e")
        self._update_status()

    def organize_automaton(self):
        if not self.automaton.states:
            return
        self.canvas.organize_layout()
        self.result_label.configure(text="📐 Layout reorganizado!", text_color="#38bdf8")

    # ──────────────────────────── Simulação ───────────────────────────────────

    def run_simulation(self):
        text = self.test_input.get()
        res  = Simulator(self.automaton).simulate(text)
        self.trace_box.delete("1.0", "end")
        if res.get("error"):
            self.result_label.configure(text=res["error"], text_color="#ef4444")
        else:
            acc   = res["accepted"]
            color = "#22c55e" if acc else "#ef4444"
            msg   = f"ACEITA ✅  '{text}'" if acc else f"REJEITADA ❌  '{text}'"
            self.result_label.configure(text=msg, text_color=color)
            for step in res["trace"]:
                sym    = step["symbol"] or "START"
                states = ",".join(step["states"]) or "∅"
                self.trace_box.insert("end", f"  [{sym}] → {states}\n")
        self.canvas.reset_highlight()

    def step_simulation(self):
        text = self.test_input.get()
        if not self._sim_trace:
            res = Simulator(self.automaton).simulate(text)
            self._sim_trace   = res.get("trace", [])
            self._sim_step    = 0
            self._sim_visited = []
            self.trace_box.delete("1.0", "end")
            self.canvas.reset_highlight()

        if self._sim_step >= len(self._sim_trace):
            last   = self._sim_trace[-1]["states"] if self._sim_trace else []
            finals = {s.name for s in self.automaton.get_final_states()}
            acc    = bool(set(last) & finals)
            self.result_label.configure(
                text="ACEITA ✅" if acc else "REJEITADA ❌",
                text_color="#22c55e" if acc else "#ef4444")
            return

        step   = self._sim_trace[self._sim_step]
        sym    = step["symbol"] or "START"
        active = set(step["states"])
        self._sim_visited = list(set(self._sim_visited) | active)
        self.canvas.highlight_states(active, self._sim_visited)
        self.trace_box.insert("end", f"  [{sym}] → {','.join(active) or '∅'}\n")
        self.trace_box.see("end")
        self.result_label.configure(
            text=f"Passo {self._sim_step + 1}/{len(self._sim_trace)}",
            text_color="#94a3b8")
        self._sim_step += 1

    def reset_simulation(self):
        self._sim_trace   = []
        self._sim_step    = 0
        self._sim_visited = []
        self.trace_box.delete("1.0", "end")
        self.result_label.configure(text="")
        self.canvas.reset_highlight()

    # ──────────────────────────── Validação ───────────────────────────────────

    def validate_automaton(self):
        aut    = self.automaton
        issues = []
        if not aut.states:
            issues.append("⚠️  Autômato vazio.")
        else:
            if not aut.get_initial_states():
                issues.append("❌  Nenhum estado inicial.")
            if not aut.get_final_states():
                issues.append("⚠️  Nenhum estado final.")
            if AutomatonValidator.is_deterministic(aut):
                issues.append("✅  Determinístico (AFD).")
            else:
                issues.append("ℹ️  Não-determinístico (AFN).")
            # Estados inalcançáveis
            reachable = {s.name for s in aut.get_initial_states()}
            changed = True
            while changed:
                changed = False
                for t in aut.transitions:
                    if t.source in reachable and t.target not in reachable:
                        reachable.add(t.target); changed = True
            isolated = set(aut.states) - reachable
            if isolated:
                issues.append(f"⚠️  Inalcançáveis: {', '.join(sorted(isolated))}")
            else:
                issues.append("✅  Todos os estados são alcançáveis.")
        mb.showinfo("Validação do Autômato", "\n".join(issues))

    # ──────────────────────────── Tabela δ ────────────────────────────────────

    def show_transition_table(self):
        aut = self.automaton
        if not aut.states:
            mb.showinfo("Tabela", "Autômato vazio.")
            return
        win = ctk.CTkToplevel(self)
        win.title("Tabela de Transições δ")
        win.geometry("640x420")
        win.grab_set()

        ctk.CTkLabel(win, text="Função de Transição δ",
                     font=ctk.CTkFont(size=14, weight="bold")
                     ).pack(pady=10)

        frame = ctk.CTkScrollableFrame(win)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        alphabet = sorted(aut.alphabet)
        states   = list(aut.states.keys())

        delta = {}
        for t in aut.transitions:
            delta.setdefault(t.source, {}).setdefault(t.symbol, []).append(t.target)

        headers = ["Estado"] + alphabet
        for c, h in enumerate(headers):
            ctk.CTkLabel(frame, text=h, font=ctk.CTkFont(size=12, weight="bold"),
                         fg_color="#334155", corner_radius=4, width=100
                         ).grid(row=0, column=c, padx=1, pady=1, sticky="ew")

        for r, s in enumerate(states, 1):
            obj   = aut.states[s]
            prefix = ("→" if obj.is_initial else " ") + ("✓" if obj.is_final else " ")
            bg = "#1e3a5f" if obj.is_initial else "#0f172a"
            ctk.CTkLabel(frame, text=f"{prefix} {s}", fg_color=bg,
                         corner_radius=4, width=100
                         ).grid(row=r, column=0, padx=1, pady=1, sticky="ew")
            for c, sym in enumerate(alphabet, 1):
                targets = delta.get(s, {}).get(sym, [])
                cell = ", ".join(targets) if targets else "—"
                ctk.CTkLabel(frame, text=cell, fg_color="#0f172a",
                             corner_radius=4, width=100
                             ).grid(row=r, column=c, padx=1, pady=1, sticky="ew")

    # ──────────────────────────── Lote ────────────────────────────────────────

    def run_batch_test(self):
        words = [w.strip() for w in self.batch_input.get("1.0", "end").splitlines() if w.strip()]
        if not words:
            return
        sim = Simulator(self.automaton)
        win = ctk.CTkToplevel(self)
        win.title("Resultados — Teste em Lote")
        win.geometry("380x480")
        win.grab_set()
        ctk.CTkLabel(win, text="Resultados", font=ctk.CTkFont(size=14, weight="bold")
                     ).pack(pady=10)
        box = ctk.CTkScrollableFrame(win)
        box.pack(fill="both", expand=True, padx=10, pady=5)
        ok = no = 0
        for w in words:
            acc = sim.simulate(w)["accepted"]
            ok += acc; no += not acc
            ctk.CTkLabel(box, text=f"  {'✅' if acc else '❌'}  \"{w}\"",
                         text_color="#22c55e" if acc else "#ef4444",
                         font=ctk.CTkFont(family="Courier", size=12), anchor="w"
                         ).pack(fill="x", pady=1)
        ctk.CTkLabel(win, text=f"Total: {len(words)}  ✅ {ok}  ❌ {no}",
                     font=ctk.CTkFont(size=12)).pack(pady=8)

    # ──────────────────────────── Sugestão ────────────────────────────────────

    def suggest_strings(self):
        if not self.automaton.states:
            mb.showinfo("Sugestão", "Crie um autômato primeiro."); return
        try:
            accepted, rejected = StringGenerator.generate(self.automaton, 6, 4)
        except Exception as e:
            mb.showerror("Erro", str(e)); return

        win = ctk.CTkToplevel(self)
        win.title("Strings de Exemplo")
        win.geometry("440x480")
        win.resizable(True, True)
        win.grab_set()

        ctk.CTkLabel(win, text="Strings sugeridas",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(12, 2))
        ctk.CTkLabel(win, text="Clique em ▶ Testar para enviar à simulação",
                     font=ctk.CTkFont(size=10), text_color="#64748b").pack()

        scroll = ctk.CTkScrollableFrame(win, fg_color="#0f172a")
        scroll.pack(fill="both", expand=True, padx=10, pady=8)

        def send_to_sim(s, w):
            self.test_input.delete(0, "end")
            self.test_input.insert(0, s)
            w.destroy()

        # ── Aceitas ──────────────────────────────────────────
        ctk.CTkLabel(scroll, text="✅  Strings Aceitas",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#22c55e").pack(anchor="w", padx=8, pady=(8, 2))

        if accepted:
            for s in accepted:
                row = ctk.CTkFrame(scroll, fg_color="#052e16", corner_radius=6)
                row.pack(fill="x", padx=6, pady=2)
                row.columnconfigure(0, weight=1)
                ctk.CTkLabel(row, text=f'"{s or "ε"}"',
                             font=ctk.CTkFont(family="Courier", size=12),
                             text_color="#86efac", anchor="w"
                             ).grid(row=0, column=0, padx=10, pady=6, sticky="w")
                ctk.CTkButton(row, text="▶ Testar", width=80, height=26,
                              fg_color="#166534", hover_color="#15803d",
                              font=ctk.CTkFont(size=11, weight="bold"),
                              command=lambda st=s: send_to_sim(st, win)
                              ).grid(row=0, column=1, padx=6, pady=4)
        else:
            ctk.CTkLabel(scroll, text="  (nenhuma string aceita encontrada)",
                         text_color="#64748b",
                         font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14)

        # ── Rejeitadas ────────────────────────────────────────
        ctk.CTkLabel(scroll, text="❌  Strings Rejeitadas",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#ef4444").pack(anchor="w", padx=8, pady=(12, 2))

        if rejected:
            for s in rejected:
                row = ctk.CTkFrame(scroll, fg_color="#300000", corner_radius=6)
                row.pack(fill="x", padx=6, pady=2)
                row.columnconfigure(0, weight=1)
                ctk.CTkLabel(row, text=f'"{s or "ε"}"',
                             font=ctk.CTkFont(family="Courier", size=12),
                             text_color="#fca5a5", anchor="w"
                             ).grid(row=0, column=0, padx=10, pady=6, sticky="w")
                ctk.CTkButton(row, text="▶ Testar", width=80, height=26,
                              fg_color="#7f1d1d", hover_color="#991b1b",
                              font=ctk.CTkFont(size=11, weight="bold"),
                              command=lambda st=s: send_to_sim(st, win)
                              ).grid(row=0, column=1, padx=6, pady=4)
        else:
            ctk.CTkLabel(scroll, text="  (nenhuma string rejeitada encontrada)",
                         text_color="#64748b",
                         font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14)


def start_gui():
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    App().mainloop()
