# analiz_svodok

## Healthcheck
Эндпоинт `/health` возвращает JSON со статусом БД, Redis и конфигурации семантической модели. Код ответа 200/503 зависит от доступности критичных подсистем.

## Offline semantic model cache
Для офлайн-режима можно:
- задать `SEMANTIC_MODEL_CACHE_DIR` для кэша модели;
- включить `SEMANTIC_MODEL_LOCAL_ONLY=true`, чтобы запретить сетевые обращения;
- использовать стандартные переменные `HF_HOME`, `TRANSFORMERS_CACHE`, `SENTENCE_TRANSFORMERS_HOME`.

## Закрытый контур (Docker)
Подробная инструкция по развёртыванию в закрытом контуре, обновлениям и smoke-прогону
находится в документе [docs/CLOSED_CONTOUR_DEPLOY.md](docs/CLOSED_CONTOUR_DEPLOY.md).

Коротко: для closed контура используйте `scripts/docker/make_release_bundle.sh`; тяжёлая модель не используется.
