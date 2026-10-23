# Sky Monitor: resumo de passagem de contexto

> Documento para continuar o projeto em outro assistente sem perder contexto.
> Atualizado em **23/10/2026**. Repositório público: **https://github.com/fasn98/sky-monitor** (branch `main`, licença GPL-3.0).
> Idioma do usuário: **português (Brasil)**.

---

## 0. Resumo em 10 linhas

- **Usuário:** Fabio, consultor SAP e arquiteto de soluções em São Paulo. Pretende morar no litoral de Santa Catarina (Blumenau ou Itajaí, ainda indefinido), num apartamento com varanda e vista ampla do céu.
- **Objetivo:** montar um **sistema de monitoramento do céu**: câmera all-sky, depois telescópio robótico, com software próprio para detectar nuvens, meteoros e satélites, fazer fotometria e mostrar tudo num dashboard. O foco é pesquisa amadora e desenvolvimento de software.
- **Decisão de hardware final:** Raspberry Pi 5 + HQ Camera (IMX477) com lente olho-de-peixe M12 + sensores (BME280, MLX90614, DS18B20) + aquecedor anti-orvalho. **A compra está adiada:** Fabio decide no fim de outubro, conforme a situação financeira.
- **Enquanto isso:** o **Galaxy S24** do Fabio (SM-S921B, Android 16) faz as fotos. O processamento roda no **notebook Ubuntu** dele.
- **Já construído e testado com dados reais:** o conversor `skymonitor-phone-ingest` (DNG/JPEG do celular → FITS), a ferramenta de diagnóstico `skymonitor-dng-info`, o gerador de pré-visualização `skymonitor-preview` e um app Android de diagnóstico de câmera.
- **Descobertas importantes no S24:**
  - apps de terceiros têm exposição máxima de **0,1 s**, então a captura é feita pelo **app de câmera da Samsung, no modo Pro** (até 30 s);
  - o modo Pro **não oferece a ultra-wide**;
  - o DNG do modo Pro é **LinearRaw** (já demosaicado), e o **LibRaw não consegue ler**.
- **Último passo pendente:** tirar uma foto **bem exposta** (ex.: 1/30 s), convertê-la e conferir o PNG de pré-visualização, para validar que a decodificação está certa. Depois disso: **noite de céu limpo** e o início do **M3** (calibração da lente, detecção de nuvens, rastros e satélites).

---

## 1. Objetivo e contexto

### 1.1 Origem
Fabio fotografou um telescópio numa livraria: um Greika BM-1000114EQIII, refletor de 114/1000 mm em montagem equatorial manual, por R$ 2.099,90. A análise concluiu que ele **não serve** para os objetivos do projeto:
- o tubo curto com focal de 1000 mm indica um provável desenho Bird-Jones;
- a montagem é leve e totalmente manual, sem GoTo nem controle por computador.

Daí surgiu o plano de um sistema automatizado.

### 1.2 Raciocínio da arquitetura
- Para monitorar uma área grande do céu, a ferramenta certa é uma **câmera all-sky** (olho-de-peixe, 180°), não um telescópio. O telescópio robótico vem depois, como complemento para alvos específicos.
- **Condições do local (SC):**
  - céu urbano (Bortle estimado em 7–8);
  - umidade e nebulosidade altas, maresia;
  - latitude de cerca de 27° S;
  - varanda voltada para o norte é a ideal;
  - não existe Polaris no hemisfério sul, então o alinhamento polar será por plate-solving;
  - nunca fotografar através de vidro;
  - a laje transmite vibração e o prédio gera turbulência térmica.
- **Redes de ciência cidadã:**
  - a **BRAMON** usa o pacote SonotaCo UFO com câmeras de campo plano;
  - o **Global Meteor Network** (software RMS) diz que câmeras all-sky comerciais não têm sensibilidade suficiente para meteoros.
  - Conclusão: a all-sky serve para **monitoramento** (nuvens, bólidos, satélites, qualidade do céu). Contribuir com dados de meteoros exigiria uma estação dedicada opcional (IMX291 + RMS ou UFOCapture).

### 1.3 Marcos (definidos no prompt original)
| Marco | Conteúdo | Status |
|---|---|---|
| M1 | Arquitetura + decisão build-vs-reuse | ✅ feito (`docs/M1-arquitetura.md`) |
| — | Conversor de fotos de celular → FITS | ✅ feito e testado com DNG real |
| — | App Android de diagnóstico de câmera | ✅ feito, rodou no S24 |
| — | BOM (lista de materiais) da estação | ✅ feito (`docs/BOM.md`) |
| M2 | Captura all-sky no simulador INDI (FITS, timelapse, keogram) | ⏳ não iniciado |
| M3 | Calibração da lente, nuvens, rastros, satélites | ⏳ próximo |
| M4 | Dashboard + alertas | ⏳ |
| M5 | Telescópio (simulador → hardware), agendador, fotometria | ⏳ |
| M6 | Guia de instalação física | ⏳ |

---

## 2. Decisões tomadas

### 2.1 Arquitetura (M1)
| Área | Decisão | Motivo |
|---|---|---|
| Captura all-sky | **Reaproveitar o indi-allsky** (GPL-3.0) **sem modificar**, tratando-o como produtor de dados externo, lido por arquivos e MQTT | Já faz captura INDI/libcamera, keogram, timelapse, detecção de rastros, contagem de estrelas, pseudo-SQM, aquecedor de orvalho, sensores e MQTT. Recomenda o Raspberry Pi 5 |
| Calibração e detecção avançada | **Construir** | O indi-allsky não faz calibração astrométrica da lente, mapa de nuvens por setor nem classificação meteoro/satélite com incerteza |
| Satélites | Skyfield + dados GP da CelesTrak em **JSON/OMM**, não TLE | Objetos com número de catálogo ≥ 100000 não existem em formato TLE |
| Telescópio | Camada de abstração (`TelescopeBackend` Protocol) com backends **INDI** (pyindi-client), **Alpaca** e simulador | Permite trocar de hardware sem reescrever |
| Seestar | Usar o **seestar_alp** como ponte | Controlador standalone com interface Alpaca |
| Agendador | **Construir** um leve | O N.I.N.A. só roda em Windows, e o Ekos é pesado demais para um Pi sem monitor |
| Fotometria | photutils, exportando no **AAVSO Extended File Format** | Formato documentado. Câmera colorida sem filtro usa o código `CV`, nunca `V` |
| Dashboard | FastAPI, aproveitando a imagem ao vivo do indi-allsky | |
| Banco de dados | SQLAlchemy: SQLite no início, PostgreSQL depois | |
| Licença | **GPL-3.0** (decidida pelo usuário) | Compatível com indi-allsky e pyindi-client |
| Repositório | **Público** | Necessário para o GitHub Actions gratuito: a conta do usuário estava com falha de pagamento |

### 2.2 Ambiente de desenvolvimento
- **Notebook do Fabio:** Ubuntu (Acer Nitro ANV15-52), usuário `fasn98`, Python 3.13. Tem conda `(base)` instalado, mas o projeto usa um **venv** próprio em `~/sky-monitor/.venv`.
- **Pastas de dados:** `~/skymonitor/inbox` (fotos copiadas do celular), `~/skymonitor/fits` (FITS gerados), `~/skymonitor/preview` (PNGs).
- **Celular → notebook:** cabo USB, por MTP. Comandos que funcionaram:
  ```bash
  gio mount mtp://SAMSUNG_SAMSUNG_Android_R3CX304KJ3X/
  CAM="$(ls -d /run/user/$(id -u)/gvfs/*/'Internal storage'/DCIM/Camera)"
  ls -t "$CAM" | head -10
  cp "$CAM"/$(ls -t "$CAM" | grep -i '\.dng$' | head -1) ~/skymonitor/inbox/
  ```
  - Existe também a pasta `Internal storage (Dual Messenger)`, que **não** tem as fotos.
  - O MTP só funciona com o celular **desbloqueado** e no modo "Transferir arquivos".
