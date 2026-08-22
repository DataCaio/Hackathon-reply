# Plano de implementação do Backend/Model Core — 3 agentes em menos de 5 horas

Baseado em `IMPLEMENTACAO_HACKATHON_VISAO.md` e ajustado ao estado atual do repositório e ao limite operacional do hackathon.

## 1. Resultado esperado

Ao final da janela, uma única branch de integração deve processar pelo menos um par de vídeos 1080p/720p e produzir:

```text
vídeo
→ segmentação/detecção de baterias
→ tracking com UUID persistente
→ medida L/W em milímetros
→ matching probabilístico com o catálogo
→ volume esperado + intervalo de incerteza
→ count gate idempotente
→ volume acumulado do lote
→ eventos JSONL consumíveis pela interface/PLC
→ resumo de métricas 1080p × 720p
```

O backend deste plano termina na emissão dos eventos. FastAPI, interface, VLM e lógica do PLC estão fora do escopo porque já estão sendo implementados por outra frente.

Princípio técnico que não deve mudar durante o hackathon:

> Segmentar por frame, inferir por track e medir por lote.

## 2. Estado real dos insumos

O repositório ainda não contém implementação do Model Core. `back/back` e `front/front` estão vazios. Os insumos disponíveis são:

- 5 vídeos 1080p e os mesmos 5 vídeos em 720p;
- aproximadamente 4,1 GB de vídeo;
- 44.788 frames por resolução e aproximadamente 24,9 minutos por resolução;
- pares perfeitamente alinhados por `frame_id`, duração e taxa de quadros;
- catálogo `data/datal.csv` com 95 linhas, 67 trincas `(L,W,H)` únicas e 11 categorias;
- uma linha de altura com decimal pt-BR (`"95,50"`), que exige parsing explícito;
- acesso à instância AWS por `AWS.sh` e chave local ignorada pelo Git.

Nomes que precisam constar em um manifesto, sem serem montados por convenção:

```text
Video_01.mp4       ↔ Video_01_720p.mp4
Video_02.mp4       ↔ Video_02_720p.mp4
Video_03.mp4       ↔ Video_03_720p.mp4
Video_04.mp4       ↔ Video_04_720P.mp4
Video_05.mp4       ↔ Video_05_720P.mp4
```

Os arquivos 04 e 05 usam `P` maiúsculo em `720P`.

### Dependência crítica no minuto zero

O repositório não contém a largura física da esteira/bandeja nem os quatro pontos físicos usados pela homografia. O time precisa obter e registrar esses valores até T+20 min.

Não inventar escala. Se não houver referência física confiável, o pipeline pode ser demonstrado em pixels e com baixa confiança, mas não deve apresentar volume absoluto como medida validada. O fallback aceitável é uma escala local obtida de uma referência física conhecida e marcada no relatório como calibração simplificada.

## 3. Decisões congeladas antes de dividir o trabalho

Estas decisões devem ser fechadas até T+20 min e não podem ser alteradas unilateralmente depois:

1. Uma classe de visão: `battery`.
2. Um único modelo treinado com exemplos 1080p e 720p.
3. Split por vídeo, mantendo cada par de resoluções na mesma partição:
   - vídeos 01, 02 e 03: treino;
   - vídeo 04: validação;
   - vídeo 05: teste.
4. Toda `bbox` e todo polígono de máscara nos contratos internos usam coordenadas do frame original.
5. `bbox` usa `xyxy = [x_min, y_min, x_max, y_max]` em pixels.
6. ROI, gate e direção do fluxo ficam normalizados em `[0,1]` no arquivo de câmera, para funcionarem nas duas resoluções.
7. Unidades físicas: milímetros para dimensão e litros para volume.
8. `frame_id` começa em zero; `timestamp_ms` vem do vídeo e deve ser monotônico.
9. O ID interno do tracker nunca é exposto. A API externa usa um UUID operacional `battery-xxxx`.
10. A ausência temporária de detecção gera `OCCLUDED`, não uma nova bateria.
11. A bateria só é contada ao cruzar o gate no sentido correto.
12. O volume lançado no lote é congelado no evento `BATTERY_COUNTED`; atualizações posteriores do posterior não alteram retroativamente o lote no MVP.
13. Campos ainda indisponíveis em `TRACK_UPDATE` são `null`, nunca zero. Essa regra deve ser comunicada à equipe de interface no freeze do contrato.
14. Vídeos, frames, pesos, `runs/`, caches e a chave `.pem` não entram no Git.

## 4. Organização do trabalho independente

| Agente | Missão | Recurso principal | Não deve editar |
|---|---|---|---|
| A — Visão | dados, labels, detector e inferência cacheada | GPU durante treino | geometria, tracking, pipeline, contratos |
| B — Medida | calibração, geometria, catálogo e incerteza | CPU | detector, tracker, pipeline, contratos |
| C — Fluxo | tracking, oclusão, gate, eventos, métricas e orquestração | CPU; GPU apenas no smoke integrado | detector e módulos matemáticos de B |

O Agente C é o responsável pela branch de integração, mas também desenvolve sua feature em branch própria. Alterações cruzadas devem ser solicitadas ao dono do arquivo ou entregues em commit isolado; nenhum agente deve “corrigir rapidamente” o módulo do outro.

## 5. Estrutura mínima do repositório

