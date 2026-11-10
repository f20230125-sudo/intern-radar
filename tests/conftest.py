"""A stand-in for the internet: every feed URL the adapters build is answered from a recorded sample."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from radar.http import Client
from radar.models import Board

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeWeb:
    """Routes requests to recorded samples and counts them. Anything unknown is a 404, so a test fails loudly
    if an adapter starts calling a URL nobody recorded."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.overrides: dict[str, httpx.Response] = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.calls.append((request.method, url))
        for needle, response in self.overrides.items():
            if needle in url:
                return response
        path = request.url.path
        host = request.url.host
        if host == "boards-api.greenhouse.io":
            if path.endswith("/jobs"):
                return httpx.Response(200, json=load("greenhouse_tamara_list.json"))
            return httpx.Response(200, json=load("greenhouse_tamara_job.json"))
        if host == "api.lever.co":
            return httpx.Response(200, json=load("lever_ifm.json"))
        if host == "api.ashbyhq.com":
            return httpx.Response(200, json=load("ashby_ziina.json"))
        if host == "apply.workable.com":
            return httpx.Response(200, json=load("workable_bayut.json"))
        if host.endswith("myworkdayjobs.com"):
            if request.method == "POST":
                body = json.loads(request.content)
                name = "workday_mastercard_page.json" if body.get("appliedFacets") else "workday_mastercard_first.json"
                return httpx.Response(200, json=load(name))
            return httpx.Response(200, json=load("workday_mastercard_job.json"))
        if host == "www.amazon.jobs":
            return httpx.Response(200, json=load("amazon_are.json"))
        return httpx.Response(404)


@pytest.fixture
def web() -> FakeWeb:
    return FakeWeb()


@pytest.fixture
def client(web: FakeWeb):
    c = Client(gap=0, transport=httpx.MockTransport(web.handler), sleep=lambda s: None)
    yield c
    c.close()


BOARDS = {
    "greenhouse": Board(key="greenhouse:tamara", system="greenhouse", slug="tamara", name="Tamara"),
    "lever": Board(key="lever:ifm-us", system="lever", slug="ifm-us", name="IFM"),
    "ashby": Board(key="ashby:ziina", system="ashby", slug="ziina", name="Ziina"),
    "workable": Board(key="workable:bayutdubizzle", system="workable", slug="bayutdubizzle", name="Bayut & dubizzle"),
    "workday": Board(key="workday:mastercard:CorporateCareers", system="workday", slug="mastercard", name="Mastercard", host="wd1", site="CorporateCareers"),
    "amazon": Board(key="amazon:amazon", system="amazon", slug="amazon", name="Amazon"),
}


@pytest.fixture
def boards() -> dict[str, Board]:
    return dict(BOARDS)
