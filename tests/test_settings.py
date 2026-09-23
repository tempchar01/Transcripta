from app.config.settings import AppSettings, SettingsStore


def test_settings_round_trip(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    settings = AppSettings()
    settings.recognition.model = "medium"
    settings.export.output_dir = str(tmp_path / "out")
    store.save(settings)

    loaded = store.load()
    assert loaded.recognition.model == "medium"
    assert loaded.export.output_dir == str(tmp_path / "out")


def test_invalid_settings_returns_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not json", encoding="utf-8")
    settings = SettingsStore(path).load()
    assert settings.recognition.model == "auto"
    assert settings.recognition.performance_profile == "balanced"


def test_legacy_automatic_profile_migrates_to_balanced():
    settings = AppSettings.from_dict({"recognition": {"performance_profile": "auto"}})
    assert settings.recognition.performance_profile == "balanced"
