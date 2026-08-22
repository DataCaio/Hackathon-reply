# Plano de Implementação — Hackathon Reply 2026
## Trilha C — Visão Computacional para Reciclagem

> **Objetivo do MVP:** processar os vídeos fornecidos, detectar e rastrear baterias sem dupla contagem, estimar o volume individual e acumulado por lote, reportar incerteza e demonstrar robustez entre 720p e 1080p.  
> **Diferencial de demo:** interface operacional com simulação de PLC baseada em limiares de confiança/incerteza e VLM apenas como assistente explicativo.

---

## 0. Restrições e insumos

Temos somente:

- 5 vídeos únicos em 1080p;
- os mesmos 5 vídeos perfeitamente pareados em 720p;
- tabela de dimensões de baterias `(comprimento, largura, altura)`;
- medidas físicas da bandeja/esteira;
- GPU Linux para treinamento;
- sem labels prontas;
- sem PLC real;
- sem massa individual;
- sem necessidade de classificar bateria de lítio no core do desafio.

### Consequência arquitetural

Não treinar uma rede para regressão direta de volume.

O pipeline será:

```text
vídeo
→ calibração/ROI
→ segmentação de bateria
→ tracking persistente
→ medida geométrica L×W
→ inferência no catálogo L×W×H
→ distribuição de volume
→ count gate
→ volume acumulado
→ UI
```

Princípio:

> **Segmentamos por frame, raciocinamos por track e medimos por lote.**

---

# 1. Arquitetura final

```text
                       ┌─────────────────────┐
                       │  Vídeo 720p / 1080p │
                       └──────────┬──────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │ Camera Preprocessing      │
                    │ - ROI                     │
                    │ - calibração              │
                    │ - correção perspectiva    │
                    │ - espaço canônico         │
                    └────────────┬──────────────┘
                                 │
                                 ▼
                    ┌───────────────────────────┐
                    │ Instance Segmentation     │
                    │ YOLO-Seg                  │
                    │ saída: masks + confidence │
                    └────────────┬──────────────┘
                                 │
                                 ▼
                    ┌───────────────────────────┐
                    │ Tracking                  │
                    │ ByteTrack + lógica própria│
                    │ Battery UUID persistente  │
                    └────────────┬──────────────┘
                                 │
                                 ▼
                    ┌───────────────────────────┐
                    │ Geometry                  │
                    │ mask → L̂,Ŵ em mm        │
                    │ + incerteza               │
                    └────────────┬──────────────┘
                                 │
                                 ▼
                    ┌───────────────────────────┐
                    │ Catalog Inference         │
                    │ P(SKU | L̂,Ŵ,frames)     │
                    │ E[V], CI95, confidence    │
                    └────────────┬──────────────┘
                                 │
                                 ▼
                    ┌───────────────────────────┐
                    │ Counting Engine           │
                    │ count gate                │
                    │ counted exactly once      │
                    └────────────┬──────────────┘
                                 │
                          eventos JSON
                                 │
                ┌────────────────┴─────────────────┐
                ▼                                  ▼
       ┌───────────────────┐              ┌──────────────────┐
       │ UI / Dashboard    │              │ Persistência      │
       │ PLC Simulator     │              │ SQLite / JSONL    │
       │ VLM Assistant     │              │ resultados        │
       └───────────────────┘              └──────────────────┘
```

---

# 2. Organização do time — 5 pessoas

Separar o time em **Model Core** e **Interface**, com um contrato JSON congelado cedo para permitir trabalho paralelo.

## Pessoa 1 — Detecção/Segmentação + Dataset

Responsável por:

- extrair frames;
- definir protocolo de anotação;
- criar dataset inicial;
- treinar YOLO-Seg;
- validação visual de máscaras;
- augmentations para CCTV;
- exportar modelo/inferência simples.

Entregável:

```text
input: frame
output:
[
  {
    "bbox": [...],
    "mask": ...,
    "confidence": 0.94
  }
]
```

---

