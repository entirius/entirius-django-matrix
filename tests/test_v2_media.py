# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""v2 media tests — gallery normalization (image/video types) and product attachments."""

from django_matrix.services.product_serializer import _normalize_video_source

BASE = "/api/matrix/v2/test-v2/products/"
QS = "?language=en&currency=EUR&country=PL"


def _get_product(api, extra_qs=""):
    response = api.get(f"{BASE}{QS}{extra_qs}")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) >= 1
    return results[0]


# ── Gallery normalization ────────────────────────────────────────────


class TestGalleryNormalization:
    """Media items must have normalized types and video_source."""

    def test_media_present_with_include_full(self, api, simple_product, channel_full):
        product = _get_product(api, "&include=full")
        assert isinstance(product["media"], list)
        assert len(product["media"]) == 3  # 2 pictures + 1 video

    def test_pictures_have_type_image_not_picture(self, api, simple_product, channel_full):
        media = _get_product(api, "&include=full")["media"]
        images = [m for m in media if m["type"] == "image"]
        assert len(images) == 2
        pictures = [m for m in media if m["type"] == "picture"]
        assert len(pictures) == 0, "type should be 'image', not 'picture'"

    def test_videos_have_type_video(self, api, simple_product, channel_full):
        media = _get_product(api, "&include=full")["media"]
        videos = [m for m in media if m["type"] == "video"]
        assert len(videos) == 1

    def test_video_has_video_source_top_level(self, api, simple_product, channel_full):
        media = _get_product(api, "&include=full")["media"]
        video = [m for m in media if m["type"] == "video"][0]
        assert "video_source" in video
        assert video["video_source"] == "youtube"

    def test_images_do_not_have_video_source(self, api, simple_product, channel_full):
        media = _get_product(api, "&include=full")["media"]
        images = [m for m in media if m["type"] == "image"]
        for img in images:
            assert "video_source" not in img

    def test_media_sorted_by_position(self, api, simple_product, channel_full):
        media = _get_product(api, "&include=full")["media"]
        positions = [m["position"] for m in media]
        assert positions == sorted(positions)

    def test_image_has_source_set_and_alt_text(self, api, simple_product, channel_full):
        media = _get_product(api, "&include=full")["media"]
        main_img = [m for m in media if m["type"] == "image" and m["role"] == "main"][0]
        assert isinstance(main_img["source_set"], list)
        assert main_img["alt_text"] == "Test Chair front view"

    def test_media_absent_without_content_include(self, api, simple_product, channel_full):
        product = _get_product(api)
        assert "media" not in product


# ── Video source normalization (unit) ────────────────────────────────


class TestNormalizeVideoSource:
    """Unit tests for _normalize_video_source — case-insensitive mapping."""

    def test_youtube_capitalized(self):
        assert _normalize_video_source("YouTube") == "youtube"

    def test_vimeo_capitalized(self):
        assert _normalize_video_source("Vimeo") == "vimeo"

    def test_unknown_capitalized(self):
        assert _normalize_video_source("Unknown") == "unknown"

    def test_lowercase_passthrough(self):
        assert _normalize_video_source("youtube") == "youtube"

    def test_empty_string(self):
        assert _normalize_video_source("") == "unknown"

    def test_unrecognized_source(self):
        assert _normalize_video_source("dailymotion") == "unknown"


# ── Attachments ──────────────────────────────────────────────────────


class TestAttachments:
    """Product attachments from PIM Files."""

    def test_attachments_present_with_include_full(self, api, simple_product, channel_full):
        product = _get_product(api, "&include=full")
        assert "attachments" in product
        assert isinstance(product["attachments"], list)
        assert len(product["attachments"]) == 1

    def test_attachment_structure(self, api, simple_product, channel_full):
        att = _get_product(api, "&include=full")["attachments"][0]
        assert att["file_label"] == "Assembly Guide"
        assert att["original_file_name"] == "assembly-guide-v2.pdf"
        assert att["file_path"] == "/media/files/abc123.pdf"
        assert att["file_type"] == "pdf"
        assert att["file_size"] == "2.45"
        assert att["category_code"] == "manuals"
        assert att["category_name"] == "Manuals"

    def test_attachments_absent_without_include(self, api, simple_product, channel_full):
        product = _get_product(api)
        assert "attachments" not in product

    def test_attachments_absent_with_attributes_include(self, api, simple_product, channel_full):
        product = _get_product(api, "&include=attributes")
        assert "attachments" not in product

    def test_attachments_present_with_content_include(self, api, simple_product, channel_full):
        product = _get_product(api, "&include=content")
        assert "attachments" in product

    def test_attachments_empty_list_when_none(self, api, configurable_product, channel_full):
        """Product without attachments should get empty list, not null."""
        response = api.get(f"{BASE}{QS}&url_key=config-sofa&include=full")
        assert response.status_code == 200
        product = response.json()["results"][0]
        assert product["attachments"] == []