- **Ainda não tem Raspberry Pi.** O M2 foi planejado para rodar no notebook, de forma nativa (o indi-allsky suporta Ubuntu 24.04 e 26.04) ou em Docker.
- **Opção discutida:** uma VPS da Contabo como ambiente de desenvolvimento remoto. Não foi configurada.

### 2.3 Galaxy S24: fatos verificados no aparelho real
| Fato | Fonte |
|---|---|
| Apps de terceiros (Camera2) têm **exposição máxima de 0,10 s** em todas as câmeras, com ISO de 25 (ou 48) a 3200 | App de diagnóstico, 22/10/2026 |
| Câmeras: 0 = traseira principal 5,4 mm (~87° na diagonal); 2 = ultra-wide 2,2 mm (~116°); 6 = tele 7,0 mm (física, dentro da lógica 0); 1 e 3 = frontais 3,3 mm | App de diagnóstico |
| O **app de câmera da Samsung** chega a 30 s no modo Pro → é ele que se usa para fotografar o céu | Documentação e teste |
| O **modo Pro do S24 oferece só 1×/2×/4×/10×**; **não tem ultra-wide** → a referência passa a ser a **câmera principal 1×**, em **12M** (não 50M) | Tela do celular |
| O DNG do modo Pro é **LinearRaw** (fotometria 34892): **já demosaicado**, 3 canais × 12 bits, compressão **lossless JPEG** (7), BlackLevel 0, WhiteLevel 4095 | `skymonitor-dng-info` |
| O **LibRaw recusa** esse DNG ("data corrupted at …"), mesmo com cópia íntegra (tamanho idêntico) → o conversor usa **tifffile + imagecodecs** | Teste real |
| A Samsung parece aplicar balanço de branco antes de gravar: em saturação, R ≈ 2301, G ≈ 4095, B ≈ 1696, e o G chega a passar do WhiteLevel (4121) | Teste real |
| A imagem saiu 3060×3060 → proporção **1:1**. Usar **4:3** (4080×3060) | Teste real |
| **Hipótese:** o EXIF `DateTimeOriginal` marca o **fim** da exposição (fica ~10 s depois do horário do nome do arquivo em fotos de 10 s). **[A VERIFICAR]** com um evento de horário conhecido (passagem da ISS) | Teste real |
| O EXIF traz `OffsetTimeOriginal` (fuso) e GPS → `TIMESRC=exif_offset`, `LOCSRC=exif_gps` | Teste real |
| Imagens enviadas por chat perdem o EXIF. Dados de verdade devem ir **por USB** | Teste real |
| Camera Assistant (app da Samsung): o timer tira até **7 fotos** (intervalo 1–3 s), e funciona no modo Pro | Samsung Community |
| Para fotografar a noite toda: app de clique automático por acessibilidade (MacroDroid ou "auto clicker"), **sem root** | Plano, ainda não testado |

### 2.4 Decisões de hardware (BOM, compra adiada)
Arquivo `docs/BOM.md` e página interativa da BOM.
- **Kit Pi 5 escolhido:** "Kit Completo Raspberry Pi5 Pi 5 8gb Ram, Sd 128gb, fonte 100%", vendedor **ALFA IMPORT** (MercadoLíder), **R$ 2.306,97 à vista**, código MLB-4490907968: https://produto.mercadolivre.com.br/MLB-4490907968-kit-completo-raspberry-pi5-pi-5-8gb-ram-sd-128gbfonte-100-_JM
  - Traz: Pi 5 8 GB, fonte branca (parece a oficial; confirmar que é de 27 W), Active Cooler, case, micro-HDMI e SanDisk Ultra de 128 GB.
  - O parcelamento tem juros: 2x = +8,3% (~5,5% a.m.); 10x = +14,4% (~2,5% a.m.).
  - **O usuário adiou a compra**: decide no fim de outubro.
- **Câmera:** Raspberry Pi HQ Camera (IMX477), de preferência a **versão M12** (vem sem lente). Alternativa: versão C/CS + lente **Arducam LN031** (1,56 mm, f/2, ~180°, vem com adaptador M12→C/CS). Precisa do **cabo de câmera do Pi 5** (mini → padrão, 22→15 pinos), achado por cerca de R$ 27,78.
- **Sensores:**
  - BME280 (cuidado: muitos anúncios vendem BMP280, que não mede umidade; teste: o registrador 0xD0 retorna 0x60 no BME280);
  - MLX90614 na versão de **3 V (ESF-BAA)**, para medir a temperatura do céu e detectar nuvens;
  - DS18B20 à prova d'água (há kits com a plaquinha que já traz o pull-up).
- **Controle:**
  - módulo MOSFET de nível lógico **D4184** (não usar o IRF520, que não funciona com 3,3 V);
  - aquecedor PTC de 12 V (5–10 W);
  - fonte de 12 V 2 A (o GND dela deve ser ligado ao GND do Pi).
- **Bancada:** protoboard de 830 pontos, jumpers **macho-fêmea**, T-Cobbler, multímetro.
- **Ligações:**
  - I2C (BME280, MLX90614, TSL2591): pino 1 3V3, pino 6 GND, GPIO2/pino 3 SDA, GPIO3/pino 5 SCL;
  - DS18B20: GPIO4/pino 7, com 4,7 kΩ para 3V3;
  - MOSFET: GPIO18/pino 12 com PWM **[confirmar no Pi 5]**.

---

## 3. O que foi construído (no repositório)

### 3.1 Ferramentas de linha de comando (Python, pacote `skymonitor`)
| Comando | O que faz |
|---|---|
| `skymonitor-phone-ingest IN... -o OUT [--tz TZ] [--lat --lon --elev] [--watch --poll 10 --settle 5] [--overwrite]` | Converte DNG/JPEG do celular em FITS. Busca em subpastas. Quando há X.dng e X.jpg, usa só o DNG. Pula FITS que já existem. `--watch` fica observando a pasta |
| `skymonitor-dng-info ARQ.dng...` | Mostra a estrutura do DNG (IFD0, SubIFDs, compressão, fotometria, tags) e tenta abrir com o LibRaw |
| `skymonitor-preview ARQ.fits... [-o DIR] [--stretch 10] [--max-size 1600]` | Gera um PNG com realce asinh, pinta de **magenta** os pixels saturados e informa a % de saturação |

**Cabeçalho FITS gerado:**
- **identificação e tempo:** `IMAGETYP, ORIGIN, SRCFILE, INSTRUME, DATE-OBS` (UTC), `TIMESRC, DATEUNC`;
- **exposição e óptica:** `EXPTIME, ISOSPEED, FOCALLEN, FOCAL35, EXIFORNT`;
- **local:** `SITELAT, SITELONG, SITEELEV, LOCSRC`;
- **pixels:** `ROWORDER=TOP-DOWN`, `PIXKIND` (cfa/linear_rgb/rgb), `DECODER` (libraw/tifffile/pillow), `LINEAR`;
- **só para CFA:** `BAYERPAT`;
- **níveis:** `WHITELVL`, `BLKLVL0..n`;
- **avisos:** `HISTORY`, transliterado para ASCII.

**Regra central:** nada é inventado. Um valor ausente fica fora do cabeçalho e o motivo vai para o `HISTORY`. O fallback de fuso ou local só é usado quando passado explicitamente, e o cabeçalho registra a origem.

### 3.2 App Android de diagnóstico (`android/`, Kotlin, Camera2, sem root)
- **Relatório:** lista todas as câmeras com RAW, MANUAL_SENSOR, faixa de exposição e ISO, focais, FOV aproximado, sensor, CFA, níveis, distorção e calibração. Salva um JSON em `Download/SkyMonitor/` e tem um botão para compartilhar.
- **Captura de teste:** faz uma exposição RAW manual e grava DNG via DngCreator. Compara a exposição e o ISO pedidos com os informados pela câmera.
- **Build:** GitHub Actions (`.github/workflows/android.yml`) → pre-release `android-diag-latest` com `skymonitor-diag.apk`. Usa uma chave de debug fixa, commitada de propósito (credenciais públicas padrão do Android).
- **Versões:** AGP 8.7.3, Kotlin 2.1.0, Gradle 8.11.1, compileSdk/targetSdk 35, minSdk 30, sem AndroidX.
- **Resultado:** confirmou o limite de 0,1 s. O app vale como ferramenta para reavaliar em atualizações futuras do celular.