## Pessoa 2 — Calibração + Geometria + Catálogo

Responsável por:

- definir ROI da esteira;
- calibrar pixels → mm;
- corrigir perspectiva quando possível;
- extrair dimensões da máscara;
- fazer matching probabilístico com a tabela;
- gerar volume esperado e intervalo de incerteza.

Entregável:

```text
input: mask + camera_config
output:
{
  "length_mm": 241.5,
  "width_mm": 174.3,
  "geometry_uncertainty_mm": 4.1,
  "catalog_candidates": [...],
  "volume_l": 7.94,
  "volume_ci95_l": [7.41, 8.05]
}
```

---

## Pessoa 3 — Tracking + Contagem + Métricas

Responsável por:

- integrar ByteTrack;
- definir Battery UUID;
- manter tracks durante oclusão;
- implementar reacquisition;
- count gate;
- evitar dupla contagem;
- métricas de volume, duplicação e consistência de resolução.

Entregável:

```text
BatteryTrack:
    uuid
    observations
    state
    position
    velocity
    volume_mean
    volume_ci95
    counted
```

---

## Pessoa 4 — Backend + Simulador de PLC

Responsável por:

- FastAPI;
- contrato entre visão e UI;
- stream de eventos;
- persistência;
- estados do PLC simulado;
- limiares configuráveis;
- endpoints de replay da demo.

Entregável:

```text
POST /events
GET  /tracks
GET  /lot
POST /plc/reset
POST /plc/continue
POST /plc/pause
GET  /health
```

---

## Pessoa 5 — Interface + VLM + Demo

Responsável por:

- dashboard Streamlit;
- vídeo anotado;
- painel do lote;
- painel por bateria;
- visualização de incerteza;
- warning / stop simulado;
- VLM como explicador;
- roteiro final da demo/pitch.

Entregável:

```text
Tela principal:
- vídeo
- contagem
- volume acumulado
- bateria atual
- confidence
- CI95
- estado do PLC simulado
- histórico de eventos
- explicação VLM
```

---

# 3. Contrato entre Model Core e Interface

Congelar este contrato nas primeiras ~45 min.

## Evento por track

```json
{
  "event": "TRACK_UPDATE",
  "timestamp_ms": 123456,
  "video_id": "video_03",
  "resolution": "720p",
  "track_id": "battery-0017",
  "state": "ACTIVE",
  "bbox": [410, 205, 502, 291],
  "mask_confidence": 0.94,
  "visibility": 0.82,
  "length_mm": 241.5,
  "width_mm": 174.3,
  "volume_l": 7.94,
  "volume_ci95_l": [7.41, 8.05],
  "volume_confidence": 0.83,
  "counted": false
}
```

## Evento de oclusão

```json
{
  "event": "TRACK_OCCLUDED",
  "track_id": "battery-0017",
  "predicted_position": [615, 320],
  "last_volume_l": 7.94,
  "volume_confidence": 0.83
}
```

## Evento de contagem

```json
{
  "event": "BATTERY_COUNTED",
  "track_id": "battery-0017",
  "volume_l": 7.94,
  "volume_ci95_l": [7.41, 8.05],
  "lot_count": 28,
  "lot_volume_l": 211.6
}
```

## Evento do PLC simulado

```json
{
  "event": "PLC_STATE",
  "state": "WARNING",
  "reason": "LOW_VOLUME_CONFIDENCE",
  "track_id": "battery-0017"
}
```

---

# 4. Dataset: qual é a unidade de dado?

Usar quatro níveis:

| Nível | Uso |
|---|---|
| **Vídeo original** | unidade de split |
| **Frame** | treinamento da segmentação |
| **Track** | inferência final de volume |
| **Lote** | métrica/resultado de negócio |

## Regra crítica

Nunca separar frames consecutivos do mesmo vídeo entre treino e teste.

Nunca colocar:

```text
video_03_1080p → train
video_03_720p  → test
```

Isso é vazamento porque os vídeos são perfeitamente pareados.

