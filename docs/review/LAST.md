Да. Я свёл свежий critic brief, два новых разгромных review, deep research и твою сводку по уже закрытому 7-приоритетному tranche и выжал из этого только те решения, которые реально стоят следующего roadmap. Коротко: вы уже закрыли прошлую фазу hardening честно и без роста machinery, но новый спор теперь уже другой — не “работает ли kernel вообще”, а “может ли он стать достаточно дешёвым, достаточно runtime-trustworthy и достаточно мало зависящим от поведения агента, чтобы выигрывать хотя бы на одном bounded everyday class, а не только на handoff/continuation wedge”. Это прямо сходится во всех новых материалах.

Что уже не надо заново “чинить”

Это важно зафиксировать, чтобы не бегать по кругу. Прошлый tranche уже закрыл:

cheapening default proof path;
proof-independence hardening;
restore matrix as honest local coverage;
shell compression;
evidence ownership split;
anti-overfit task-class scoping;
fresh unseen validation.
И всё это сделано без новых semantic sections, continuation families и runtime artifact surfaces. Значит новый roadmap не должен повторять прошлую фазу под новыми словами.
Мой итог: что действительно стоит взять в новый roadmap
Priority 1 — Everyday economics как главный enemy metric

Самый сильный и согласованный удар критиков: everyday class всё ещё baseline-favorable overall. Да, теперь есть один repeatable low-drag winner, но класс в целом всё ещё не выигран. Это означает, что главный remaining risk уже не в correctness, а в structural fixed cost самого control stack. Если после нескольких correct cheapening tranches класс всё ещё проигрывает, значит проблема может быть уже не seam-specific, а structural.

Что из этого следует

Следующий roadmap должен ставить не “ещё один seam fix”, а одну жёсткую цель:

сделать один bounded everyday class boringly repeatable and boringly cheap.

Не искать второй winner, а стабилизировать первый:

same host
same agent lane
same task family
same invocation family
low variance
near-one-pass or one-pass behavior.
Конкретное решение

Добавить fixed control mass accounting:

обязательные mental steps;
trust-bearing artifacts;
реальные operator-visible actions;
checks per accepted closure;
restore/repair count;
“got lost” moments.
Не как ещё один красивый score, а как основной cost metric everyday lane. Это критики прямо требуют, а deep research усиливает это как главный вопрос продукта: сколько false closure вы убираете на единицу attention tax.
Priority 2 — Behavioral cheapening, а не просто kernel cheapening

Очень сильный и недооценённый вывод из критики: часть remaining tax теперь сидит не в ядре, а в том, что агент по привычке продолжает делать лишнюю работу. Значит следующий враг — не ещё одна proof rule, а зависимость от agent habit formation. Иначе вы получите иллюзию прогресса: “kernel стал дешевле”, хотя по факту “агент просто лучше воспитан”.

Что из этого следует

Нужно отдельно мерить:

kernel cheapness
behavior cheapness

И уменьшать разрыв между ними.

Конкретное решение

В следующем tranche добивать не abstract proof, а default behavior:

если trust уже закрыт через final_result + runtime-backed verification, агент по умолчанию не пишет readback, scenario_proof, cleanup_status;
эти surfaces остаются fallback-only, но должны исчезать не только в shell language, а и в natural agent behavior;
prompt bridge и starter surfaces должны направлять именно в final_result-first cheap path.

Это сейчас один из самых сильных practical moves.

Priority 3 — Proof independence attack pack, не новые heuristic sections

Proof independence стала сильнее, но все новые review повторяют одно и то же: она всё ещё corpus-bounded. Текущие strict lanes уже режут thin labeled self-description, placeholder outputs и exit-code-only observations, но критики справедливо спрашивают: это уже принцип или всё ещё хорошо закрытый набор последних observed mistakes?

Что из этого следует

Следующий шаг — не добавлять ещё семантические секции.
Нужно делать:

unseen task-shape attacks;
structured-but-thin proof that should fail;
domain-local weak proof that should fail;
terse concrete runtime evidence that should pass;
runtime-backed corroboration that must dominate prose;
unknown task classes that must stay out of hostile policy by default.
Что брать из deep research

Вот здесь есть реальная полезность:

mutation/adversarial strengthening
targeted property-based tests
proof attack pack
Это как раз усиливает самый уязвимый remaining seam без роста shell or artifact mass. Но важно: не как broad framework, а как focused attack pack на measured proof-sensitive lanes.
Priority 4 — Restore как explicitly narrow but dependable primitive

Restore стал матрично честнее и сильнее, но все материалы очень едины: restore ещё не mature enough to carry broad product story. Сейчас правильная формула не “restore уже зрел”, а “restore стал честнее, локально покрыт и больше не врёт на covered families”. Это хороший прогресс, но не повод раздувать promise.

Что из этого следует

Следующий roadmap должен не “делать restore ещё умнее”, а:

удержать explicit matrix;
мерить operator weight per family;
честно разделить:
dependable
honest fail
limited preview only
Что реально стоит делать

Из deep research тут полезна одна идея:

