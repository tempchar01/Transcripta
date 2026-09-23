# Модели

| UI | faster-whisper id | Рекомендация |
| --- | --- | --- |
| Medium | `medium` | memory-safe fallback для русского |
| Large | `large-v3` | основной quality default на 12 GB+ |

`tiny` и `small` сохранены только в development/smoke tools и не показываются пользователю в GUI.

Модель загружается только после явного согласия в интерфейсе. В MVP Model Manager выбирает и кэширует модели; экран списка/удаления моделей — следующий этап, а не заявленная работающая функция.

## AUTO recommendations

| Effective VRAM | Default model | Compute | Chunk |
| --- | --- | --- | --- |
| 6 GB | Medium | `int8_float16` (or `int8`) | 300 s |
| 8 GB | Medium | `int8_float16` (or `int8`) | 600 s |
| 10–12 GB | Large | `float16` (or `int8_float16`) | 900 s |
| 16+ GB | Large | `float16` | 900 s |

`--vram-class` in the benchmark and the advanced UI setting constrain decisions only. It cannot emulate a physical OOM on another card.