Sempre considerar:

```text
VIDEO_03 = {1080p, 720p}
```

como uma única unidade.

---

# 5. Split recomendado

Com somente 5 vídeos únicos:

## Durante desenvolvimento

```text
3 vídeos → train
1 vídeo  → validation
1 vídeo  → test
```

As duas resoluções permanecem juntas.

## Para relatório final

Se houver tempo:

```text
Leave-One-Video-Out
```

Cinco folds:

```text
Fold 1: test video 1
Fold 2: test video 2
...
Fold 5: test video 5
```

Não treinar cinco modelos completos se o tempo for insuficiente; priorizar um split limpo e uma avaliação cross-resolution convincente.

---

# 6. Criação das labels

Não existe label pronta, então produzir um **golden dataset pequeno e diverso**.

## 6.1 Frames para anotação

Não anotar centenas de frames consecutivos.

Amostrar keyframes de:

- baterias isoladas;
- baterias encostadas;
- alta densidade de objetos;
- rotações distintas;
- reflexo forte;
- papelão/lixo;
- oclusão parcial;
- oclusão forte;
- trabalhador na cena;
- bordas da esteira;
- entrada/saída;
- tamanhos distintos.

Meta inicial:

```text
~150–300 frames HR bem escolhidos
```

Se o tempo for muito curto:

```text
~80–120 frames excelentes > 500 frames redundantes
```

---

## 6.2 Label principal

Uma classe:

```text
battery
```

Annotation:

```text
instance segmentation mask
```

Não criar dezenas de classes por SKU.

---

## 6.3 Metadata útil

Quando viável:

```json
{
  "video_id": "video_02",
  "frame_id": 1450,
  "instance_id": 7,
  "track_id_gt": "gt-07",
  "occlusion": "partial"
}
```

Occlusion:

```text
none
partial
heavy
```

---

## 6.4 Transferência HR → 720p

Como os vídeos são perfeitamente pareados:

1. anotar 1080p;
2. redimensionar máscara/bbox;
3. transferir automaticamente para o frame correspondente 720p;
4. validar uma amostra.

Isso praticamente dobra o dataset supervisionado sem dobrar a anotação.

---

# 7. Fase 1 — Baseline visual

## Objetivo

Detectar/segmentar baterias suficientemente bem para alimentar geometria e tracking.

## Modelo

```text
YOLO-Seg
```

Começar com pesos pré-treinados.

## Augmentations

Usar augmentations compatíveis com CCTV:

```text
resize
downsample / upsample
JPEG compression
motion blur
Gaussian blur
noise
brightness
contrast
gamma
small perspective perturbation
```

Evitar augmentations geometricamente absurdas que prejudiquem medição.

---

# 8. Fase 2 — Generalização 720p ↔ 1080p

Este é um diferencial central.

## Baseline obrigatório

Treinar um único modelo com exemplos de ambas as resoluções.

## Representação canônica

Antes do detector:

```text
1080p ─┐
       ├→ crop ROI → resize canônico → modelo
720p  ─┘
```

A dimensão canônica deve preservar detalhes suficientes para a menor bateria.

---

## Consistency test

Para cada vídeo pareado:

```text
resultado 1080p
vs
resultado 720p
```

Medir:

```text
count_gap
volume_gap
track_match
```

### Resolution Volume Gap

\[
RVG =
\frac{
|\hat V_{1080}-\hat V_{720}|
}{
(\hat V_{1080}+\hat V_{720})/2
}
\]

Objetivo:

```text
RVG → 0
```

---

## Stretch: consistency loss

Somente se o baseline estiver funcionando.

Para pares `(HR, LR)`:

\[
L =
L_{seg,HR}
+
L_{seg,LR}
+
\lambda L_{consistency}
\]

A consistência pode ser aplicada em:

- máscara;
- embedding;
- dimensões estimadas;
- volume final.

Não colocar isso antes do MVP.

---

# 9. Fase 3 — Calibração geométrica

