# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from collections import defaultdict
from itertools import groupby

from django.core.exceptions import ObjectDoesNotExist
from django_utils.api.utils import make_media_url
from process_logger import ProcessLogger

from django_matrix.dto.view.picture import Picture as PictureDTO
from django_matrix.dto.view.picture import SourceSet
from django_matrix.models import Channel, ProductRepresentation, ProductT9N
from django_matrix.settings import LANGUAGE_IMAGE_IMPORT_TYPE

try:
    from django_pim.models import Picture, PictureRoleEnum, PictureThumb, Product, ProductPicture
except ImportError:
    raise Exception("django_matrix does not have access to django_pim module")


class LanguageImageImportType:
    # 1 - Import images for all languages 1:1 from pim to product t9n
    # 2 - Import images from pim, but if image in specific type is not found for language, use default language image or first found
    LANGUAGES_1_TO_1_AS_PIM = 1
    FILL_MISSING_LANGUAGES_WITH_DEFAULT = 2


def _resolve_alt_text(alt_t9n, lang, default_iso2):
    """Flatten PIM's per-language alt dict to the single string the read model stores.

    Fallback chain: requested language -> the channel's default language. No other keys are
    honoured (the legacy magic "default" key was cut — nothing in PIM/CMS ever wrote it).
    """
    if not alt_t9n:
        return None
    if lang:
        return alt_t9n.get(lang) or alt_t9n.get(default_iso2) or None
    return alt_t9n.get(default_iso2) or None


