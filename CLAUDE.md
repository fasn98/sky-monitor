# CLAUDE.md

Guia para agentes trabalhando neste repositório.

## Contexto
- A especificação completa está em `docs/prompt.md`.
- A arquitetura aprovada (ou em revisão) está em `docs/M1-arquitetura.md`. Siga-a. Se precisar divergir, atualize o documento no mesmo PR e explique o motivo.

## Regras
- Trabalhe **um marco por vez**. Ao final de cada marco, informe:
  - o que foi feito;
  - como foi testado;
  - as suposições pendentes;
  - as perguntas para o usuário.
- O indi-allsky é um produtor de dados externo: consuma seus arquivos e o MQTT, sem importar nem modificar o código dele.
- Nunca invente comandos de API, endpoints ou formatos de arquivo. Confirme na documentação oficial e cite a fonte em comentário ou no doc.
- Nunca preencha dados ausentes com valores fictícios. Toda medida carrega sua incerteza.
- Use Python 3.11+, tipagem estrita (mypy), ruff, pytest e configuração em YAML (`config/`).
- Os testes devem passar sem hardware (simuladores INDI e imagens em `tests/data/`, sempre com a fonte e a licença de cada imagem).
- A documentação e as mensagens ao usuário são em português; código e identificadores, em inglês.