### 3.3 Documentos
- `docs/prompt.md`: especificação completa original (prompt para agente).
- `docs/M1-arquitetura.md`: arquitetura, fluxo de dados, avaliação dos projetos existentes, perguntas e suposições, fontes.
- `docs/protocolo-captura-celular.md`: configuração do celular e sessões de teste (céu limpo, nublado, passagem da ISS, darks, Lua).
- `docs/protocolo-captura-automatica-s24.md`: captura automática com o app da Samsung, horários de crepúsculo, armazenamento, transferência, checagem pelo FITS e o que o DNG do S24 é.
- `docs/BOM.md`: lista de materiais com armadilhas de compra.
- `samples/`: 3 JPEGs reais (sem EXIF) e uma análise rápida:
  - foto com tremor: 111 rastros paralelos, ou seja, a câmera se mexeu;
  - céu 100% nublado: fundo ~141/255 e 0 fontes pontuais, a "assinatura" de nuvem urbana.
- `android/README.md`: instalação do APK e tabela de resultados do S24.

### 3.4 Testes e qualidade
- **29 testes passam e 1 é pulado** (o teste com DNG real em `tests/data/phone/`, que ainda não tem arquivo).
- `mypy --strict` e `ruff` estão limpos.
- Fixtures sintéticas cobrem:
  - JPEG com EXIF controlado;
  - DNG Bayer nos 4 padrões, lido pelo LibRaw;
  - DNG LinearRaw, lido pelo LibRaw e também com fallback forçado.
- **Bug encontrado e corrigido:** o LibRaw devolve 4 canais para LinearRaw; o conversor agora corta para `num_colors`.

---

## 4. Problemas em aberto e próximos passos

### 4.1 Imediatos (onde a conversa parou)
1. **Validar a decodificação do DNG LinearRaw com uma foto bem exposta.** As duas fotos de teste (10 s, ISO 800, quarto iluminado) saíram **99,9% saturadas**.
   - Próximo passo: foto no **modo Pro, 1/30 s, ISO 800, 4:3, 1×** de algo com detalhe → copiar → `skymonitor-phone-ingest` → `skymonitor-preview` → comparar o PNG com a foto da Galeria.
   - Se bater, a cadeia celular → FITS está validada.
2. Mudar a proporção da câmera para **4:3**.
3. **Primeira noite de céu limpo**, de preferência no litoral (o usuário planeja passar uns dias lá):
   - celular fixo (tripé ou apoiado), timer ou comando de voz ("Capturar");
   - modo Pro, 1×, 12M, RAW, ISO 800, 10 s, MF no infinito, WB fixo 4000K;
   - sessões: céu limpo (20–30 frames), nublado, passagem da ISS, darks no fim.

### 4.2 Pendências marcadas [A VERIFICAR]
- Se o EXIF do S24 marca o fim da exposição (hipótese). Confirmar com um evento de horário conhecido antes de mudar o `DATE-OBS` para o meio da exposição.
- Que processamento a Samsung aplica no DNG LinearRaw (redução de ruído, sombreamento, balanço de branco).
- Se o app Expert RAW libera a ultra-wide com exposição manual.
- Formato exato do MQTT do indi-allsky e se ele funciona com `indi_simulator_ccd` (M2).
- Interface Alpaca do seestar_alp com o firmware atual (M5).
- Política de frequência de download da CelesTrak (M3).
- Pino PWM do Pi 5 para o MOSFET (provavelmente GPIO18).
- Se a fonte do kit do Mercado Livre é mesmo a oficial de 27 W.

### 4.3 Próximos marcos técnicos
- **M3 com dados do celular:**
  - calibração astrométrica da lente (modelo de projeção ajustado com estrelas do Yale BSC ou Hipparcos);
  - mapa de nuvens (estrelas detectadas versus esperadas, por setor);
  - detecção de rastros com OpenCV;
  - cruzamento com satélites (Skyfield + CelesTrak JSON);
  - estimativa do brilho de fundo;
  - máscara de horizonte (no local de teste em SP há um telhado e um prédio).
- **M2:** indi-allsky + simulador INDI no notebook (Ubuntu nativo ou Docker).
- **Automação noturna com o S24:** Camera Assistant ou clique automático a cada 60 s (~480 fotos ou ~12 GB por noite) e sincronização para o notebook (USB ou um fork do Syncthing; o app oficial do Syncthing para Android foi descontinuado).
- **Compra do hardware** (fim de outubro), depois montagem na protoboard e migração do pipeline para o Pi.

---

## 5. Regras, estilo e preferências

### 5.1 Do usuário
- **Só verdade e ciência:** "No fake news, only facts based on science". Nada de afirmar o que não foi verificado; marcar incertezas.
- Prefere **prompts completos, prontos para agente**, em vez de passo a passo.
- Comunicação **clara e prática**; temas complexos acessíveis, sem sensacionalismo.
- Conversa em **português**. Usa muito o **celular**, então mensagens curtas e comandos prontos para copiar funcionam melhor.
- Ao comprar, quer **links clicáveis** do Mercado Livre para conferir. Pediu comparação de parcelamento (forneça fatos, não recomendação financeira).

### 5.2 Do repositório (`CLAUDE.md`, válido para qualquer agente)
```markdown
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
```

### 5.3 Convenções de commit
- Mensagens em português, descritivas.
- Autor: `Fabio <fasn98@gmail.com>` (o repositório é público, então esse e-mail aparece nos commits).
- Imagens em `samples/` e `tests/data/` precisam de fonte, autor e licença no README da pasta. A licença das fotos do Fabio ainda está "a definir pelo autor".

---

## 6. Estrutura do repositório

```
sky-monitor/
├── .github/workflows/android.yml   # build do APK + pre-release android-diag-latest
├── .gitignore
├── CLAUDE.md                       # regras para agentes (seção 5.2)
├── LICENSE                         # GPL-3.0
├── README.md                       # status dos marcos e links
├── pyproject.toml                  # pacote skymonitor (seção 7.1)
├── android/                        # app de diagnóstico de câmera (Kotlin)
│   ├── README.md                   # instalação e tabela de resultados do S24
│   ├── build.gradle.kts, settings.gradle.kts, gradle.properties, gradlew*, gradle/wrapper/
│   └── app/
│       ├── build.gradle.kts, debug.keystore
│       └── src/main/{AndroidManifest.xml, res/values/strings.xml,
│           java/io/github/fasn98/skymonitor/diag/{MainActivity,CameraReport,TestCapture,Downloads}.kt}
├── docs/
│   ├── prompt.md                   # especificação original (seção 7.5)
│   ├── M1-arquitetura.md
│   ├── BOM.md
│   ├── protocolo-captura-celular.md
│   └── protocolo-captura-automatica-s24.md
├── samples/                        # fotos reais de teste + README com a análise
├── src/skymonitor/
│   ├── __init__.py, py.typed
│   ├── preview.py                  # skymonitor-preview
│   └── ingest/
│       ├── __init__.py
│       ├── phone.py                # skymonitor-phone-ingest
│       └── dnginfo.py              # skymonitor-dng-info
└── tests/
    ├── conftest.py                 # fixtures: JPEG/DNG sintéticos
    ├── test_phone_ingest.py
    ├── test_preview.py
    └── data/phone/README.md        # onde colocar DNGs reais (pendente)
```

**Instalação (notebook):**
```bash
cd ~ && git clone https://github.com/fasn98/sky-monitor.git && cd sky-monitor
conda deactivate                    # se o (base) do conda estiver ativo
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q && mypy && ruff check .
mkdir -p ~/skymonitor/{inbox,fits,preview}
skymonitor-phone-ingest ~/skymonitor/inbox -o ~/skymonitor/fits --watch --tz America/Sao_Paulo
```

---

## 7. Código e configurações principais (completos)

### 7.1 pyproject.toml

