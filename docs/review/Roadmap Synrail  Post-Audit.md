Технический Roadmap Synrail — Post-Audit (v2, скорректированный)

  Основание: аудит Opus 4.6 от 2026-04-23 + авторская калибровка + коррекции по execution plan
  Принцип: каждый пункт привязан к конкретным файлам, строкам и дефектам. Сначала trust truthfulness, потом evidence breadth, потом refactor.

  ---
  Фаза A — Trust gap closer + tiny cleanup

  Самый большой quality jump за минимальное время. Все пункты независимы, можно делать параллельно.

  ---
  T0.1 — Verification re-execution в bundle (MVP)

  Проблема: synrail_bundle_v0.py:343-378 проверяет verification_command и verification_result на непустоту, но никогда не переисполняет команду. Claim
  "runtime-backed trust" не подкреплён.

  Что делать:

  В synrail_bundle_v0.py, после строки 347 (has_verification = bool(verification_command and verification_result)), добавить опциональный re-execution path:

  1. Парсить verification_command через shlex.split() — никакого shell=True
  2. Whitelist только прямые бинарники: grep, cat, head, tail, git, python3
  3. Для python3 — только python3 -c "..." с length cap (~500 chars)
  4. Без bash -c — это security/consistency seam, а не fix
  5. cwd = project root, timeout=10s, stdout cap 4KB
  6. Сравнить stdout с verification_result (exact match или contains)
  7. Записать в bundle новое поле:
  "verification_recheck": {
    "executed": true,
    "command_allowed": true,
    "matched": true,
    "stdout_snippet": "...",
    "skip_reason": ""
  }
  8. Если команда не в whitelist: executed: false, skip_reason: "command_not_in_allowlist" — не блокировать, просто записать
  9. Scope: только diff_provenance record, не prose surfaces

  Файлы: synrail_bundle_v0.py (основная работа)
  Тесты в test_truth_regressions.py:
  - recheck matches → verification_recheck.matched == true
  - recheck fails → verification_recheck.matched == false
  - command not in whitelist → executed == false, skip_reason set
  - timeout → executed == true, matched == false, skip_reason == "timeout"

  ---
  T0.3 — Closure awareness of recheck

  Проблема: Closure (synrail_closure_v0.py:55-164) не знает о результатах re-verification.

  Что делать:

  В synrail_closure_v0.py, после строки 134 (bundle status check), добавить новый blocking path:

  recheck = bundle.get("verification_recheck", {})
  if recheck.get("executed") and not recheck.get("matched"):
      verdict["blocking_reason"] = "VERIFICATION_RECHECK_FAILED"
      verdict["next_allowed_transition"] = "PROOF_BUNDLE_REPAIR"
      verdict["narrow_next_safe_step"] = "re-run the verification and update diff_provenance"
      return verdict

  Если recheck не выполнялся (command not in whitelist) — не блокировать. Блокировать только при executed == True и matched == False.

  Файлы: synrail_closure_v0.py (одна новая проверка)
  Тесты: pass case, block case, skip case (not executed)

  ---
  T1.1 — Doctor override marking

  Проблема: synrail_doctor_v1.py — 5 gate'ов имеют bypass-флаги (строки 179, 208, 222, ~312, ~353). При override record записывает PASS без маркировки.

  Что делать:

  В каждом probe_* при использовании bypass-флага — сохранять status "PASS", но добавлять поля:

  # Вместо:
  return gate("PASS", "execution surface is acceptable")

  # Делать:
  return gate("PASS", "execution surface is acceptable", override=True,
              override_reason="operator bypass via --clean-surface")

  Конкретно расширить gate() helper, чтобы он принимал optional override: bool = False и override_reason: str = "", и пробрасывал их в dict.

  5 мест изменения:
  - probe_clean_execution_surface — строка 182
  - probe_artifact_viability — строка 209
  - probe_helper_integrity — строка 223
  - probe_credential_surface — строка ~312
  - probe_prompt_task_identity — строка ~353

  В build_record (строка 397-406): собирать override_gates: list[str] из gate'ов, где override == True. Записывать в doctor record.

  Почему не PASS_OVERRIDE как новый status: Существующие consumers знают только PASS/FAIL/NOT_APPLICABLE. Новый status расползётся и сломает ветки. PASS +
  override: true ломает ноль существующего кода.

  Файлы: synrail_doctor_v1.py (gate helper + 5 probe + build_record)
  Тесты: doctor с override → override_gates непустой; doctor без override → override_gates пустой

  ---
  T5.3 — hotspot() empty-input guard

  Проблема: synrail_cost_of_control_v0.py:45 — max(records, ...) падает на пустой последовательности.

  Что делать:

  def hotspot(records: list[dict], key: str) -> dict:
      if not records:
          return {}
      winner = max(records, key=lambda record: record["economics_summary"].get(key, 0))

  Одна строка, ноль риска.

  Файлы: synrail_cost_of_control_v0.py:45

  ---
  T5.0 — Tiny integrity cleanup

  Дешёвые wins без риска:

  1. Убрать duplicate build_parser() из synrail_thin_output_v0.py, если найден
  2. Убрать 21 blank line в synrail_thin_output_v0.py:205-226 (deleted code оставило пустоту)
  3. Проверить и убрать другие phantom/drift seams, если найдутся при прогоне фазы A

  Файлы: synrail_thin_output_v0.py

  ---
  Оценка фазы A: 3-5 дней при фокусированной работе. T0.1 — самый тяжёлый кусок. Остальное — часы.

  ---
  Фаза B — Integrity hardening + restore safety

  После Фазы A: trust path уже реальнее, теперь усиливаем integrity и убираем destructive restore.

  ---
  T0.2 — Last-known hash integrity

  Проблема: final_result.json легитимно меняется по workflow. initial_artifact_hash — неправильная модель.

  Что делать:

  1. В state.json хранить last_known_final_result_hash: str
  2. Обновлять его только после Synrail-controlled writes:
    - После synrail start (initial creation)
    - После synrail check (если check перезаписывает artifacts)
    - После synrail repair-step (если repair обновляет final_result)
  3. При synrail check / closure: пересчитать текущий hash, сравнить с last_known_final_result_hash
  4. Если mismatch:
    - Записать artifact_integrity_warning: true в bundle
    - Не блокировать closure сразу — но записать в verdict closure_warnings: ["artifact_modified_outside_workflow"]
    - В будущем (strict mode) — можно блокировать

  Реализация: synrail_cli_v0.py:1121 уже имеет file_sha256(). Добавить update_last_known_hash() и check_artifact_integrity().

  Файлы: synrail_cli_v0.py (hash tracking), synrail_bundle_v0.py (integrity check), synrail_closure_v0.py (warning)

  ---
  T1.2 — Closure warnings for doctor overrides

  Проблема: Closure не знает, что доктор прошёл через bypass.

  Что делать:

  В synrail_closure_v0.py, строка 111 (if state["doctor"]["status"] != "PASS"): добавить проверку.

  Начинать с soft mode (warnings, не blocks):

  doctor_overrides = state["doctor"].get("override_gates", [])
  if doctor_overrides:
      verdict["closure_warnings"] = verdict.get("closure_warnings", []) + [
          f"doctor_override_present: {', '.join(doctor_overrides)}"
      ]

  Не блокировать closure при наличии overrides — только маркировать. Переход к strict mode (blocking) — отдельное решение после стабилизации.

  Файлы: synrail_closure_v0.py (одна проверка), synrail_spine_v0.py (проброс override_gates в state через apply_record_to_state в synrail_doctor_v1.py:435)

  ---
  T2.1 — Atomic file-copy restore

  Проблема: synrail_checkpoint_v0.py:270-293 — _file_copy_restore удаляет файлы проекта (строки 277-283), затем копирует из snapshot. Прерывание = разрушенный
  workspace.

  Что делать:

  Заменить _file_copy_restore на atomic sequence:

  1. staging_dir = project_root.parent / f".synrail_restore_staging_{uuid4().hex[:8]}"
  2. Скопировать snapshot → staging_dir
  3. backup_dir = project_root.parent / f".synrail_restore_backup_{uuid4().hex[:8]}"
  4. Переименовать текущий content → backup_dir  (os.rename — atomic на одном fs)
  5. Переименовать staging_dir content → project_root
  6. Удалить backup_dir
  7. При любой ошибке на шагах 4-5: восстановить backup → project_root, удалить staging

  T2.2 (git restore rollback) — отдельный nice-to-have, не в этой фазе. Git stash rollback — скользкая зона. File-copy restore покрывает самый destructive
  path. Git restore остаётся as-is пока не стабилизируется T2.1.

  CLI: при restore без --preview, если workspace_restore_destructive == true, печатать warning и требовать --confirm

  Файлы: synrail_checkpoint_v0.py (main change), synrail_cli_v0.py (confirm flow)
  Тесты в test_gate_units.py:
  - restore success + verify backup cleaned up
  - simulated mid-copy failure + verify rollback restores original
  - restore с --preview не меняет workspace

  ---
  Оценка фазы B: 3-5 дней. T2.1 — самый сложный кусок (atomic rename + rollback logic).

  ---
  Фаза C — Evidence honesty + instrumentation

  Критический порядок: сначала честность evidence, потом расширение benchmark.

  ---
  T4.1 — Provenance marking в фикстурах и harness

  Проблема: Все benchmark-числа — ручные оценки без маркировки. Невозможно отличить curated estimate от эмпирических данных.

  Что делать:

  1. В каждый comparison input в fixtures/ добавить обязательное поле:
  "data_provenance": "curated_local_estimate"
  1. Допустимые значения: curated_local_estimate, pressure_synthetic, external_empirical
  2. В synrail_baseline_harness_v1.py (~строка 44): при сборке economics summary, пробрасывать data_provenance из обоих inputs в output record
  3. В synrail_cost_of_control_v0.py: при агрегации записывать provenance_mix: ["curated_local_estimate"] — set всех встреченных provenance types
  4. В docs (docs/core/REPEATABLE_EVERYDAY_BENCHMARK_001.md, docs/core/BASELINE_HARNESS_001.md): явно указать, что текущие данные — curated_local_estimate, не
  эмпирические

  Файлы: все comparison input fixtures, synrail_baseline_harness_v1.py, synrail_cost_of_control_v0.py, docs

  ---
  T4.4 — Instrumentation для будущих эмпирических данных

  Что делать:

  1. В synrail_cli_v0.py при synrail start: записывать start_timestamp_utc в state
  2. При accepted closure: записывать closure_timestamp_utc
  3. При каждом synrail check: инкрементировать check_count в state
  4. Записывать в telemetry / session replay

  Не менять harness и не менять benchmark logic. Просто накапливать данные, чтобы в будущем можно было калибровать operator_minutes и checks_per_closure из
  реальных сессий вместо ручных оценок.

  Файлы: synrail_cli_v0.py (start + check + closure handlers)

  ---
  T4.2 — Focused family expansion до N >= 5

  Проблема: Focused class win на N=2 (EVERYDAY_LOCAL_005, EVERYDAY_LOCAL_006). Статистически бессмысленно.

  Что делать:

  Добавить 3+ новых сценария в fixtures/small_template_text_fix_benchmark_pack_001.json:

  1. Slightly uglier variant — multi-line template fix (2-3 строки вместо 1)
  2. Tool-heavy variant — template fix + grep verification required
  3. Less cooperative agent variant — extra prose generated, then cleaned up (higher behavioral_control_tax)

  Все новые записи должны иметь "data_provenance": "curated_local_estimate" (честно). Обновить tests/test_small_template_text_fix_benchmark_pack.py.

  Важно: N >= 5 curated — это не почти внешнее доказательство. Это всё ещё curated_local_estimate. Не позволять расширению звучать как transition к empirical.

  Файлы: fixtures, tests

  ---
  Оценка фазы C: 3-4 дня. T4.1 — самый широкий по количеству файлов (все fixtures), но каждое изменение тривиальное.

  ---
  Фаза D — Closure state semantics + proof guard broadening

  ---
  T3 — CLOSURE_REJECTED реализация

  Проблема: build_verdict() (строки 55-164) не генерирует REJECTED. Но CLOSURE_REJECTED обрабатывается в spine, thin_output, repair_handoff, CLI и 8 тестах.

  Семантика (строгая):

  REJECTED = "мы попытались закрыть и явно отказали из-за hard contradiction":
  - verification_recheck executed и failed (T0.1/T0.3)
  - artifact_integrity_failed (T0.2, в будущем strict mode)
  - Возможно: strict doctor override violation (если T1 перейдёт в strict mode)

  REJECTED не для:
  - Обычный non-green (чего-то не хватает) — для этого есть CLAIMED_NOT_ACCEPTED
  - Обычный progress state — для этого есть blocking_reason

  Реализация:

  В synrail_closure_v0.py:build_verdict(), перед финальным ACCEPTED:

  # Hard contradiction checks
  recheck = bundle.get("verification_recheck", {})
  if recheck.get("executed") and not recheck.get("matched"):
      verdict["closure_status"] = "REJECTED"
      verdict["blocking_reason"] = "VERIFICATION_RECHECK_FAILED"
      ...
      return verdict

  Теперь spine (строка 1075-1076) реально получит REJECTED от closure, и обработка перестанет быть dead code.

  Файлы: synrail_closure_v0.py, тесты: test_truth_regressions.py, test_gate_units.py, test_deploy_gate.py

  ---
  T6.1 — Broader observation guard в shadow mode

  Проблема: Strict guard только для 5 hardcoded task classes (synrail_bundle_v0.py:478-484). Передача task_class="feature_work" полностью отключает
  anti-narrative checks.

  Что делать (shadow mode first):

  1. В strict_observation_guard_enabled (строка 910): не менять return value
  2. Добавить параллельную функцию broad_observation_guard_would_fire(task_class, line) — вычисляет, сработал бы ли guard при broader default
  3. В bundle: записывать shadow_observation_guard_results: {would_block: bool, lines_flagged: int} — без блокировки
  4. Мониторить false positive rate на текущих тестах
  5. Переход к blocking default — отдельное решение после shadow-периода

  Файлы: synrail_bundle_v0.py

  ---
  T6.2 — Proof attack pack expansion

  Что делать:

  В test_truth_regressions.py добавить 10+ attack cases с synonym-обходами текущих фразовых списков:

  - "Verified: functioning properly" (нет в vacuous list)
  - "Confirmed: operational" (нет в vacuous list)
  - "Observed: it processes correctly" (synonym bypass)
  - Thin structured self-description с числом, но без literal evidence
  - Proof text с padding-словами для снижения word overlap ниже 70%

  Фиксить bundle heuristics по мере обнаружения пробоев. Каждый fix — отдельный commit с конкретным attack case.

  Файлы: test_truth_regressions.py, synrail_bundle_v0.py (fixes)

  ---
  Оценка фазы D: 3-4 дня. T3 зависит от T0.1/T0.3. T6.1 и T6.2 независимы.

  ---
  Фаза E — Structural tech-debt

  Самая дорогая по времени, самая низкая по urgency. Делать только после стабилизации фаз A-D.

  ---
  T5.1 — Shared JSON IO module

  Что делать:

  1. Создать tools/reference/synrail_io_v0.py:
  def load_json(path: Path) -> dict: ...
  def save_json(path: Path, payload: dict) -> None: ...
  def load_json_if_valid(path: Path | None) -> tuple[bool, dict]: ...
  def save_json_safe(path: Path, payload: dict) -> None:
      """save_json with mkdir — for checkpoint and similar."""
      path.parent.mkdir(parents=True, exist_ok=True)
      save_json(path, payload)
  2. Заменить 48 определений на import
  3. Тест: полный suite (492 теста) должен пройти без изменений

  Оценка: Это более дорогой refactor, чем кажется — 48+ файлов, каждый с try/except import fallback pattern. Лучше делать в 2-3 batch'а, а не одним commit.

  ---
  T5.2 — Policy renderer dedup

  Что делать:

  Параметризировать три функции в synrail_cli_v0.py:338-617:

  def render_policy_markdown(
      agent_type: Literal["agents", "gemini", "claude"],
      *,
      artifact_root: str,
      command: str,
      ...
  ) -> str:

  Per-agent различия (header format, orientation lines, workspace notes) → параметры или маленькие per-agent helper'ы.

  ---
  T5.4 — Первый split CLI

  Что делать:

  Извлечь command handlers (cmd_start, cmd_check, cmd_restore, cmd_orchestrate, etc.) в tools/reference/synrail_commands_v0.py. Оставить argparse routing и
  shared utilities в synrail_cli_v0.py.

  Это дорогой и рискованный refactor. CLI handler'ы тесно переплетены через shared state (alpha_root, project_root, args forwarding). Нужна аккуратная работа
  по extraction boundaries.

  Рекомендация: делать инкрементально. Первый cut — извлечь 3-4 самых изолированных команды (install, telemetry export, bug-packet, session-export). Оставить
  cmd_check и cmd_start в монолите до следующего раунда.

  ---
  Оценка фазы E: 5-8 дней. T5.1 — 2-3 дня (48 файлов). T5.4 — 2-3 дня (extraction boundaries). T5.2 — 1 день.

  ---
  Сводная таблица

  ┌──────┬──────────────────────────────┬────────────────────────┬──────────┬──────────────────────────────────────┐
  │ Фаза │            Пункты            │      Зависимости       │  Оценка  │               Что даёт               │
  ├──────┼──────────────────────────────┼────────────────────────┼──────────┼──────────────────────────────────────┤
  │ A    │ T0.1, T0.3, T1.1, T5.3, T5.0 │ Нет                    │ 3-5 дней │ Trust path становится реальным       │
  ├──────┼──────────────────────────────┼────────────────────────┼──────────┼──────────────────────────────────────┤
  │ B    │ T0.2, T1.2, T2.1             │ A                      │ 3-5 дней │ Integrity + safe restore             │
  ├──────┼──────────────────────────────┼────────────────────────┼──────────┼──────────────────────────────────────┤
  │ C    │ T4.1, T4.4, T4.2             │ Нет (но лучше после A) │ 3-4 дня  │ Evidence honesty                     │
  ├──────┼──────────────────────────────┼────────────────────────┼──────────┼──────────────────────────────────────┤
  │ D    │ T3, T6.1, T6.2               │ T0.1/T0.3 для T3       │ 3-4 дня  │ Closure semantics + proof broadening │
  ├──────┼──────────────────────────────┼────────────────────────┼──────────┼──────────────────────────────────────┤
  │ E    │ T5.1, T5.2, T5.4             │ Нет                    │ 5-8 дней │ Tech-debt reduction                  │
  └──────┴──────────────────────────────┴────────────────────────┴──────────┴──────────────────────────────────────┘

  Общая реалистичная оценка:
  - High-leverage ядро (A + B + C): ~2 недели
  - Полный roadmap (A → E): ~3-4 недели