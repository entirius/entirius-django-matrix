# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Cached v1 views skip the cache for requests with an Authorization header.

v1 views read an optional JWT, so a response may depend on the caller (verified-customer prices). Such a
request neither reads a cached response nor stores its own; anonymous requests are cached as before.
"""

import pytest
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, override_settings

from django_matrix import settings as matrix_settings
from django_matrix.urls import apply_cache, cache_anonymous_only

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "matrix-cache-test"}}
URL = "/api/matrix/v1/test-v2/products/"
AUTH = {"HTTP_AUTHORIZATION": "Bearer token"}


class CountingView:
    """A view whose body names the call number, so a cached answer is recognisable."""

    __name__ = "products_listing_view"

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, request: HttpRequest) -> HttpResponse:
        self.calls += 1
        return HttpResponse(f"call {self.calls}")


@pytest.fixture
def locmem_cache():
    with override_settings(CACHES=LOCMEM):
        cache.clear()
        yield
        cache.clear()


@pytest.fixture
def rf() -> RequestFactory:
    return RequestFactory()


def test_anonymous_request_is_cached(locmem_cache, rf):
    view = CountingView()
    cached = cache_anonymous_only(view, 60)
    first, second = cached(rf.get(URL)), cached(rf.get(URL))
    assert view.calls == 1
    assert first.content == second.content == b"call 1"


def test_authorized_request_does_not_get_the_cached_anonymous_response(locmem_cache, rf):
    view = CountingView()
    cached = cache_anonymous_only(view, 60)
    cached(rf.get(URL))
    response = cached(rf.get(URL, **AUTH))
    assert view.calls == 2
    assert response.content == b"call 2"


def test_authorized_response_is_not_stored(locmem_cache, rf):
    view = CountingView()
    cached = cache_anonymous_only(view, 60)
    cached(rf.get(URL, **AUTH))
    cached(rf.get(URL, **AUTH))
    anonymous = cached(rf.get(URL))
    assert view.calls == 3
    assert anonymous.content == b"call 3"


def test_apply_cache_uses_the_anonymous_only_wrapper(locmem_cache, rf, monkeypatch):
    monkeypatch.setattr(matrix_settings, "USE_CACHED_VIEWS", True)
    view = CountingView()
    cached = apply_cache(view)
    cached(rf.get(URL))
    cached(rf.get(URL))
    cached(rf.get(URL, **AUTH))
    assert view.calls == 2
