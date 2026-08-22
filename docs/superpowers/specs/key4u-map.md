# Key4U mapping

Key4U static marker observed in bot source: **yes**. This audit makes no network call and does not verify a key, balance, model availability, or paid endpoint.

| Capability family | Feature keys to validate |
| --- | --- |
| Video | video_single, video_multiscene, video_long |
| Voice / audio | voice_tts, voice_clone, voice_saved_tts |
| Music | music_background, music_song, music_library, sfx_library |
| Caption / dub | subtitle_asr, subtitle_translate, video_dub |

Before enabling each feature, verify provider adapter, required ENV name, quote/confirm policy, job polling, output validation, and public-safe failure copy through the private bridge.