O commit-base de T+20 deve criar somente o esqueleto, contratos, fixtures e configuração de testes:

```text
configs/
├── camera.yaml                 # dono: B
├── dataset.yaml                # dono: A
├── model.yaml                  # dono: A
├── thresholds.yaml             # dono: C
└── videos.yaml                 # congelado no commit-base
data/
└── catalog/
    └── catalog_normalized.csv  # dono: B; pequeno e versionável
models/
└── weights/                    # ignorado; artefato externo
src/
├── contracts/
│   ├── domain.py               # congelado; dono: C
│   └── events.py               # congelado; dono: C
├── vision/
│   ├── detector.py             # dono: A
│   └── tracker.py              # dono: C
├── geometry/
│   ├── calibration.py          # dono: B
│   └── measurement.py          # dono: B
├── catalog/
│   ├── loader.py               # dono: B
│   ├── matcher.py              # dono: B
│   └── uncertainty.py          # dono: B
├── counting/
│   └── gate.py                 # dono: C
├── metrics/
│   ├── volume.py               # dono: C
│   ├── tracking.py             # dono: C
│   └── resolution.py           # dono: C
└── pipeline.py                 # dono: C
scripts/
├── extract_frames.py           # dono: A
├── train.py                    # dono: A
├── infer_detector.py           # dono: A
├── smoke_geometry.py           # dono: B
├── replay_detections.py        # dono: C
├── run_video.py                # dono: C
├── validate_events.py          # dono: C
└── compare_resolutions.py      # dono: C
tests/
├── fixtures/                   # congelado no commit-base
├── vision/                     # dono: A
├── geometry/                   # dono: B
├── catalog/                    # dono: B
├── tracking/                   # dono: C
├── counting/                   # dono: C
└── integration/                # dono: C
```

Somente o Agente C altera arquivos comuns como `requirements.txt`/`pyproject.toml`, `.gitignore`, contratos e fixture canônica. A e B informam dependências necessárias, mas não editam esses arquivos em paralelo.

## 6. Contratos internos

O objetivo dos contratos é impedir que objetos do Ultralytics, ByteTrack ou OpenCV vazem entre módulos.

### 6.1 Metadados do frame

```python
FrameMeta(
    video_id: str,
    resolution: Literal["720p", "1080p"],
    frame_id: int,
    timestamp_ms: int,
    width: int,
    height: int,
    camera_id: str,
)
```

### 6.2 Saída do Agente A

```python
Detection(
    detection_id: int,
    bbox_xyxy: tuple[float, float, float, float],
    mask_polygon: list[tuple[float, float]],
    confidence: float,
    class_id: int = 0,
)

Detector.predict(frame_bgr, meta: FrameMeta) -> list[Detection]
```

O polígono e a bbox voltam ao espaço do frame original mesmo que o modelo rode sobre ROI redimensionada. Para cache em disco, usar JSONL com polígonos; não serializar uma matriz binária do tamanho do frame.

### 6.3 Saída do tracker e entrada do Agente B

```python
TrackObservation(
    track_id: str,
    state: TrackState,
    meta: FrameMeta,
    bbox_xyxy: tuple[float, float, float, float],
    mask_polygon: list[tuple[float, float]] | None,
    mask_confidence: float | None,
    visibility: float,
    predicted_centroid: tuple[float, float] | None,
)

Tracker.update(meta, detections) -> list[TrackObservation]
```

### 6.4 Saída do Agente B

```python
FrameMeasurement(
    track_id: str,
    frame_id: int,
    length_mm: float | None,
    width_mm: float | None,
    geometry_uncertainty_mm: float | None,
    quality: float,
)

TrackEstimate(
    track_id: str,
    catalog_candidates: list[CatalogCandidate],
    volume_l: float | None,
    volume_ci95_l: tuple[float, float] | None,
    volume_confidence: float,
)

GeometryEstimator.measure(observation) -> FrameMeasurement
CatalogMatcher.update(track_id, measurement) -> TrackEstimate
```

### 6.5 Orquestração do Agente C

```python
detections = detector.predict(frame, meta)
observations = tracker.update(meta, detections)

for observation in observations:
    measurement = geometry.measure(observation)
    estimate = catalog.update(observation.track_id, measurement)
    events = counter.update(observation, estimate)
    event_sink.write(events)
```

O pipeline precisa aceitar dois modos sem mudar código downstream:

- `live`: executa o detector no vídeo;
- `replay`: consome `detections.jsonl` produzido pelo Agente A.

Esse replay é a principal proteção contra atraso de treinamento, disputa de GPU e instabilidade na demo.

## 7. Contrato externo com interface/PLC

O core emite os três eventos previstos no documento original. Ele não emite nem decide `PLC_STATE`.

### `TRACK_UPDATE`

Campos obrigatórios:

