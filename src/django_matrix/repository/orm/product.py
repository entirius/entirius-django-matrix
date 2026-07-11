# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import gc

from django_pim.models import FeatureInFeatureSet, FeatureSet, FeatureTypeEnum, ProductAttribute
from django_pim.models import Product as PIMProduct
from process_logger import ProcessLoggerMixin

from django_matrix import settings
from django_matrix.enums import FeatureType
from django_matrix.models import Attribute, Channel, ProductRepresentation, ProductT9N
from django_matrix.utils import remove_trailing_zeros, split_dict_to_chunks


class Product(ProcessLoggerMixin):
    app_name: str = "django_matrix"
    BULK_BATCH_SIZE: int = 1000
    CHUNK_SIZE: int = 10000
    updated_at = None
    channel: Channel

    feature_sets_for_feature_cache: dict[str, list[FeatureSet]] = {}

    def __init__(self, channel: Channel):
        self.channel = channel

    def set_channel(self, channel: Channel):
        self.channel = channel

    def set_updated_at(self, updated_at):
        self.updated_at = updated_at

    def diff_update(self, entity, attribute, data, need_save: list):
        if getattr(entity, attribute) != data:
            setattr(entity, attribute, data)
            need_save.append(attribute)
        return entity

    def product_representation_bulk_update_or_create(self, products_respresentation: dict[str, ProductRepresentation]):
        # Chciałem tutaj tez uzyc bulk_create ale nie działało mi to z powodu tego ze unique ma Lower()
        create = products_respresentation
        update = {}
        result: list[ProductRepresentation] = ProductRepresentation.objects.prefetch_related("parent").filter(
            channel=self.channel, sku__in=products_respresentation.keys()
        )
        for in_db in result:
            updated_pr: ProductRepresentation = products_respresentation[in_db.sku]
            in_db.product_type = updated_pr.product_type
            in_db.kind_of_product = updated_pr.kind_of_product
            in_db.parent = updated_pr.parent
            in_db.url_keys = updated_pr.url_keys
            in_db.categories_url_key = updated_pr.categories_url_key
            in_db.categories_position = updated_pr.categories_position
            in_db.attributes_filter = updated_pr.attributes_filter
            in_db.search = updated_pr.search
            in_db.have_product_links = updated_pr.have_product_links
            in_db.product_links = updated_pr.product_links
            in_db.children = updated_pr.children
            in_db.tags = updated_pr.tags
            in_db.average_rating = updated_pr.average_rating
            in_db.number_of_reviews = updated_pr.number_of_reviews
            in_db.feature_set = updated_pr.feature_set
            in_db.updated_at = updated_pr.updated_at
            # v2 columns
            in_db.is_virtual = updated_pr.is_virtual
            in_db.main_image = updated_pr.main_image
            in_db.categories_data = updated_pr.categories_data
            update[in_db.sku] = in_db
            create.pop(in_db.sku)

        created = {}
        if len(create) > 0:
            create_chunks = list(split_dict_to_chunks(create, self.CHUNK_SIZE))
            for create_chunk in create_chunks:
                self.logger.set_db_operation("BULK_CREATE", self.app_name, "ProductRepresentation")
                prs = ProductRepresentation.objects.bulk_create(create_chunk.values(), batch_size=self.BULK_BATCH_SIZE)
                for ps in prs:
                    created[ps.sku] = ps
                self.logger.set_code(2002)
                self.logger.info(f"ProductRepresentation created in bulk: {len(create_chunk)}")

        if len(update) > 0:
            update_chunks = list(split_dict_to_chunks(update, self.CHUNK_SIZE))
            for update_chunk in update_chunks:
                self.logger.set_db_operation("BULK_UPDATE", self.app_name, "ProductRepresentation")
                updated = ProductRepresentation.objects.bulk_update(
                    update_chunk.values(),
                    fields=[
                        "product_type",
                        "kind_of_product",
                        "parent",
                        "url_keys",
                        "categories_url_key",
                        "categories_position",
                        "attributes_filter",
                        "search",
                        "have_product_links",
                        "product_links",
                        "children",
                        "tags",
                        "average_rating",
                        "number_of_reviews",
                        "feature_set",
                        "updated_at",
                        # v2 columns
                        "is_virtual",
                        "main_image",
                        "categories_data",
                    ],
                    batch_size=self.BULK_BATCH_SIZE,
                )
                self.logger.set_code(2002)
                self.logger.info(f"ProductRepresentation updated in bulk: {updated}")

        return created, update

    def product_t9n_bulk_save(self, products_t9n: dict[str, dict[str, ProductT9N]]):
        for lang, products in products_t9n.items():
            self.logger.add_log_param("lang", lang)
            if len(products) > 0:
                self.logger.set_db_operation("BULK_SAVE", self.app_name, "ProductT9N")
                ProductT9N.objects.bulk_create(
                    products.values(),
                    batch_size=self.BULK_BATCH_SIZE,
                    update_conflicts=True,
                    update_fields=[
                        "name",
                        "desc",
                        "short_desc",
                        "url_key",
                        "badges",
                        "subnames",
                        "brands",
                        "meta_title",
                        "meta_description",
                        "updated_at",
                    ],
                    unique_fields=["product_representation", "language"],
                )
                self.logger.set_code(2004)
                self.logger.info(f"ProductT9N {lang} saved in bulk: {len(products)}")

    def get_attribute_by_type(
        self, product_attribute: ProductAttribute, feature_type: int, langs: list[str] | None = None
    ) -> str | dict | None | tuple[dict | None, str | None, any]:
        if feature_type == FeatureTypeEnum.BOOL:
            return "True" if product_attribute.value_bool else "False"

        if feature_type == FeatureTypeEnum.DECIMAL:
            return str(remove_trailing_zeros(product_attribute.value_decimal))

        if feature_type in (FeatureTypeEnum.JSON, FeatureTypeEnum.JSON_T9N):
            return product_attribute.value_json

        if feature_type in (FeatureTypeEnum.VARCHAR255, FeatureTypeEnum.TEXT):
            if not product_attribute.value_txt:
                return None
            return product_attribute.value_txt

        if feature_type in (FeatureTypeEnum.LENGTH, FeatureTypeEnum.MASS, FeatureTypeEnum.TEMPERATURE):
            return product_attribute.get_value(langs=langs)

        if feature_type == FeatureTypeEnum.DATETIME:
            try:
                formated_date = product_attribute.value_datetime.strftime(settings.MATRIX_DATETIME_FORMAT)
                return formated_date
            except AttributeError:
                raise Exception("Can not get_attribute_by_type() of feature_type=DATETIME. It is not a datetime object")

        if feature_type == FeatureTypeEnum.SELECT:
            if product_attribute.attribute is None:
                return None, None, None
            return (
                product_attribute.attribute.name_t9n,
                product_attribute.attribute.idx,
                product_attribute.attribute.extension,
            )

        if feature_type == FeatureTypeEnum.MULTISELECT:
            if product_attribute.attribute is None:
                return None, None, None
            return (
                product_attribute.attribute.name_t9n,
                product_attribute.attribute.idx,
                product_attribute.attribute.extension,
            )

        if feature_type in (FeatureTypeEnum.VARCHAR255_T9N, FeatureTypeEnum.TEXT_T9N):
            if not product_attribute.value_txt_t9n:
                return None
            return {k: v for k, v in product_attribute.value_txt_t9n.items() if v}

        raise Exception(f"Can not get_attribute_by_type() of feature_type={feature_type}")

    def build_attribute(
        self, product: PIMProduct, pa: ProductAttribute, attributes_for_skip: list[str], linking_attributes: list = None
    ) -> Attribute | None:
        if linking_attributes is None:
            linking_attributes = []

        self.logger.add_log_param("feature_idx", pa.feature.idx)
        if self.logger.get_locale() in pa.feature.name_t9n:
            self.logger.add_log_param("feature_name", pa.feature.name_t9n[self.logger.get_locale()])

        if pa.feature.idx in attributes_for_skip:
            self.logger.set_code(2007)
            self.logger.info(
                f"Attribute skipped bcs of idx: {pa.feature.idx}. This attribute has likely been saved in Product"
            )
            self.logger.delete_few_log_param(["feature_idx", "feature_name"])
            return None

        # Cache: {feature_idx: [(feature_set_idx, group_idx, group_name_t9n, position)]}
        if pa.feature.idx not in self.feature_sets_for_feature_cache:
            self.feature_sets_for_feature_cache[pa.feature.idx] = list(
                FeatureInFeatureSet.objects.filter(feature=pa.feature)
                .select_related("attributes_group")
                .values_list("feature_set__idx", "attributes_group__idx", "attributes_group__name_t9n", "position")
            )
        fis_data = self.feature_sets_for_feature_cache[pa.feature.idx]
        feature_sets = [row[0] for row in fis_data]

        if product.feature_set and product.feature_set.idx not in feature_sets:
            self.logger.set_code(2027)
            self.logger.info(
                f"Attribute skipped bcs of feature_set: {product.feature_set.idx} not matched with feature: {pa.feature.idx} feature sets"
            )
            self.logger.delete_few_log_param(["feature_idx", "feature_name"])
            return None

        idx = None
        if pa.feature.feature_type in [FeatureTypeEnum.SELECT, FeatureTypeEnum.MULTISELECT]:
            val, idx, extension = self.get_attribute_by_type(pa, pa.feature.feature_type)
            linking = True if idx in linking_attributes else False
            values = {"attribute_idx": idx, "attribute_value_t9n": val, "linking": linking, "extension": extension}
        elif pa.feature.feature_type in [FeatureTypeEnum.TEXT_T9N, FeatureTypeEnum.VARCHAR255_T9N]:
            val = self.get_attribute_by_type(pa, pa.feature.feature_type)
            values = {"attribute_value_t9n": val}
        elif pa.feature.feature_type in [FeatureTypeEnum.JSON, FeatureTypeEnum.JSON_T9N]:
            val = self.get_attribute_by_type(pa, pa.feature.feature_type)
            values = {"attribute_value_json": val}
        elif pa.feature.feature_type in [FeatureTypeEnum.TEMPERATURE, FeatureTypeEnum.LENGTH, FeatureTypeEnum.MASS]:
            val = self.get_attribute_by_type(
                pa, pa.feature.feature_type, langs=list(self.channel.languages.all().values_list("iso2", flat=True))
            )
            values = {"attribute_value_t9n": val}
        else:
            val = self.get_attribute_by_type(pa, pa.feature.feature_type)
            values = {"attribute_value_text": val}

        if not val:
            self.logger.set_code(2018)
            self.logger.info("Attribute skipped. This product attribute has empty value.")
            self.logger.add_log_param("feature_idx", pa.feature.idx)
            self.logger.add_log_param("sku", pa.product.real_product.sku)
            self.logger.delete_few_log_param(["feature_idx", "feature_name"])
            return None

        # v2 read model gate: skip attributes without any front-facing flag
        _is_visible = getattr(pa.feature, "is_visible", True)
        _has_visual_asset = getattr(pa.feature, "has_visual_asset", False)
        _is_comparable = getattr(pa.feature, "is_comparable", False)
        _is_seo = getattr(pa.feature, "is_seo", False)
        if not (_is_visible or _has_visual_asset or _is_comparable or _is_seo):
            self.logger.set_code(2028)
            self.logger.info(f"Attribute skipped: no front-facing flag for feature {pa.feature.idx}")
            return None

        # Resolve attribute group from FeatureInFeatureSet for this product's feature_set
        group_idx = None
        group_name_t9n = None
        group_position = None
        if product.feature_set:
            for fs_idx, g_idx, g_name_t9n, pos in fis_data:
                if fs_idx == product.feature_set.idx:
                    group_idx = g_idx
                    group_name_t9n = g_name_t9n
                    group_position = pos
                    break

        a = Attribute(
            feature_idx=pa.feature.idx,
            feature_is_for_customization=getattr(pa.feature, "is_for_customization", False),
            feature_name_t9n=pa.feature.name_t9n,
            feature_type=FeatureType.map(pa.feature.feature_type),
            updated_at=self.updated_at,
            # v2 flags from PIM Feature
            is_visible=_is_visible,
            has_visual_asset=_has_visual_asset,
            is_comparable=_is_comparable,
            is_seo=_is_seo,
            # Attribute group from PIM FeatureInFeatureSet
            group_idx=group_idx,
            group_name_t9n=group_name_t9n,
            group_position=group_position,
            **values,
        )
        a.hash = a.generate_hash()
        return a

    def attribute_bulk_save(self, attributes: dict[str, dict[str, Attribute]]):
        create = []
        for attrs in attributes.values():
            for attr in attrs.values():
                create.append(attr)

        del attributes
        gc.collect()

        if len(create) > 0:
            self.logger.set_db_operation("BULK_SAVE", self.app_name, "Attribute")
            Attribute.objects.bulk_create(
                create,
                batch_size=self.BULK_BATCH_SIZE,
                update_conflicts=True,
                update_fields=[
                    "feature_idx",
                    "feature_name_t9n",
                    "feature_type",
                    "feature_is_for_customization",
                    "attribute_idx",
                    "attribute_value_text",
                    "attribute_value_t9n",
                    "attribute_value_json",
                    "extension",
                    "linking",
                    "updated_at",
                    # v2 flags
                    "is_visible",
                    "has_visual_asset",
                    "is_comparable",
                    "is_seo",
                    # v2 attribute group
                    "group_idx",
                    "group_name_t9n",
                    "group_position",
                ],
                unique_fields=["product", "hash"],
            )
            self.logger.set_code(2008)
            self.logger.info(f"Attribute saved in bulk: {len(create)}")