## Objetivo

Converter pixels em medidas físicas.

Usar as dimensões conhecidas da bandeja/esteira como referência.

Criar:

```text
configs/camera.yaml
```

Exemplo:

```yaml
camera_id: cctv_01
roi:
  x1: 50
  y1: 150
  x2: 1110
  y2: 600

count_gate:
  p1: [850, 180]
  p2: [850, 610]

physical_reference:
  width_mm: 1500

canonical:
  width_px: 1200
```

## Implementação

Testar duas abordagens:

### A. Homografia simples

Boa para MVP.

```text
plano da esteira → plano canônico
```

### B. Correção por perspectiva/local

Stretch se a altura das baterias causar erro relevante.

Não bloquear o hackathon tentando reconstrução 3D perfeita.

---

# 10. Fase 4 — Medida geométrica

Por instância:

```text
mask
→ contour
→ minAreaRect
→ rotated rectangle
→ dimensão em pixels
→ conversão para mm
```

Sempre tratar orientação:

```text
(L, W)
(W, L)
```

como equivalentes no matching.

## Quality score da medida

Atribuir qualidade por frame:

```text
q_t =
mask_confidence
× visibility
× contour_quality
× geometry_stability
```

Frames ruins devem contribuir menos para a inferência do track.

---

# 11. Fase 5 — Matching probabilístico com catálogo

Não escolher simplesmente o SKU mais próximo por distância euclidiana e encerrar.

Para cada observação:

\[
y_t = [\hat L_t,\hat W_t]
\]

Para candidato `s` do catálogo:

\[
p(y_t|s)
\propto
\exp
\left(
-\frac12
(y_t-d_s)^T\Sigma_t^{-1}(y_t-d_s)
\right)
\]

Acumular evidência por track:

\[
\log P(s|y_{1:T})
=
\log P(s)
+
\sum_t q_t \log P(y_t|s)
\]

Saída:

```text
top candidates
probabilidade
volume de cada candidato
```

---

# 12. Volume e incerteza

Para cada candidato:

\[
V_s = L_sW_sH_s
\]

Converter:

```text
mm³ → litros
1 L = 1,000,000 mm³
```

Volume esperado:

\[
E[V] = \sum_s P(s)V_s
\]

Variância:

\[
Var(V)=\sum_sP(s)(V_s-E[V])^2
\]

Retornar:

```text
volume_mean
volume_p05
volume_p95
confidence
```

Exemplo:

```text
Battery #17

Volume:
7.94 L

95% interval:
7.41–8.05 L

Confidence:
83%
```

---

# 13. Fase 6 — Tracking e oclusão

## Baseline

```text
ByteTrack
```

A identidade operacional deve ser um UUID persistente independente do ID interno do tracker.

```text
tracker_id → Battery UUID
```

## Estados

```text
DETECTED
TRACKING
OCCLUDED
REACQUIRED
COUNTED
LOST
```

---

## Oclusão por papelão/lixo

Regra:

```text
não detectado ≠ objeto desapareceu
```

Quando um track some:

1. manter track por `N` frames;
2. prever posição usando movimento;
3. manter volume/posterior anterior;
4. procurar reacquisition próximo à posição esperada;
5. comparar dimensão;
6. opcionalmente comparar aparência.

Score de reassociação:

\[
Score =
w_m Motion +
w_s Size +
w_a Appearance
\]

No MVP:

```text
motion + size
```

já pode bastar.

---

# 14. Fase 7 — Count Gate

Não contar no nascimento do track.

Definir uma linha virtual:

```text
fluxo →

DETECÇÃO      ANÁLISE                   GATE
─────────────────────────────────────────│────
                                         │
```

Evento:

```python
if crossed_gate(track) and not track.counted:
    track.counted = True
    lot.count += 1
    lot.volume += track.volume_mean
```

Uma bateria pode sumir/reaparecer depois.

O evento de contagem não se repete.

---

# 15. Métricas