```json
{
  "event": "TRACK_UPDATE",
  "timestamp_ms": 123456,
  "video_id": "video_03",
  "resolution": "720p",
  "track_id": "battery-0017",
  "state": "TRACKING",
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

Estados permitidos:

```text
DETECTED, TRACKING, OCCLUDED, REACQUIRED, COUNTED, LOST
```

### `TRACK_OCCLUDED`

```json
{
  "event": "TRACK_OCCLUDED",
  "track_id": "battery-0017",
  "predicted_position": [615, 320],
  "last_volume_l": 7.94,
  "volume_confidence": 0.83
}
```

### `BATTERY_COUNTED`

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

Regras de compatibilidade:

- não renomear nem remover campos do plano original;
- campos adicionais, como `schema_version`, só entram após confirmação da equipe de interface;
- números devem ser tipos JSON numéricos, sem `NaN` ou `Infinity`;
- antes de existir medida confiável, campos físicos em `TRACK_UPDATE` são `null`;
- `BATTERY_COUNTED` só é emitido se houver volume finito e positivo;
- cada linha do arquivo de saída contém exatamente um objeto JSON.

Até T+25, entregar à equipe de interface:

1. os três exemplos acima;
2. uma fixture com pelo menos 20 eventos;
3. a regra de `null`;
4. os enums de estado;
5. a informação de que `bbox` está no frame original;
6. a regra de que PLC é consumidor, nunca dependência do Model Core.

## 8. Plano do Agente A — dados, segmentação e inferência

### Missão

Entregar rapidamente uma implementação de `Detector` substituível, um checkpoint utilizável e detecções cacheadas para que os outros agentes nunca precisem esperar pela GPU.

### Arquivos sob ownership

```text
src/vision/detector.py
scripts/extract_frames.py
scripts/train.py
scripts/infer_detector.py
configs/model.yaml
configs/dataset.yaml
tests/vision/
```

### Sequência de execução

#### A. Inventário e amostragem — T+00 a T+25

1. Validar com `ffprobe` os dez vídeos e o manifesto.
2. Usar apenas os vídeos 01–03 para treino.
3. Extrair keyframes HR distribuídos no tempo e complementar manualmente com cenas de:
   - bateria isolada;
   - baterias encostadas;
   - alta densidade;
   - rotação;
   - reflexo;
   - papelão/lixo;
   - oclusão parcial e forte;
   - borda, entrada e saída da esteira;
   - tamanhos distintos.
4. Não extrair longas sequências consecutivas.

Meta adaptada ao limite de cinco horas:

```text
piso:   36 frames HR anotados
alvo:   60 frames HR anotados
limite: 80 frames HR; depois disso parar de anotar
```

Distribuição alvo:

```text
36 treino (12 por vídeo 01–03)
12 validação (vídeo 04)
12 teste (vídeo 05)
```

Transferir cada anotação HR para o frame 720p correspondente com escala exata:

```text
x_720 = x_1080 × 1280 / 1920
y_720 = y_1080 × 720 / 1080
```

Validar visualmente pelo menos 10 máscaras transferidas.

#### B. Rotulagem rápida — T+20 a T+50

Preferência operacional:

1. desenhar caixas rapidamente em ferramenta acessível por túnel SSH;
2. usar SAM/SAM2 já disponível para converter caixas em máscaras;
3. corrigir apenas contornos claramente errados;
4. se SAM não estiver disponível em 10 minutos, anotar polígonos manualmente e reduzir ao piso de 36 frames.

Não gastar tempo montando uma plataforma completa de anotação. Se for necessário servir uma ferramenta web na instância, expor apenas em `localhost` e acessar por port forwarding SSH.

#### C. Fallback em paralelo — até T+45

Implementar `ClassicalRoiDetector` com background subtraction/contornos dentro da ROI. Ele deve obedecer ao mesmo contrato de `Detector`.

Esse fallback não precisa ser perfeito; precisa permitir o primeiro E2E e a continuidade da geometria/tracking se o treino falhar.

#### D. Treino — T+45 a T+90

Estratégia:

```text
modelo: YOLO nano segmentation pré-treinado
classe: battery
imgsz inicial: 640; subir para 768 apenas se baterias pequenas desaparecerem
epochs finais: 20–35
batch: 8 ou o maior valor validado no smoke
precision: AMP
cache: disk
patience: 8
runs máximos: 1 smoke + 1 treino final
tempo máximo por treino final: 35 minutos
```

Augmentations permitidas:

```text
resize, downsample/upscale, JPEG, blur leve, noise,
brightness, contrast, gamma e perspectiva pequena
```

Evitar transformações geométricas agressivas que destruam a relação usada na medida.

Executar primeiro um smoke de uma época. Só iniciar o treino final se:

- CUDA estiver disponível;
- um batch completar;
- validação produzir máscaras;
- o exportador conseguir voltar as coordenadas ao frame original.

#### E. Promoção do artefato — até T+90 e no máximo T+150

Cada checkpoint publicado precisa de um manifesto:

```json
{
  "git_commit": "<sha>",
  "weights_sha256": "<sha256>",
  "model": "yolo-nano-seg",
  "imgsz": 640,
  "epochs": 25,
  "train_videos": ["01", "02", "03"],
  "validation_video": "04",
  "created_at": "<ISO-8601>"
}
```

Publicar sem sobrescrever:

```text
shared/artifacts/detector/run-001/
├── best.pt
├── manifest.json
├── metrics.csv
└── overlays/
```

Gerar imediatamente `detections.jsonl` para 300–900 frames do trecho escolhido para integração. A partir daí, B e C usam replay e não dependem do processo de treino.

### Testes obrigatórios do Agente A

- frame sem bateria retorna lista vazia, não exceção;
- coordenadas ficam dentro do frame original;
- confiança fica em `[0,1]`;
- polígono tem ao menos três pontos;
- 10 overlays 720p e 10 overlays 1080p são inspecionados visualmente;
- inferência de 30 frames produz JSONL parseável;
- o backend seleciona `ClassicalRoiDetector` por configuração se `best.pt` não existir.

### Definition of Done do Agente A

- `Detector.predict` implementado;
- peso ou fallback promovido;
- configuração reproduzível;
- detecções cacheadas entregues;
- nenhum downstream importa tipos do Ultralytics;
- branch limpa, testes verdes e commit de handoff.

### Regra de corte do Agente A

- T+45 sem pipeline de labels: congelar o piso de frames e ativar fallback.
- T+75 sem checkpoint visualmente utilizável: integrar o fallback; treinamento passa a ser melhoria opcional.
- T+150: promover o melhor artefato existente e encerrar treino.
- Nunca iniciar consistency loss, ReID, TensorRT ou sweep de hiperparâmetros.

## 9. Plano do Agente B — calibração, geometria, catálogo e incerteza

### Missão

Entregar uma cadeia matemática testável com máscaras sintéticas desde o primeiro minuto e substituí-las por detecções reais quando o cache do Agente A chegar.

### Arquivos sob ownership

```text
src/geometry/
src/catalog/
configs/camera.yaml
data/catalog/catalog_normalized.csv
scripts/smoke_geometry.py
tests/geometry/
tests/catalog/
```

### Sequência de execução

#### A. Normalização do catálogo — T+00 a T+25

1. Ler CSV como UTF-8 e converter decimal pt-BR para ponto.
2. Validar que `L`, `W` e `H` são positivos e estão em milímetros.
3. Criar `catalog_id` estável.
4. Remover duplicatas exatas de `(L,W,H)` para que repetições na planilha não criem um prior artificial.
5. Preservar todas as categorias associadas a uma dimensão.
6. Reportar linhas rejeitadas; nunca corrigi-las silenciosamente.

O catálogo normalizado pequeno pode ser versionado; o CSV bruto permanece no diretório de dados compartilhado.

#### B. Configuração de câmera — T+00 a T+35

Formato recomendado:

```yaml
camera_id: cctv_01
roi_polygon_norm:
  - [0.05, 0.15]
  - [0.95, 0.15]
  - [0.95, 0.90]
  - [0.05, 0.90]
