# Sky Monitor

Sistema de monitoramento do céu: câmera all-sky + telescópio robótico, com detecção de nuvens, rastros (meteoros e satélites), fotometria e dashboard.

Pensado para uma estação em varanda de apartamento em Santa Catarina, Brasil (~27° S), com céu urbano e clima úmido.

## Status

| Marco | Descrição | Status |
|---|---|---|
| M1 | Arquitetura e decisão build-vs-reuse | ✅ Proposta para revisão — [docs/M1-arquitetura.md](docs/M1-arquitetura.md) |
| — | Adaptador de fotos de celular (DNG/JPEG → FITS) para testes com céu real | ✅ [protocolo](docs/protocolo-captura-celular.md) |
| M2 | Captura all-sky no simulador (FITS, timelapse, keogram) | ⏳ |
| M3 | Calibração da lente, nuvens, rastros, satélites | ⏳ |
| M4 | Dashboard e alertas | ⏳ |
| M5 | Telescópio (simulador → hardware), agendador, fotometria | ⏳ |
| M6 | Guia de instalação física | ⏳ |

## Documentos

- [Especificação completa (prompt original)](docs/prompt.md)
- [M1 — Arquitetura](docs/M1-arquitetura.md)
- [Protocolo de captura com celular](docs/protocolo-captura-celular.md)

## Desenvolvimento

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest && mypy && ruff check .
```

## Licença

[GPL-3.0](LICENSE)

## Princípios

- Nenhum dado inventado; toda incerteza é registrada.
- Funciona sem hardware (simuladores INDI).
- Reaproveita projetos open source maduros (indi-allsky, seestar_alp) em vez de reescrevê-los.
