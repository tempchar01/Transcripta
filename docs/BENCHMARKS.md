# Benchmarks

## Test conditions

- Windows 10, Python 3.14.3, faster-whisper 1.1.1, CTranslate2 4.8.2;
- NVIDIA RTX 5060 Ti, 16,311 MiB reported VRAM, NVIDIA driver 616.56;
- CUDA backend, cuBLAS from `nvidia-cublas-cu12` 12.9.2.10 and `cudnn64_9.dll` from the CTranslate2 wheel;
- the same private local Russian audio, 22.180 s; its source file is intentionally not distributed;
- clean Python process with inherited NVIDIA DLL directories removed from `PATH`; Transcripta then discovers and activates its package-local runtime paths itself;
- `float16`, `device="cuda"`, `language="ru"`, `beam_size=5`, VAD enabled.

`peak_vram_mb_sampled` is a before/after `nvidia-smi` sample, not a continuous profiler high-water mark. Model-load numbers below are warm-cache values, after the models were downloaded locally; first download/load took 132.500 s (`small`), 129.317 s (`medium`) and 231.302 s (`large-v3`) and is intentionally not used to compare inference speed.

## Results

| Model | Load, s | Audio, s | Processing, s | RTF | Sampled peak VRAM | Segments | CUDA inference |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| tiny | 0.503 | 22.180 | 10.124 | 0.4564 | 1,038 MB | 3 | passed |
| small | 0.809 | 22.180 | 9.783 | 0.4411 | 1,548 MB | 3 | passed |
| medium | 1.660 | 22.180 | 10.485 | 0.4727 | 2,892 MB | 3 | passed |
| large-v3 | 2.919 | 22.180 | 11.199 | 0.5049 | 4,780 MB | 3 | passed |

All four runs loaded the model on CUDA, used CUDA for inference and detected `ru`.

## Recognized text

- `tiny`: «Да, я так сделаю, я на самом деле тоже чклинно, что он сейчас может ну прям зарваться перед моим лицом, а я его не с угрудий, и это может мне просто разорвать просто вообще дворечка, конечно, вообще таков одну пушу».
- `small`: «Да, я так и сделаю. Я на самом деле тоже очкинула, что он сейчас может, ну, прям взорваться перед моим лицом, а я его несу в груди. И это может меня просто разорвать. Просто вообще дурочка я, конечно, вообще так холодно отношусь.»
- `medium`: «Да, я так и сделаю. Я, на самом деле, тоже очкнула, что он сейчас может прям взорваться перед моим лицом, а я его несу у груди. И это может меня просто разорвать, просто. Вообще дурочка я, конечно, вообще так колладно отношусь.»
- `large-v3`: «Да, я так сделаю. Я на самом деле тоже очканула, что он сейчас может, ну, прям взорваться перед моим лицом, а я его несу в груди. И это может меня просто разорвать. Просто. Вообще, дурочка я. Конечно, вообще, я так калатно отношусь.»

There is no verified ground-truth transcript for this informal source. The comparison is therefore qualitative, not a WER claim. Nevertheless, `tiny` is visibly unsuitable as the Russian quality default. `medium` is the smallest model that consistently keeps the speech intelligible in this sample; `large-v3` improves several colloquial words but costs about 1.9 GB more sampled VRAM than `medium` and is slightly slower.

## Russian defaults and AUTO policy

| VRAM class | Balanced / AUTO default | Quality choice | Rationale |
| --- | --- | --- | --- |
| 6 GB | `medium`, `int8_float16` | manual `large-v3` only after a user accepts OOM risk | preserve Russian quality while retaining headroom |
| 8 GB | `medium`, `float16` where supported | `large-v3` is explicit only | Medium is the practical quality/safety point |
| 12 GB | `large-v3`, `float16` | same | user-approved quality-default policy |
| 16 GB | `large-v3`, `float16` | same | benchmarked `large-v3` fits at 4,780 MB sampled |

The 16 GB row is physically measured on this GPU. The 6/8/12 GB rows are conservative policy recommendations derived from the observed footprint, not physical OOM tests on those cards. `Fast` selects `small` for development throughput; `AUTO` selects `medium` on 6–8 GB and `large-v3` on 12 GB+. Audio duration influences chunk size and keeps processing serial/bounded.

## Reproduction

```powershell
python -m scripts.gpu_smoke sample.ogg --model tiny --compute float16 --allow-model-download
python -m scripts.gpu_smoke sample.ogg --model small --compute float16 --allow-model-download
python -m scripts.gpu_smoke sample.ogg --model medium --compute float16 --allow-model-download
python -m scripts.gpu_smoke sample.ogg --model large-v3 --compute float16 --allow-model-download
```

`large` in the UI maps to factual model id `large-v3`. `--vram-class 6|8|12|16` in `scripts.benchmark` checks policy only; it does not emulate a physical OOM on another card.
