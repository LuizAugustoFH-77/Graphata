# Formato de Importação e Exportação JSON

Este simulador permite a importação e exportação de autômatos em um formato leve estruturado em JSON para facilitar o armazenamento e intercâmbio dos modelos com outras plataformas.

O documento base é um objeto JSON que contém três atributos raiz: `type`, `states` e `transitions`.

## 📌 Estrutura do Arquivo

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
            "source": "q1",
            "symbol": "b",
            "target": "q1"
        }
    ]
}
```

### 1. `type` (String)
Indica a categoria do autômato (ex.: `"AFD"`, `"AFN"`). Isso serve mais para categorização interna; o motor do simulador rodará a leitura não determinística e determinará o rastreamento automaticamente.

### 2. `states` (Lista de Objetos)
Descreve os nós (estados) do seu grafo temporal.
- **`name`** (String): O nome legível do estado, por padrão ex: `"q0"`, mas pode ser `S`, `A`, etc.
- **`is_initial`** (Boolean): Define se o estado inicia a leitura (true ou false).
- **`is_final`** (Boolean): Define se esse estado representa um passo de aceitação/condição de parada com sucesso.

### 3. `transitions` (Lista de Objetos)
Descreve as arestas direcionadas e seus pesos lógicos.
- **`source`** (String): Nome referenciado do estado origem. Deve constar na lista de states.
- **`symbol`** (String): O Token consumido. Use string única tipo `"a"` ou `"1"`. Caso for uma transição vazia (Epsilon), use uma string vazia `""` ou `"ε"`.
- **`target`** (String): O estado em que a máquina entrará após ler aquele símbolo a partir da fonte.

## Comportamento de Interface Gráfica
Ao fazer uso do recém implementado botão **Importar Autômato**, o canvas lerá os nós deste JSON e fará a disperão radial num círculo na interface. Transições serão mapeadas automaticamente e numeradas as arestas para sua correspondência visual.
