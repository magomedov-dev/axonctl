# Примеры axonctl

[English](README.md) · **Русский**

Автономные скрипты, импортирующие `axonctl` ровно так, как это делал бы внешний
проект. Они **не** часть пакета.

| Скрипт | Что показывает |
|--------|----------------|
| `single_device.py` | Подключиться к одному устройству, дождаться элемента, прочитать. |
| `inspect_ui.py` | Сделать дамп UI и напечатать компактное дерево (искать селекторы). |
| `run_group.py` | `FleetController` + `run` по группе, с `Results`. |
| `fleet.toml` | Пример конфигурации парка. |

## Запуск

Установи библиотеку, затем для скриптов на одно устройство сначала подними
forward:

```bash
pip install axonctl
adb forward tcp:10001 tcp:9008
python examples/single_device.py <serial>
python examples/inspect_ui.py <serial>
```

Для примера с парком отредактируй `fleet.toml` со своими серийниками и запусти:

```bash
python examples/run_group.py
```

Контроллер парка сам поднимает форварды, так что ручной `adb forward` там не
нужен.
