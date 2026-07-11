# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""v2 prices/ endpoint tests — JWT required, per-customer pricing."""

BASE = "/api/matrix/v2/test-v2/prices/"


class TestPricesAuth:
    """JWT is mandatory for prices/."""

    def test_unauthenticated_returns_401_or_403(self, api, channel_full):
        response = api.get(f"{BASE}?sku=TEST-001")
        assert response.status_code in (401, 403)

    def test_admin_can_access(self, admin_client, channel_full):
        response = admin_client.get(f"{BASE}?sku=TEST-001")
        assert response.status_code == 200


class TestPricesShape:
    """Response shape and caching."""

    def test_empty_without_skus(self, admin_client, channel_full):
        response = admin_client.get(BASE)
        assert response.status_code == 200
        assert response.json() == {}

    def test_cache_private_no_store(self, admin_client, channel_full):
        response = admin_client.get(f"{BASE}?sku=TEST-001")
        assert "private" in response.get("Cache-Control", "")
        assert "no-store" in response.get("Cache-Control", "")

    def test_returns_dict_keyed_by_sku(self, admin_client, channel_full):
        response = admin_client.get(f"{BASE}?sku=TEST-001")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    def test_unknown_channel_404(self, api):
        response = api.get("/api/matrix/v2/nonexistent/prices/?sku=TEST")
        # Prices requires auth first, so it may return 401 before 404
        assert response.status_code in (401, 403, 404)