def fill_read_model_pictures_and_thumbs(channel: Channel, product_id: str = None):
    process_logger = ProcessLogger("FILL_READ_MODEL_PICTURES_AND_THUMBS")
    process_logger.add_log_param("channel_idx", channel.idx)

    query = {"product__real_product__sku": product_id} if product_id else {}
    product_pictures: list[ProductPicture] = (
        ProductPicture.objects.filter(product__shop__idx=channel.idx, **query)
        .prefetch_related("product", "picture")
        .order_by("product__real_product__sku", "position")
    )
    grouped_product_pictures = {
        k: list(v) for k, v in groupby(product_pictures, key=lambda x: x.product.real_product.sku)
    }
    query = {"sku": product_id} if product_id else {}
    products_representation: list[ProductRepresentation] = list(
        ProductRepresentation.objects.filter(channel=channel, **query).values_list("sku", flat=True)
    )

    for product_sku, pictures in grouped_product_pictures.items():
        pictures = sorted(pictures, key=lambda x: x.language.iso2 if x.language else "")

        try:
            pr = ProductRepresentation.objects.get(sku=product_sku, channel=channel)
        except ObjectDoesNotExist:
            process_logger.delete_log_param("product_sku")
            process_logger.clear_db_operation()
            continue

        all_lang_prod_list = pr.t9ns.all().values_list("language__iso2", flat=True)
        final_by_lang = {}
        match LANGUAGE_IMAGE_IMPORT_TYPE:
            case LanguageImageImportType.LANGUAGES_1_TO_1_AS_PIM:
                final_by_lang = {
                    k: list(v) for k, v in groupby(pictures, key=lambda x: x.language.iso2 if x.language else "")
                }
            case LanguageImageImportType.FILL_MISSING_LANGUAGES_WITH_DEFAULT:
                final_by_lang = {}
                main_pictures = {pic.picture for pic in pictures if pic.picture_role == PictureRoleEnum.MAIN}
                grouped_product_pictures_by_role = defaultdict(list)
                for picture in pictures:
                    if picture.picture_role != PictureRoleEnum.MAIN and picture.picture in main_pictures:
                        continue

                    grouped_product_pictures_by_role[picture.picture_role].append(picture)

                grouped_product_pictures_by_role = dict(grouped_product_pictures_by_role)
                for lang in all_lang_prod_list:
                    final_by_lang[lang] = []
                    for role, pictures_role in grouped_product_pictures_by_role.items():
                        pictures_role = sorted(pictures_role, key=lambda x: x.language.iso2 if x.language else "")
                        grouped_by_lang = {
                            k: list(v)
                            for k, v in groupby(pictures_role, key=lambda x: x.language.iso2 if x.language else "")
                        }
                        if lang in grouped_by_lang.keys():
                            final_by_lang[lang].extend(grouped_by_lang[lang])
                        elif channel.default_language.iso2 in grouped_by_lang.keys():
                            final_by_lang[lang].extend(grouped_by_lang[channel.default_language.iso2])
                        else:
                            final_by_lang[lang].extend(list(grouped_by_lang.values())[0])

        for lang, pictures_per_lang in final_by_lang.items():
            # make json pictures for language, if pictures doesn't have language, it will be in stored in "all" key

            pictures_for_product = []
            try:
                if product_sku in products_representation:
                    process_logger.add_log_param("product_sku", product_sku)
                    products_representation.remove(product_sku)
                for product_picture in pictures_per_lang:
                    source_set = []

                    picture: Picture = product_picture.picture
                    source_set.append(
                        SourceSet(source=make_media_url(str(picture.image)), width=picture.width, height=picture.height)
                    )

                    picture_thumbs: list[PictureThumb] = product_picture.picture.picture_thumbs.all()

                    for picture_thumb in picture_thumbs:
                        source_set.append(
                            SourceSet(
                                source=make_media_url(str(picture_thumb.thumb.image)),
                                width=picture_thumb.thumb.width,
                                height=picture_thumb.thumb.height,
                            )
                        )

                    alt_text = _resolve_alt_text(
                        getattr(product_picture, "alt_text_t9n", None), lang, channel.default_language.iso2
                    )

                    picture_dto = PictureDTO(
                        position=product_picture.position,
                        role=product_picture.get_role_api_label(),
                        source_set=source_set,
                        alt_text=alt_text,
                    )
                    pictures_for_product.append(picture_dto.asdict())

                if not lang or lang == channel.default_language.iso2:
                    # if picture has no language or is in default language, save it in pictures
                    try:
                        pr.pictures = pictures_for_product
                        # v2: resolve main_image — role=main first, then position=1 fallback
                        main_img = None
                        for pic in pictures_for_product:
                            if pic.get("role") == "main":
                                main_img = pic
                                break
                        if not main_img and pictures_for_product:
                            main_img = min(pictures_for_product, key=lambda p: p.get("position", 9999))
                        pr.main_image = main_img
                        pr.save()
                        process_logger.set_db_operation("UPDATE", "django_matrix", "ProductRepresentation")
                        process_logger.set_code(2016)
                        process_logger.info(f"ProductRepresentation sku: {pr.sku} pictures saved/updated.")
                    except Exception as e:
                        process_logger.set_code(4013)
                        process_logger.exception(e)

                if lang:
                    # if picture has language, save it in t9n_pictures
                    try:
                        product_t9n = pr.t9ns.get(language__iso2=lang)
                        product_t9n.pictures = pictures_for_product
                        product_t9n.save()
                        process_logger.set_db_operation("UPDATE", "django_matrix", "ProductT9N")
                        process_logger.set_code(2018)
                        process_logger.info(f"ProductT9N picture for lang {lang} sku: {pr.sku} pictures saved/updated.")
                    except ObjectDoesNotExist:
                        process_logger.set_code(4019)
                        process_logger.exception(f"ProductT9N for lang {lang} not found.")
                    except Exception as e:
                        process_logger.set_code(4019)
                        process_logger.exception(e)

                process_logger.clear_db_operation()
                process_logger.delete_log_param("product_sku")

            except Exception as e:
                process_logger.set_code(4014)
                process_logger.exception(e)

    # usuwam zdjęcia z pozostałych modeli, które nie mają zdjęć
    products = ProductRepresentation.objects.filter(sku__in=products_representation, channel=channel)
    for product in products:
        try:
            if not product.pictures:
                continue
            product.pictures = []

            process_logger.add_log_param_once("product_sku", product.sku)
            process_logger.set_db_operation("UPDATE", "django_matrix", "ProductRepresentation")
            process_logger.set_code(2017)
            process_logger.info(f"Remove product {product.sku} pictures to keep them up to date.")
            product.save()
            process_logger.clear_db_operation()

        except Exception as e:
            process_logger.set_code(4015)
            process_logger.exception(e)

    products = ProductT9N.objects.filter(
        product_representation__sku__in=products_representation, product_representation__channel=channel
    )

    for product in products:
        try:
            if not product.pictures:
                continue

            product.pictures = []
            process_logger.add_log_param_once("product_sku", product.product_representation.sku)
            process_logger.set_db_operation("UPDATE", "django_matrix", "ProductT9N")
            process_logger.set_code(2019)
            process_logger.info(f"Remove product {product.sku} pictures t9n to keep them up to date.")
            product.save()
            process_logger.clear_db_operation()
        except Exception as e:
            process_logger.set_code(4015)
            process_logger.exception(e)
