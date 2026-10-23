# Amostras

Imagens reais para testes manuais e demonstração. **Não** são dados científicos, porque não têm metadados completos.

| Arquivo | Data | Local | Aparelho | Origem | Autor | Licença |
|---|---|---|---|---|---|---|
| `2026-10-22_sao-paulo_teste-celular.jpg` | 2026-10-22, noite | São Paulo (SP) | Galaxy S24 | Enviada pelo chat (JPEG recomprimido, **sem EXIF**: sem hora, exposição nem GPS) | Fabio | a definir pelo autor |
| `2026-10-22_sao-paulo_nublado_enquadramento-A.jpg` | 2026-10-22, ~21h | São Paulo (SP) | Galaxy S24 | Chat (sem EXIF útil). Céu 100% encoberto; estrutura do telhado no topo, prédio à esquerda | Fabio | a definir pelo autor |
| `2026-10-22_sao-paulo_nublado_enquadramento-B.jpg` | 2026-10-22, ~21h | São Paulo (SP) | Galaxy S24 | Chat (sem EXIF útil). Céu 100% encoberto; telhado embaixo, prédio à direita | Fabio | a definir pelo autor |

## Análise rápida (2026-10-22)

Conversão com `skymonitor-phone-ingest --tz America/Sao_Paulo --lat -23.55 --lon -46.63`. Detecção simples (fundo por mediana, limiar de 5σ, componentes ≥ 6 px):

- 140 fontes detectadas. Ainda não se sabe quantas são estrelas e quantas são luzes da cidade: isso exige plate-solving (M3).
- Alongamento mediano de 3,6. **111 fontes alongadas na mesma direção** (11° ± 13°).
- Interpretação: rastros paralelos e com a mesma forma indicam **movimento da câmera durante a exposição**, não movimento das estrelas. Em 10 s, a rotação da Terra desloca uma estrela cerca de 0,04°, ou 1–2 px na ultra-wide.

## Céu nublado: referência (2026-10-22)

Medidas na região central de céu (JPEG, escala 0–255; o valor depende da exposição automática, então serve como comparação qualitativa):

| Imagem | Fundo mediano | Fontes pontuais | Céu útil no quadro (estimativa) |
|---|---|---|---|
| teste-celular (céu com estrelas) | ~3 | 56 | ~86% |
| nublado A | ~141 | **0** | ~75% |
| nublado B | ~143 | não comparável (a região central inclui a borda do telhado) | ~70% |

**Assinatura de céu encoberto em área urbana:** fundo claro e uniforme (as nuvens refletem a iluminação da cidade) e **nenhuma fonte pontual**. É exatamente o padrão que o módulo de nuvens (M3) precisa reconhecer. Para medidas comparáveis entre noites, use DNG com exposição e ISO fixos.
