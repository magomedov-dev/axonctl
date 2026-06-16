# Вклад в axonctl

[English](CONTRIBUTING.md) · **Русский**

Спасибо за вклад! Это руководство описывает локальную настройку, запуск
проверок и git-процесс.

## Тулчейн — всё живёт в `.tooling/`

Чтобы не засорять твою машину, **весь** инструментарий (uv, интерпретатор
Python, dev-виртуальное окружение и Android `adb`) скачивается в локальную для
проекта папку `.tooling/` скриптами из `scripts/`. Ничего не ставится
системно, а `.tooling/` игнорируется git.

```bash
# Одной командой: uv + uv-managed CPython + venv + adb, всё в .tooling/
scripts/bootstrap.sh

# Или по отдельности:
scripts/install-uv.sh     # -> .tooling/uv
scripts/setup-venv.sh     # -> .tooling/python, .tooling/venv  (axonctl[dev], editable)
scripts/install-adb.sh    # -> .tooling/platform-tools/adb
```

Затем активируй окружение:

```bash
source .tooling/venv/bin/activate
```

`adb` axonctl ищет в таком порядке: `$AXONCTL_ADB`, затем
`.tooling/platform-tools/adb`, затем `adb` в `$PATH`.

## Проверки качества

Все четыре должны быть зелёными перед вливанием ветки — это часть критерия
«готово» каждого этапа:

```bash
ruff check .
black --check .
mypy
pytest -q
```

## Git-процесс (git-flow)

- `main` — только релизы, всегда стабильна; каждый merge тегается `vX.Y.Z`.
- `develop` — интеграционная ветка.
- `feature/<name>` — от `develop`, по одной на этап реализации.
- `release/<version>` — от `develop`, вливается в `main` и обратно.
- `hotfix/<name>` — от `main`, вливается в `main` и `develop`.

Поток этапа: `feature/stageN-<short>` от `develop` → реализация с тестами,
докстрингами и зелёными проверками → merge в `develop` через `--no-ff` →
удалить feature-ветку.

Коммиты — по [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `build:`) в
повелительном наклонении; атомарные (один логический шаг — один коммит).

## Стандарты кода

- Полные type hints везде; `mypy --strict` обязан проходить.
- Google-style docstrings на всём публичном API (на английском); секция
  `Raises:` обязана перечислять подклассы `RpcError`, которые метод может
  поднять.
- Никаких «голых» `except:` — только конкретные исключения; ошибки протокола
  маппятся в типизированные подклассы `RpcError`.

## Язык документации

Проза документации ведётся на двух языках: английский — канонический источник
(`FILE.md`), русский — зеркало (`FILE.ru.md`). При изменении одного держи второй
в синхронности в том же коммите. **Docstrings — только на английском** (это код;
из них автогенерируется API Reference).
