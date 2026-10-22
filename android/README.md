# App Android de diagnóstico de câmeras

App pequeno (Kotlin, API Camera2, **sem root**) que responde a uma pergunta antes de investirmos num app de captura completo:

> **O que o Galaxy S24 libera para apps de terceiros?** RAW, exposição longa, ISO, ultra-wide?

A própria câmera da Samsung pode ter recursos que apps de terceiros não recebem. Este app mede isso no aparelho real.

## O que ele faz

1. **Relatório:** lista todas as câmeras (inclusive as físicas dentro da câmera lógica) com:
   - suporte a RAW e controle manual do sensor;
   - faixa de exposição e de ISO;
   - distâncias focais e FOV aproximado;
   - tamanho do sensor, padrão Bayer, níveis de preto/branco e calibração da lente.

   O JSON completo é salvo em `Download/SkyMonitor/` e pode ser compartilhado pelo botão **Compartilhar**.
2. **Captura de teste:** faz **uma** exposição RAW manual (foco no infinito, AE/AF desligados, redução de ruído desligada quando possível) e salva um **DNG** em `Download/SkyMonitor/`. Depois compara:
   - a exposição e o ISO **pedidos** com os **informados** pela câmera;
   - a duração real medida no relógio.

   Isso mostra se o limite anunciado é respeitado de fato.

## Instalar no S24

O APK é compilado automaticamente pelo GitHub Actions a cada mudança em `android/`.

1. No celular, abra o GitHub (app ou site, logado) → repositório **sky-monitor** → **Releases** → **android-diag-latest** → baixe `skymonitor-diag.apk`.
2. Abra o arquivo. O Android pede para permitir a instalação de "fontes desconhecidas" para o navegador ou o app de arquivos. Permita só para essa instalação.
3. Abra **Sky Monitor Diag** e conceda a permissão de câmera.

Root e modo desenvolvedor não são necessários. O APK é assinado com uma chave de debug fixa (`app/debug.keystore`, credenciais públicas padrão), então versões novas instalam por cima da anterior.

## Usar

1. O relatório é gerado ao abrir. Toque em **Compartilhar** e envie o JSON (por exemplo, para o chat do Claude).
2. Para a captura de teste, coloque o celular no tripé apontado para o céu (ou tampe a lente, para um dark). Escolha a câmera, a exposição e o ISO, e toque em **Capturar DNG de teste**.
3. Converta o DNG no notebook:
   ```bash
   skymonitor-phone-ingest ~/Downloads/SkyMonitor -o out/diag --tz America/Sao_Paulo
   ```
   O DNG do app não tem GPS. Use `--lat/--lon` se quiser coordenadas no FITS.

## Limitações conhecidas

- A captura de teste só funciona em câmeras que podem ser abertas diretamente. Uma câmera física que só existe dentro da câmera lógica (como a ultra-wide em alguns aparelhos) aparece no relatório, mas fica fora da captura nesta versão.
- O FOV é uma aproximação retilínea. Lentes ultra-wide têm distorção, e o valor real vem da calibração no `calib`.

## Compilar localmente (opcional)

Requer JDK 17 e Android SDK (ou Android Studio):

```bash
cd android
./gradlew assembleDebug
# APK em app/build/outputs/apk/debug/app-debug.apk
```

Referência da API: https://developer.android.com/reference/android/hardware/camera2/package-summary

## Resultados

### Galaxy S24 (SM-S921B), Android 16 — 2026-10-22

Relatório gerado pelo app no aparelho do usuário:

| Câmera | Lado | Focal | FOV diag. (aprox.) | RAW | Manual | Exposição máx. | ISO | Abre direto |
|---|---|---|---|---|---|---|---|---|
| 0 | traseira (principal) | 5,40 mm | 87° | sim | sim | **0,10 s** | 25–3200 | sim |
| 2 | traseira (ultra-wide) | 2,20 mm | 116° | sim | sim | **0,10 s** | 48–3200 | sim |
| 5 | traseira (física, em 0) | 5,40 mm | 87° | sim | sim | 0,10 s | 25–3200 | não |
| 6 | traseira (tele, física, em 0) | 7,00 mm | 36° | sim | sim | 0,10 s | 25–3200 | não |
| 1, 3 | frontais | 3,30 mm | 81° / 71° | sim | sim | 0,10 s | 25–3200 | sim |

**Conclusão:** apps de terceiros recebem RAW, controle manual e acesso direto à ultra-wide, mas a **exposição máxima anunciada é 0,1 s** em todas as câmeras. O app de câmera da Samsung (modo Pro) chega a 30 s, então os recursos de exposição longa ficam reservados ao app do fabricante.

**Consequência:** um app de captura próprio no S24 só funcionaria empilhando muitos quadros de 0,1 s. Com isso o ruído de leitura se acumula a cada quadro, e o resultado fica muito pior que uma exposição única de 10–30 s. **[A VERIFICAR]** com uma captura de teste noturna (0,1 s, ISO 3200) quantas estrelas aparecem de fato.