`pyproject.toml`

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "sky-monitor"
version = "0.1.0"
description = "Monitoramento do céu: câmera all-sky + telescópio robótico"
readme = "README.md"
license = "GPL-3.0-only"
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.26",
    "astropy>=6.0",
    "exifread>=3.0",
    "rawpy>=0.21",
    "pillow>=10.0",
    "tifffile>=2024.1",
    "imagecodecs>=2024.1",
]

[project.optional-dependencies]
dev = ["pytest>=8", "mypy>=1.10", "ruff>=0.5"]

[project.scripts]
skymonitor-phone-ingest = "skymonitor.ingest.phone:main"
skymonitor-dng-info = "skymonitor.ingest.dnginfo:main"
skymonitor-preview = "skymonitor.preview:main"

[tool.hatch.build.targets.wheel]
packages = ["src/skymonitor"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]

[tool.mypy]
python_version = "3.11"
strict = true
mypy_path = "src"
packages = ["skymonitor"]

[[tool.mypy.overrides]]
module = ["exifread.*", "rawpy.*", "astropy.*", "tifffile.*"]
ignore_missing_imports = true
```

### 7.2 Conversor celular → FITS

`src/skymonitor/ingest/phone.py`

```python
"""Ingest adapter for smartphone sky photos (DNG RAW or JPEG) -> FITS.

Lets the downstream pipeline (calibration, cloud/trail detection) be developed and
tested with real sky images from a phone (e.g. Galaxy S24) before the all-sky camera
exists. Every output is a FITS file, the same format indi-allsky produces.

Scientific rules applied here (see CLAUDE.md):
* A value missing from EXIF is never invented: the FITS keyword is simply omitted and
  a HISTORY line records the absence.
* Fallbacks (configured time zone / site) are only used when explicitly passed in, and
  the header records that the value came from a fallback (TIMESRC / LOCSRC).
* The timestamp uncertainty is recorded (DATEUNC), because EXIF does not say whether
  DateTimeOriginal marks the start, middle or end of a long exposure.

References:
* EXIF 2.32 (CIPA DC-008-2019): DateTimeOriginal, SubSecTimeOriginal,
  OffsetTimeOriginal (added in 2.31), ExposureTime, ISOSpeedRatings
  (PhotographicSensitivity), FocalLength, FocalLengthIn35mmFilm, GPS IFD.
  Published by CIPA (Camera & Imaging Products Association).
* FITS Standard 4.0 (DATE-OBS as ISO-8601 UTC).
  https://fits.gsfc.nasa.gov/fits_standard.html
* SITELAT/SITELONG/SITEELEV, FOCALLEN, BAYERPAT, XBAYROFF/YBAYROFF and ROWORDER are
  community conventions (used by N.I.N.A., SharpCap, ASTAP and others), not part of
  the FITS standard.
* DNG decoding via rawpy (LibRaw bindings): https://letmaik.github.io/rawpy/
"""

from __future__ import annotations

import argparse
import sys
import time
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

import exifread
import numpy as np
import numpy.typing as npt
from astropy.io import fits
from PIL import Image

RAW_SUFFIXES = frozenset({".dng"})
JPEG_SUFFIXES = frozenset({".jpg", ".jpeg"})
SUPPORTED_SUFFIXES = RAW_SUFFIXES | JPEG_SUFFIXES

# EXIF DateTimeOriginal has 1 s resolution unless SubSecTimeOriginal is present.
_EXIF_SECOND_RESOLUTION_S = 1.0

TimeSource = Literal["exif_offset", "fallback_tz"]
LocationSource = Literal["exif_gps", "fallback_site"]


@dataclass(frozen=True)
class Site:
    """Observing site used only as an explicit fallback when EXIF has no GPS."""

    latitude_deg: float
    longitude_deg: float
    elevation_m: float | None = None


@dataclass(frozen=True)
class PhoneFrameMetadata:
    source_path: Path
    make: str | None = None
    model: str | None = None
    date_obs_utc: datetime | None = None
    time_source: TimeSource | None = None
    date_obs_uncertainty_s: float | None = None
    exposure_s: float | None = None
    iso: int | None = None
    focal_length_mm: float | None = None
    focal_length_35mm: float | None = None
    orientation: int | None = None
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    elevation_m: float | None = None
    location_source: LocationSource | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PixelData:
    """Pixel array plus what is needed to interpret it.

    kind == "cfa": raw Bayer mosaic, linear, shape (H, W), uint16.
    kind == "linear_rgb": demosaiced but still linear DNG ("LinearRaw"), shape (3, H, W).
    kind == "rgb": processed JPEG, gamma-encoded (non-linear), shape (3, H, W), uint8.
    """

    data: npt.NDArray[Any]
    kind: Literal["cfa", "linear_rgb", "rgb"]
    bayer_pattern: str | None = None
    black_levels: tuple[float, ...] | None = None
    white_level: int | None = None
    decoder: str | None = None


# --------------------------------------------------------------------------- EXIF