Como o desafio é volume, a headline deve ser volume — não F1/F3.

## 15.1 Relative Volume Error

\[
RVE =
\frac{|\hat V-V|}{V}
\]

Por bateria e por lote.

---

## 15.2 Duplicate Rate

\[
DuplicateRate =
\frac{\text{objetos contados >1 vez}}
{\text{objetos físicos}}
\]

Meta:

```text
0%
```

ou o mais próximo possível.

---

## 15.3 Count Error

\[
CountError =
\frac{|\hat N-N|}{N}
\]

---

## 15.4 Resolution Volume Gap

\[
RVG =
\frac{
|\hat V_{1080}-\hat V_{720}|
}{
(\hat V_{1080}+\hat V_{720})/2
}
\]

Essa é uma métrica-chave para o argumento de custo.

---

## 15.5 Uncertainty Calibration

Se houver golden set suficiente:

Verificar quantas vezes o volume real está dentro do CI95.

Ideal:

```text
~95%
```

Com dataset minúsculo, reportar apenas como evidência exploratória.

---

# 16. Golden set manual

Como não existe ground truth de volume fornecido, criar uma pequena referência manual.

## Meta

Selecionar:

```text
20–50 tracks
```

em situações variadas.

Para cada track, registrar quando possível:

```text
categoria/SKU provável
L/W/H da tabela
volume verdadeiro da tabela
frames em que aparece
oclusões
```

Se a identidade exata não puder ser confirmada visualmente:

```text
não inventar label
```

Marcar:

```text
ambiguous
valid_candidates: [...]
```

Usar esses casos para avaliação de incerteza, não como ground truth absoluto.

---

# 17. PLC Simulator — diferencial de interface

O PLC é **simulado** e explicitamente apresentado assim.

Não dizer que existe integração real.

## Estados

```text
RUNNING
WARNING
PAUSED
```

## Dois limiares

Usar confiança da estimativa de volume:

```text
confidence >= T_warning
    → RUNNING

T_stop <= confidence < T_warning
    → WARNING

confidence < T_stop
    → PAUSED (simulado)
```

Exemplo inicial:

```text
T_warning = 0.70
T_stop    = 0.45
```

Ajustar na demo.

### Alternativa melhor

Usar largura do intervalo relativo:

\[
RelativeUncertainty =
\frac{V_{p95}-V_{p05}}{E[V]}
\]

Então:

```text
< 10%     → RUNNING
10–25%    → WARNING
> 25%     → PAUSED
```

Isso é mais interpretável que confiar só em um confidence score arbitrário.

---

# 18. UI da demo

```text
┌─────────────────────────────────────────────────────────────┐
│ ESTEIRA 01                      PLC SIMULADO: ● RUNNING      │
├───────────────────────────────────┬─────────────────────────┤
│                                   │ LOTE ATUAL              │
│         VÍDEO ANOTADO             │                         │
│                                   │ Peças: 37               │
│   mask + ID + confidence          │ Volume: 291.4 L         │
│                                   │ CI95: 285–299 L         │
│                                   │ Duplicações: 0          │
├───────────────────────────────────┼─────────────────────────┤
│ BATTERY #0017                     │ GENERALIZAÇÃO           │
│                                   │                         │
│ Volume: 7.94 L                    │ 1080p: 291.4 L          │
│ CI95: 7.41–8.05 L                 │ 720p:  289.9 L          │
│ Confidence: 83%                   │ Gap:    0.51%            │
│ State: TRACKING                   │                         │
├───────────────────────────────────┴─────────────────────────┤
│ VLM: "A bateria #17 foi reassociada após oclusão..."       │
│                                                             │
│             [PAUSAR] [CONTINUAR] [RESET LOTE]              │
└─────────────────────────────────────────────────────────────┘
```

---

# 19. VLM Assistant

O VLM não participa do cálculo.

Recebe somente dados estruturados:

