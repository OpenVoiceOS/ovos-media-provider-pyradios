"""Tests for the pyradios MediaProvider plugin (network-free)."""
from unittest.mock import MagicMock

from mediavocab import MediaType, Release, Signals, Work

from ovos_media_provider_pyradios import (
    PyRadiosMediaProvider,
    station_to_release,
)


# A representative radio-browser station dict (trimmed to the fields used).
SAMPLE_STATION = {
    "name": "BBC Radio 1",
    "url": "http://stream.example/bbc1",
    "url_resolved": "http://stream.example/bbc1.mp3",
    "favicon": "http://example/bbc1.png",
    "tags": "pop,top 40,charts",
    "codec": "MP3",
    "bitrate": 128,
    "language": "english",
    "countrycode": "GB",
    "stationuuid": "abc-123",
    "clickcount": 3000,
}


def test_instantiation():
    provider = PyRadiosMediaProvider()
    assert provider.name == "pyradios"


def test_station_to_release_builds_valid_release():
    rel = station_to_release(SAMPLE_STATION)
    assert isinstance(rel, Release)
    assert isinstance(rel.work, Work)
    assert rel.work.media_type == MediaType.RADIO
    assert rel.work.title == "BBC Radio 1"
    assert rel.work.content_genres == ["pop", "top 40", "charts"]
    assert rel.uri == "http://stream.example/bbc1.mp3"
    assert rel.image == "http://example/bbc1.png"
    assert rel.codec == "MP3"
    assert rel.bitrate == "128"
    assert rel.external_ids["radio_browser_uuid"] == "abc-123"
    assert 0.0 <= rel.match_confidence <= 1.0


def test_station_to_release_skips_unplayable():
    assert station_to_release({"name": "no url"}) is None
    assert station_to_release({"url": "http://x"}) is None


def test_search_empty_signals_returns_empty():
    provider = PyRadiosMediaProvider()
    assert provider.search(Signals(title="")) == []
    assert provider.search(Signals()) == []


def test_search_maps_stations_to_releases():
    """search() drives RadioBrowser.search and returns list[Release] built
    from each station dict."""
    provider = PyRadiosMediaProvider()

    fake_rb = MagicMock()
    fake_rb.search.return_value = [SAMPLE_STATION]
    provider._rb = fake_rb

    results = provider.search(Signals(title="bbc radio 1"))

    fake_rb.search.assert_called_once()
    _, kwargs = fake_rb.search.call_args
    assert kwargs["name"] == "bbc radio 1"

    assert isinstance(results, list)
    assert len(results) == 1
    assert all(isinstance(r, Release) for r in results)
    r = results[0]
    assert isinstance(r.work, Work)
    assert r.work.media_type == MediaType.RADIO
    assert r.work.title == "BBC Radio 1"


def test_search_passes_tag_list_for_genres():
    provider = PyRadiosMediaProvider()
    fake_rb = MagicMock()
    fake_rb.search.return_value = []
    provider._rb = fake_rb

    provider.search(Signals(content_genres=["jazz", "blues"]))

    _, kwargs = fake_rb.search.call_args
    assert kwargs["tag_list"] == "jazz,blues"


def test_search_swallows_per_item_errors():
    provider = PyRadiosMediaProvider()
    fake_rb = MagicMock()
    # one unplayable (skipped), one good
    fake_rb.search.return_value = [{"name": "broken"}, SAMPLE_STATION]
    provider._rb = fake_rb

    results = provider.search(Signals(title="anything"))
    assert [r.work.title for r in results] == ["BBC Radio 1"]


def test_search_swallows_backend_error():
    provider = PyRadiosMediaProvider()
    fake_rb = MagicMock()
    fake_rb.search.side_effect = RuntimeError("boom")
    provider._rb = fake_rb

    assert provider.search(Signals(title="x")) == []
