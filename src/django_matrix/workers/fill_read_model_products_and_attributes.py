# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import gc
import logging
from collections import defaultdict

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils import timezone
from django_regional.models import Language
from process_logger import ProcessLogger

from django_matrix import settings
from django_matrix.enums import Attributes, KindOfProduct, ProductType
from django_matrix.models import Attribute, Channel, ProductRepresentation, ProductT9N
from django_matrix.repository.orm.product import Product as ProductRepository
from django_matrix.settings import DELETE_WHEN_IMPORT_OLD_DATA_SAFETY_FACTOR

try:
    from django_pim.models import (
        BundleLink,
        ConfigurableLink,
        FeatureTypeEnum,
        Product,
        ProductAttribute,
        ProductInCategory,
        ProductLink,
    )
except ImportError:
    raise Exception("django_matrix does not have access to django_pim module")

from django_matrix.utils.timestamp_print import timestamp_print

POSITION_LAST = 9999999999
ITERATOR = 1000

logger = logging.getLogger()


def substring(text: str | None, max_chars: int = 1024):
    if text is not None:
        if len(text) > max_chars:
            logger.warning("Text cut to 1024 chars")
            return text[:max_chars]
        else:
            return text
    return text


def stale_rows(updated_at) -> Q:
    """Rows an earlier run stamped, or never stamped. A row with a newer stamp belongs to a later run and stays."""
    return Q(updated_at__lt=updated_at) | Q(updated_at__isnull=True)


def import_reviews_for_product(sku):
    # RuntimeError: an app that is installed but not in INSTALLED_APPS raises it on model import, not ImportError.
    try:
        from django_reviews.models import ProductRepresentation as PRReviews

        pr_review = PRReviews.objects.get(sku=sku)
        return pr_review.average_rate, pr_review.number_of_reviews
    except (ImportError, RuntimeError):
        return None, None
    except ObjectDoesNotExist:
        return None, None


