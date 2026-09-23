from __future__ import annotations

import locale


STRINGS = {
    "ru": {
        "app_name": "Transcripta", "window_title": "Transcripta", "module_name": "Transcripta", "tagline": "Локальная транскрибация без облака", "drop_title": "Перетащите аудио или видео", "drop_or_choose": "или выберите файл",
        "workspace_empty_title": "Добавьте запись для транскрибации", "workspace_empty_detail": "Файл обрабатывается только на этом компьютере", "file_ready": "Готово к обработке", "replace_file": "Заменить файл",
        "selector_mode": "Режим", "selector_language": "Язык", "selector_recording_language": "Язык записи", "selector_device": "Устройство", "transcript_empty": "Здесь появится текст записи после начала обработки.", "tab_text": "Текст", "tab_summary": "Сводка", "tab_subtitles": "Субтитры", "tab_export": "Экспорт", "tab_waiting": "Результат появится после транскрибации.", "stage_load": "Загрузка", "stage_processing": "Обработка", "stage_ready": "Готово",
        "drop_hint": "Файл остаётся на этом компьютере", "choose_file": "Выбрать файл", "upload_file": "Загрузить файл", "file": "Файл", "duration": "Длительность",
        "size": "Размер", "language": "Язык", "mode": "Режим", "device": "Устройство", "model": "Модель", "start": "Транскрибировать",
        "settings": "Настройки", "pause": "Пауза", "resume": "Продолжить", "cancel": "Отменить", "open_folder": "Открыть папку", "open_document": "Открыть документ",
        "ready_title": "ГОТОВО", "ready_duration": "Длительность аудио: {duration}", "ready_processing": "Время обработки: {duration}", "ready_output": "Файл результата: {path}", "new_transcription": "Новая транскрибация", "processing_title": "ОБРАБОТКА",
        "auto_policy": "Автоматический выбор качества", "quality_default": "Основная модель: large-v3", "memory_fallback": "Fallback: medium",
        "gpu_ready": "CUDA готов", "gpu_unavailable": "GPU недоступен — будет использован CPU", "russian": "Русский", "auto": "Авто",
        "progress": "Прогресс: {percent}\nОбработано: {processed} / {duration}\nПрошло: {elapsed}\nОсталось: {eta}", "progress_details": "{processed} / {duration}\nОсталось ~{eta}", "completed": "Транскрибация завершена",
        "estimating": "расчёт времени…", "processing_context": "Режим: {mode}\nУстройство: {device}",
        "cancelled": "Задача отменена. При повторном запуске она продолжится с последнего checkpoint.", "preparing": "Подготовка модели и первого фрагмента…",
        "general": "Общие", "transcription": "Транскрибация", "advanced": "Расширенные", "theme": "Тема", "switch_theme": "Сменить тему", "system": "Как в системе",
        "light": "Светлая", "dark": "Тёмная", "graphite": "Графит", "pearl": "Жемчуг", "output_folder": "Папка результатов", "timestamps": "Добавлять таймкоды", "formats": "Форматы экспорта",
        "quality": "Качество", "economy": "Экономия памяти", "diagnostics": "Диагностика", "model_override": "Переопределение модели",
        "compute_override": "Переопределение precision", "save": "Сохранить", "cancel_dialog": "Отмена", "close": "Закрыть", "error": "Ошибка транскрибации",
        "file_error": "Не удалось открыть файл", "need_file": "Сначала выберите аудио- или видеофайл.", "model_needed": "Для транскрибации требуется языковая модель.",
        "download_model": "Скачать модель", "download": "Скачать", "download_hint": "После загрузки модель работает offline.", "advanced_details": "Подробности",
        "all_files": "Все файлы", "media_files": "Аудио и видео", "choose_media": "Выберите аудио или видео",
        "automatic": "Автоматически", "real_gpu": "Фактическая GPU", "vram_policy": "Политика {size} GB",
        "eco": "Eco", "balanced": "Balanced", "maximum_speed": "Maximum Speed", "cpu": "CPU", "performance": "Производительность", "vram_class": "Класс памяти", "beam_size": "Beam size", "mode_eco": "Eco", "mode_balanced": "Balanced", "mode_maximum_speed": "Maximum Speed", "mode_auto": "Авто", "mode_quality": "Качество", "mode_economy": "Экономия",
        "model_download_question": "Модель {model} не найдена локально. Примерный размер: {size} MB.\n\nСкачать сейчас?",
        "model_not_installed": "Модель не установлена", "download_declined": "Без явного согласия модель не скачивается.",
        "model_required": "Требуется модель распознавания", "model_required_message": "Для локальной транскрибации необходимо один раз загрузить модель.\nПосле загрузки интернет для распознавания не потребуется.\n\nМодель: {model}\nРазмер загрузки: {size}\nПапка: {path}",
        "download_continue": "Скачать и продолжить", "model_downloading": "Загрузка модели", "model_downloading_message": "Загружается {model}. Приложение останется отзывчивым.",
        "download_progress": "{downloaded} из {total}", "download_progress_unknown": "Подготавливаем загрузку…", "download_speed": "{speed}/с", "download_speed_unknown": "Скорость определяется…", "download_eta_seconds": "осталось ≈ {seconds} с", "download_cancelling": "Отмена загрузки…", "download_cancelled": "Загрузка модели отменена.",
        "download_failed": "Не удалось загрузить модель. Проверьте подключение к интернету и повторите попытку.", "retry": "Повторить",
        "recognition_models": "Модели распознавания", "installed": "Установлена", "not_installed": "Не установлена", "size_on_disk": "Размер на диске: {size}", "download_model_action": "Скачать", "delete_model_action": "Удалить",
        "delete_model_title": "Удалить модель?", "delete_model_message": "Модель {model} будет удалена с этого компьютера. Это не затронет результаты транскрибации.", "delete_model_active": "Нельзя удалить модель, пока она используется или загружается.",
        "unknown_error": "Неизвестная ошибка транскрибации.", "profile_status": "Профиль: {profile}; подготовка модели и первого фрагмента…",
        "device_gpu": "GPU: {name}{memory}; {backend}", "device_cpu": "NVIDIA GPU не обнаружена. Используется CPU.",
        "cuda_available": "CUDA/CTranslate2 доступен", "cuda_unavailable": "CTranslate2 CUDA недоступен", "policy_simulation": " (симуляция политики)",
        "primary_large": "Основная модель large-v3", "fallback_medium": "Fallback medium", "profile_details": "{model}; {precision}; фрагменты по {seconds} с{simulation}",
        "pause_safe": "Пауза: текущий участок завершится, затем задача остановится.", "cancelling": "Отмена: сохраняется последний безопасный checkpoint…",
        "completed_details": "Транскрибация завершена{resume}.\nЭкспорт: {exports}\nОбработка: {time}, RTF: {rtf}\nGPU inference: {gpu}; {peaks}",
        "resumed": " (возобновлено из checkpoint)", "gpu_confirmed": "подтверждён", "gpu_not_confirmed": "не подтверждён",
        "peak_usage": "Peak RAM: {ram} MB; Peak VRAM (sampled): {vram} MB", "failed": "Транскрибация остановлена: {message}",
        "error_log_hint": "{message}\nПодробности сохранены в logs/transcripta.log.", "source_placeholder": "—",
        "use_auto": "Использовать авто-политику", "vad": "Определение речи (VAD)", "chunk_strategy": "Стратегия фрагментов", "chunk_strategy_auto": "Автоматическая — зависит от профиля и длительности записи", "diagnostic_command": "Диагностика: python -m scripts.diagnose",
        "browse": "Обзор…", "open_output_folder": "Открыть папку", "select_output_folder": "Выберите папку результатов", "open_diagnostics": "Открыть диагностику", "open_log": "Открыть журнал",
        "media_missing": "Файл не существует или недоступен.", "media_unsupported": "Формат файла не поддерживается.", "media_open": "Не удалось открыть медиафайл. Формат повреждён или не поддерживается.",
        "vad_tooltip": "Автоматически определяет участки записи, где присутствует речь, и пропускает длительную тишину.", "beam_tooltip": "Количество вариантов распознавания, которые модель сравнивает при декодировании. Большие значения могут немного повысить качество, но увеличивают время обработки.",
        "about": "О программе", "about_description": "Локальная интеллектуальная система транскрибации.", "created_by": "Создано {creator}", "contact": "Связаться", "telegram": "Telegram", "instagram": "Instagram",
    },
    "en": {
        "app_name": "Transcripta", "window_title": "Transcripta", "module_name": "Transcripta", "tagline": "Private, local transcription", "drop_title": "Drop audio or video", "drop_or_choose": "or choose a file",
        "workspace_empty_title": "Add a recording to transcribe", "workspace_empty_detail": "Your file is processed only on this computer", "file_ready": "Ready to process", "replace_file": "Replace file",
        "selector_mode": "Mode", "selector_language": "Language", "selector_recording_language": "Recording language", "selector_device": "Device", "transcript_empty": "The transcript will appear here when processing starts.", "tab_text": "Text", "tab_summary": "Summary", "tab_subtitles": "Subtitles", "tab_export": "Export", "tab_waiting": "The result will appear after transcription.", "stage_load": "Load", "stage_processing": "Processing", "stage_ready": "Ready",
        "drop_hint": "Your file stays on this computer", "choose_file": "Choose file", "upload_file": "Upload file", "file": "File", "duration": "Duration",
        "size": "Size", "language": "Language", "mode": "Mode", "device": "Device", "model": "Model", "start": "Transcribe",
        "settings": "Settings", "pause": "Pause", "resume": "Resume", "cancel": "Cancel", "open_folder": "Open folder", "open_document": "Open document",
        "ready_title": "READY", "ready_duration": "Audio duration: {duration}", "ready_processing": "Processing time: {duration}", "ready_output": "Output file: {path}", "new_transcription": "New transcription", "processing_title": "PROCESSING",
        "auto_policy": "Automatic quality selection", "quality_default": "Primary model: large-v3", "memory_fallback": "Fallback: medium",
        "gpu_ready": "CUDA ready", "gpu_unavailable": "GPU unavailable — CPU will be used", "russian": "Russian", "auto": "Auto",
        "progress": "Progress: {percent}\nProcessed: {processed} / {duration}\nElapsed: {elapsed}\nRemaining: {eta}", "progress_details": "{processed} / {duration}\nAbout {eta} left", "completed": "Transcription complete",
        "estimating": "estimating…", "processing_context": "Mode: {mode}\nDevice: {device}",
        "cancelled": "Task cancelled. Starting again resumes from the last checkpoint.", "preparing": "Preparing the model and first chunk…",
        "general": "General", "transcription": "Transcription", "advanced": "Advanced", "theme": "Theme", "switch_theme": "Switch theme", "system": "System",
        "light": "Light", "dark": "Dark", "graphite": "Graphite", "pearl": "Pearl", "output_folder": "Output folder", "timestamps": "Include timestamps", "formats": "Export formats",
        "quality": "Quality", "economy": "Memory saver", "diagnostics": "Diagnostics", "model_override": "Model override",
        "compute_override": "Precision override", "save": "Save", "cancel_dialog": "Cancel", "close": "Close", "error": "Transcription error",
        "file_error": "Could not open file", "need_file": "Choose an audio or video file first.", "model_needed": "A language model is required for transcription.",
        "download_model": "Download model", "download": "Download", "download_hint": "After download, the model works offline.", "advanced_details": "Details",
        "all_files": "All files", "media_files": "Audio and video", "choose_media": "Choose audio or video",
        "automatic": "Automatic", "real_gpu": "Actual GPU", "vram_policy": "{size} GB policy",
        "eco": "Eco", "balanced": "Balanced", "maximum_speed": "Maximum Speed", "cpu": "CPU", "performance": "Performance", "vram_class": "Memory class", "beam_size": "Beam size", "mode_eco": "Eco", "mode_balanced": "Balanced", "mode_maximum_speed": "Maximum Speed", "mode_auto": "Auto", "mode_quality": "Quality", "mode_economy": "Economy",
        "model_download_question": "Model {model} is not available locally. Approximate size: {size} MB.\n\nDownload now?",
        "model_not_installed": "Model not installed", "download_declined": "The model is never downloaded without explicit permission.",
        "model_required": "Recognition model required", "model_required_message": "Local transcription needs a one-time model download.\nAfter downloading, transcription does not need internet access.\n\nModel: {model}\nDownload size: {size}\nFolder: {path}",
        "download_continue": "Download and continue", "model_downloading": "Downloading model", "model_downloading_message": "Downloading {model}. The application will remain responsive.",
        "download_progress": "{downloaded} of {total}", "download_progress_unknown": "Preparing download…", "download_speed": "{speed}/s", "download_speed_unknown": "Calculating speed…", "download_eta_seconds": "about {seconds}s left", "download_cancelling": "Cancelling download…", "download_cancelled": "Model download cancelled.",
        "download_failed": "Could not download the model. Check your internet connection and try again.", "retry": "Retry",
        "recognition_models": "Recognition models", "installed": "Installed", "not_installed": "Not installed", "size_on_disk": "Size on disk: {size}", "download_model_action": "Download", "delete_model_action": "Delete",
        "delete_model_title": "Delete model?", "delete_model_message": "{model} will be removed from this computer. This will not affect transcription results.", "delete_model_active": "The model cannot be deleted while it is in use or downloading.",
        "unknown_error": "Unknown transcription error.", "profile_status": "Profile: {profile}; preparing the model and first chunk…",
        "device_gpu": "GPU: {name}{memory}; {backend}", "device_cpu": "NVIDIA GPU was not found. CPU will be used.",
        "cuda_available": "CUDA/CTranslate2 available", "cuda_unavailable": "CTranslate2 CUDA unavailable", "policy_simulation": " (policy simulation)",
        "primary_large": "Primary model large-v3", "fallback_medium": "Fallback medium", "profile_details": "{model}; {precision}; {seconds} s chunks{simulation}",
        "pause_safe": "Pause: the current chunk will finish, then the task stops.", "cancelling": "Cancelling: saving the last safe checkpoint…",
        "completed_details": "Transcription complete{resume}.\nExports: {exports}\nProcessing: {time}, RTF: {rtf}\nGPU inference: {gpu}; {peaks}",
        "resumed": " (resumed from checkpoint)", "gpu_confirmed": "confirmed", "gpu_not_confirmed": "not confirmed",
        "peak_usage": "Peak RAM: {ram} MB; Peak VRAM (sampled): {vram} MB", "failed": "Transcription stopped: {message}",
        "error_log_hint": "{message}\nDetails were saved to logs/transcripta.log.", "source_placeholder": "—",
        "use_auto": "Use automatic policy", "vad": "Speech detection (VAD)", "chunk_strategy": "Chunk strategy", "chunk_strategy_auto": "Automatic — follows the profile and recording duration", "diagnostic_command": "Diagnostics: python -m scripts.diagnose",
        "browse": "Browse…", "open_output_folder": "Open folder", "select_output_folder": "Choose output folder", "open_diagnostics": "Open diagnostics", "open_log": "Open log",
        "media_missing": "The file does not exist or is unavailable.", "media_unsupported": "This file format is not supported.", "media_open": "Could not open the media file. The format may be damaged or unsupported.",
        "vad_tooltip": "Detects portions of the recording with speech and skips long silence.", "beam_tooltip": "The number of decoding alternatives the model compares. Larger values can slightly improve quality but take longer.",
        "about": "About", "about_description": "Local intelligent transcription system.", "created_by": "Created by {creator}", "contact": "Contact", "telegram": "Telegram", "instagram": "Instagram",
    },
}


def system_language() -> str:
    language = (locale.getlocale()[0] or "en").lower()
    return "ru" if language.startswith("ru") else "en"


class Translator:
    def __init__(self, language: str = "system") -> None:
        self.set_language(language)

    def set_language(self, language: str) -> None:
        self.preference = language if language in {"ru", "en", "system"} else "system"

    @property
    def language(self) -> str:
        return system_language() if self.preference == "system" else self.preference

    def __call__(self, key: str, **values: object) -> str:
        return STRINGS[self.language].get(key, key).format(**values)