def read_exif(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        tags: dict[str, Any] = exifread.process_file(fh, details=False)
    return tags


def _first(tags: Mapping[str, Any], key: str) -> Any | None:
    tag = tags.get(key)
    if tag is None:
        return None
    values = tag.values
    if isinstance(values, list):
        return values[0] if values else None
    return values


def _str(tags: Mapping[str, Any], key: str) -> str | None:
    value = _first(tags, key)
    if value is None:
        return None
    text = str(value).strip().strip("\x00").strip()
    return text or None


def _float(tags: Mapping[str, Any], key: str) -> float | None:
    value = _first(tags, key)
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return result if np.isfinite(result) else None


def dms_to_degrees(dms: Sequence[Any], ref: str) -> float:
    """Convert EXIF GPS (degrees, minutes, seconds) + ref (N/S/E/W) to signed degrees."""
    if len(dms) != 3:
        raise ValueError(f"GPS coordinate must have 3 components, got {len(dms)}")
    deg, minutes, seconds = (float(v) for v in dms)
    value = deg + minutes / 60.0 + seconds / 3600.0
    ref = ref.strip().upper()
    if ref in ("S", "W"):
        return -value
    if ref in ("N", "E"):
        return value
    raise ValueError(f"Invalid GPS reference {ref!r}")


def _parse_offset(text: str) -> timezone:
    sign = -1 if text.startswith("-") else 1
    hours, minutes = text.lstrip("+-").split(":")
    return timezone(sign * timedelta(hours=int(hours), minutes=int(minutes)))


def parse_metadata(
    path: Path,
    tags: Mapping[str, Any],
    *,
    fallback_tz: tzinfo | None = None,
    fallback_site: Site | None = None,
) -> PhoneFrameMetadata:
    warnings: list[str] = []

    exposure_s = _float(tags, "EXIF ExposureTime")
    if exposure_s is None:
        warnings.append("EXIF sem ExposureTime: EXPTIME omitido")

    iso_value = _first(tags, "EXIF ISOSpeedRatings")
    iso = int(iso_value) if iso_value is not None else None

    # --- time
    date_obs_utc: datetime | None = None
    time_source: TimeSource | None = None
    uncertainty: float | None = None
    raw_dt = _str(tags, "EXIF DateTimeOriginal")
    if raw_dt is None:
        warnings.append("EXIF sem DateTimeOriginal: DATE-OBS omitido")
    else:
        naive = datetime.strptime(raw_dt, "%Y:%m:%d %H:%M:%S")
        resolution = _EXIF_SECOND_RESOLUTION_S
        subsec = _str(tags, "EXIF SubSecTimeOriginal")
        if subsec and subsec.isdigit():
            naive += timedelta(seconds=float(f"0.{subsec}"))
            resolution = 10.0 ** -len(subsec)

        offset_text = _str(tags, "EXIF OffsetTimeOriginal")
        tz: tzinfo | None = None
        if offset_text:
            try:
                tz = _parse_offset(offset_text)
                time_source = "exif_offset"
            except ValueError:
                warnings.append(f"OffsetTimeOriginal inválido: {offset_text!r}")
        if tz is None and fallback_tz is not None:
            tz = fallback_tz
            time_source = "fallback_tz"
            warnings.append(f"Fuso horário ausente no EXIF; usado o configurado ({fallback_tz})")
        if tz is None:
            warnings.append("Fuso horário desconhecido: DATE-OBS omitido")
        else:
            date_obs_utc = naive.replace(tzinfo=tz).astimezone(UTC)
            # EXIF does not define whether the stamp is start/mid/end of exposure.
            uncertainty = resolution + (exposure_s or 0.0)

    # --- location
    lat = lon = elev = None
    location_source: LocationSource | None = None
    lat_tag, lon_tag = tags.get("GPS GPSLatitude"), tags.get("GPS GPSLongitude")
    lat_ref, lon_ref = _str(tags, "GPS GPSLatitudeRef"), _str(tags, "GPS GPSLongitudeRef")
    if lat_tag is not None and lon_tag is not None and lat_ref and lon_ref:
        try:
            lat = dms_to_degrees(lat_tag.values, lat_ref)
            lon = dms_to_degrees(lon_tag.values, lon_ref)
            location_source = "exif_gps"
            elev = _float(tags, "GPS GPSAltitude")
            if elev is not None and _first(tags, "GPS GPSAltitudeRef") == 1:
                elev = -elev
        except (ValueError, ZeroDivisionError) as exc:
            warnings.append(f"GPS inválido no EXIF: {exc}")
            lat = lon = elev = None
    if location_source is None:
        if fallback_site is not None:
            lat, lon = fallback_site.latitude_deg, fallback_site.longitude_deg
            elev = fallback_site.elevation_m
            location_source = "fallback_site"
            warnings.append("EXIF sem GPS; usado o local configurado")
        else:
            warnings.append("Local desconhecido: SITELAT/SITELONG omitidos")

    orientation = _first(tags, "Image Orientation")

    return PhoneFrameMetadata(
        source_path=path,
        make=_str(tags, "Image Make"),
        model=_str(tags, "Image Model"),
        date_obs_utc=date_obs_utc,
        time_source=time_source,
        date_obs_uncertainty_s=uncertainty,
        exposure_s=exposure_s,
        iso=iso,
        focal_length_mm=_float(tags, "EXIF FocalLength"),
        focal_length_35mm=_float(tags, "EXIF FocalLengthIn35mmFilm"),
        orientation=int(orientation) if orientation is not None else None,
        latitude_deg=lat,
        longitude_deg=lon,
        elevation_m=elev,
        location_source=location_source,
        warnings=tuple(warnings),
    )


# ------------------------------------------------------------------------- pixels


def bayer_pattern_string(raw_pattern: npt.NDArray[Any], color_desc: bytes) -> str:
    """Build a pattern such as "RGGB" from LibRaw's 2x2 index array and color list."""
    pattern = np.asarray(raw_pattern)
    if pattern.shape != (2, 2):
        raise ValueError(f"Only 2x2 CFA patterns are supported, got {pattern.shape}")
    colors = color_desc.decode("ascii")
    return "".join(colors[int(i)] for i in pattern.flatten())


def load_pixels(path: Path) -> PixelData:
    suffix = path.suffix.lower()
    if suffix in RAW_SUFFIXES:
        import rawpy  # imported lazily: LibRaw is only needed for RAW files

        try:
            return _load_dng_libraw(path, rawpy)
        except (rawpy._rawpy.LibRawError, OSError) as exc:
            # LibRaw rejects some phone DNGs, e.g. Galaxy S24 Pro-mode files
            # (LinearRaw + lossless JPEG): "data corrupted at ...". Fall back to a plain
            # TIFF/DNG reader. The original LibRaw error is kept if that also fails.
            try:
                return _load_dng_tifffile(path)
            except Exception as fallback_exc:
                raise ValueError(
                    f"LibRaw: {exc}; leitor alternativo (tifffile): {fallback_exc}"
                ) from fallback_exc
    if suffix in JPEG_SUFFIXES:
        with Image.open(path) as img:
            rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)
        return PixelData(np.moveaxis(rgb, -1, 0).copy(), "rgb", decoder="pillow")
    raise ValueError(f"Unsupported file type: {path.suffix}")


def _load_dng_libraw(path: Path, rawpy: Any) -> PixelData:
    with rawpy.imread(str(path)) as raw:
        data = np.array(raw.raw_image_visible, dtype=np.uint16, copy=True)
        # raw_pattern is relative to the visible area's top-left pixel. Confirmed by
        # tests on synthetic DNGs (all 4 Bayer layouts, no sensor margins).
        # [A VERIFICAR com DNG real do S24, que pode ter margens/ActiveArea.]
        raw_pattern = raw.raw_pattern
        pattern = (
            bayer_pattern_string(raw_pattern, raw.color_desc) if raw_pattern is not None else None
        )
        black = tuple(float(b) for b in raw.black_level_per_channel)
        white = int(raw.white_level)
        n_colors = int(raw.num_colors)
    if data.ndim == 3:
        # LibRaw pads LinearRaw images to 4 channels; keep only the real colour planes.
        data = data[..., :n_colors]
        black = black[:n_colors]
        # Some phones write already-demosaiced "LinearRaw" DNGs (no Bayer mosaic).
        return PixelData(
            np.moveaxis(data, -1, 0).copy(), "linear_rgb", None, black, white, "libraw"
        )
    return PixelData(data, "cfa", pattern, black, white, "libraw")


_PHOTOMETRIC_CFA = 32803
_PHOTOMETRIC_LINEAR_RAW = 34892
_TAG_CFA_PATTERN = 33422
_TAG_BLACK_LEVEL = 50714
_TAG_WHITE_LEVEL = 50717
_CFA_LETTERS = {0: "R", 1: "G", 2: "B"}


def _load_dng_tifffile(path: Path) -> PixelData:
    """Read the main raw image of a DNG with tifffile (+ imagecodecs for lossless JPEG).

    Observed on the Galaxy S24 (2026-10-22): Pro-mode DNGs are LinearRaw (already
    demosaiced, 3 x 12 bit), lossless-JPEG compressed, BlackLevel 0, WhiteLevel 4095.
    Which processing Samsung applies before writing (noise reduction, lens shading…)
    is not documented. [A VERIFICAR]
    """
    import tifffile

    with tifffile.TiffFile(path) as tif:
        candidates = [tif.pages[0], *(getattr(tif.pages[0], "pages", None) or [])]
        main = None
        for page in candidates:
            subfile = page.tags.get(254)
            is_main = subfile is None or int(subfile.value) == 0
            if is_main and int(page.photometric) in (_PHOTOMETRIC_CFA, _PHOTOMETRIC_LINEAR_RAW):
                main = page
                break
        if main is None:
            raise ValueError("nenhuma imagem RAW principal (CFA ou LinearRaw) no DNG")
        data = np.asarray(main.asarray(), dtype=np.uint16)
        black_tag = main.tags.get(_TAG_BLACK_LEVEL)
        white_tag = main.tags.get(_TAG_WHITE_LEVEL)
        black = tuple(float(v) for v in np.atleast_1d(black_tag.value)) if black_tag else None
        white_values = np.atleast_1d(white_tag.value) if white_tag else None
        white = int(white_values.min()) if white_values is not None else None

        if int(main.photometric) == _PHOTOMETRIC_LINEAR_RAW:
            if data.ndim != 3:
                raise ValueError(f"LinearRaw com forma inesperada {data.shape}")
            channels = data.shape[-1]
            if black and len(black) % channels == 0:
                # BlackLevel may repeat per pixel of a repeat pattern: average per channel
                black = tuple(float(np.mean(black[c::channels])) for c in range(channels))
            return PixelData(
                np.moveaxis(data, -1, 0).copy(), "linear_rgb", None, black, white, "tifffile"
            )

        cfa_tag = main.tags.get(_TAG_CFA_PATTERN)
        pattern = (
            "".join(_CFA_LETTERS.get(int(v), "?") for v in bytes(cfa_tag.value))
            if cfa_tag
            else None
        )
        return PixelData(data, "cfa", pattern, black, white, "tifffile")


# --------------------------------------------------------------------------- FITS


