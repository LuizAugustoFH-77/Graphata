# Formato de Importação e Exportação JSON do Graphata

O Graphata utiliza um formato leve e estruturado em JSON para exportação e importação de autômatos, visando facilitar o armazenamento, compartilhamento e a interoperabilidade com outras ferramentas acadêmicas ou de simulação.

O arquivo JSON define exclusivamente as propriedades lógicas do autômato (estados, transições e classificação), separando totalmente os dados do modelo da sua representação visual.

---

## 📌 Estrutura Base do Arquivo

O documento raiz deve ser um objeto JSON contendo três propriedades principais obrigatórias:
* `type`: Classificação do autômato.
* `states`: Definição de todos os estados (nós).
* `transitions`: Definição da função de transição (arestas).

### Exemplo Completo de um Arquivo `.json`

```json
{
  "type": "AFD",
  "states": [
    {
      "name": "q0",
      "is_initial": true,
      "is_final": false
    },
    {
      "name": "q1",
      "is_initial": false,
      "is_final": true
    }
  ],
  "transitions": [
    {
      "source": "q0",
      "symbol": "a",
      "target": "q1"
    },
    {
      "source": "q0",
      "symbol": "b",
      "target": "q0"
    },
    {
      "source": "q1",
      "symbol": "a",
      "target": "q1"
    },
    {
      "source": "q1",
      "symbol": "b",
      "target": "q0"
    }
  ]
}
```

---

## 📖 Especificação das Propriedades

### 1. `type` (String)
Define a categoria teórica do autômato carregado.
* **Valores comuns:** `"AFD"` (Autômato Finito Determinístico), `"AFN"` (Autômato Finito Não-Determinístico) ou `"AFNe"` (com transições vazias/Epsilon).
* **Nota:** O simulador do Graphata é capaz de rodar e analisar o grafo dinamicamente; logo, este atributo serve primariamente para categorização e metadados, determinando como validações estritas (como as de determinismo) são aplicadas.

### 2. `states` (Lista de Objetos)
Define todos os estados existentes no autômato. Cada estado deve ser um objeto JSON contendo estritamente os atributos abaixo:
* **`name`** *(String)*: Identificador único e legível do estado (ex.: `"q0"`, `"q1"`, `"S"`, `"A"`).
* **`is_initial`** *(Boolean)*: Sinaliza se este é um estado inicial. Pelo menos um estado deve possuir este valor como `true`.
* **`is_final`** *(Boolean)*: Sinaliza se este é um estado de aceitação (final).

### 3. `transitions` (Lista de Objetos)
Lista a função de transição do autômato na forma de um conjunto de arestas direcionadas.
* **`source`** *(String)*: Nome exato do estado de origem (deve coincidir com o `name` de um estado definido na lista `states`).
* **`symbol`** *(String)*: O símbolo do alfabeto que dispara a transição (ex.: `"a"`, `"0"`).
  * **Transições Vazias (Épsilon / $\varepsilon$):** Representadas rigorosamente por uma string vazia `""` ou pelo caractere `"ε"`.
* **`target`** *(String)*: Nome exato do estado de destino.

---

## 🎨 Aspectos Visuais e Interface Gráfica

Como o formato JSON do Graphata armazena **apenas o modelo lógico**, informações de posição visual (coordenadas XY dos nós e curvas das arestas) não são persistidas no arquivo.

**Comportamento do Aplicativo:**
1. Ao acionar a opção **Importar Autômato**, o motor lê e instancializa os estados.
2. O sistema de layout (`utils/layout.py`) assume o controle visual, gerando de forma orgânica e automática as posições ideais (graças à sua disposição radial ou por forças de atração/repulsão).
3. Transições com múltiplos símbolos entre os mesmos nós são agrupadas visualmente e auto-rotuladas na interface gráfica.
