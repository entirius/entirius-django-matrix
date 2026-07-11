# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from itertools import groupby

from django.core.exceptions import ObjectDoesNotExist
from process_logger import ProcessLogger

from django_matrix.dto.view.video import SourceSet
from django_matrix.dto.view.video import Video as VideoDTO
from django_matrix.models import Channel, ProductRepresentation, ProductT9N
from django_matrix.settings import LANGUAGE_VIDEO_IMPORT_TYPE

try:
    from django_pim.models import Product, ProductVideo, Video
except ImportError:
    raise Exception("django_matrix does not have access to django_pim module")


class LanguageVideoImportType:
    # 1 - Import images for all languages 1:1 from pim to product t9n
    # 2 - Import images from pim, but if image in specific type is not found for language, use default language image or first found
    LANGUAGES_1_TO_1_AS_PIM = 1
    FILL_MISSING_LANGUAGES_WITH_DEFAULT = 2


def fill_read_model_videos(channel: Channel, product_id: str = None):
    process_logger = ProcessLogger("FILL_READ_MODEL_VIDEOS")
    process_logger.add_log_param("channel_idx", channel.idx)

    query = {"product__real_product__sku": product_id} if product_id else {}
    product_videos: list[ProductVideo] = (
        ProductVideo.objects.filter(product__shop__idx=channel.idx, **query)
        .prefetch_related("product", "video")
        .order_by("product__real_product__sku", "position")
    )
    grouped_product_videos = {k: list(v) for k, v in groupby(product_videos, key=lambda x: x.product.real_product.sku)}
    query = {"sku": product_id} if product_id else {}
    products_representation: list[ProductRepresentation] = list(
        ProductRepresentation.objects.filter(channel=channel, **query).values_list("sku", flat=True)
    )

    for product_sku, videos in grouped_product_videos.items():
        videos = sorted(videos, key=lambda x: x.language.iso2 if x.language else "")

        try:
            pr = ProductRepresentation.objects.get(sku=product_sku, channel=channel)
        except ObjectDoesNotExist:
            process_logger.delete_log_param("product_sku")
            process_logger.clear_db_operation()
            continue

        all_lang_prod_list = pr.t9ns.all().values_list("language__iso2", flat=True)
        final_by_lang = {}
        match LANGUAGE_VIDEO_IMPORT_TYPE:
            case LanguageVideoImportType.LANGUAGES_1_TO_1_AS_PIM:
                final_by_lang = {
                    k: list(v) for k, v in groupby(videos, key=lambda x: x.language.iso2 if x.language else "")
                }
            case LanguageVideoImportType.FILL_MISSING_LANGUAGES_WITH_DEFAULT:
                final_by_lang = {}
                grouped_product_videos_by_role = {k: list(v) for k, v in groupby(videos, key=lambda x: x.video_role)}
                for lang in all_lang_prod_list:
                    final_by_lang[lang] = []
                    for role, videos_role in grouped_product_videos_by_role.items():
                        videos_role = sorted(videos_role, key=lambda x: x.language.iso2 if x.language else "")
                        grouped_by_lang = {
                            k: list(v)
                            for k, v in groupby(videos_role, key=lambda x: x.language.iso2 if x.language else "")
                        }
                        if lang in grouped_by_lang.keys():
                            final_by_lang[lang].extend(grouped_by_lang[lang])
                        elif channel.default_language.iso2 in grouped_by_lang.keys():
                            final_by_lang[lang].extend(grouped_by_lang[channel.default_language.iso2])
                        else:
                            final_by_lang[lang].extend(list(grouped_by_lang.values())[0])
            case _:
                raise NotImplementedError(f"LanguageVideoImportType {LANGUAGE_VIDEO_IMPORT_TYPE} not implemented")

        for lang, videos_per_lang in final_by_lang.items():
            # make json videos for language, if video doesn't have language, it will be in stored in "all" key

            videos_for_product = []
            try:
                if product_sku in products_representation:
                    process_logger.add_log_param("product_sku", product_sku)
                    products_representation.remove(product_sku)
                for product_video in videos_per_lang:
                    source_set = []

                    video: Video = product_video.video
                    source_set.append(
                        SourceSet(title=video.title, url=video.video_url, source=video.get_source_label())
                    )

                    video_dto = VideoDTO(
                        position=product_video.position, role=product_video.get_role_api_label(), source_set=source_set
                    )
                    videos_for_product.append(video_dto.asdict())

                if not lang or lang == channel.default_language.iso2:
                    # if video has no language or is in default language, save it in videos
                    try:
                        pr.videos = videos_for_product
                        pr.save()
                        process_logger.set_db_operation("UPDATE", "django_matrix", "ProductRepresentation")
                        process_logger.set_code(2020)
                        process_logger.info(f"ProductRepresentation sku: {pr.sku} videos saved/updated.")
                    except Exception as e:
                        process_logger.set_code(4020)
                        process_logger.exception(e)

                if lang:
                    # if videos has language, save it in t9n_videos
                    try:
                        product_t9n = pr.t9ns.get(language__iso2=lang)
                        product_t9n.videos = videos_for_product
                        product_t9n.save()
                        process_logger.set_db_operation("UPDATE", "django_matrix", "ProductT9N")
                        process_logger.set_code(2022)
                        process_logger.info(f"ProductT9N video for lang {lang} sku: {pr.sku} videos saved/updated.")
                    except ObjectDoesNotExist:
                        process_logger.set_code(4023)
                        process_logger.exception(f"ProductT9N for lang {lang} not found.")
                    except Exception as e:
                        process_logger.set_code(4023)
                        process_logger.exception(e)

                process_logger.clear_db_operation()
                process_logger.delete_log_param("product_sku")

            except Exception as e:
                process_logger.set_code(4021)
                process_logger.exception(e)

    # usuwam video z pozostałych modeli, które nie mają zdjęć
    products = ProductRepresentation.objects.filter(sku__in=products_representation, channel=channel)
    for product in products:
        try:
            if not product.videos:
                continue
            product.videos = []

            process_logger.add_log_param_once("product_sku", product.sku)
            process_logger.set_db_operation("UPDATE", "django_matrix", "ProductRepresentation")
            process_logger.set_code(2021)
            process_logger.info(f"Remove product {product.sku} videos to keep them up to date.")
            product.save()
            process_logger.clear_db_operation()

        except Exception as e:
            process_logger.set_code(4022)
            process_logger.exception(e)

    products = ProductT9N.objects.filter(
        product_representation__sku__in=products_representation, product_representation__channel=channel
    )

    for product in products:
        try:
            if not product.videos:
                continue

            product.videos = []
            process_logger.add_log_param_once("product_sku", product.product_representation.sku)
            process_logger.set_db_operation("UPDATE", "django_matrix", "ProductT9N")
            process_logger.set_code(2023)
            process_logger.info(f"Remove product {product.sku} videos t9n to keep them up to date.")
            product.save()
            process_logger.clear_db_operation()
        except Exception as e:
            process_logger.set_code(4022)
            process_logger.exception(e)
