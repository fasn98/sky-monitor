# Protocolo de captura com celular (Galaxy S24)

**Objetivo:** gerar imagens **reais** do céu do seu local para desenvolver e testar o processamento: detecção de estrelas, contagem por setor, nuvens, rastros e brilho do fundo. Isso permite trabalhar nesses módulos antes de ter a câmera all-sky.

**O que este protocolo NÃO valida:** a captura automática (indi-allsky/INDI), a operação durante a noite inteira e a cobertura de 180°. Para isso continuam os simuladores INDI e, depois, a câmera all-sky.

> Os nomes de menus abaixo podem variar com a versão do One UI. Itens marcados **[A VERIFICAR]** não foram confirmados no aparelho.

---

## 1. Equipamento

- Galaxy S24, com bateria carregada e, se possível, um power bank.
- Um destes suportes:
  - tripé com cabeça que incline até **90°** (para apontar ao zênite) e suporte para celular com rosca 1/4";
  - **ou** o celular deitado de costas sobre uma superfície firme, com a câmera para cima.
- Controle remoto Bluetooth ou temporizador de 2–5 s, para não tremer a imagem ao tocar na tela.

## 2. Configuração da câmera

1. **Ative o salvamento RAW:** Câmera → Configurações → Opções avançadas de imagem → Formatos de imagem → *Cópias RAW (Pro)*. **[A VERIFICAR]** o nome exato no seu One UI.
2. **Ative a localização nas fotos:** Câmera → Configurações → *Tags de local*. Sem isso, o sistema precisa de `--lat/--lon` manuais.
3. Abra o **modo Pro** e selecione a **ultra-wide (0,6×)**. **[A VERIFICAR]** se o modo Pro do S24 permite a ultra-wide; se não permitir, use a câmera principal (1×) e anote isso.
4. Ajuste:

   | Parâmetro | Valor inicial | Observação |
   |---|---|---|
   | ISO | 800 | Teste também 1600 |
   | Velocidade | 10 s | Teste também 20 e 30 s; reduza se as estrelas ficarem esticadas |
   | Foco | Manual (MF) no infinito | Confirme ampliando uma estrela brilhante |
   | Balanço de branco | Fixo (ex.: 4000 K) | Nunca "Auto", para manter os JPEGs comparáveis |

5. **Desligue:** modo Noite, Otimizador de cena e qualquer processamento automático. **Não use o Astrofoto do Expert RAW** para estes testes, porque ele empilha e processa as imagens, e isso distorce as medidas.

## 3. Sessões de captura (casos de teste)

Mantenha o celular **na mesma posição** durante cada sessão.

| Sessão | O que fazer | Para que serve |
|---|---|---|
| **A. Céu limpo** | 20–30 fotos seguidas, de preferência com a Lua abaixo do horizonte | Calibração da lente e linha de base da contagem de estrelas |
| **B. Parcialmente nublado** | 20–30 fotos seguidas | Mapa de nuvens por setor |
| **C. Passagem de satélite prevista** | Consulte a passagem da ISS (ou de outro satélite brilhante) num app de previsão e fotografe durante ela | **Verdade de referência**: um rastro com horário e trajetória conhecidos, para testar a classificação meteoro × satélite |
| **D. Darks** | 5–10 fotos com a lente **tampada**, com as mesmas configurações e logo após as sessões | Ruído térmico e pixels quentes (o celular aquece) |
| **E. Lua alta** (opcional) | 10 fotos com a Lua visível | Correção da contagem de estrelas pela Lua |

Para cada sessão, crie uma pasta com um arquivo `notas.txt` registrando:
- data e local (bairro ou cidade);
- direção para a qual o celular apontou;
- ISO e velocidade usados;
- condições do céu;
- qualquer imprevisto.

Exemplo de pasta: `2026-10-25_A_ceu-limpo/`.

## 4. Converter para FITS

No notebook (Ubuntu), dentro do repositório:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

skymonitor-phone-ingest ~/Fotos/2026-10-25_A_ceu-limpo -o out/2026-10-25_A \
  --tz America/Sao_Paulo
```

- `--tz` só é usado se a foto não tiver o fuso no EXIF.
- `--lat/--lon/--elev` só são usados se a foto não tiver GPS.
- Em ambos os casos, o FITS registra que o valor veio da configuração (`TIMESRC`/`LOCSRC`) e grava um aviso no `HISTORY`.

### O que vai no FITS

| Entrada | Pixels | Uso |
|---|---|---|
| **DNG** | Mosaico Bayer bruto, linear, `uint16`, sem interpolação; `BAYERPAT`, `BLKLVL0..3` e `WHITELVL` no cabeçalho | **Medidas** (fotometria, contagem de estrelas) |
| **JPEG** | RGB processado, não linear; `LINEAR = F` | Apenas visualização e testes de detecção grosseira |

O cabeçalho também inclui:
- `DATE-OBS` em UTC, com `DATEUNC` (incerteza em segundos). O EXIF não diz se o horário marca o início, o meio ou o fim da exposição, então a incerteza inclui o tempo de exposição;
- `EXPTIME`, `ISOSPEED`, `FOCALLEN`, `SITELAT`/`SITELONG`.

Um valor ausente no EXIF **não é inventado**: o campo fica fora do FITS e o motivo vai para o `HISTORY`.

## 5. Guardar como dados de teste

- Copie **1 ou 2 DNGs representativos** para `tests/data/phone/`. O teste `test_real_dng_roundtrip` passa a rodar automaticamente com eles.
- Cada DNG tem uns 20–30 MB. **Não comite sessões inteiras** no Git: guarde-as fora do repositório ou, se necessário, use Git LFS.
- Como as fotos são suas, declare a licença em `tests/data/phone/README.md` (sugestão: CC BY 4.0).

## 6. Limitações conhecidas

- A ultra-wide do S24 cobre cerca de 120°, não 180°. O modelo de lente do `calib` será ajustado para essa lente, e não para a olho-de-peixe definitiva.
- O sensor do celular é pequeno e aquece com uso contínuo, o que aumenta o ruído ao longo da sessão (por isso os darks no fim).
- O céu urbano limita as estrelas visíveis. Isso é bom para o teste, porque é o cenário real da estação.
- **[A VERIFICAR com DNG real]:**
  - se o DNG do S24 já sai com correção de distorção aplicada;
  - se há margens no sensor (ActiveArea) que alterem o padrão Bayer.

  O primeiro DNG que você enviar responde às duas perguntas.
