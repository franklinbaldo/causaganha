# Multilingual Configuration

The extraction pipeline supports Portuguese and Spanish decisions. Settings are defined in `config.toml` under the `[multilingual]` section:

```toml
[multilingual]
enable_translation = true
target_language = "pt"
supported_languages = ["pt", "es"]
```

When `enable_translation` is enabled, decision fields detected in a language different from `target_language` are translated automatically. The detected language is stored in each decision alongside the translated text.
