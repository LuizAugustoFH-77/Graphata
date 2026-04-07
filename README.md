# Graphata

> Montador, simulador e visualizador interativo de autômatos finitos — feito em Python com GUI moderna (CustomTkinter, tema dark).

Crie, edite, simule, converta e minimize autômatos diretamente no canvas. Tudo visual, tudo em tempo real.

---

## O que faz

- **Canvas interativo** — duplo clique para criar estados, Shift+arrastar para ligar transições, arraste para mover, scroll para zoom, clique do meio para pan.
- **Simulação passo a passo** — rode uma cadeia de entrada e veja o autômato se iluminar em verde (estado ativo) e amarelo (visitado).
- **Conversão AFN → AFD** — Powerset Construction com fechamento épsilon automático.
- **Minimização de AFD** — algoritmo de particionamento (Hopcroft).
- **Organização visual automática** — layout em camadas com *barycenter ordering* + force-directed relaxation para grafos esparsos; *dense grid* para grafos com 10+ estados.
- **Validação** — detecta estados inalcançáveis, falta de estado inicial/final, (não-)determinismo.
- **Tabela de transições δ** — janela dedicada com a função de transição completa.
- **Teste em lote** — teste dezenas de strings de uma vez.
- **Sugestão inteligente de strings** — BFS no grafo gera exemplos aceitos e rejeitados automaticamente, com botão "Testar" que envia direto pra simulação.
- **Import / Export JSON** — formato leve documentado em [`FORMATO_JSON.md`](FORMATO_JSON.md).
- **Undo (Ctrl+Z)** — histórico de até 30 snapshots.
- **Curvas de aresta manuais** — clique e arraste qualquer aresta para curvá-la do jeito que quiser, melhorando a organização visual. Solte perto do segmento original para resetar.

## Atalhos rápidos

| Ação | Como |
|---|---|
| Criar estado | Duplo clique no vazio |
| Criar transição | Shift + arrastar de um nó ao outro |
| Renomear estado | Duplo clique no nó |
| Menu do estado | Botão direito no nó |
| Apagar estado | Ctrl + botão direito no nó |
| Selecionar aresta | Botão direito na aresta |
| Apagar aresta | Selecione + Delete |
| Curvar aresta manual | Clique e arraste na aresta |
| Resetar curva | Arraste até o segmento e solte, ou Ctrl+Z |
| Zoom | Scroll do mouse |
| Pan | Clique do meio (ou botão esquerdo no vazio) |
| Desfazer | Ctrl+Z |
| Importar JSON | Ctrl+O |
| Exportar JSON | Ctrl+S |

## Instalação

```bash
pip install -r requirements.txt
```

Dependência principal: [`customtkinter`](https://github.com/TomSchimansky/CustomTkinter) (GUI moderna e dark por padrão).

## Execução

```bash
python main.py
```

A janela abre em 1280×720 (mínimo 960×600) com sidebar à esquerda e canvas expansível à direita.

## Estrutura do projeto

```
Graphata/
├── main.py                  # Entry point
├── gui/
│   ├── app.py               # Janela principal, sidebar, topbar, statusbar
│   └── canvas.py            # Canvas Tkinter interativo (nós, arestas, zoom, pan)
├── core/
│   ├── automaton.py         # Modelo do autômato (State, Transition, Automaton)
│   ├── simulator.py         # Motor de simulação com tokenização greedy
│   ├── converter.py         # AFN → AFD (Powerset Construction + ε-closure)
│   └── minimizer.py         # Minimização (Hopcroft) + StringGenerator (BFS)
├── utils/
│   ├── serializer.py        # Import/export JSON
│   ├── validator.py         # Checa determinismo, completude, etc.
│   └── layout.py            # Auto-layout: layered + dense grid + force-directed
├── tests/
│   ├── test_core.py         # Testes da lógica de autômato
│   └── test_layout.py       # Testes do algoritmo de layout
├── FORMATO_JSON.md          # Documentação do formato de serialização
└── requirements.txt         # Dependências
```

## Detalhes técnicos

### Tokenização inteligente
O simulador suporta símbolos multi-caractere (ex: `HC`, `HL`, `M200`). A entrada pode ser separada por vírgulas (`HC,H,HR`) ou tokenizada automaticamente via *greedy longest-match*.

### Geração de strings
O `StringGenerator` usa BFS no grafo de transições com limite de profundidade (20) e nós visitados (5000), gerando exemplos de strings aceitas e rejeitadas — ideal para testar rapidamente se o autômato está correto.

### Layout automático
- **Grafos esparsos (< 10 estados):** layout em camadas (Sugiyama-style) com *barycenter ordering* (4 passagens) e force-directed relaxation.
- **Grafos densos (≥ 10 estados, avg out-degree ≥ 2.6):** grid denso com estados iniciais à esquerda e relaxation adaptativo.

## Testes

```bash
pytest
```

## Formato JSON

Consulte [`FORMATO_JSON.md`](FORMATO_JSON.md) para a especificação completa do formato de importação/exportação.

---

Feito com Python 3 + CustomTkinter + Tkinter Canvas puro. zero dependências externas de grafos.
