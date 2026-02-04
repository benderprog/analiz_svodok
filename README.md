# analiz_svodok

## Healthcheck
Эндпоинт `/health` возвращает JSON со статусом БД, Redis и конфигурации семантической модели. Код ответа 200/503 зависит от доступности критичных подсистем.

## Offline semantic model cache
Для офлайн-режима можно:
- задать `SEMANTIC_MODEL_CACHE_DIR` для кэша модели;
- включить `SEMANTIC_MODEL_LOCAL_ONLY=true`, чтобы запретить сетевые обращения;
- при необходимости задать `SEMANTIC_MODEL_PATH` на локальный снапшот;
- использовать стандартные переменные `HF_HOME`, `TRANSFORMERS_CACHE`, `SENTENCE_TRANSFORMERS_HOME`.

## Документация
- [docs/INSTALL_OPEN.md](docs/INSTALL_OPEN.md) — сборка релиза в открытом контуре.
- [docs/INSTALL_CLOSED.md](docs/INSTALL_CLOSED.md) — запуск в закрытом контуре без интернета.
- [docs/USAGE.md](docs/USAGE.md) — инструкция оператора.
