# ovos-media-provider-pyradios

OVOS **MediaProvider** plugin for internet radio. It replaces the deprecated
OCP search skill [`ovos-skill-pyradios`](https://github.com/OpenVoiceOS/ovos-skill-pyradios).

Instead of broadcasting `ovos.common_play.query` over the bus and waiting for
skills to answer, the OCP pipeline loads MediaProvider plugins in-process,
gates them by routing, and calls `search()` directly. This plugin wraps the
[`pyradios`](https://github.com/andreztz/pyradios) client for the
[radio-browser.info](https://www.radio-browser.info) API.

`pyradios` ships no `mediavocab` bridge, so this plugin builds
[`mediavocab.Release`](https://github.com/TigreGotico/mediavocab) objects
itself from the raw station dicts: each station becomes a `MediaType.RADIO`
`Work` plus a continuous-stream `Release` that points at the resolved stream
URL.

## Install

```bash
pip install ovos-media-provider-pyradios
```

## Usage

OCP loads this plugin through its `opm.media.provider` entry point, so most
users never call it directly. To use it as a standalone library, call
`search()` with a `mediavocab.Signals` object:

```python
from mediavocab import Signals
from ovos_media_provider_pyradios import PyRadiosMediaProvider

provider = PyRadiosMediaProvider()
releases = provider.search(Signals(title="BBC Radio 1"))
for release in releases:
    print(release.work.title, release.uri)
```

`search()` queries radio-browser by station name. If `signals` carries genre
or content tags, the plugin passes them through as a radio-browser
`tag_list` filter. It returns an empty list when the request carries neither
a title nor genres, or when the radio-browser API is unreachable.

## Routing

There is no declarative routing table. OCP calls every installed provider's `search()`
method for each query; a provider that cannot serve the query (no title or genre tags in
the request, no matching stations, an unreachable radio-browser API) just returns an
empty list.

## Entry point

```toml
[project.entry-points."opm.media.provider"]
pyradios = "ovos_media_provider_pyradios:PyRadiosMediaProvider"
```

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `max_results` | `10` | Maximum number of stations returned per search. |

## Related projects

- [`ovos-plugin-manager`](https://github.com/OpenVoiceOS/ovos-plugin-manager): loads and gates MediaProvider plugins for the OCP pipeline.
- [`mediavocab`](https://github.com/TigreGotico/mediavocab): defines the `Work`/`Release`/`Signals` types this plugin builds and consumes.
- [`ovos-skill-pyradios`](https://github.com/OpenVoiceOS/ovos-skill-pyradios): the deprecated OCP search skill this plugin replaces.
- [`ovos-media-provider-somafm`](https://github.com/OpenVoiceOS/ovos-media-provider-somafm), [`ovos-media-provider-tunein`](https://github.com/OpenVoiceOS/ovos-media-provider-tunein), [`ovos-media-provider-radio-tuga`](https://github.com/TigreGotico/ovos-media-provider-radio-tuga), [`ovos-media-provider-radio-spain`](https://github.com/TigreGotico/ovos-media-provider-radio-spain): sibling radio MediaProvider plugins.

## License

Apache-2.0
