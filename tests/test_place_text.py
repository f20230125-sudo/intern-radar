import pytest

from radar import place
from radar.text import clip, sentences, slugify, to_text


@pytest.mark.parametrize(
    "raw, emirate",
    [
        ("Dubai", "Dubai"),
        ("AE - Dubai, United Arab Emirates", "Dubai"),
        ("Dubai, Dubai, United Arab Emirates", "Dubai"),
        ("Abu Dhabi", "Abu Dhabi"),
        ("Abu Dhabi (ADGM)", "Abu Dhabi"),
        ("Masdar City", "Abu Dhabi"),
        ("DIFC", "Dubai"),
        ("AE, Dubai", "Dubai"),
        ("Sharjah, UAE", "Sharjah"),
        ("Ras Al Khaimah", "Ras Al Khaimah"),
        ("United Arab Emirates", "UAE"),
        ("UAE", "UAE"),
        ("Remote - UAE", "UAE"),
        ("AE", "UAE"),
    ],
)
def test_uae_places(raw, emirate):
    assert place.match(raw).emirate == emirate


@pytest.mark.parametrize(
    "raw",
    ["Riyadh, Saudi Arabia", "Remote - EMEA", "London", "Sunnyvale, CA", "Wanchai, Hong Kong", "Singapore", "Quae, Portugal", "Israel", "", "Are you remote?", "2 Locations"],
)
def test_places_elsewhere(raw):
    assert place.match(raw) is None


def test_read_counts_places_elsewhere():
    places, elsewhere = place.read(["Riyadh; Dubai", "London"])
    assert [p.emirate for p in places] == ["Dubai"]
    assert elsewhere == 2


def test_country_and_city_on_one_posting_is_one_place():
    places, _ = place.read(["Dubai", "United Arab Emirates"])
    assert [p.emirate for p in places] == ["Dubai"]


def test_two_emirates_are_two_places():
    places, _ = place.read(["Dubai / Abu Dhabi"])
    assert [p.emirate for p in places] == ["Dubai", "Abu Dhabi"]


def test_to_text_keeps_blocks_apart_and_unescapes_once():
    escaped = "&lt;p&gt;Paid &amp;amp; fun&lt;/p&gt;&lt;ul&gt;&lt;li&gt;One&lt;/li&gt;&lt;li&gt;Two&lt;/li&gt;&lt;/ul&gt;"
    assert to_text(escaped) == "Paid & fun\nOne\nTwo"
    assert to_text("<p>A<br>B</p><script>alert(1)</script><style>p{}</style>") == "A\nB"
    assert to_text(None) == ""


def test_sentences_split_on_stops_and_lines_but_not_inside_numbers():
    text = "The stipend is AED 3.5k e.g. monthly. It lasts 12 weeks.\n- First item\n2. Second item"
    assert sentences(text) == ["The stipend is AED 3.5k e.g. monthly.", "It lasts 12 weeks.", "First item", "Second item"]


def test_clip_and_slugify():
    assert clip("short") == "short"
    cut = clip("word " * 100, 50)
    assert len(cut) <= 51 and cut.endswith("…") and not cut[:-1].endswith(" ")
    assert slugify("Bayut & dubizzle") == "bayut-dubizzle"
    assert slugify("!!!") == "role"
