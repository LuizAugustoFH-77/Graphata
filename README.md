# Graphata

Graphata é um montador e simulador de autômatos em Python com interface gráfica. O foco do projeto é criar, importar, organizar, simular e converter autômatos finitos de forma visual.

## Funcionalidades

- Criação de estados e transições pela interface.
- Simulação passo a passo de cadeias de entrada.
- Conversão de AFN para AFD.
- Minimização de AFD.
- Organização visual automática do grafo.
- Importação e exportação em JSON.

## Execução

Instale as dependências:

```bash
pip install -r requirements.txt
```

Abra a aplicação:

```bash
python main.py
```

## Estrutura

- `core/`: lógica central do autômato, simulador, conversor e minimizador.
- `gui/`: interface gráfica e canvas interativo.
- `utils/`: serialização, validação e layout visual.
- `tests/`: testes automatizados.

## Testes

```bash
pytest
```

## Formato JSON

O projeto usa um JSON leve com `type`, `states` e `transitions`. Consulte [FORMATO_JSON.md](FORMATO_JSON.md) para os detalhes.
