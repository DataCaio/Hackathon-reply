# Graph Report - Hackathon-reply  (2026-08-22)

## Corpus Check
- 107 files · ~45,440 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1041 nodes · 1894 edges · 98 communities (90 shown, 8 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 146 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8c3127cd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- FrameMeta
- hackathon-reply
- IMPLEMENTACAO_HACKATHON_VISAO.md
- IoUTracker
- 22. Cronograma para o dia do hackathon
- Core Principles
- Plano de implementação do Backend/Model Core — 3 agentes em menos de 5 horas
- 24. Demo final sugerida
- 15. Métricas
- 2. Organização do time — 5 pessoas
- 8. Fase 2 — Generalização 720p ↔ 1080p
- ReplayRunner
- 3. Contrato entre Model Core e Interface
- 6. Criação das labels
- 9. Fase 3 — Calibração geométrica
- Plano de Implementação — Hackathon Reply 2026
- 13. Fase 6 — Tracking e oclusão
- 17. PLC Simulator — diferencial de interface
- 21. Ordem de implementação
- 7. Fase 1 — Baseline visual
- AGENTS.md
- GEMINI.md
- Hackathon Reply backend
- Tasks: User Story 3 — Consume Stable, Honest Events
- TrackManager
- Detection
- counter.py
- hackathon_reply/events.py
- CountGate
- 10. Plano do Agente C — tracking, contagem, eventos, métricas e integração
- 8. Plano do Agente A — dados, segmentação e inferência
- 9. Plano do Agente B — calibração, geometria, catálogo e incerteza
- 13. Cronograma integrado — entrega em 4h40 dentro da janela máxima de 5 horas
- 5. Split recomendado
- AWS.sh
- CatalogCandidate
- contracts/__init__.py
- metrics/audit.py
- ExactlyOnceEventSink
- ManifestError
- fixtures/README.md
- tests/__init__.py
- loader.py
- measurement.py
- lot.py
- Feature Specification: Backend Model Core
- run_replay
- pipeline.py
- domain.py
- .from_csv_text
- 11. Operação na AWS por SSH
- 6. Contratos internos
- ContractError
- 15. Smoke E2E e release gate
- validate_summary
- 7. Contrato externo com interface/PLC
- us1_events.py
- scripts/__init__.py
- test_track_keeps_operational_identity_across_temporary_occlusion
- contracts/events.py
- hackathon_reply/__init__.py
- fixture_root
- matcher.py
- EventValidationError
- hackathon_reply/replay.py
- Implementation Plan: User Story 3 — Consume Stable, Honest Events
- Contract: Battery Domain Events
- Research: User Story 3 — Consume Stable, Honest Events
- Quickstart: User Story 3 Event Handoff and Replay
- .update
- ReplayDetector
- contract/conftest.py
- 🔋 Trilha C: Visão Computacional para Reciclagem (Detecção de Baterias)
- Data Model: User Story 3 Event Boundary
- Specification Quality Checklist: Backend Model Core
- User Scenarios & Testing *(mandatory)*
- test_user_story3_replay.py
- Contract: Run Summary and Diagnostics
- Contract: User Story 3 Replay
- test_user_story_1_volume.py
- test_detector.py
- main
- validate_events.py
- TrackState

## God Nodes (most connected - your core abstractions)
1. `run_replay()` - 27 edges
2. `IoUTracker` - 22 edges
3. `TrackManager` - 21 edges
4. `Plano de implementação do Backend/Model Core — 3 agentes em menos de 5 horas` - 20 edges
5. `FrameMeta` - 19 edges
6. `VolumeEstimate` - 19 edges
7. `validate_event()` - 18 edges
8. `EventValidationError` - 17 edges
9. `CountGate` - 16 edges
10. `validate_summary()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `test_unvalidated_measurement_cannot_produce_countable_volume()` --uses--> `FrameMeasurement`  [INFERRED]
  tests/unit/test_user_story_1_volume.py → src/hackathon_reply/contracts/domain.py
- `test_uncertainty_uses_expected_volume_and_candidate_measurement_bounds()` --uses--> `CatalogCandidate`  [INFERRED]
  tests/unit/test_user_story_1_volume.py → src/hackathon_reply/contracts/domain.py
- `test_paired_comparison_reports_count_and_relative_volume_gaps()` --uses--> `RunSummary`  [INFERRED]
  tests/unit/test_user_story_1_comparison.py → src/hackathon_reply/contracts/domain.py
- `main()` --uses--> `ReplayError`  [INFERRED]
  scripts/replay_events.py → src/hackathon_reply/io/replay.py
- `build_runner()` --uses--> `CounterConfig`  [INFERRED]
  scripts/replay_story2.py → src/hackathon_reply/counting/counter.py

## Import Cycles
- None detected.

## Communities (98 total, 8 thin omitted)

### Community 0 - "FrameMeta"
Cohesion: 0.21
Nodes (13): Detection, FrameMeta, Path, ValueError, Cached detection replay input with deterministic frame validation., Raised when cached detections cannot be replayed deterministically., Yield validated cached frames in zero-based monotonic order., read_detection_jsonl() (+5 more)

### Community 2 - "IMPLEMENTACAO_HACKATHON_VISAO.md"
Cohesion: 0.12
Nodes (16): 10. Fase 4 — Medida geométrica, 11. Fase 5 — Matching probabilístico com catálogo, 12. Volume e incerteza, 14. Fase 7 — Count Gate, 16. Golden set manual, 18. UI da demo, 19. VLM Assistant, 1. Arquitetura final (+8 more)

### Community 3 - "IoUTracker"
Cohesion: 0.06
Nodes (41): Box, build_runner(), main(), CatalogCandidate, Detection, FrameMeasurement, FrameMeta, Point (+33 more)

### Community 4 - "22. Cronograma para o dia do hackathon"
Cohesion: 0.15
Nodes (13): 09:30–10:15 — Freeze de arquitetura, 10:15–11:30 — Primeiro pipeline, 11:30–13:00 — MVP E2E, 14:00–15:00 — Robustez, 15:00–16:00 — 720p vs 1080p, 16:00–16:40 — Interface diferencial, 16:40–17:15 — Pitch e backup, 16:40 — CODE FREEZE DA DEMO (+5 more)

### Community 5 - "Core Principles"
Cohesion: 0.18
Nodes (10): Core Principles, Development Workflow & Quality Gates, Governance, Hackathon Reply Constitution, I. Architecture-First, Contract-Driven Boundaries, II. SOLID and Clean Code, III. Test-First Development (TDD, NON-NEGOTIABLE), IV. Evidence-First Vision and Measurement Integrity (+2 more)

### Community 6 - "Plano de implementação do Backend/Model Core — 3 agentes em menos de 5 horas"
Cohesion: 0.13
Nodes (14): 12. Git, branches e prevenção de conflitos, 14. Procedimento de merge, 16. Artefato final único, 17. Handoff para interface e PLC, 18. Ordem de abandono de features, 19. Definition of Done do backend, 1. Resultado esperado, 2. Estado real dos insumos (+6 more)

### Community 7 - "24. Demo final sugerida"
Cohesion: 0.29
Nodes (7): 24. Demo final sugerida, Cena 1 — problema, Cena 2 — visão, Cena 3 — oclusão, Cena 4 — incerteza, Cena 5 — PLC simulado, Cena 6 — custo/generalização

### Community 8 - "15. Métricas"
Cohesion: 0.33
Nodes (6): 15.1 Relative Volume Error, 15.2 Duplicate Rate, 15.3 Count Error, 15.4 Resolution Volume Gap, 15.5 Uncertainty Calibration, 15. Métricas

### Community 9 - "2. Organização do time — 5 pessoas"
Cohesion: 0.33
Nodes (6): 2. Organização do time — 5 pessoas, Pessoa 1 — Detecção/Segmentação + Dataset, Pessoa 2 — Calibração + Geometria + Catálogo, Pessoa 3 — Tracking + Contagem + Métricas, Pessoa 4 — Backend + Simulador de PLC, Pessoa 5 — Interface + VLM + Demo

### Community 10 - "8. Fase 2 — Generalização 720p ↔ 1080p"
Cohesion: 0.33
Nodes (6): 8. Fase 2 — Generalização 720p ↔ 1080p, Baseline obrigatório, Consistency test, Representação canônica, Resolution Volume Gap, Stretch: consistency loss

### Community 11 - "ReplayRunner"
Cohesion: 0.32
Nodes (5): ReplayFrame, ValueError, VolumeEstimate, ReplayResult, ReplayRunner

### Community 12 - "3. Contrato entre Model Core e Interface"
Cohesion: 0.40
Nodes (5): 3. Contrato entre Model Core e Interface, Evento de contagem, Evento de oclusão, Evento do PLC simulado, Evento por track

### Community 13 - "6. Criação das labels"
Cohesion: 0.40
Nodes (5): 6.1 Frames para anotação, 6.2 Label principal, 6.3 Metadata útil, 6.4 Transferência HR → 720p, 6. Criação das labels

### Community 14 - "9. Fase 3 — Calibração geométrica"
Cohesion: 0.40
Nodes (5): 9. Fase 3 — Calibração geométrica, A. Homografia simples, B. Correção por perspectiva/local, Implementação, Objetivo

### Community 15 - "Plano de Implementação — Hackathon Reply 2026"
Cohesion: 0.50
Nodes (4): 0. Restrições e insumos, Consequência arquitetural, Plano de Implementação — Hackathon Reply 2026, Trilha C — Visão Computacional para Reciclagem

### Community 16 - "13. Fase 6 — Tracking e oclusão"
Cohesion: 0.50
Nodes (4): 13. Fase 6 — Tracking e oclusão, Baseline, Estados, Oclusão por papelão/lixo

### Community 17 - "17. PLC Simulator — diferencial de interface"
Cohesion: 0.50
Nodes (4): 17. PLC Simulator — diferencial de interface, Alternativa melhor, Dois limiares, Estados

### Community 18 - "21. Ordem de implementação"
Cohesion: 0.50
Nodes (4): 21. Ordem de implementação, P0 — Obrigatório para existir demo, P1 — Diferencial de qualidade, P2 — Só se tudo acima funcionar

### Community 19 - "7. Fase 1 — Baseline visual"
Cohesion: 0.50
Nodes (4): 7. Fase 1 — Baseline visual, Augmentations, Modelo, Objetivo

### Community 22 - "Hackathon Reply backend"
Cohesion: 0.40
Nodes (4): Hackathon Reply backend, US1 replay quickstart, US3 event handoff, Verification

### Community 23 - "Tasks: User Story 3 — Consume Stable, Honest Events"
Cohesion: 0.12
Nodes (17): Dependencies & Execution Order, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, Parallel execution example: User Story 3, Parallel Opportunities, Phase 1: Setup (Shared Infrastructure), Phase 2: Foundational (Blocking Prerequisites) (+9 more)

### Community 24 - "TrackManager"
Cohesion: 0.15
Nodes (16): bbox_centroid(), Return the center of an original-frame xyxy box., TrackObservation, _box_size(), _predict_box(), Detection, FrameMeta, TrackObservation (+8 more)

### Community 25 - "Detection"
Cohesion: 0.19
Nodes (10): Protocol, CallableDetector, Detector, EmptyDetector, Detection, FrameMeta, Project-owned detector boundary; vendor objects stop behind it., Detector used for an empty or deliberately disabled live source. (+2 more)

### Community 26 - "counter.py"
Cohesion: 0.13
Nodes (12): CountDecision, CounterConfig, ExactlyOnceCounter, CountGate, TrackObservation, VolumeEstimate, Directed, confirmed, exactly-once count decisions., CountRecord (+4 more)

### Community 27 - "hackathon_reply/events.py"
Cohesion: 0.24
Nodes (12): battery_counted_event(), JsonlEventSink, Any, Path, TrackObservation, VolumeEstimate, External JSON event contract and validation for the replay path., track_occluded_event() (+4 more)

### Community 28 - "CountGate"
Cohesion: 0.12
Nodes (18): DomainCountGate, CountGate, CountGate, crossed_gate(), crossed_gate_pixels(), GateError, normalized_centroid(), FrameMeta (+10 more)

### Community 29 - "10. Plano do Agente C — tracking, contagem, eventos, métricas e integração"
Cohesion: 0.17
Nodes (12): 10. Plano do Agente C — tracking, contagem, eventos, métricas e integração, A. Commit-base e fixture — T+00 a T+20, Arquivos sob ownership, B. Tracker e máquina de estados — T+20 a T+75, C. Count gate e lote — T+55 a T+90, D. Runner e eventos — T+75 a T+120, Definition of Done do Agente C, E. Métricas — T+100 a T+155 (+4 more)

### Community 30 - "8. Plano do Agente A — dados, segmentação e inferência"
Cohesion: 0.17
Nodes (12): 8. Plano do Agente A — dados, segmentação e inferência, A. Inventário e amostragem — T+00 a T+25, Arquivos sob ownership, B. Rotulagem rápida — T+20 a T+50, C. Fallback em paralelo — até T+45, D. Treino — T+45 a T+90, Definition of Done do Agente A, E. Promoção do artefato — até T+90 e no máximo T+150 (+4 more)

### Community 31 - "9. Plano do Agente B — calibração, geometria, catálogo e incerteza"
Cohesion: 0.17
Nodes (12): 9. Plano do Agente B — calibração, geometria, catálogo e incerteza, A. Normalização do catálogo — T+00 a T+25, Arquivos sob ownership, B. Configuração de câmera — T+00 a T+35, C. Medida geométrica — T+25 a T+70, D. Matching probabilístico — T+55 a T+100, Definition of Done do Agente B, E. Calibração e fixture real — T+100 a T+150 (+4 more)

### Community 32 - "13. Cronograma integrado — entrega em 4h40 dentro da janela máxima de 5 horas"
Cohesion: 0.18
Nodes (11): 13. Cronograma integrado — entrega em 4h40 dentro da janela máxima de 5 horas, T+00 a T+20 — bootstrap e freeze, T+165 a T+195 — merge completo e smoke curto, T+195 a T+235 — execução real, T+20 a T+75 — primeira versão independente, T+235 a T+260 — métricas e artefatos, T+260 a T+280 — backup e ensaio técnico, T+260 — code freeze do Model Core (+3 more)

### Community 33 - "5. Split recomendado"
Cohesion: 0.67
Nodes (3): 5. Split recomendado, Durante desenvolvimento, Para relatório final

### Community 35 - "CatalogCandidate"
Cohesion: 0.31
Nodes (9): estimate_volume(), _normalized_candidates(), CatalogCandidate, VolumeEstimate, Deterministic uncertainty calculations for catalog-constrained volume., Return a weighted expected volume and auditable candidate/error bounds. The…, _volume_l(), CatalogCandidate (+1 more)

### Community 36 - "contracts/__init__.py"
Cohesion: 0.17
Nodes (22): Validate an iterable of decoded event objects in canonical order., validate_event_stream(), Shared backend value contracts plus the public Story 3 event boundary. The…, canonical_json(), load_event_stream(), load_summary(), Any, Path (+14 more)

### Community 37 - "metrics/audit.py"
Cohesion: 0.12
Nodes (30): complete_manifest(), main(), GoldenSet, GoldenTrack, Traceable golden-set evidence for measurements, identity, and occlusion., DatasetManifest, Explicit, case-sensitive paired-video manifest and leakage checks., VideoPair (+22 more)

### Community 39 - "ExactlyOnceEventSink"
Cohesion: 0.14
Nodes (9): EventDeliveryError, ExactlyOnceEventSink, Path, RuntimeError, Exactly-once JSONL event output for one clean run., Raised when a run cannot deliver a valid exactly-once event stream., Write one immutable, ordered JSONL stream for a single run., Return the next contiguous sequence number for a new event. (+1 more)

### Community 40 - "ManifestError"
Cohesion: 0.18
Nodes (13): load_manifest(), ManifestError, Any, Path, ValueError, Explicit, case-sensitive paired-recording contracts., Raised when a pair manifest or its recordings are invalid., Load a JSON manifest while preserving filename case exactly. (+5 more)

### Community 49 - "loader.py"
Cohesion: 0.11
Nodes (27): Decimal, Namespace, Explicit alias for the US1 cached-detection replay runner., build_parser(), _gate(), main(), ArgumentParser, CountGate (+19 more)

### Community 50 - "measurement.py"
Cohesion: 0.09
Nodes (29): _calibration(), Path, CalibrationError, PhysicalCalibration, PlanarCalibration, Point, ValueError, Trusted planar calibration and explicitly marked pixel-scale fallback. (+21 more)

### Community 51 - "lot.py"
Cohesion: 0.28
Nodes (7): is_countable(), LotError, ValueError, VolumeEstimate, Exactly-once lot aggregation., Raised when a lot contribution is invalid., Check the invariant required before a volume can enter a lot.

### Community 52 - "Feature Specification: Backend Model Core"
Cohesion: 0.15
Nodes (13): Assumptions, Clarifications, Constitutional Quality Constraints, Dependencies, Feature Specification: Backend Model Core, Functional Requirements, Key Entities, Measurable Outcomes (+5 more)

### Community 53 - "run_replay"
Cohesion: 0.16
Nodes (15): measure_bbox(), US1FrameMeasurement, Measure a replay bounding box and preserve missing physical evidence., PipelineError, CatalogEntry, CountGate, ReplayFrame, RuntimeError (+7 more)

### Community 54 - "pipeline.py"
Cohesion: 0.13
Nodes (18): ResolutionComparison, main(), Path, Compare completed US1 1080p and 720p summary JSON files., _summary(), Any, ResolutionComparison, RunSummary (+10 more)

### Community 55 - "domain.py"
Cohesion: 0.21
Nodes (8): Lot, Enum, str, Framework-independent value objects for the US1 processing pipeline., Supported source resolutions., Externally visible battery-track lifecycle states., Resolution, TrackState

### Community 56 - ".from_csv_text"
Cohesion: 0.11
Nodes (21): CatalogEntry, CatalogLoader, CatalogLoadResult, _detect_delimiter(), _find_field(), _normalize_header(), _parse_locale_decimal(), Any (+13 more)

### Community 57 - "11. Operação na AWS por SSH"
Cohesion: 0.33
Nodes (6): 11.1 Topologia, 11.2 Preflight único — T+00 a T+10, 11.3 GPU, 11.4 Sessões resilientes, 11.5 Dados, 11. Operação na AWS por SSH

### Community 58 - "6. Contratos internos"
Cohesion: 0.33
Nodes (6): 6.1 Metadados do frame, 6.2 Saída do Agente A, 6.3 Saída do tracker e entrada do Agente B, 6.4 Saída do Agente B, 6.5 Orquestração do Agente C, 6. Contratos internos

### Community 59 - "ContractError"
Cohesion: 0.22
Nodes (5): ContractError, _finite(), _point(), ValueError, Raised when an externally supplied domain value is invalid.

### Community 60 - "15. Smoke E2E e release gate"
Cohesion: 0.40
Nodes (5): 15.1 Replay determinístico, 15.2 Vídeo curto, 15.3 Par completo, 15. Smoke E2E e release gate, Release gate obrigatório

### Community 61 - "validate_summary"
Cohesion: 0.18
Nodes (21): DiagnosticValidationError, _finite(), _non_empty_string(), normalize_summary(), Any, ValueError, Versioned run-summary and diagnostics validation for User Story 3., Return the semantic summary used for deterministic replay comparison. (+13 more)

### Community 62 - "7. Contrato externo com interface/PLC"
Cohesion: 0.50
Nodes (4): 7. Contrato externo com interface/PLC, `BATTERY_COUNTED`, `TRACK_OCCLUDED`, `TRACK_UPDATE`

### Community 63 - "us1_events.py"
Cohesion: 0.12
Nodes (26): Path, Validate a US1 flattened JSONL stream and its completion marker. The Story 3…, validate(), build_battery_counted(), build_track_occluded(), build_track_update(), _ensure_finite(), _envelope() (+18 more)

### Community 65 - "test_track_keeps_operational_identity_across_temporary_occlusion"
Cohesion: 0.38
Nodes (5): Detection and persistent tracking adapters., _detection(), _meta(), FrameMeta, test_track_keeps_operational_identity_across_temporary_occlusion()

### Community 66 - "contracts/events.py"
Cohesion: 0.25
Nodes (18): _error(), _EventStreamValidator, _is_finite_number(), iter_validated_jsonl(), load_event_stream(), Any, Path, Strict validation for the versioned battery event contract. This module is… (+10 more)

### Community 67 - "hackathon_reply/__init__.py"
Cohesion: 0.33
Nodes (4): main(), US1 battery-volume processing core., Keep the package entry point available until the CLI runner is added., test_paired_comparison_reports_count_and_relative_volume_gaps()

### Community 68 - "fixture_root"
Cohesion: 0.40
Nodes (4): fixture_root(), fixture, Path, Repository-wide fixtures shared by contract and integration tests.

### Community 69 - "matcher.py"
Cohesion: 0.24
Nodes (15): estimate_from_measurement(), match_candidates(), US1FrameMeasurement, Probabilistic catalog matching and catalog-derived volume uncertainty., Rank plausible US1 catalog dimensions without collapsing ambiguity., Convert a validated US1 measurement posterior into volume., Stateful US1 matcher that preserves the best posterior per track., _relative_dimension_error() (+7 more)

### Community 70 - "EventValidationError"
Cohesion: 0.23
Nodes (12): EventValidationError, ValueError, A structured event or JSONL stream validation failure., counted_event(), occluded_event(), test_compatibility_examples_keep_v1_strict_until_approved_contract_update(), test_counted_event_requires_positive_frozen_volume_and_lot_tally(), test_occlusion_requires_transition_and_fixed_state() (+4 more)

### Community 71 - "hackathon_reply/replay.py"
Cohesion: 0.22
Nodes (12): Exception, CanonicalReplayResult, Path, Deterministic replay utilities for the Story 2 and Story 3 acceptance paths., A Story 3 event replay input or summary violates its contract., Semantic result for a validated Story 3 canonical JSONL stream., Replay and validate a Story 3 canonical event stream., Replay a Story 3 stream to canonical JSONL and normalized result JSON. (+4 more)

### Community 72 - "Implementation Plan: User Story 3 — Consume Stable, Honest Events"
Cohesion: 0.17
Nodes (12): Complexity Tracking, Constitution Check, Constitution Check — Post-Design, Documentation (this feature), Implementation Boundaries for Later Tasks, Implementation Plan: User Story 3 — Consume Stable, Honest Events, Phase 0: Research Complete, Phase 1: Design Complete (+4 more)

### Community 73 - "Contract: Battery Domain Events"
Cohesion: 0.20
Nodes (10): `BATTERY_COUNTED`, Boundary, Canonical serialization, Common fixed envelope, Contract: Battery Domain Events, Fixed event keys, Minimal examples, Ordering and compatibility (+2 more)

### Community 74 - "Research: User Story 3 — Consume Stable, Honest Events"
Cohesion: 0.20
Nodes (10): Decision 1: Canonical event serialization, Decision 2: Event versioning, Decision 3: Operational diagnostics boundary, Decision 4: Track-update cadence, Decision 5: Fixed event shapes and missing values, Decision 6: Runtime and test boundary, Decision 7: Occlusion and deterministic-summary semantics, Decision 8: Frame ordering without a new v1 field (+2 more)

### Community 76 - "Quickstart: User Story 3 Event Handoff and Replay"
Cohesion: 0.22
Nodes (9): 1. Install the project test environment, 2. Run focused contract and replay tests, 3. Validate the canonical JSONL fixture, 4. Replay twice and compare canonical results, 5. Exercise the consumer boundary, Failure checks, Handoff checklist, Prerequisites (+1 more)

### Community 77 - ".update"
Cohesion: 0.32
Nodes (6): _credible_interval(), _posterior_quantile(), CatalogCandidate, FrameMeasurement, _softmax(), _squared_error()

### Community 78 - "ReplayDetector"
Cohesion: 0.29
Nodes (6): DetectorError, ReplayFrame, ValueError, Raised when a detector adapter returns an invalid domain result., Read cached detections by zero-based frame identifier., ReplayDetector

### Community 79 - "contract/conftest.py"
Cohesion: 0.32
Nodes (7): canonical_json(), fixture_root(), Any, fixture, Path, Shared helpers for published-contract tests., read_json()

### Community 80 - "🔋 Trilha C: Visão Computacional para Reciclagem (Detecção de Baterias)"
Cohesion: 0.29
Nodes (6): 📋 Checklist de Interface e Entregas - Hackathon Reply 2026, 🌟 Diferenciais da Interface (Pontuação de "Aplicação Real"), 📦 Entregáveis da Equipe (Para o Repositório), 🚫 Fora de Escopo (Não percam tempo com isso), 🟢 Requisitos Obrigatórios da Interface (MVP), 🔋 Trilha C: Visão Computacional para Reciclagem (Detecção de Baterias)

### Community 81 - "Data Model: User Story 3 Event Boundary"
Cohesion: 0.29
Nodes (7): 1. Common domain-event envelope, 2. Track update, 3. Track occlusion, 4. Battery counted, 5. Run-summary/diagnostics record, 6. Relationships and invariants, Data Model: User Story 3 Event Boundary

### Community 82 - "Specification Quality Checklist: Backend Model Core"
Cohesion: 0.33
Nodes (5): Content Quality, Feature Readiness, Notes, Requirement Completeness, Specification Quality Checklist: Backend Model Core

### Community 83 - "User Scenarios & Testing *(mandatory)*"
Cohesion: 0.33
Nodes (6): Edge Cases, User Scenarios & Testing *(mandatory)*, User Story 1 - Produce a Trustworthy Lot Result (Priority: P1), User Story 2 - Count Each Battery Exactly Once (Priority: P2), User Story 3 - Consume Stable, Honest Events (Priority: P3), User Story 4 - Audit Measurement and Resolution Evidence (Priority: P4)

### Community 84 - "test_user_story3_replay.py"
Cohesion: 0.53
Nodes (5): Path, test_fixture_contains_per_frame_updates_and_transition_occlusion(), test_invalid_fixture_corpus_fails_closed(), test_replay_preserves_canonical_order_and_is_deterministic(), test_replay_reports_first_invalid_line()

### Community 85 - "Contract: Run Summary and Diagnostics"
Cohesion: 0.40
Nodes (5): Contract: Run Summary and Diagnostics, Example, Fixed keys, Invariants, Purpose and boundary

### Community 86 - "Contract: User Story 3 Replay"
Cohesion: 0.40
Nodes (5): Acceptance fixtures, Behavior, Consumer boundary, Contract: User Story 3 Replay, Inputs

### Community 88 - "test_detector.py"
Cohesion: 0.60
Nodes (4): _meta(), FrameMeta, test_empty_detector_is_a_valid_boundary_adapter(), test_replay_detector_returns_domain_detections_and_empty_frames()

### Community 89 - "main"
Cohesion: 0.67
Nodes (3): build_parser(), main(), ArgumentParser

### Community 90 - "validate_events.py"
Cohesion: 0.67
Nodes (3): build_parser(), main(), ArgumentParser

### Community 92 - "TrackState"
Cohesion: 0.67
Nodes (3): Enum, str, TrackState

## Knowledge Gaps
- **236 isolated node(s):** `AWS.sh script`, `hackathon-reply`, `_NormalizedRow`, `I. Architecture-First, Contract-Driven Boundaries`, `II. SOLID and Clean Code` (+231 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `IoUTracker` connect `IoUTracker` to `counter.py`, `ReplayRunner`, `hackathon_reply/replay.py`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `ExactlyOnceEventSink` connect `ExactlyOnceEventSink` to `run_replay`, `pipeline.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Why does `run_replay()` connect `run_replay` to `FrameMeta`, `matcher.py`, `ExactlyOnceEventSink`, `ReplayDetector`, `loader.py`, `measurement.py`, `pipeline.py`, `domain.py`, `TrackManager`, `CountGate`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `run_replay()` (e.g. with `CatalogEntry` and `RunSummary`) actually correct?**
  _`run_replay()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `IoUTracker` (e.g. with `build_runner()` and `ReplayRunner`) actually correct?**
  _`IoUTracker` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `TrackManager` (e.g. with `Detection` and `FrameMeta`) actually correct?**
  _`TrackManager` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `FrameMeta` (e.g. with `crossed_gate_pixels()` and `normalized_centroid()`) actually correct?**
  _`FrameMeta` has 12 INFERRED edges - model-reasoned connections that need verification._