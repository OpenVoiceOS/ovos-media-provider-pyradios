"""OVOS MediaProvider plugin for radio-browser.info (via ``pyradios``).

Replaces the deprecated OCP search skill ``ovos-skill-pyradios``. Instead of
answering ``ovos.common_play.query`` over the bus, this provider is loaded
in-process by the OCP pipeline and its :meth:`search` is called directly. The
provider serves radio stations; any request it cannot satisfy (no query, the
backend unreachable, …) yields an empty list.

``pyradios`` is a thin client over the `radio-browser.info
<https://www.radio-browser.info>`_ HTTP API. It does **not** ship a
``mediavocab`` bridge (no ``mediavocab_bridge``/``converters`` module and it is
not part of mediavocab's consumer contract set), so this plugin constructs
:class:`mediavocab.Release` objects itself from the raw station dicts returned
by the API.

Each radio-browser station is a live-linear broadcast, modelled per mediavocab
axiom 8 as a :class:`mediavocab.Work` with ``MediaType.RADIO`` plus a single
``StreamMode.CONTINUOUS`` :class:`mediavocab.Release` pointing at the resolved
stream URL.
"""
from typing import ClassVar, List, Optional, Set

from ovos_utils.log import LOG

from mediavocab import MediaType, Release, Signals, Work
from ovos_plugin_manager.templates.media_provider import MediaProvider

from ovos_media_provider_pyradios.version import __version__  # noqa: F401


def station_to_release(station: dict) -> Optional[Release]:
    """Build a :class:`mediavocab.Release` from a radio-browser station dict.

    radio-browser stations expose (among others) the keys ``name``,
    ``url_resolved``/``url``, ``favicon``, ``tags`` (comma-separated string),
    ``codec``, ``bitrate``, ``language``, ``countrycode``, ``stationuuid`` and
    a ``0.0``–``1.0``-ish vote/click signal. Returns ``None`` for a station
    with neither a name nor a playable URL.
    """
    name = (station.get("name") or "").strip()
    uri = (station.get("url_resolved") or station.get("url") or "").strip()
    if not name or not uri:
        return None

    raw_tags = station.get("tags") or ""
    if isinstance(raw_tags, (list, tuple)):
        tags = [str(t).strip().lower() for t in raw_tags if str(t).strip()]
    else:
        tags = [t.strip().lower() for t in str(raw_tags).split(",") if t.strip()]

    language = (station.get("language") or "").strip() or None
    country = (station.get("countrycode") or "").strip() or None

    external_ids: dict = {}
    if station.get("stationuuid"):
        external_ids["radio_browser_uuid"] = str(station["stationuuid"])

    work = Work(
        title=name,
        media_type=MediaType.RADIO,
        language=language,
        broadcaster_country=country,
        content_genres=tags,
        external_ids=dict(external_ids),
    )

    bitrate = None
    raw_bitrate = station.get("bitrate")
    if raw_bitrate:
        try:
            # mediavocab's Release.bitrate is a free-form string (e.g. "128")
            bitrate = str(int(raw_bitrate)) if int(raw_bitrate) else None
        except (TypeError, ValueError):
            bitrate = str(raw_bitrate).strip() or None

    return Release(
        work=work,
        uri=uri,
        image=(station.get("favicon") or "").strip(),
        codec=(station.get("codec") or "").strip() or None,
        bitrate=bitrate,
        platform="radio-browser",
        match_confidence=_station_confidence(station),
        external_ids=dict(external_ids),
    )


def _station_confidence(station: dict) -> float:
    """Derive a coarse ``0.0``–``1.0`` ranking signal from a station's
    radio-browser popularity. Uses ``clickcount`` (saturating) so more popular
    stations float to the top across a multi-provider search."""
    try:
        clicks = int(station.get("clickcount") or 0)
    except (TypeError, ValueError):
        clicks = 0
    # saturate: 0 clicks -> 0.5 baseline, ~1000+ clicks -> ~1.0
    return round(min(1.0, 0.5 + clicks / 2000.0), 3)


class PyRadiosMediaProvider(MediaProvider):
    """Search radio-browser.info and return ``mediavocab.Release`` playables.

    Serves live-linear radio stations (``MediaType.RADIO``, consumed as audio).
    """

    name: ClassVar[str] = "pyradios"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        # max results per search, overridable via plugin config
        self.max_results: int = int(self.config.get("max_results", 10))
        self._rb = None

    @property
    def rb(self):
        """Lazily-constructed ``pyradios.RadioBrowser`` client (it pings the
        API's DNS pool at construction time, so build it on first use)."""
        if self._rb is None:
            from pyradios import RadioBrowser
            self._rb = RadioBrowser()
        return self._rb

    def search(self, signals: Signals, lang: str = "en-us", *,
               supported_playback_types: Optional[Set[str]] = None,
               blocked_genres: Optional[Set[str]] = None,
               region: Optional[str] = None,
               session_id: Optional[str] = None) -> List[Release]:
        """Search radio-browser for ``signals.title`` and return Releases.

        Queries by station name; if ``signals`` carry genre/content tags those
        are passed through as a radio-browser ``tag_list`` filter. Each station
        dict is mapped to a :class:`mediavocab.Release` via
        :func:`station_to_release`. Returns ``[]`` when the request carries
        neither a title nor genres, or when the radio-browser API is
        unreachable.
        """
        query = (signals.title or "").strip()
        tags = [str(g).strip() for g in (signals.content_genres or []) if str(g).strip()]
        if not query and not tags:
            return []

        kwargs: dict = {
            "limit": self.max_results,
            "hidebroken": True,
            "order": "clickcount",
            "reverse": True,
        }
        if query:
            kwargs["name"] = query
        if tags:
            kwargs["tag_list"] = ",".join(tags)

        releases: List[Release] = []
        try:
            stations = self.rb.search(**kwargs) or []
        except Exception:
            LOG.exception(f"radio-browser search failed for query: {query!r}")
            return []

        for station in stations:
            try:
                rel = station_to_release(station)
                if rel is not None:
                    releases.append(rel)
            except Exception:
                LOG.exception("Failed to convert radio-browser station to Release")
        return releases