homography:
  src_points_norm: []       # quatro pontos no frame
  dst_points_mm: []         # quatro pontos no plano físico
count_gate_norm:
  p1: [0.75, 0.15]
  p2: [0.75, 0.90]
flow_direction: [1.0, 0.0]
calibration_rmse_mm: null
```

Os valores acima são apenas formato, não valores de calibração. O Agente B deve marcar pontos reais em um frame, calcular a homografia e registrar a referência física fornecida.

Se houver somente a largura conhecida da esteira, usar escala local e aumentar `geometry_uncertainty_mm`. Não implementar reconstrução 3D.

#### C. Medida geométrica — T+25 a T+70

Por observação válida:

```text
polygon → máscara/contorno → homografia → minAreaRect
→ lados no plano físico → ordenar max/min → L/W em mm
```

Tratar `(L,W)` e `(W,L)` como equivalentes. Rejeitar ou degradar qualidade quando:

- máscara toca a borda da ROI;
- área é pequena demais;
- contorno é degenerado;
- objeto está fortemente ocluído;
- razão entre área da máscara e área do retângulo é anormal;
- dimensão varia abruptamente em relação ao histórico do track.

Quality score por frame:

```text
q = mask_confidence × visibility × contour_quality × geometry_stability
```

Todos os fatores ficam em `[0,1]`. Um frame ruim contribui pouco; não apaga o posterior bom acumulado anteriormente.

#### D. Matching probabilístico — T+55 a T+100

Para observação `y=[L,W]` e candidato de catálogo `s`, calcular a likelihood considerando as duas orientações:

```text
p(y|s) = max(
  N([L,W]; [Ls,Ws], Sigma),
  N([L,W]; [Ws,Ls], Sigma)
)
```

Acumular log-evidência por track ponderada por `q`. Usar log-sum-exp na normalização para evitar underflow.

Para cada dimensão candidata:

```text
V_s = L_s × W_s × H_s / 1_000_000
```

Saídas:

```text
volume_l       = Σ p_s V_s
volume_ci95_l  = quantis 2,5% e 97,5% da distribuição discreta
confidence     = quality_agg × (1 - entropy(p) / log(K))
```

Se não houver observação utilizável, retornar `null` para dimensões/volume e `0.0` para confiança.

#### E. Calibração e fixture real — T+100 a T+150

1. Rodar máscaras sintéticas de tamanho conhecido.
2. Rodar o cache de detecções do Agente A.
3. Verificar visualmente as dimensões de pelo menos 10 observações.
4. Ajustar somente erro de escala/homografia e thresholds grosseiros.
5. Não tentar resolver oclusão no módulo geométrico; isso pertence ao tracker.

### Testes obrigatórios do Agente B

- quatro pontos conhecidos são reprojetados dentro da tolerância;
- retângulo rotacionado recupera L/W;
- trocar L e W não muda o ranking do catálogo;
- `1_000_000 mm³ == 1 L`;
- `197 × 130 × 225 mm == 5.76225 L`;
- probabilidades somam 1 com tolerância numérica;
- CI é ordenado e inclui o volume esperado quando aplicável;
- duplicatas exatas do catálogo não duplicam prior;
- a altura `"95,50"` vira `95.5`;
- máscara truncada reduz qualidade;
- máscara inválida não derruba o pipeline.

### Definition of Done do Agente B

- `camera.yaml` preenchido com valores reais e origem documentada;
- parser/catalog matcher testados;
- `GeometryEstimator` e `CatalogMatcher` obedecem aos contratos;
- fixture sintética e cache real processados;
- branch limpa, testes verdes e commit de handoff.

### Regra de corte do Agente B

- T+35 sem quatro pontos físicos: usar escala local documentada.
- T+90 sem covariance confiável: usar erro fixo conservador e softmax/likelihood diagonal.
- T+150: congelar calibração MVP.
- Cortar perspectiva por altura, reconstrução 3D e calibração sofisticada antes de cortar volume por catálogo.

## 10. Plano do Agente C — tracking, contagem, eventos, métricas e integração

### Missão

Entregar o pipeline executável e idempotente, inicialmente sobre fixtures, e integrar A e B sem acoplar o core à interface ou ao PLC.

### Arquivos sob ownership

```text
src/contracts/
src/vision/tracker.py
src/counting/
src/metrics/
src/pipeline.py
configs/thresholds.yaml
scripts/replay_detections.py
scripts/run_video.py
scripts/validate_events.py
scripts/compare_resolutions.py
tests/fixtures/
tests/tracking/
tests/counting/
tests/integration/
requirements.txt ou pyproject.toml
.gitignore
```

### Sequência de execução

#### A. Commit-base e fixture — T+00 a T+20

1. Criar tipos de domínio e schemas de evento.
2. Criar uma fixture determinística com duas baterias:
   - bateria A aparece, fica ocluída por 10 frames, reaparece, cruza o gate e reaparece depois;
   - bateria B aproxima-se do gate, mas não cruza;
   - incluir variação de bbox/tamanho e um falso positivo curto.
3. Criar configuração comum de testes.
4. Criar o commit-base antes de abrir as três branches de feature.
5. Entregar a fixture de eventos externos à equipe de interface.

#### B. Tracker e máquina de estados — T+20 a T+75

Baseline preferido: ByteTrack por adapter. Se a API/dependência consumir mais de 15 minutos, ativar imediatamente o fallback IoU + centro predito + tamanho.

Nenhum objeto da biblioteca de tracking pode sair do adapter.

Estados:

```text
DETECTED → TRACKING → OCCLUDED → REACQUIRED → TRACKING
                               ↘ LOST
