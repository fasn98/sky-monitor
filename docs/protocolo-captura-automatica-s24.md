# Captura automática com o Galaxy S24 (sem root)

**Por que existe:** apps de terceiros no S24 ficam limitados a 0,1 s de exposição (ver [`android/README.md`](../android/README.md#resultados)). O **app de câmera da Samsung** chega a 30 s no modo Pro. Este protocolo usa o app da Samsung para capturar e automatiza o disparo por fora. As fotos vão para o notebook, onde o sky-monitor converte e processa.

```
S24 (câmera Samsung, modo Pro, RAW)
   │  disparo automático: Camera Assistant (até 7 fotos) ou auto clicker (a noite toda)
   ▼
DCIM/Camera/*.dng
   │  cabo USB ou sincronização (Syncthing)
   ▼
Notebook: skymonitor-phone-ingest --watch  →  FITS  →  (M3: nuvens, rastros, calibração)
```

Configuração geral da câmera: [`protocolo-captura-celular.md`](protocolo-captura-celular.md). Este documento cobre só o que muda para captura automática.

---

## 1. Antes de escurecer: posição

1. **Janela aberta.** Nunca fotografe através do vidro, que gera reflexos e reduz o contraste.
2. Aponte o mais alto possível no céu (de preferência o zênite) e deixe o celular **fixo**: tripé, suporte de celular ou apoio firme. Não toque mais nele durante a sessão.
3. **Registre a direção:** com uma bússola no celular ou o Google Maps, anote para que ponto cardeal o topo da imagem aponta e qual a inclinação aproximada.
4. **Tire uma foto de dia na mesma posição.** Ela mostra prédios, árvores e antenas que bloqueiam o céu, e vira a máscara de horizonte do sistema.

**São Paulo, 22/10/2026** (calculado com Astropy para -23,55°, -46,63°):

| Evento | Hora local |
|---|---|
| Pôr do sol | 18:15 |
| Fim do crepúsculo civil | 18:38 |
| Fim do crepúsculo náutico | 19:06 |
| Fim do crepúsculo astronômico (céu totalmente escuro) | 19:34 |

## 2. Celular

- **Carregador ligado** a sessão inteira.
- **Economia de energia desligada** e **otimização de bateria desativada** para o app de clique automático. Caso contrário, o Android pode encerrar o app no meio da noite.
- **Brilho da tela no mínimo.** Reduz o aquecimento e a luz que chega na janela.
- **Câmera:** modo Pro, **ultra-wide (0,6×)**, RAW ativado, foco manual no infinito, balanço de branco fixo (ex.: 4000 K).
- **Exposição:** comece com **ISO 800 e 10 s**. No céu de São Paulo, 30 s pode estourar o fundo. Veja um frame e ajuste.
- **Tags de local ativadas**, para gravar o GPS nas fotos.

## 3. Disparo automático

### Opção A: Camera Assistant (sequências curtas)
App oficial da Samsung, instalado pela Galaxy Store.
- **Timer com várias fotos:** até **7 fotos**, com intervalo de 1–3 s. Funciona no modo Pro.
- **Tempo para fechar a câmera:** coloque **10 min**, o máximo.
- Uso: ative o timer de 3 s no app da câmera e toque no obturador uma vez para tirar 7 fotos seguidas.

### Opção B: app de clique automático (a noite toda)
Apps como MacroDroid ou "auto clicker" usam o **serviço de acessibilidade** do Android e não precisam de root.
1. Crie **um ponto de toque sobre o botão do obturador** do modo Pro.
2. **Intervalo = exposição + 10 s**, no mínimo. Com exposição de 10 s, use 20–60 s.
3. **Repetição infinita.**
4. **Teste de dia primeiro:** exposição de 1/100 s e intervalo de 5 s por 1 minuto. Confira na Galeria se saíram cerca de 12 fotos, cada uma com o DNG.

> A automação depende da posição do botão na tela. Se o app de câmera for atualizado, refaça o ponto de toque.

## 4. Espaço de armazenamento

Um DNG da ultra-wide (12 MP, 16 bits por pixel) ocupa cerca de 24 MB, mais o JPEG.

| Intervalo | Fotos em 8 h | Espaço aproximado |
|---|---|---|
| 20 s | 1440 | ~35 GB |
| 60 s | 480 | ~12 GB |
| 120 s | 240 | ~6 GB |

Confira o espaço livre antes. **Para hoje, sugiro 60 s.**

## 5. Notebook

### Levar as fotos
- **Cabo USB:** conecte, escolha "Transferir arquivos" e copie `DCIM/Camera/*.dng` para `~/skymonitor/inbox/<data>/`.
- **Sincronização automática (opcional):** Syncthing no Ubuntu e um app compatível no Android, sincronizando `DCIM/Camera` com `~/skymonitor/inbox`. O app oficial do Syncthing para Android foi descontinuado. Use uma alternativa mantida, como o fork da comunidade.

### Converter (e observar novas fotos)
```bash
cd sky-monitor && source .venv/bin/activate
skymonitor-phone-ingest ~/skymonitor/inbox -o ~/skymonitor/fits \
  --watch --tz America/Sao_Paulo
```
- `--watch` fica observando a pasta e converte cada foto nova depois que ela termina de copiar (`--settle`, padrão 5 s).
- Quando houver X.dng e X.jpg com o mesmo nome, só o **DNG** é convertido.
- Se a foto não tiver GPS: `--lat -23.55 --lon -46.63`.

### Conferir se a foto saiu certa
Depois de converter, o `fitsheader` mostra qual câmera e quais ajustes foram usados (focais do relatório do app de diagnóstico):

| Campo | Esperado | Se vier diferente |
|---|---|---|
| `FOCALLEN` | **2.2** (ultra-wide traseira) | 5.4 = câmera principal · **3.3 = câmera frontal (selfie)** |
| `PIXKIND` | `cfa` ou `linear_rgb` (DNG) | `rgb` = só JPEG: RAW desligado ou fora do modo Pro |
| `EXPTIME` / `ISOSPEED` | os valores fixados no Pro (ex.: 10 s / 800) | frações de segundo e ISO alto = modo automático |

Primeiro teste real (2026-10-22, 21:22): `FOCALLEN=3.3`, `EXPTIME≈1/17 s`, `ISOSPEED=2500`, `PIXKIND=rgb`. Ou seja: câmera frontal no modo automático. Hora (com fuso) e GPS chegaram corretos.

> Para apontar a câmera **traseira** para o céu, a tela fica virada para baixo e você não a vê. Ajuste tudo antes, vire o celular e dispare com o timer (Camera Assistant) ou com um controle remoto Bluetooth/Galaxy Watch.

## 6. Registro da sessão

Crie um `notas.txt` na pasta da sessão com:
- data, local e andar;
- direção e inclinação do celular;
- ISO, exposição e intervalo usados;
- condição do céu: **nublado também serve**, porque são dados reais para o módulo de nuvens;
- horários de início e fim e qualquer imprevisto.

## 7. Limitações

- A ultra-wide cobre cerca de 120°, não o céu inteiro.
- O celular aquece com o uso contínuo, o que aumenta o ruído ao longo da noite. Tire **darks** no fim (lente tampada, mesmas configurações).
- Não há proteção contra orvalho nem chuva: deixe em local coberto.
- **[A VERIFICAR com o primeiro DNG real]:** se o DNG do modo Pro sai como mosaico Bayer ou como DNG linear já processado. O conversor aceita os dois e registra qual é em `PIXKIND` no FITS.
