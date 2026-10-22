# Amostras

Imagens reais para testes manuais e demonstração. **Não** são dados científicos, porque não têm metadados completos.

| Arquivo | Data | Local | Aparelho | Origem | Autor | Licença |
|---|---|---|---|---|---|---|
| `2026-10-22_sao-paulo_teste-celular.jpg` | 2026-10-22, noite | São Paulo (SP) | Galaxy S24 | Enviada pelo chat (JPEG recomprimido, **sem EXIF**: sem hora, exposição nem GPS) | Fabio | a definir pelo autor |

## Análise rápida (2026-10-22)

Conversão com `skymonitor-phone-ingest --tz America/Sao_Paulo --lat -23.55 --lon -46.63`. Detecção simples (fundo por mediana, limiar de 5σ, componentes ≥ 6 px):

- 140 fontes detectadas. Ainda não se sabe quantas são estrelas e quantas são luzes da cidade: isso exige plate-solving (M3).
- Alongamento mediano de 3,6. **111 fontes alongadas na mesma direção** (11° ± 13°).
- Interpretação: rastros paralelos e com a mesma forma indicam **movimento da câmera durante a exposição**, não movimento das estrelas. Em 10 s, a rotação da Terra desloca uma estrela cerca de 0,04°, ou 1–2 px na ultra-wide.