не full evidence graph rewrite,
а dependency / invalidation semantics only where restore and continuation need them.
Иными словами: не превращать proof bundle в философский DAG прямо сейчас, а использовать его минимально ради restore-aware invalidation и cheaper retry/repair. Это действительно может помочь economics, если делать узко.
Priority 5 — Shell pruning до реально thin first-loop

Shell уже стал тоньше, но критика справедлива: он всё ещё может быть thinner in wording than in felt weight. Значит следующий ход — не naming polish, а literally visible surface deletion.

Что из этого следует

Каждая видимая команда должна отвечать на один вопрос:

какой конкретный saved confusion или saved damage исчезнет, если она останется visible?

Если ответа нет — прятать.

Практически

Следующий tranche должен brutally classify:

first-loop only
advanced only
compatibility only
should disappear

Особенно пересматривать:

repair-step
retry
confirm-restore
telemetry export
bug-packet
session-export
Не перепрятать глубже, а убрать из operator-visible path, если они не уменьшают trust tax на первом контуре.
Priority 6 — Fresh external critic pass именно по current cheapened branch

Evidence hygiene как process rule — сильный шаг, но критики правы: это ещё не делает evidence base независимой. Сейчас проект всё ещё partly self-curated, и это нормальный, но опасный remaining risk. Значит следующий сильный move — не ещё одна synthesis note, а свежий hostile external pass по уже cheapened and evidence-gated branch.

Какой именно

Не общий “что думаешь о проекте”, а три вопроса:

still too heavy on everyday lane?
still smells self-issued on proof?
restore/handoff worth the control mass or not?

Это даст больше product truth, чем ещё одна внутренняя итерация docs/logic.

Priority 7 — Handoff/continuation усиливать, но только без machinery growth

Handoff/continuation honesty — strongest wedge, strongest positive signal, и это уже выглядит earned. Но это же и самое опасное место для соблазна “ещё немножко continuation machinery”. Этого делать нельзя. Всё, что усиливает handoff, должно усиливать именно non-author operability on uglier live states, а не богатство packet/receipt family.

Что реально стоит делать

Из всей массы здесь самое ценное:

ugly second-operator contours;
blind/non-author handoff;
continuation manifest only if it materially lowers ambiguity;
explicit pending obligations + invalidation map for receiver.
Это полезно. А вот новые continuation families ради completeness — нет.
Что из deep research реально брать, а что не лоббировать
Брать
1. Task-class evidence contracts

Это сильная идея и очень хорошо ложится на вашу текущую реальность:

trivial lane не должна нести тот же rigor tax;
consequential lane может нести больше.
Это не новая вселенная, а хорошая policy layer над текущим closure model.
2. Change-impact invalidation / selective reruns

Вот это реально сильная идея.
Если хотите улучшать everyday economics без weakening truth, это, возможно, лучший следующий технический ход:

не доказывать всё заново;
доказывать заново только то, что реально стало stale.
3. Proof attack pack with mutation/adversarial strengthening

Очень качественное предложение.
Это прямой ответ на corpus-local proof independence. И оно усиливает продукт без surface growth.

4. False-closure budget by lane

Но не как runtime magic.
Как governance/evaluation discipline — да.
Как новый live kernel behavior — пока нет.

Брать только как микро-прототип, а не roadmap rewrite
5. Typed evidence graph / closure certificate

Это потенциально сильная архитектурная идея. Но если её брать, то только на одном bounded class как A/B prototype. Не в виде full rewrite proof bundle.
Иначе вы снова рискуете уйти в elegant machinery раньше product proof.

Не лоббировать сейчас
universal confidence score;
literal sigma-style gate;
OpenTelemetry как новая большая тема;
Nix/devcontainers universal;
DSSE/signing;
broad runtime monitors everywhere;
full evidence graph rewrite across kernel.
Это всё либо преждевременно, либо даёт больше architecture mass, чем текущей value.
Лучшие решения, если выжать всё до сути

Если отбросить все средние и сомнительные идеи, я бы оставил 7 сильных решений:

Сделать один everyday class boringly repeatable and boringly cheap
Убрать behavioral tax по умолчанию: optional prose must stop appearing naturally
Собрать proof attack pack на unseen shapes вместо роста semantic grid
Добавить change-impact invalidation / selective reruns для cheaper retry/check
Удержать restore как narrow dependable primitive, не раздувая claim
Сжать visible shell до реально thin first-loop, а не thin wording
Прогнать hostile external critic pass именно по cheapened current branch

Это, на мой взгляд, лучший следующий roadmap из всей массы.

Что я бы сознательно не делал в новом roadmap
не broadening product story;
не новые semantic sections;
не новые continuation families;
не большие refactor/repackaging moves;
не giant assurance-graph rewrite;
не confidence engine;
не “платформизацию” handoff/restore.
Потому что вся свежая критика очень ясна: самый большой риск теперь не в том, что Synrail недостаточно умный, а в том, что он может остаться слишком тяжёлым для everyday value.
Мой финальный вердикт

Сейчас лучший следующий roadmap — это не “ещё одна волна hardening вообще”, а:

доказать, что cheapened kernel может быть достаточно дешёвым и достаточно независимым от поведения агента хотя бы на одном repeatable everyday class, не ломая strongest wedge — handoff/continuation honesty.

Это и будет следующая по-настоящему важная итерация.