TRACKING/REACQUIRED → COUNTED
```

Regras mínimas:

- `tracker_id` interno mapeia para UUID operacional;
- manter track por `max_age_frames`, inicialmente 45 frames;
- preservar último posterior de volume durante oclusão;
- predizer centro por velocidade recente;
- reassociar por movimento e tamanho;
- aparência/ReID é P2 e não deve ser iniciado;
- um track `COUNTED` pode continuar visível sem gerar novo evento.

Score de reassociação MVP:

```text
score = w_motion × motion_similarity + w_size × size_similarity
```

#### C. Count gate e lote — T+55 a T+90

O gate é uma linha normalizada com direção de fluxo. Contar somente quando o centro do track muda do lado anterior para o lado posterior no sentido válido.

Guardas obrigatórias:

```python
if crossed_in_valid_direction and not track.counted and volume_is_valid:
    track.counted = True
    lot.count += 1
    lot.volume_l += estimate.volume_l
    emit_battery_counted_once()
```

O acumulador precisa garantir:

```text
lot.count == número de eventos BATTERY_COUNTED únicos
lot.volume_l == soma dos volume_l desses eventos
```

#### D. Runner e eventos — T+75 a T+120

Implementar CLI headless:

```text
scripts/run_video.py
  --video
  --weights
  --camera-config
  --thresholds
  --events
  --summary
  --render-output opcional
  --max-frames opcional
  --detections-cache opcional