def fill_read_model_products_and_attributes(channel: Channel, product_class: int, product_id: str = None):
    process_logger = ProcessLogger("FILL_READ_MODEL_PRODUCTS_AND_ATTRIBUTES")
    process_logger.add_log_param("channel_idx", channel.idx)
    process_logger.add_log_param("product_class", product_class)
    if product_id:
        process_logger.add_log_param("requested_sku", product_id)
    query = {"real_product__sku": product_id} if product_id else {}

    updated_at = timezone.now()

    # Find products to fill
    timestamp_print("Find products in PIM")
    pim_products = Product.objects.filter(shop__idx=channel.idx, product_class=product_class, **query).select_related(
        "real_product", "feature_set"
    )

    # Find all attributes for those products and cache them
    timestamp_print("Cache Product Attributes")
    product_attibutes_cache = {}
    products_attributes = (
        ProductAttribute.objects.filter(product__in=pim_products)
        .exclude(feature__feature_type=FeatureTypeEnum.UNKNOWN)
        .select_related("feature", "attribute", "product__real_product")
        .iterator(ITERATOR * 10)
    )
    for pa in products_attributes:
        sku = pa.product.real_product.sku
        if sku not in product_attibutes_cache:
            product_attibutes_cache[sku] = []
        product_attibutes_cache[sku].append(pa)
    del products_attributes

    # Find all configurable links for those products and cache them
    timestamp_print("Cache Product Configurable Links")
    configurable_links_cache = {}
    configurable_links = ConfigurableLink.objects.filter(subproduct__in=pim_products).select_related(
        "subproduct__real_product", "subproduct_attribute__attribute", "product_configurable__real_product"
    )
    for cl in configurable_links:
        sku = cl.subproduct.real_product.sku
        if sku not in configurable_links_cache:
            configurable_links_cache[sku] = []
        configurable_links_cache[sku].append(cl)
    del configurable_links

    # Find all bundle links for those products and cache them
    timestamp_print("Cache Product Bundle Links")
    bundle_links_cache = {}
    bundle_links = BundleLink.objects.filter(product_bundle__in=pim_products).select_related(
        "subproduct__real_product", "product_bundle__real_product"
    )
    for bl in bundle_links:
        sku = bl.product_bundle.real_product.sku
        child_sku = bl.subproduct.real_product.sku
        if sku not in bundle_links_cache:
            bundle_links_cache[sku] = []
        bundle_links_cache[sku].append(child_sku)
    del bundle_links

    # Product Representation cache
    timestamp_print("Cache Product Representation")
    product_representation_cache = {}
    prs = ProductRepresentation.objects.filter(channel=channel)
    for pr in prs:
        sku = pr.sku
        if sku not in product_representation_cache:
            product_representation_cache[sku] = pr
    del prs

    # Product Reviews cache
    timestamp_print("Cache Product Reviews")
    pr_reviews_cache = {}
    try:
        from django_reviews.models import ProductRepresentation as PRReviews

        channel_skus = pim_products.values_list("real_product__sku", flat=True)
        pr_reviews = PRReviews.objects.filter(sku__in=channel_skus).only("sku", "average_rate", "number_of_reviews")
        for pr_review in pr_reviews:
            sku = pr_review.sku
            if sku not in pr_reviews_cache:
                pr_reviews_cache[sku] = pr_review
        del pr_reviews
    except (ImportError, RuntimeError):
        pass

    # Categories cache
    timestamp_print("Cache Product Categories")
    product_categories_cache = {}
    pics = ProductInCategory.objects.filter(product__in=pim_products).select_related(
        "product__real_product", "category"
    )
    for pic in pics:
        sku = pic.product.real_product.sku
        if sku not in product_categories_cache:
            product_categories_cache[sku] = []
        product_categories_cache[sku].append(pic)
    del pics

    # Product links cache
    timestamp_print("Cache Product Links")
    product_links_cache = {}
    product_links = ProductLink.objects.filter(product__in=pim_products).select_related(
        "product__real_product", "linked_product__real_product", "link_type"
    )
    for pl in product_links:
        sku = pl.product.real_product.sku
        if sku not in product_links_cache:
            product_links_cache[sku] = []
        product_links_cache[sku].append(pl)
    del product_links

    # Languages cache
    timestamp_print("Cache Languages")
    languages_cache = {}
    for lang in Language.objects.all():
        languages_cache[lang.iso2] = lang

    product_repository = ProductRepository(channel)
    product_repository.set_logger(process_logger)
    product_repository.set_updated_at(updated_at)

    gc.collect()

    product_representation_to_save = {}
    product_t9n_to_save = {}
    attribute_to_save = {}

    timestamp_print("Prepare Product readmodel data")
    pim_products = pim_products.iterator(ITERATOR)
    for pim_product in pim_products:
        pim_product: Product
        sku = pim_product.real_product.sku
        process_logger.add_log_param("sku", sku)
        process_logger.add_log_param("product_class", pim_product.product_class)
        process_logger.add_log_param("is_enabled", pim_product.is_enabled)
        try:
            if not pim_product.is_enabled:
                process_logger.set_code(2001)
                process_logger.info(f"Product {pim_product.sku} skipped. It's disabled")
                continue

            products_attributes = product_attibutes_cache.get(sku, [])
            product_main_attributes = defaultdict(dict)
            product_filtrable_attributes = {}
            product_attributes_search = []
            product_url_keys = []
            tags = []

            for pa in products_attributes:
                process_logger.add_log_param("feature_idx", pa.feature.idx)
                try:
                    # Name, Desc, Short Desc, URL_KEY, Meta
                    if pa.feature.idx in [
                        Attributes.NAME,
                        Attributes.DESC,
                        Attributes.SHORT_DESC,
                        Attributes.URL_KEY,
                        Attributes.META_TITLE,
                        Attributes.META_DESCRIPTION,
                    ]:
                        main_attrs = product_repository.get_attribute_by_type(pa, pa.feature.feature_type)
                        if not isinstance(main_attrs, dict):
                            continue
                        for lang, attr_val in main_attrs.items():
                            product_main_attributes[lang][pa.feature.idx] = attr_val
                            # URL_KEY
                            if pa.feature.idx == Attributes.URL_KEY:
                                product_url_keys.append(attr_val)
                except Exception as e:
                    process_logger.set_code(4017)
                    process_logger.exception(e)

                try:
                    # fill search
                    # v2: use PIM is_searchable flag (Decision #11). Fallback to settings for v1 compat.
                    _is_searchable = getattr(pa.feature, "is_searchable", None)
                    if _is_searchable is True or (
                        _is_searchable is None and pa.feature.idx in settings.SEARCH_LIST_OF_FEATURES_IDX_MATRIX
                    ):
                        search_value = []
                        if pa.feature.feature_type in [FeatureTypeEnum.VARCHAR255, FeatureTypeEnum.TEXT]:
                            search_value = [product_repository.get_attribute_by_type(pa, pa.feature.feature_type)]
                        if pa.feature.feature_type in [FeatureTypeEnum.VARCHAR255_T9N, FeatureTypeEnum.TEXT_T9N]:
                            search_value_t9n = product_repository.get_attribute_by_type(pa, pa.feature.feature_type)
                            for lang, attr_val in search_value_t9n.items():
                                if attr_val:
                                    search_value.append(attr_val)

                        if pa.feature.feature_type in [FeatureTypeEnum.SELECT, FeatureTypeEnum.MULTISELECT]:
                            search_value_t9n, idx, extension = product_repository.get_attribute_by_type(
                                pa, pa.feature.feature_type
                            )
                            search_value = [search_value_t9n.get(channel.default_language.iso2, None)]

                        if search_value is not None and search_value not in product_attributes_search:
                            product_attributes_search.extend(search_value)

                except Exception as e:
                    process_logger.set_code(4017)
                    process_logger.exception(e)

                try:
                    # Badge, Brand, Subname
                    if pa.feature.idx in settings.PRODUCT_ADDITIONAL_ATTRIBUTES:
                        idx = None
                        extension = None
                        if pa.feature.feature_type in [FeatureTypeEnum.SELECT, FeatureTypeEnum.MULTISELECT]:
                            x, idx, extension = product_repository.get_attribute_by_type(pa, pa.feature.feature_type)
                        else:
                            x = product_repository.get_attribute_by_type(pa, pa.feature.feature_type)
                        feature_idx = pa.feature.idx
                        if feature_idx in [Attributes.SUBNAME1, Attributes.SUBNAME2]:
                            feature_idx = "subname"
                        for lang, attr_val in x.items():
                            if feature_idx not in product_main_attributes[lang]:
                                product_main_attributes[lang][feature_idx] = []
                            data_val = attr_val
                            if idx or extension:
                                data_val = {"idx": idx, "name": attr_val, "extension": extension}
                            product_main_attributes[lang][feature_idx].append(data_val)
                except Exception as e:
                    process_logger.set_code(4017)
                    process_logger.exception(e)

                try:
                    # Tags
                    if pa.feature.idx in [Attributes.TAGS_AUTOMATIC, Attributes.TAGS_MANUAL]:
                        x = product_repository.get_attribute_by_type(pa, pa.feature.feature_type)
                        tags.extend(x)
                        tags = list(set(tags))
                except Exception as e:
                    process_logger.set_code(4017)
                    process_logger.exception(e)

                try:
                    # For filtrable
                    if pa.feature.feature_type in [
                        FeatureTypeEnum.SELECT,
                        FeatureTypeEnum.MULTISELECT,
                        FeatureTypeEnum.TEXT,
                        FeatureTypeEnum.BOOL,
                        FeatureTypeEnum.DECIMAL,
                        FeatureTypeEnum.DATETIME,
                    ]:
                        if pa.feature.feature_type in [FeatureTypeEnum.SELECT, FeatureTypeEnum.MULTISELECT]:
                            x, value, extension = product_repository.get_attribute_by_type(pa, pa.feature.feature_type)
                        else:
                            value = product_repository.get_attribute_by_type(pa, pa.feature.feature_type)
                            if pa.feature.feature_type != FeatureTypeEnum.DATETIME:
                                value = int(value) if value.isdigit() else value

                        if pa.feature.idx in product_filtrable_attributes:
                            product_filtrable_attributes[pa.feature.idx].append(value)
                        else:
                            product_filtrable_attributes[pa.feature.idx] = [value]
                except Exception as e:
                    process_logger.set_code(4017)
                    process_logger.exception(e)

                try:
                    # mass/temperature/length: store the raw canonical value in attributes_filter (a list,
                    # like DECIMAL). Queried list-aware (any-in-range / MIN|MAX) and merged onto configurable
                    # parents by the parent block below, so configurable products keep their variants' values.
                    if pa.feature.feature_type in [
                        FeatureTypeEnum.MASS,
                        FeatureTypeEnum.TEMPERATURE,
                        FeatureTypeEnum.LENGTH,
                    ]:
                        if pa.value_decimal is not None:
                            value = float(pa.value_decimal)
                            if pa.feature.idx in product_filtrable_attributes:
                                product_filtrable_attributes[pa.feature.idx].append(value)
                            else:
                                product_filtrable_attributes[pa.feature.idx] = [value]
                except Exception as e:
                    process_logger.set_code(4017)
                    process_logger.exception(e)

                process_logger.delete_log_param("feature_idx")

            # Unique
            product_attributes_search = list(set(product_attributes_search))
            product_url_keys = list(set(product_url_keys))

            parents = configurable_links_cache.get(sku, [])
            rep_parent = None
            linking_attributes = []

            for parent in parents:
                # Chce znać, po jakich atrybutach nastąpiło powiązanie
                if parent.subproduct_attribute and parent.subproduct_attribute.attribute:
                    linking_attributes.append(parent.subproduct_attribute.attribute.idx)

            for parent in parents:
                # Zakładam ze simple moze miec jednego configa nad soba
                # Biore pierwsze powiazanie z brzegu. Dogadane z Kloczim

                try:
                    parent_sku = parent.product_configurable.sku
                    rep_parent = product_representation_cache.get(parent_sku, None)
                    if rep_parent:
                        parent_search = rep_parent.search
                        if product_attributes_search:
                            if isinstance(rep_parent.search, list) and parent_search:
                                rep_parent.search = list(set(parent_search + product_attributes_search))
                            else:
                                rep_parent.search = product_attributes_search

                        for feature_idx, attributes in product_filtrable_attributes.items():
                            if feature_idx in rep_parent.attributes_filter:
                                rep_parent.attributes_filter[feature_idx] = list(
                                    set(rep_parent.attributes_filter[feature_idx] + attributes)
                                )
                            else:
                                rep_parent.attributes_filter[feature_idx] = attributes
                        product_representation_cache[parent_sku] = rep_parent
                        product_representation_to_save[parent_sku] = rep_parent
                        break
                except Exception as e:
                    process_logger.set_code(4001)
                    process_logger.exception(e)

            pr_review = pr_reviews_cache.get(sku, None)
            average_rate = pr_review.average_rate if pr_review else None
            number_of_reviews = pr_review.number_of_reviews if pr_review else None

            categories_url_key = []
            categories_position = {}
            categories_data = []  # v2: [{idx, name, url_key}] for GA4
            for pic in product_categories_cache.get(sku, []):
                pic: ProductInCategory
                if pic:
                    position = pic.position if pic.position > 0 else POSITION_LAST
                else:
                    position = POSITION_LAST
                for url_key in pic.category.url_key_t9n.values():
                    categories_url_key.append(url_key)
                    categories_position[url_key] = position
                # v2: build categories_data from PIM category
                cat_name = pic.category.name_lang(channel.default_language.iso2 if channel.default_language else "en")
                cat_url_key = pic.category.url_key_t9n.get(
                    channel.default_language.iso2 if channel.default_language else "en", pic.category.idx
                )
                categories_data.append({"idx": pic.category.idx, "name": cat_name, "url_key": cat_url_key})

            feature_set = {}
            if pim_product.feature_set:
                feature_set = {
                    "idx": pim_product.feature_set.idx,
                    "name": pim_product.feature_set.name,
                    "desc": pim_product.feature_set.desc,
                    "is_default": pim_product.feature_set.is_default,
                }

            links_for_sku = product_links_cache.get(sku, [])
            have_product_links = len(links_for_sku) > 0
            product_links_data = [
                {
                    "linked_sku": pl.linked_product.real_product.sku,
                    "type": pl.link_type.idx if pl.link_type else "unknown",
                    "position": pl.position,
                }
                for pl in links_for_sku
            ] or None

            kind_of_product_value = KindOfProduct.map(pim_product.real_product.kind_of_product)
            pr = ProductRepresentation(
                sku=sku,
                channel=channel,
                product_type=ProductType.map(pim_product.product_class),
                kind_of_product=kind_of_product_value,
                parent=rep_parent,
                url_keys=product_url_keys,
                categories_url_key=categories_url_key,
                categories_position=categories_position,
                attributes_filter=product_filtrable_attributes,
                search=product_attributes_search,
                feature_set=feature_set,
                have_product_links=have_product_links,
                product_links=product_links_data,
                children=bundle_links_cache.get(sku, []),
                average_rating=average_rate,
                number_of_reviews=number_of_reviews,
                tags=tags,
                updated_at=updated_at,
                # v2 dual-write
                is_virtual=(kind_of_product_value == KindOfProduct.PRODUCT_VIRTUAL),
                categories_data=categories_data,
            )
            product_representation_to_save[sku] = pr
            process_logger.set_code(2024)
            process_logger.info(f"ProductRepresentation {sku} added to save queue sku")

            for lang, main_attr in product_main_attributes.items():
                process_logger.add_log_param("lang", lang)
                language = languages_cache.get(lang, None)
                if language is None:
                    process_logger.set_code(4026)
                    process_logger.error(f"Language {lang} does not exists in django_regional.Language")
                    continue

                pt = ProductT9N(
                    language=language,
                    name=substring(main_attr.get(Attributes.NAME, None)),
                    desc=main_attr.get(Attributes.DESC, None),
                    short_desc=main_attr.get(Attributes.SHORT_DESC, None),
                    url_key=substring(main_attr.get(Attributes.URL_KEY, None)),
                    badges=main_attr.get(Attributes.BADGE, None),
                    subnames=main_attr.get("subname", None),
                    brands=main_attr.get(Attributes.BRAND, None),
                    meta_title=main_attr.get(Attributes.META_TITLE, None),
                    meta_description=main_attr.get(Attributes.META_DESCRIPTION, None),
                    updated_at=updated_at,
                )

                if lang not in product_t9n_to_save:
                    product_t9n_to_save[lang] = {}
                product_t9n_to_save[lang][sku] = pt

                process_logger.set_code(2025)
                process_logger.info(f"ProductT9N {sku} {lang} added to save queue")

            attributes_for_skip = [
                Attributes.NAME,
                Attributes.DESC,
                Attributes.SHORT_DESC,
                Attributes.URL_KEY,
                Attributes.META_DESCRIPTION,
                Attributes.META_TITLE,
            ] + settings.PRODUCT_ADDITIONAL_ATTRIBUTES
            for pa in products_attributes:
                a = product_repository.build_attribute(pim_product, pa, attributes_for_skip, linking_attributes)
                if not a:
                    continue

                if sku not in attribute_to_save:
                    attribute_to_save[sku] = {}

                attribute_to_save[sku][a.hash] = a
                process_logger.add_log_param("feature_idx", pa.feature.idx)
                process_logger.set_code(2026)
                process_logger.info(f"Attribute {pa.feature.idx} for {sku} added to save queue")

        except Exception as e:
            process_logger.set_code(4007)
            process_logger.exception(e)

    del languages_cache
    del product_links_cache
    del product_categories_cache
    del pr_reviews_cache
    del configurable_links_cache
    del product_representation_cache
    del product_attibutes_cache
    del pim_products
    gc.collect()

    process_logger.delete_few_log_param(["sku", "is_enabled", "lang", "feature_idx", "feature_name"])

    timestamp_print("Saving products representations")

    stop_del_pr = False
    try:
        created, updated = product_repository.product_representation_bulk_update_or_create(
            product_representation_to_save
        )
    except Exception as e:
        stop_del_pr = True
        process_logger.set_code(4029)
        process_logger.exception(e)

    del product_representation_to_save
    gc.collect()

    for products_t9n in product_t9n_to_save.values():
        for sku, pt in products_t9n.items():
            pt: ProductT9N
            if sku in created:
                pr = created.get(sku)
            elif sku in updated:
                pr = updated.get(sku)
            else:
                process_logger.add_log_param("sku", sku)
                process_logger.set_code(3001)
                process_logger.warning("Can't find ProductRepresentation to assign to ProductT9n")
                continue
            pt.product_representation = pr

    timestamp_print("Saving products t9n")
    stop_del_t9n = False
    try:
        product_repository.product_t9n_bulk_save(product_t9n_to_save)
    except Exception as e:
        stop_del_t9n = True
        process_logger.set_code(4030)
        process_logger.exception(e)

    del product_t9n_to_save
    gc.collect()

    for sku, attributes in attribute_to_save.items():
        pt: ProductT9N
        if sku in created:
            pr = created.get(sku)
        elif sku in updated:
            pr = updated.get(sku)
        else:
            process_logger.add_log_param("sku", sku)
            process_logger.set_code(3001)
            process_logger.warning("Can't find ProductRepresentation to assign to Attribute")
            continue
        for a in attributes.values():
            a: Attribute
            a.product = pr

    stop_del_attr = False
    timestamp_print("Saving attributes")
    try:
        product_repository.attribute_bulk_save(attribute_to_save)
    except Exception as e:
        stop_del_attr = True
        process_logger.set_code(4031)
        process_logger.exception(e)

    del attribute_to_save
    gc.collect()

    timestamp_print("Removing old attributes")
    process_logger.clear_db_operation()
    query = {"product__sku": product_id} if product_id else {}

    attr = Attribute.objects.filter(
        product__channel=channel, product__product_type=ProductType.map(product_class), **query
    )
    attr_excluded = attr.filter(stale_rows(updated_at))
    if (
        attr_excluded.count() > DELETE_WHEN_IMPORT_OLD_DATA_SAFETY_FACTOR * attr.count() and attr.count() > 1
    ) or stop_del_attr:
        process_logger.add_log_param("total", attr.count())
        process_logger.add_log_param("to_delete", attr_excluded.count())
        process_logger.set_code(4032)
        process_logger.error("Too many attributes to delete. Operation stopped.")
    else:
        attr_excluded.delete()
        process_logger.set_db_operation("DELETE", "django_matrix", "Attribute")
        process_logger.set_code(2006)
        process_logger.info("All previous Attribute correlated have been deleted.")
        process_logger.clear_db_operation()

    timestamp_print("Removing old products t9n")
    process_logger.clear_db_operation()
    query = {"product_representation__sku": product_id} if product_id else {}

    product_t9n = ProductT9N.objects.filter(
        product_representation__channel=channel,
        product_representation__product_type=ProductType.map(product_class),
        **query,
    )
    product_t9n_excluded = product_t9n.filter(stale_rows(updated_at))

    if (
        product_t9n_excluded.count() > DELETE_WHEN_IMPORT_OLD_DATA_SAFETY_FACTOR * product_t9n.count()
        and product_t9n.count() > 1
    ) or stop_del_t9n:
        process_logger.add_log_param("total", product_t9n.count())
        process_logger.add_log_param("to_delete", product_t9n_excluded.count())
        process_logger.set_code(4033)
        process_logger.error("Too many ProductT9n to delete. Operation stopped.")
    else:
        product_t9n_excluded.delete()
        process_logger.set_db_operation("DELETE", "django_matrix", "ProductT9n")
        process_logger.set_code(2005)
        process_logger.info("All previous ProductT9n correlated have been deleted.")
        process_logger.clear_db_operation()

    timestamp_print("Removing old products representations")
    process_logger.clear_db_operation()
    query = {"sku": product_id} if product_id else {}

    product_representation = ProductRepresentation.objects.filter(
        channel=channel, product_type=ProductType.map(product_class), **query
    )
    product_representation_excluded = product_representation.filter(stale_rows(updated_at))
    if (
        product_representation_excluded.count()
        > DELETE_WHEN_IMPORT_OLD_DATA_SAFETY_FACTOR * product_representation.count()
        and product_representation.count() > 1
    ) or stop_del_pr:
        process_logger.add_log_param("total", product_representation.count())
        process_logger.add_log_param("to_delete", product_representation_excluded.count())
        process_logger.set_code(4034)
        process_logger.error("Too many ProductRepresentation to delete. Operation stopped.")
    else:
        product_representation_excluded.delete()
        process_logger.set_db_operation("DELETE", "django_matrix", "ProductRepresentation")
        process_logger.set_code(2003)
        process_logger.info("All previous ProductRepresentation have been deleted.")
        process_logger.clear_db_operation()