```json
{
  "track_id": "battery-0017",
  "state": "REACQUIRED",
  "frames_seen": 53,
  "occluded_frames": 11,
  "volume_l": 7.94,
  "volume_ci95_l": [7.41, 8.05],
  "confidence": 0.83,
  "counted": true
}
```

Uso:

- explicar incerteza;
- explicar oclusão/reacquisition;
- explicar por que o PLC simulado entrou em warning;
- resumir lote;
- responder perguntas do operador.

Não usar VLM para:

- segmentação;
- tracking;
- volume;
- decisão do count gate.

---

# 20. Estrutura do repositório

```text
project/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── configs/
│   ├── camera.yaml
│   ├── thresholds.yaml
│   └── model.yaml
├── data/
│   ├── raw/
│   ├── frames/
│   ├── annotations/
│   └── catalog/
├── models/
│   └── weights/
├── src/
│   ├── vision/
│   │   ├── detector.py
│   │   ├── tracker.py
│   │   └── reid.py
│   ├── geometry/
│   │   ├── calibration.py
│   │   └── measurement.py
│   ├── catalog/
│   │   ├── matcher.py
│   │   └── uncertainty.py
│   ├── counting/
│   │   └── gate.py
│   ├── metrics/
│   │   ├── volume.py
│   │   ├── tracking.py
│   │   └── resolution.py
│   ├── api/
│   │   └── main.py
│   └── ui/
│       └── app.py
├── scripts/
│   ├── extract_frames.py
│   ├── train.py
│   ├── evaluate.py
│   ├── run_video.py
│   └── compare_resolutions.py
└── tests/
```

---

# 21. Ordem de implementação

## P0 — Obrigatório para existir demo

- [ ] extrair frames
- [ ] criar annotations mínimas
- [ ] YOLO-Seg baseline
- [ ] inferência em vídeo
- [ ] tracking
- [ ] calibração
- [ ] L/W em mm
- [ ] catálogo → volume
- [ ] count gate
- [ ] volume acumulado
- [ ] JSON de eventos
- [ ] dashboard básico
- [ ] replay estável da demo

## P1 — Diferencial de qualidade

- [ ] incerteza de volume
- [ ] estados de oclusão
- [ ] reacquisition
- [ ] comparação 720p vs 1080p
- [ ] painel de métricas
- [ ] PLC simulado com thresholds

## P2 — Só se tudo acima funcionar

- [ ] consistency loss HR/LR
- [ ] ReID visual
- [ ] VLM
- [ ] ONNX/TensorRT
- [ ] refinamento geométrico avançado

---

# 22. Cronograma para o dia do hackathon

Considerando aproximadamente:

```text
09:30–13:00 desenvolvimento
14:00–17:30 desenvolvimento
17:30 pitch
```

## 09:30–10:15 — Freeze de arquitetura

Todos:

- confirmar direção do fluxo da esteira;
- abrir todos os vídeos;
- verificar sincronização 720p↔1080p;
- congelar JSON de integração;
- escolher count gate;
- criar repositório/branches.

### Marco 10:15

Interface já consegue rodar com **dados mockados**.

Modelos trabalham independentemente.

---

## 10:15–11:30 — Primeiro pipeline

P1:
- frames + annotations;
- primeiro YOLO-Seg.

P2:
- ROI/calibração;
- parsing da tabela.

P3:
- tracking baseline;
- count gate.

P4:
- FastAPI;
- mock event stream;
- PLC simulator.

P5:
- dashboard sobre dados falsos;
- layout final.

### Marco 11:30

```text
vídeo → alguma detecção
mock → UI funcionando
```

---

## 11:30–13:00 — MVP E2E

Integrar:

```text
detector → tracker → geometry → volume
```

P4 adapta contrato se necessário.

P5 conecta UI ao backend.

### Marco antes do almoço

Obrigatório ter:

```text
1 vídeo
→ roda inteiro
→ conta
→ mostra algum volume
```

Mesmo imperfeito.

Se isso não existir às 13:00:

```text
cancelar stretch goals
```

---

## 14:00–15:00 — Robustez

