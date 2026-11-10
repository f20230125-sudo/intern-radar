"""Each adapter against a recorded sample of the real feed."""

import httpx
import pytest

from radar import reader
from radar.http import Client, SourceError
from radar.sources import ADAPTERS, parse_time, workday


@pytest.mark.parametrize("system", sorted(ADAPTERS))
def test_every_adapter_returns_usable_postings(system, client, boards):
    postings = ADAPTERS[system].listing(client, boards[system])
    assert postings, "the sample has postings"
    ids = [p.id for p in postings]
    assert len(ids) == len(set(ids))
    for p in postings:
        assert p.title and p.native_id
        assert p.url.startswith("https://")
        assert p.locations and all(isinstance(loc, str) and loc for loc in p.locations)
        assert p.id.startswith(boards[system].key + ":")


@pytest.mark.parametrize("system", sorted(ADAPTERS))
def test_every_adapter_finds_a_uae_student_role(system, client, boards):
    adapter = ADAPTERS[system]
    roles = []
    for p in adapter.listing(client, boards[system]):
        if not reader.places_of(p)[0]:
            continue
        if p.html is None and p.text is None:
            adapter.detail(client, p)
        role = reader.read(p, now="2026-11-10T08:00:00+00:00")
        if role:
            roles.append(role)
    if system == "ashby":  # Ziina had no student role when the sample was taken
        assert roles == []
        return
    assert roles, f"{system}: the sample contains a student role in the UAE"
    assert all(r.places and r.url.startswith("https://") for r in roles)


def test_one_request_per_board_where_the_feed_allows(client, web, boards):
    for system in ("lever", "ashby", "workable", "amazon", "greenhouse"):
        before = len(web.calls)
        ADAPTERS[system].listing(client, boards[system])
        assert len(web.calls) - before == 1, system


def test_greenhouse_reads_the_description_only_on_demand(client, web, boards):
    postings = ADAPTERS["greenhouse"].listing(client, boards["greenhouse"])
    assert all(p.html is None for p in postings)
    ADAPTERS["greenhouse"].detail(client, postings[0])
    assert postings[0].html
    assert web.calls[-1][1].endswith(f"/jobs/{postings[0].native_id}")


def test_workable_marks_what_the_employer_files_as_an_internship(client, boards):
    postings = ADAPTERS["workable"].listing(client, boards["workable"])
    interns = [p for p in postings if "ntern" in p.title]
    assert interns and all(p.employment_type == "Internship" for p in interns)
    assert all(p.html for p in postings)


def test_workday_asks_for_the_uae_only(client, web, boards):
    postings = ADAPTERS["workday"].listing(client, boards["workday"])
    assert len(postings) == 11
    assert all("Dubai" in p.locations[0] for p in postings)
    posts = [c for c in web.calls if c[0] == "POST"]
    assert len(posts) == 2  # one to read the filters, one page of results
    p = next(p for p in postings if "Intern" in p.title)
    ADAPTERS["workday"].detail(client, p)
    assert p.html and p.posted_at is not None


def test_workday_without_a_uae_filter_is_an_error_not_an_empty_board(client, web, boards):
    web.overrides["myworkdayjobs.com"] = httpx.Response(200, json={"total": 5, "jobPostings": [], "facets": []})
    with pytest.raises(SourceError, match="no UAE filter"):
        ADAPTERS["workday"].listing(client, boards["workday"])


def test_workday_filter_search_prefers_country_over_city():
    facets = [
        {"facetParameter": "locationCountry", "values": [{"descriptor": "United Arab Emirates", "id": "c1"}, {"descriptor": "India", "id": "c2"}]},
        {"facetParameter": "locations", "values": [{"descriptor": "Dubai", "id": "d1"}]},
    ]
    assert workday._uae_facets(facets) == {"locationCountry": ["c1"]}
    assert workday._uae_facets(facets[1:]) == {"locations": ["d1"]}
    assert workday._uae_facets([]) == {}


def test_amazon_reads_its_own_date_format(client, boards):
    postings = ADAPTERS["amazon"].listing(client, boards["amazon"])
    assert all(p.posted_at is not None for p in postings)
    assert all("United Arab Emirates" in p.locations[0] for p in postings)


@pytest.mark.parametrize(
    "value, year",
    [("2026-10-04T23:20:00-04:00", 2026), (1788935575734, 2026), ("2026-11-10", 2026), ("2026-11-10T00:00:00.000Z", 2026), (None, None), ("", None), ("soon", None)],
)
def test_parse_time(value, year):
    got = parse_time(value)
    assert (got.year if got else None) == year
    assert got is None or got.tzinfo is not None


# ------------------------------------------------------------- the client


def test_client_retries_then_gives_a_plain_error():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    slept = []
    with Client(gap=0, retries=2, transport=httpx.MockTransport(handler), sleep=slept.append) as c, pytest.raises(SourceError, match="HTTP 503"):
        c.get("https://example.test/x")
    assert len(calls) == 3 and len(slept) == 2


def test_client_waits_as_long_as_the_server_asks_but_never_long():
    def handler(request):
        return httpx.Response(429, headers={"Retry-After": "84439"})

    slept = []
    with Client(gap=0, retries=1, transport=httpx.MockTransport(handler), sleep=slept.append) as c, pytest.raises(SourceError):
        c.get("https://example.test/x")
    assert slept == [30.0]


def test_client_does_not_retry_a_missing_board():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(404)

    with Client(gap=0, transport=httpx.MockTransport(handler), sleep=lambda s: None) as c, pytest.raises(SourceError, match="404"):
        c.get("https://example.test/x")
    assert len(calls) == 1


def test_client_keeps_a_gap_between_requests_to_one_host():
    now = [0.0]
    slept = []

    def sleep(seconds):
        slept.append(seconds)
        now[0] += seconds

    with Client(gap=1.0, transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})), sleep=sleep, clock=lambda: now[0]) as c:
        c.get("https://a.test/1")
        c.get("https://a.test/2")
        c.get("https://b.test/1")
    assert slept == [1.0]


def test_client_rejects_a_page_that_is_not_json():
    with Client(gap=0, transport=httpx.MockTransport(lambda r: httpx.Response(200, text="<html>blocked</html>")), sleep=lambda s: None) as c, pytest.raises(SourceError, match="not JSON"):
        c.get("https://example.test/x")
