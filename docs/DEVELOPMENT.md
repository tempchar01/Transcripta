# Разработка

## Проверки

```powershell
$testRoot = Join-Path (Get-Location) "work\pytest"
python -m pytest --basetemp $testRoot -p no:cacheprovider
python -m compileall -q app scripts tests
```

Основные тесты используют синтетический секундный WAV, не требуют модели, CUDA, FFmpeg или сети. Они покрывают настройки, форматирование длительности, планирование фрагментов, checkpoint/resume, TXT/SRT/DOCX и границу отмены. Python 3.14 — основной development baseline; 3.12 допустим при том же наборе прошедших проверок.

Профильная часть также покрывает 6/8/12/16 GB, Fast/Balanced/Quality policy, выбор precision, CPU fallback, ограниченную OOM-деградацию, ownership overlap и OOM-retry с fake model. `tests/test_nvidia_runtime.py` отдельно проверяет discovery DLL, отсутствие cuBLAS/cuDNN, логирование и clean subprocess startup; GPU-marked тест выполняется только с реально установленным CTranslate2/CUDA.

## Ограничения тестов MVP

Интеграционный тест реального Whisper требует модель и GPU. После установки зависимостей на целевой машине сначала запустите `python -m scripts.diagnose`, затем clean-start `python -m scripts.gpu_smoke <аудио> --model tiny --compute float16`. Для сравнительного качества используйте один и тот же русский файл с tiny/small/medium/large-v3 и сохраните результаты в `docs/BENCHMARKS.md`.

Полный pipeline запускается отдельным validator без CPU fallback:

```powershell
python -m scripts.e2e_validate .\samples\russian.ogg --chunk-seconds 45
python -m scripts.e2e_validate .\samples\russian-long.ogg --chunk-seconds 60 --cancel-after-chunks 3
```

Первый вызов проверяет probe → sequential chunks → ASR → checkpoint → TXT/SRT/DOCX/JSON. Второй безопасно отменяет задачу после сохранённых checkpoints; повторный запуск без `--cancel-after-chunks` должен показать `recovered_from_checkpoint` в логе и завершить экспорт.