```

Quando `--detections-cache` estiver presente, não carregar GPU nem modelo. Isso será usado nos testes e no replay da demo.

Implementar validação fail-fast:

- configuração ausente;
- vídeo/resolução divergente;
- timestamps regressivos;
- evento não serializável;
- volume negativo/não finito;
- UUID contado mais de uma vez.

#### E. Métricas — T+100 a T+155

Gerar `summary.json` por execução:

```json
{
  "video_id": "video_01",
  "resolution": "720p",
  "frames_processed": 9026,
  "lot_count": 28,
  "lot_volume_l": 211.6,
  "unique_tracks": 30,
  "counted_track_ids": [],
  "processing_fps": 34.2
}
```

Comparação pareada:

```text
count_gap = abs(N_1080 - N_720)
RVG = abs(V_1080 - V_720) / ((V_1080 + V_720) / 2)
```

RVE, Count Error e Duplicate Rate só podem ser apresentados como métricas avaliadas se existir golden set manual. Sem ground truth, marcar como `not_available`; não substituir ground truth por uma das resoluções.

Criar um golden set mínimo para o trecho de demo:

- contagem manual de baterias que cruzam o gate;
- UUID/intervalo de frames de 10–20 tracks;
- casos de oclusão marcados;
- SKU/volume somente quando verificável; caso contrário `ambiguous` com candidatos válidos.

### Testes obrigatórios do Agente C

- cruzamento no sentido correto conta uma vez;
- cruzamento reverso não conta;
- permanecer além do gate por vários frames não reconta;
- oclusão e reacquisition preservam UUID na fixture;
- reaparecimento após `COUNTED` não gera novo evento;
- falso positivo curto não chega ao gate como track confirmado;
- timestamps dos eventos são monotônicos;
- JSONL obedece ao contrato externo;
- CI é `null` ou `[lo, hi]` válido;
- soma do lote coincide com os eventos de contagem;
- replay é determinístico.

### Definition of Done do Agente C

- tracker/fallback funcional;
- gate idempotente;
- runner live e replay;
- validadores e métricas;
- fixture compatível entregue à interface;
- branch limpa, testes verdes e commit de handoff.

### Regra de corte do Agente C

- após 15 minutos de problema com ByteTrack, usar tracker fallback.
- sem E2E por fixture em T+90: parar métricas avançadas e corrigir apenas contratos/gate.
- não implementar FastAPI, banco, PLC ou VLM nesta branch.
- cortar ReID e matching de aparência antes de reduzir a idempotência do gate.

## 11. Operação na AWS por SSH

### 11.1 Topologia

Usar uma única instância GPU compartilhada por três sessões SSH/tmux. Não usar treino distribuído: o dataset é pequeno e o custo de configuração não compensa.

Layout recomendado:

```text
/home/ubuntu/hackathon/
├── repo/                    # clone principal
├── integration/             # branch integration/backend-core
├── worktrees/
│   ├── agent-a-vision/
│   ├── agent-b-geometry/
│   └── agent-c-tracking/
└── shared/
    ├── data/                # 10 vídeos; somente leitura
    ├── artifacts/
    ├── cache/
    ├── logs/
    └── venv/
```

Não duplicar os 4,1 GB em cada worktree. Cada processo recebe o caminho de dados por `HACKATHON_DATA_DIR` ou configuração. Não copiar a chave `.pem` para a instância.

### 11.2 Preflight único — T+00 a T+10

O coordenador executa uma única vez:

```bash
nvidia-smi
nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv
lscpu
free -h
df -h
python3 --version
ffmpeg -version
git --version
```

Depois validar o ambiente Python existente antes de instalar qualquer pacote:

```bash
python3 -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
python3 -c "import cv2, numpy; print(cv2.__version__, numpy.__version__)"
```

Não reinstalar `torch` cegamente: preservar a build compatível com o driver/CUDA da AMI. Criar uma única virtualenv compartilhada e dar a uma pessoa — o Agente C durante o bootstrap — ownership exclusivo de `pip install`. Depois do freeze, ninguém instala dependências sem coordenação.

Congelar o ambiente aprovado:

```bash
python -m pip freeze > /home/ubuntu/hackathon/shared/artifacts/requirements.freeze.txt
```

### 11.3 GPU

Se houver uma GPU:

- A tem exclusividade durante treino;
- B trabalha em CPU;
- C trabalha em replay/fixtures em CPU;
- smoke integrado na GPU ocorre entre jobs de treino.

Proteger GPU única:

```bash
flock /tmp/hackathon-gpu0.lock <comando-de-treino-ou-inferencia>
```

Se houver duas GPUs, reservar GPU 0 para A e GPU 1 para smoke de C. Não usar DDP.

### 11.4 Sessões resilientes

```bash
tmux new -s agent-a
tmux new -s agent-b
tmux new -s agent-c
tmux new -s integration
```

Todo job longo grava log em `shared/logs/<agente>/`. O nome do run, commit e caminho do artefato devem aparecer na primeira linha do log.

### 11.5 Dados

Primeiro verificar se os vídeos já estão na instância. Se não estiverem, transferir somente `data/`, nunca o ZIP redundante, usando `rsync --partial --append-verify` da máquina local.

Depois rodar `ffprobe` nos dez arquivos e gravar `configs/videos.yaml`. Como todos os pares já foram observados com frames e duração idênticos, qualquer divergência na AWS indica upload incompleto ou arquivo errado.

## 12. Git, branches e prevenção de conflitos

O worktree local atual possui alterações/untracked de outras frentes. Não usar `git add .`, `git clean`, `git reset` ou checkout destrutivo.

### Branches

```text
integration/backend-core
agents/a-vision
agents/b-geometry
agents/c-tracking
```

Primeiro criar o worktree de integração. O Agente C cria nele o commit-base; somente depois criar os três worktrees de feature a partir exatamente desse SHA:

```bash
git worktree add -b integration/backend-core \
  /home/ubuntu/hackathon/integration main

# O Agente C cria e commita o esqueleto no worktree de integração.

git worktree add -b agents/a-vision \
  /home/ubuntu/hackathon/worktrees/agent-a-vision integration/backend-core

git worktree add -b agents/b-geometry \
  /home/ubuntu/hackathon/worktrees/agent-b-geometry integration/backend-core

git worktree add -b agents/c-tracking \
  /home/ubuntu/hackathon/worktrees/agent-c-tracking integration/backend-core
