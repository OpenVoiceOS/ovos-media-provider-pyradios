# ovos-media-provider-pyradios

OVOS **MediaProvider** plugin for internet radio. Replaces the deprecated OCP
search skill [`ovos-skill-pyradios`](https://github.com/OpenVoiceOS/ovos-skill-pyradios).

Instead of broadcasting `ovos.common_play.query` over the bus and waiting for
skills to answer, the OCP pipeline loads MediaProvider plugins in-process, gates
them by routing, and calls `search()` directly. This plugin wraps the
[`pyradios`](https://github.com/andreztz/pyradios) client for the
[radio-browser.info](https://www.radio-browser.info) API.

`pyradios` ships no `mediavocab` bridge, so this plugin constructs
[`mediavocab.Release`](https://github.com/TigreGotico/mediavocab) objects itself
from the raw station dicts: each station becomes a `MediaType.RADIO` `Work` plus
a continuous-stream `Release` pointing at the resolved stream URL.

## Install

```bash
pip install ovos-media-provider-pyradios
```

## Routing

| Axis | Value |
|------|-------|
| `media` | `RADIO` |
| `playback_type` | `AUDIO` |
| `genre_filter` | *(none)* |

## Entry point

```toml
[project.entry-points."opm.media.provider"]
pyradios = "ovos_media_provider_pyradios:PyRadiosMediaProvider"
```

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `max_results` | `10` | Maximum number of stations returned per search. |

## License

Apache-2.0