def build_header(meta: PhoneFrameMetadata, pixels: PixelData) -> fits.Header:
    h = fits.Header()

    def put(key: str, value: object | None, comment: str) -> None:
        if value is not None:
            h[key] = (value, comment)

    put("IMAGETYP", "LIGHT", "Frame type")
    put("ORIGIN", "sky-monitor", "Software that wrote this file")
    put("SRCFILE", meta.source_path.name, "Original phone file")
    instrument = " ".join(p for p in (meta.make, meta.model) if p) or None
    put("INSTRUME", instrument, "Camera make and model (EXIF)")
    if meta.date_obs_utc is not None:
        put(
            "DATE-OBS",
            meta.date_obs_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
            "UTC, from EXIF DateTimeOriginal",
        )
    put("TIMESRC", meta.time_source, "exif_offset or fallback_tz")
    put("DATEUNC", meta.date_obs_uncertainty_s, "[s] DATE-OBS uncertainty")
    put("EXPTIME", meta.exposure_s, "[s] Exposure time (EXIF)")
    put("ISOSPEED", meta.iso, "ISO sensitivity (EXIF)")
    put("FOCALLEN", meta.focal_length_mm, "[mm] Focal length (EXIF)")
    put("FOCAL35", meta.focal_length_35mm, "[mm] 35mm-equivalent focal length (EXIF)")
    put("EXIFORNT", meta.orientation, "EXIF Orientation; pixels not rotated")
    put("SITELAT", meta.latitude_deg, "[deg] Latitude, north positive")
    put("SITELONG", meta.longitude_deg, "[deg] Longitude, east positive")
    put("SITEELEV", meta.elevation_m, "[m] Elevation")
    put("LOCSRC", meta.location_source, "exif_gps or fallback_site")
    put("ROWORDER", "TOP-DOWN", "Row 0 is the top of the image")
    put("PIXKIND", pixels.kind, "cfa, linear_rgb or rgb")
    put("DECODER", pixels.decoder, "Library that decoded the pixels")

    if pixels.kind == "cfa":
        put("LINEAR", True, "Pixel values are linear in flux")
        put("BAYERPAT", pixels.bayer_pattern, "CFA pattern from LibRaw")
        put("XBAYROFF", 0, "X offset of Bayer pattern")
        put("YBAYROFF", 0, "Y offset of Bayer pattern")
        put("WHITELVL", pixels.white_level, "[ADU] Saturation level")
        for i, level in enumerate(pixels.black_levels or ()):
            put(f"BLKLVL{i}", level, f"[ADU] Black level, CFA channel {i}")
    elif pixels.kind == "linear_rgb":
        put("LINEAR", True, "Linear DNG, already demosaiced")
        put("WHITELVL", pixels.white_level, "[ADU] Saturation level")
        for i, level in enumerate(pixels.black_levels or ()):
            put(f"BLKLVL{i}", level, f"[ADU] Black level, channel {i}")
    else:
        put("LINEAR", False, "JPEG: gamma-encoded, not for photometry")
        put("COLORSP", "sRGB", "Assumed JPEG color space")

    for warning in meta.warnings:
        h.add_history(_ascii(warning))
    return h


def _ascii(text: str) -> str:
    """FITS header text must be printable ASCII: strip accents (e.g. "horário" -> "horario")."""
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def convert_to_fits(
    path: Path,
    out_dir: Path,
    *,
    fallback_tz: tzinfo | None = None,
    fallback_site: Site | None = None,
    overwrite: bool = False,
) -> tuple[Path, PhoneFrameMetadata]:
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    meta = parse_metadata(
        path, read_exif(path), fallback_tz=fallback_tz, fallback_site=fallback_site
    )
    pixels = load_pixels(path)
    hdu = fits.PrimaryHDU(data=pixels.data, header=build_header(meta, pixels))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{path.stem}.fits"
    hdu.writeto(out_path, overwrite=overwrite)
    return out_path, meta


# ---------------------------------------------------------------------------- CLI


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="skymonitor-phone-ingest",
        description="Converte fotos de celular (DNG ou JPEG) em FITS para o sky-monitor.",
    )
    p.add_argument("inputs", nargs="+", type=Path, help="Arquivos ou pastas de entrada")
    p.add_argument("-o", "--out", type=Path, required=True, help="Pasta de saída")
    p.add_argument("--tz", help="Fuso de fallback, ex.: America/Sao_Paulo")
    p.add_argument("--lat", type=float, help="Latitude de fallback (graus, norte +)")
    p.add_argument("--lon", type=float, help="Longitude de fallback (graus, leste +)")
    p.add_argument("--elev", type=float, help="Altitude de fallback (m)")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument(
        "--watch",
        action="store_true",
        help="Fica observando as pastas e converte arquivos novos assim que chegam",
    )
    p.add_argument("--poll", type=float, default=10.0, help="Intervalo entre varreduras (s)")
    p.add_argument(
        "--settle",
        type=float,
        default=5.0,
        help="Só converte arquivos sem modificação há pelo menos N s (ainda copiando)",
    )
    return p


def _expand(inputs: Sequence[Path]) -> list[Path]:
    """List input files (folders are searched recursively, e.g. inbox/<date>/).
    When a folder has both X.dng and X.jpg (phones often save both),
    keep only the DNG: same stem would produce the same X.fits, and RAW is the better data.
    """
    files: list[Path] = []
    for item in inputs:
        if item.is_dir():
            candidates = sorted(
                f for f in item.rglob("*") if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES
            )
            raw_stems = {(f.parent, f.stem) for f in candidates if f.suffix.lower() in RAW_SUFFIXES}
            files.extend(
                f
                for f in candidates
                if f.suffix.lower() in RAW_SUFFIXES or (f.parent, f.stem) not in raw_stems
            )
        else:
            files.append(item)
    return files


def pending_files(
    inputs: Sequence[Path], out_dir: Path, *, now: float, settle_s: float
) -> list[Path]:
    """Files that have no FITS output yet and have not been modified for settle_s seconds."""
    ready: list[Path] = []
    for f in _expand(inputs):
        if (out_dir / f"{f.stem}.fits").exists():
            continue
        try:
            age = now - f.stat().st_mtime
        except FileNotFoundError:
            continue
        if age >= settle_s:
            ready.append(f)
    return ready