```

Como o `.gitignore` atual ignora todo `data/*`, o commit-base deve abrir exceção somente para o catálogo normalizado, sem liberar vídeos ou frames:

```gitignore
data/*
!data/catalog/
!data/catalog/catalog_normalized.csv
```

Cada agente faz commits pequenos e testáveis. Sugestão:

```text
A: feat(vision): add detector adapter and cached inference
A: feat(vision): publish first segmentation checkpoint manifest
B: feat(geometry): add homography and mask measurement
B: feat(catalog): add probabilistic volume posterior
C: feat(tracking): add persistent track state machine
C: feat(counting): add idempotent directed gate
C: feat(pipeline): add replay and event validation
```

Antes do handoff:

```bash
git status --short
git diff --check integration/backend-core...HEAD
pytest -q <testes-do-agente>
git log -1 --oneline
```

O handoff de cada agente deve informar:

```text
branch e commit
testes executados
artefatos externos e SHA256
comando de smoke
limitações/fallback ativo
arquivos que a integração não deve sobrescrever
```

## 13. Cronograma integrado — entrega em 4h40 dentro da janela máxima de 5 horas

### T+00 a T+20 — bootstrap e freeze

Todos:

- conectar por SSH/tmux;
- inventariar GPU, disco, Python e dados;
- confirmar dimensão física/calibração;
- congelar split, coordenadas, contratos e evento externo.

Em paralelo:

- A começa amostragem/labels;
- B normaliza catálogo e coleta pontos de calibração;
- C cria commit-base, contratos e fixtures.

Marco T+20:

- três worktrees criados do mesmo SHA;
- fixture de interface entregue;
- nenhuma dúvida sobre coordenadas/unidades/null.

### T+20 a T+75 — primeira versão independente

- A: fallback, labels, smoke de treino, primeiro cache.
- B: homografia, medidas e catálogo sobre máscaras sintéticas.
- C: tracking, FSM e gate sobre fixture.

Marco T+75:

- cada módulo passa seus testes isolados;
- existe `detections.jsonl` real ou fallback;
- nenhum agente está esperando outro para continuar.

### T+75 a T+95 — integração 1 por fixture

Integrar contratos → B → C, ainda com detector cacheado/mockado.

Marco T+95:

```text
fixture de detecção
→ UUID
→ L/W
→ volume/CI
→ cruzamento
→ um BATTERY_COUNTED
```

Se este marco falhar, suspender toda melhoria de modelo e resolver apenas contrato/E2E.

### T+95 a T+165 — refinamento paralelo com dados reais

- A executa seu único treino final e publica artefato imutável.
- B calibra com cache real e valida 10 medidas.
- C ajusta tracking/oclusão, runner e golden set do trecho.

Marco T+150: treinamento encerrado e melhor detector promovido.

Marco T+165: três branches prontas para merge, cada uma com commit e testes.

### T+165 a T+195 — merge completo e smoke curto

Ordem de merge em `integration/backend-core`:

1. `agents/b-geometry`;
2. `agents/c-tracking`;
3. `agents/a-vision`.

A ordem mantém o pipeline testável com fixtures até a última troca do detector mock pelo real.

Após cada merge:

```bash
pytest -q
python scripts/replay_detections.py <argumentos-da-fixture>
```

Depois rodar 300 frames de um vídeo 720p. Corrigir somente integração, tipos, coordenadas e falhas fatais.

### T+195 a T+235 — execução real

1. Rodar o trecho de demo completo.
2. Rodar um vídeo completo conhecido.
3. Rodar o par da outra resolução com a mesma configuração canônica.
4. Gravar eventos, summary e overlay opcional.

Marco T+235:

- processo termina sem exceção;
- há contagens e volumes positivos;
- não há UUID contado duas vezes;
- lote fecha com soma consistente.

### T+235 a T+260 — métricas e artefatos

- calcular `count_gap` e RVG;
- validar JSONL contra o contrato;
- inspecionar casos de oclusão/reacquisition;
- promover release imutável;
- entregar eventos e instruções à equipe de interface/PLC.

### T+260 — code freeze do Model Core

Depois deste ponto:

- não trocar modelo;
- não instalar dependência;
- não alterar schema;
- não refatorar;
- só corrigir regressão que bloqueia a demo.

### T+260 a T+280 — backup e ensaio técnico

- gerar vídeo/overlay de backup;
- testar replay sem GPU;
- copiar release e resultados para local seguro;
- ensaiar comando único de execução.

### T+280 a T+300 — margem

Reservada para falha de SSH, upload, conflito final ou compatibilidade com a interface. Não é tempo para features.

## 14. Procedimento de merge

No worktree de integração:

```bash
git status --short
git merge --no-ff agents/b-geometry
pytest -q tests/geometry tests/catalog

git merge --no-ff agents/c-tracking
pytest -q tests/tracking tests/counting tests/integration

git merge --no-ff agents/a-vision
pytest -q
```

Regras:

- não copiar arquivos manualmente entre worktrees;
- não resolver conflito escolhendo “ours/theirs” sem ler o diff;
- contratos congelados vencem mudanças de implementação;
- se um branch depender de mudança de contrato não aprovada, adaptar o branch, não o contrato;
- pesos são promovidos por manifesto e checksum, nunca por merge Git.

## 15. Smoke E2E e release gate

### 15.1 Replay determinístico

```bash
python scripts/replay_detections.py \
  --input tests/fixtures/detections.jsonl \
  --events /tmp/replay-events.jsonl \
  --summary /tmp/replay-summary.json

python scripts/validate_events.py --input /tmp/replay-events.jsonl
```

Aceite:

- exatamente um `BATTERY_COUNTED` para a bateria A;
- zero para a bateria B;
- oclusão/reacquisition preserva UUID;
- duas execuções geram o mesmo resumo.

### 15.2 Vídeo curto

```bash
python scripts/run_video.py \
  --video /home/ubuntu/hackathon/shared/data/Video_01_720p.mp4 \
  --weights /home/ubuntu/hackathon/shared/artifacts/release/mvp-01/weights/best.pt \
  --camera-config configs/camera.yaml \
  --thresholds configs/thresholds.yaml \
  --max-frames 300 \
  --events /tmp/e2e-events.jsonl \
  --summary /tmp/e2e-summary.json
```

Se o fallback estiver ativo, substituir `--weights` por configuração explícita de detector; nunca fingir que o modelo treinado está sendo usado.

### 15.3 Par completo

Executar o mesmo `video_id` nas duas resoluções e depois:

```bash
python scripts/compare_resolutions.py \
  --hr results/video_01_1080-summary.json \
  --lr results/video_01_720-summary.json \
  --output results/video_01-resolution-comparison.json
```

### Release gate obrigatório

- todos os testes passam;
- um vídeo completo termina sem exceção;
- JSONL é parseável e compatível com a interface;
- timestamps são monotônicos;
- `track_id` nunca é vazio;
- `volume_l` contado é finito e positivo;
- CI é `null` ou `[lo, hi]` válido;
- nenhum UUID produz dois eventos de contagem;
- total do lote coincide com a soma de `BATTERY_COUNTED`;
- 720p e 1080p geram `count_gap` e RVG;
- replay funciona sem GPU;
- checkpoint/fallback e configurações estão identificados sem ambiguidade.

## 16. Artefato final único

Promover uma release imutável:

```text
shared/artifacts/release/mvp-01/
├── manifest.json
├── requirements.freeze.txt
├── weights/
│   └── best.pt                # ausente se fallback clássico
├── configs/
│   ├── camera.yaml
│   ├── model.yaml
│   ├── thresholds.yaml
│   └── videos.yaml
├── events/
│   ├── demo.jsonl
│   ├── video_01_1080.jsonl
│   └── video_01_720.jsonl
├── summaries/
│   ├── video_01_1080.json
│   ├── video_01_720.json
│   └── resolution-comparison.json
├── overlays/
│   └── demo.mp4
└── checksums.sha256
```

`manifest.json` deve conter:

```text
commit da branch integrada
commits dos três agentes
modo de detector (trained/classical)
SHA256 do peso
vídeos usados em train/val/test
configurações usadas
comando exato da demo
limitações conhecidas
horário do code freeze
```

## 17. Handoff para interface e PLC

Entregar somente uma fronteira:

```text
DomainEvent → JSONL/stream
```

Pacote de handoff:

- fixture de eventos congelada em T+25;
- `demo.jsonl` real em T+260;
- enum de estados;
- semântica de `null`;
- bbox em pixels do frame original;
- frequência esperada de `TRACK_UPDATE`;
- garantia de idempotência de `BATTERY_COUNTED`;
- comando de replay;
- aviso explícito de que o Model Core não emite `PLC_STATE`.

A equipe de interface/PLC pode fazer replay do JSONL ou envolvê-lo em FastAPI/WebSocket sem importar Ultralytics, OpenCV ou tracker.

## 18. Ordem de abandono de features

Se o cronograma escorregar, cortar nesta ordem:

1. consistency loss HR/LR;
2. ReID/aparência;
3. ONNX/TensorRT;
4. leave-one-video-out;
5. perspectiva/3D avançada;
6. métricas de calibração de CI além do golden set;
7. tuning fino do matcher;
8. ByteTrack, substituindo-o pelo tracker fallback já testado.

Não cortar:

- contrato de eventos;
- replay cacheado;
- tracking com UUID persistente;
- gate idempotente;
- volume via catálogo;
- incerteza, mesmo que conservadora;
- execução 720p e 1080p;
- RVG e `count_gap`;
- release imutável e demo de backup.

## 19. Definition of Done do backend

O backend está concluído quando:

- processa pelo menos um vídeo completo e seu par em outra resolução;
- detecta baterias por modelo treinado ou fallback explicitamente identificado;
- cria IDs persistentes;
- demonstra ao menos um `OCCLUDED → REACQUIRED` no replay controlado;
- nunca adiciona volume duas vezes para o mesmo UUID;
- estima volume usando dimensões do catálogo, não regressão direta;
- fornece intervalo de incerteza e confiança;
- acumula contagem e volume do lote;
- calcula RVG e `count_gap`;
- emite eventos reais no contrato combinado;
- roda em modo replay sem GPU;
- possui testes, manifesto, checksums, logs e vídeo de backup;
- a equipe de interface/PLC consegue consumir a fixture e o replay sem depender do código interno.

Mensagem técnica da entrega:

> A rede encontra a bateria; a geometria mede; o catálogo restringe; o tempo reduz a incerteza; o tracking garante contagem única; e os vídeos pareados comprovam a robustez à resolução.