Foco:

- oclusão;
- dupla contagem;
- calibração;
- matching catálogo;
- incerteza.

Rodar em pelo menos 2 vídeos.

---

## 15:00–16:00 — 720p vs 1080p

Rodar o mesmo pipeline nos pares.

Gerar tabela:

```text
Vídeo | Count HR | Count LR | Volume HR | Volume LR | Gap
```

Essa tabela entra direto no pitch.

---

## 16:00–16:40 — Interface diferencial

Adicionar:

- uncertainty;
- warning;
- pause simulado;
- histórico;
- comparação de resolução;
- VLM apenas se seguro.

---

## 16:40 — CODE FREEZE DA DEMO

Depois disso:

```text
não trocar modelo
não refatorar arquitetura
não adicionar dependência grande
```

Criar um caminho de replay conhecido.

---

## 16:40–17:15 — Pitch e backup

Preparar:

- vídeo de backup;
- screenshots;
- tabela de métricas;
- arquitetura;
- 1 exemplo de oclusão;
- 1 exemplo HR vs 720p.

---

## 17:15–17:30 — Ensaio

Rodar exatamente o fluxo que será apresentado.

---

# 23. Critério de abandono de feature

Uma feature deve ser cortada se:

1. não melhora o cálculo de volume;
2. não melhora tracking;
3. não melhora demonstração de robustez;
4. não pode ser explicada em <20 s no pitch;
5. ameaça a estabilidade da demo.

Primeiros candidatos a corte:

```text
PINN
FFT
autoencoder
3D reconstruction completa
ReID complexo
VLM sofisticado
TensorRT
```

---

# 24. Demo final sugerida

## Cena 1 — problema

Mostrar 3–5 s do vídeo cru.

Mensagem:

> "Temos apenas CCTV, catálogo de dimensões e geometria da esteira."

---

## Cena 2 — visão

Rodar vídeo:

```text
masks
IDs persistentes
volume individual
```

---

## Cena 3 — oclusão

Escolher trecho com papelão/lixo.

Mostrar:

```text
TRACKING
→ OCCLUDED
→ REACQUIRED
```

E destacar:

```text
counted exactly once
```

---

## Cena 4 — incerteza

Mostrar uma bateria com candidatos ambíguos:

```text
Volume: 7.94 L
CI95: 7.41–8.05 L
```

A UI explica a incerteza.

---

## Cena 5 — PLC simulado

Forçar/usar um caso com alta incerteza:

```text
RUNNING
→ WARNING
→ PAUSED
```

Mensagem explícita:

> "PLC simulation — integração com hardware está fora do escopo."

---

## Cena 6 — custo/generalização

Mostrar lado a lado:

```text
1080p vs 720p
```

Exemplo:

```text
1080p volume: X
720p volume:  Y
gap: Z%
```

Mensagem:

> "A mesma solução mantém desempenho semelhante em 720p, reduzindo o requisito de câmera e infraestrutura."

---

# 25. Definition of Done

A solução está pronta quando:

- [ ] processa pelo menos um vídeo completo;
- [ ] detecta baterias;
- [ ] cria IDs persistentes;
- [ ] recupera pelo menos alguns casos de oclusão;
- [ ] não adiciona volume duas vezes para o mesmo UUID;
- [ ] estima volume via tabela;
- [ ] fornece intervalo de incerteza;
- [ ] acumula volume do lote;
- [ ] roda em 720p e 1080p;
- [ ] calcula Resolution Volume Gap;
- [ ] envia eventos reais para a interface;
- [ ] interface mostra PLC claramente como simulado;
- [ ] demo possui replay conhecido;
- [ ] existe vídeo de backup da demo.

---

# 26. Mensagem técnica do projeto

> **A rede encontra a bateria; a geometria mede; o catálogo restringe; o tempo reduz a incerteza; o tracking garante contagem única; e os vídeos pareados provam robustez à resolução.**

Essa deve ser a linha arquitetural defendida no pitch.