def _convert_and_report(
    paths: Sequence[Path],
    out_dir: Path,
    *,
    tz: tzinfo | None,
    site: Site | None,
    overwrite: bool,
) -> int:
    failures = 0
    for path in paths:
        if not overwrite and (out_dir / f"{path.stem}.fits").exists():
            print(f"PULADO {path.name}: FITS já existe (use --overwrite para refazer)", flush=True)
            continue
        try:
            out, meta = convert_to_fits(
                path, out_dir, fallback_tz=tz, fallback_site=site, overwrite=overwrite
            )
        except Exception as exc:
            failures += 1
            print(f"FALHA  {path}: {exc}", file=sys.stderr, flush=True)
            continue
        print(f"OK     {path.name} -> {out}", flush=True)
        for warning in meta.warnings:
            print(f"       aviso: {warning}", flush=True)
    return failures


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if (args.lat is None) != (args.lon is None):
        print("Erro: --lat e --lon devem ser informados juntos.", file=sys.stderr)
        return 2
    site = Site(args.lat, args.lon, args.elev) if args.lat is not None else None
    tz = ZoneInfo(args.tz) if args.tz else None

    if not args.watch:
        failures = _convert_and_report(
            _expand(args.inputs), args.out, tz=tz, site=site, overwrite=args.overwrite
        )
        return 1 if failures else 0

    print(f"Observando {', '.join(map(str, args.inputs))} (Ctrl+C para parar)…", flush=True)
    failed: set[Path] = set()
    try:
        while True:
            todo = [
                f
                for f in pending_files(args.inputs, args.out, now=time.time(), settle_s=args.settle)
                if f not in failed
            ]
            for f in todo:
                if _convert_and_report([f], args.out, tz=tz, site=site, overwrite=False):
                    failed.add(f)  # don't retry a broken file forever
            time.sleep(args.poll)
    except KeyboardInterrupt:
        print("Parado.", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### 7.3 Diagnóstico de DNG

`src/skymonitor/ingest/dnginfo.py`

```python
"""Inspect the internal structure of a DNG file (diagnostics).

Prints, for the main IFD and every SubIFD: image shape, data type, compression,
photometric interpretation and the DNG-specific tags that matter for decoding.
Then tries to open the file with LibRaw (rawpy) and reports the result.

Used to answer questions such as "is this a Bayer (CFA) or a LinearRaw DNG?",
"which compression does the phone use?" and "was the file copied completely?".

Tag numbers: TIFF 6.0, TIFF/EP and Adobe DNG Specification 1.7.
Compression codes: 1 none, 7 lossless JPEG, 8 Deflate, 34892 lossy JPEG,
52546 JPEG XL (added in DNG 1.7).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import tifffile

_COMPRESSION_NAMES = {
    1: "none",
    7: "lossless JPEG",
    8: "Deflate",
    34892: "lossy JPEG (DNG)",
    52546: "JPEG XL (DNG 1.7)",
}
_PHOTOMETRIC_NAMES = {2: "RGB", 6: "YCbCr", 32803: "CFA (Bayer)", 34892: "LinearRaw"}
_TAGS = {
    50706: "DNGVersion",
    50708: "UniqueCameraModel",
    271: "Make",
    272: "Model",
    254: "NewSubfileType",
    33422: "CFAPattern",
    50714: "BlackLevel",
    50717: "WhiteLevel",
    50829: "ActiveArea",
}


def _code(value: Any) -> int:
    return int(getattr(value, "value", value))


def describe_page(page: Any, label: str) -> list[str]:
    comp = _code(page.compression)
    phot = _code(page.photometric)
    lines = [
        f"{label}: shape={page.shape} dtype={page.dtype} bits={page.bitspersample} "
        f"compression={comp} ({_COMPRESSION_NAMES.get(comp, '?')}) "
        f"photometric={phot} ({_PHOTOMETRIC_NAMES.get(phot, '?')})"
    ]
    for code, name in _TAGS.items():
        tag = page.tags.get(code)
        if tag is not None:
            value = tag.value
            if isinstance(value, bytes):
                if code in (50706, 33422):  # DNGVersion, CFAPattern: byte arrays
                    value = tuple(value)
                else:
                    value = value.decode("ascii", "replace").strip("\x00")
            lines.append(f"    {name} = {value}")
    return lines


def inspect(path: Path) -> list[str]:
    lines = [f"Arquivo: {path}", f"Tamanho: {path.stat().st_size} bytes"]
    with tifffile.TiffFile(path) as tif:
        main = tif.pages[0]
        lines += describe_page(main, "IFD0")
        for i, sub in enumerate(getattr(main, "pages", None) or []):
            lines += describe_page(sub, f"SubIFD{i}")
    try:
        import rawpy

        with rawpy.imread(str(path)) as raw:
            lines.append(
                f"LibRaw: OK, raw_image_visible={raw.raw_image_visible.shape}, "
                f"pattern={None if raw.raw_pattern is None else raw.raw_pattern.tolist()}, "
                f"colors={raw.color_desc!r}"
            )
    except Exception as exc:  # report, don't crash: this is a diagnostic tool
        lines.append(f"LibRaw: FALHA ({type(exc).__name__}: {exc})")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="skymonitor-dng-info", description="Mostra a estrutura interna de arquivos DNG."
    )
    p.add_argument("files", nargs="+", type=Path)
    args = p.parse_args(argv)
    status = 0
    for f in args.files:
        try:
            print("\n".join(inspect(f)), end="\n\n")
        except Exception as exc:
            status = 1
            print(f"{f}: não foi possível ler ({type(exc).__name__}: {exc})", file=sys.stderr)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
```

### 7.4 Pré-visualização PNG

`src/skymonitor/preview.py`

```python
"""Render a FITS frame (from skymonitor-phone-ingest) as a PNG for quick visual checks.

Linear data (cfa / linear_rgb) is scaled by its saturation level (WHITELVL) and
stretched with asinh so faint detail stays visible; gamma-encoded JPEG data (rgb) is
written as is. Saturated pixels can be painted magenta to make clipping obvious.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from astropy.io import fits
from PIL import Image


def render(
    data: npt.NDArray[Any], header: Any, *, stretch: float = 10.0, mark_saturated: bool = True
) -> npt.NDArray[np.uint8]:
    kind = header.get("PIXKIND", "rgb")
    if data.ndim == 2:
        data = data[np.newaxis]
    img = np.moveaxis(np.asarray(data, dtype=float), 0, -1)  # (H, W, C)
    if kind == "rgb":
        rgb8: npt.NDArray[np.uint8] = np.clip(img, 0, 255).astype(np.uint8)
        if rgb8.shape[-1] != 3:
            rgb8 = np.repeat(rgb8, 3, axis=-1)
        return rgb8
    white = float(header.get("WHITELVL", np.nanmax(img)))
    blacks = [float(header.get(f"BLKLVL{i}", 0.0)) for i in range(img.shape[-1])]
    norm = np.clip((img - np.array(blacks)) / max(white - max(blacks), 1.0), 0, None)
    stretched = np.arcsinh(stretch * norm) / np.arcsinh(stretch)
    out: npt.NDArray[np.uint8] = (np.clip(stretched, 0, 1) * 255).astype(np.uint8)
    if out.shape[-1] == 1:
        out = np.repeat(out, 3, axis=-1)
    if mark_saturated:
        saturated = (img >= white).any(axis=-1)
        out[saturated] = (255, 0, 255)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="skymonitor-preview", description="Gera PNG de pré-visualização a partir de FITS."
    )
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("-o", "--out", type=Path, help="Pasta de saída (padrão: ao lado do FITS)")
    p.add_argument("--stretch", type=float, default=10.0, help="Intensidade do realce asinh")
    p.add_argument("--max-size", type=int, default=1600, help="Maior lado do PNG, em pixels")
    p.add_argument("--no-saturation", action="store_true", help="Não pinta saturação de magenta")
    args = p.parse_args(argv)
    for f in args.files:
        with fits.open(f) as hdul:
            rgb = render(
                hdul[0].data,
                hdul[0].header,
                stretch=args.stretch,
                mark_saturated=not args.no_saturation,
            )
            sat = float((rgb == np.array([255, 0, 255], dtype=np.uint8)).all(axis=-1).mean() * 100)
        im = Image.fromarray(rgb)
        im.thumbnail((args.max_size, args.max_size))
        out_dir = args.out or f.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{f.stem}.png"
        im.save(dest)
        print(f"OK     {f.name} -> {dest}   saturado: {sat:.1f}% dos pixels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### 7.5 Especificação original (prompt para agente)

`docs/prompt.md`, copiado na íntegra:

````markdown
# Prompt para agente: Sistema de Monitoramento do Céu (All-Sky + Telescópio Robótico)

## Papel
Você é um engenheiro de software sênior com experiência em astronomia computacional (Python, Astropy, INDI/ASCOM), sistemas embarcados (Raspberry Pi/Linux) e aplicações web. Seu trabalho é projetar e implementar um sistema de monitoramento do céu, modular e automatizado. Ele deve ser cientificamente rigoroso: nenhum dado inventado, e toda suposição deve ser marcada explicitamente.

## Contexto
- **Local:** apartamento em Santa Catarina, Brasil (Blumenau ou Itajaí, ainda a definir). Latitude aproximada de 27° S, longitude de 48–49° W, fuso America/Sao_Paulo. As coordenadas exatas devem ser um parâmetro de configuração.
- **Condições:** observação a partir de uma varanda de prédio, com céu urbano (poluição luminosa alta, Bortle estimado entre 7 e 8). Clima úmido e com nebulosidade frequente. Possível exposição à maresia.
- **Hemisfério sul:** não há Polaris. O alinhamento polar deve usar plate-solving.
- **Objetivo:** (1) monitorar o céu inteiro continuamente; (2) apontar um telescópio robótico para alvos específicos; (3) gerar dados úteis para ciência cidadã (meteoros, fotometria) e um dashboard para acompanhamento.

## Hardware alvo (parametrizável, não codificar nada fixo)
**Fase 1, all-sky:**
- Raspberry Pi 5 (ou mini-PC Linux).
- Câmera astronômica colorida com sensor sensível (ex.: família ZWO ASI224MC/ASI678MC) e lente olho-de-peixe de 180°.
- Cúpula de acrílico com aquecedor anti-orvalho.
- Opcional: sensor de temperatura/umidade (BME280) e sensor de nuvens IR (MLX90614).

**Fase 2, telescópio:**
- Telescópio inteligente (ex.: ZWO Seestar) **ou** setup modular: montagem GoTo compatível com INDI/ASCOM (ex.: Sky-Watcher HEQ5 ou ZWO AM5), tubo pequeno e câmera astronômica.
- O controle deve passar por uma camada de abstração (driver INDI, ASCOM Alpaca ou API própria do fabricante), para que o hardware possa ser trocado sem reescrever o sistema.

## Antes de codificar
1. Avalie projetos open source existentes e decida entre usar, estender ou construir do zero. Justifique a escolha.
   - **indi-allsky** para captura all-sky.
   - **seestar_alp** para controle do Seestar.
   - **KStars/Ekos** e **N.I.N.A.**
2. Verifique a documentação atual de cada API e driver. Não presuma comandos ou endpoints: confirme na fonte e cite-a.
3. Entregue um documento de arquitetura curto (diagrama de componentes + fluxo de dados) antes da implementação.

## Requisitos funcionais
### Módulo 1: Captura all-sky
- Captura automática do pôr ao nascer do sol, com crepúsculo astronômico calculado via Astropy/Skyfield.
- Exposição e ganho automáticos, com modos diferentes para dia e noite.
- Arquivos FITS com cabeçalhos completos (DATE-OBS, EXPTIME, GAIN, coordenadas, temperatura) e JPEG para visualização.
- Timelapse noturno e keogram gerados automaticamente.

### Módulo 2: Calibração e detecção
- Calibração astrométrica da imagem all-sky: modelo de projeção da lente ajustado por correspondência com estrelas de catálogo (ex.: Hipparcos/Yale BSC).
- **Detecção de meteoros** por diferença entre quadros e detecção de linhas (OpenCV). Para cada evento, registrar horário, trajetória (az/alt), duração e brilho estimado.
- **Distinção entre satélites e meteoros** cruzando as detecções com TLEs atuais (CelesTrak) via Skyfield.
- **Detecção de nuvens:** fração de céu coberto por contagem de estrelas visíveis versus esperadas e, se houver, pelo sensor IR.
- Estimativa de brilho do céu de fundo (proxy de SQM), documentando a metodologia e as limitações.
- Exportação de eventos de meteoros em formato compatível com redes de ciência cidadã (pesquisar o formato aceito pela BRAMON/UFOAnalyzer ou equivalente).

### Módulo 3: Controle do telescópio
- Agendador de observações. Antes de executar, verifica: o alvo está acima da altitude mínima configurável, no setor de céu visível da varanda (máscara de horizonte editável) e sem nuvens segundo o Módulo 2.
- Plate-solving (ASTAP ou astrometry.net local) para apontamento e alinhamento polar.
- Fotometria diferencial de estrelas variáveis e trânsitos de exoplanetas com photutils. Saída em formato compatível com a AAVSO.
- Fechamento seguro (park) em caso de chuva, umidade acima de um limite configurável ou perda de conexão.

### Módulo 4: Dados e dashboard
- Armazenamento: FITS em disco com política de retenção configurável, metadados e eventos em PostgreSQL (ou SQLite na fase inicial).
- Dashboard web responsivo (funcionar bem no celular) com:
  - imagem all-sky ao vivo;
  - mapa de nuvens;
  - lista de meteoros;
  - status do telescópio;
  - previsão do tempo (API Open-Meteo);
  - gráfico da qualidade do céu por noite.
- Alertas por Telegram ou e-mail para bólidos, céu limpo após período nublado e falhas de hardware.

## Requisitos não funcionais
- Python 3.11+, código tipado, testes com pytest e configuração em YAML.
- Funcionar **sem hardware**: usar os simuladores INDI (`indi_simulator_ccd`, `indi_simulator_telescope`) e um conjunto de imagens all-sky de teste.
- Serviços isolados (systemd ou Docker), com reinício automático e logs estruturados.
- Resiliente a quedas de energia e de internet: buffer local e sincronização posterior.
- Rigor científico:
  - registrar incertezas;
  - nunca preencher dados ausentes com valores fictícios;
  - citar a fonte de cada catálogo e algoritmo.

## Entregáveis e marcos
1. **M1:** documento de arquitetura e decisão build-vs-reuse.
2. **M2:** captura all-sky funcionando no simulador, com FITS, timelapse e keogram.
3. **M3:** calibração astrométrica, detecção de meteoros e nuvens, e cruzamento com satélites.
4. **M4:** dashboard com dados ao vivo e alertas.
5. **M5:** integração com o telescópio (simulador primeiro), agendador e fotometria.
6. **M6:** guia de instalação física para a varanda, cobrindo:
   - proteção contra umidade e maresia;
   - máscara de horizonte;
   - alinhamento polar no hemisfério sul.

Ao final de cada marco: liste o que foi feito, o que foi testado e como, as suposições pendentes e as perguntas para o usuário.
````

### 7.6 Outros arquivos (não colados aqui; estão no repositório público)
- `tests/conftest.py`, `tests/test_phone_ingest.py`, `tests/test_preview.py`: 29 testes.
- `android/…/*.kt`: app de diagnóstico (CameraReport, TestCapture com DngCreator, MainActivity, Downloads via MediaStore).
- `docs/M1-arquitetura.md`, `docs/BOM.md`, `docs/protocolo-*.md`: documentação detalhada com fontes.
- Página interativa da BOM no claude.ai (artifact privado do usuário). O conteúdo é o mesmo de `docs/BOM.md`.

---

## 8. Fontes principais usadas

- indi-allsky: https://github.com/aaronwmorris/indi-allsky (wiki: Sensors, Dew-Heater-Support, Raspberry-PI-HQ-Camera, libcamera-enablement)
- seestar_alp: https://github.com/smart-underworld/seestar_alp
- Global Meteor Network: https://globalmeteornetwork.org/wiki/
- BRAMON: artigo na Revista Brasileira de Ensino de Física, v. 47 (2025): https://www.scielo.br/j/rbef/a/y8bqvjMGccgDGhHrWG54NYS/?lang=pt
- CelesTrak GP: https://celestrak.org/NORAD/elements/
- AAVSO Extended File Format: https://aavso.org/node/76453
- N.I.N.A. (requisitos: só Windows): https://nighttime-imaging.eu/docs/master/site/requirements
- HQ Camera M12: https://www.pishop.us/product/raspberry-pi-hq-camera-m12/
- Arducam LN031: https://welectron.com/Arducam-LN031-180-Degree-Fisheye-1-23-M12-Lens-with-Lens-Adapter-for-Raspberry-Pi-High-Quality-Camera
- MLX90614 3 V: https://www.adafruit.com/products/1747
- Samsung Camera Assistant: https://r2.community.samsung.com/t5/CamCyclopedia/Camera-Assistant/ba-p/13317867
- AZ-GTi no INDI (opção de montagem futura): https://casite-460905.cloudaccess.net/telescopes/skywatcher/az-gti.html

---

## 9. Como continuar (instrução para o próximo assistente)

1. Leia este documento e, se puder, o repositório: `CLAUDE.md`, `docs/M1-arquitetura.md` e `docs/protocolo-captura-automatica-s24.md`.
2. **Primeira ação:** pedir ao Fabio a saída de `skymonitor-preview` de uma foto **bem exposta** (1/30 s) e o PNG gerado, para validar a decodificação do DNG LinearRaw do S24.
3. Depois, planejar o **M3** usando DNGs reais da câmera principal do S24 (5,4 mm, ~87° na diagonal, LinearRaw de 12 bits). Comece pela detecção de estrelas e pelo mapa de nuvens. A calibração astrométrica precisa de uma foto de **céu limpo**.
4. Siga as regras da seção 5: nada inventado, incertezas marcadas, fontes citadas, um marco por vez, testes sem hardware.
