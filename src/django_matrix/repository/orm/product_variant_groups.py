# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
ORM repository for product variant groups (django_pim.ProductVariantGroup).

Side-loaded into the product-detail response: given the requested SKU(s), returns the groups that
SKU OWNS (its own Magento cross slice) with localized labels and per-channel stock. Serving by owner
rather than membership avoids duplicate selectors — a product is listed as a member of many
overlapping same-label crosses, but only its own owned group should render on its page. Mirrors
repository/orm/variants.py but reads simple-product groups (no configurable parent) and derives
everything from existing Volkanos data — labels from name_t9n, stock from ProductRepresentation.
"""

from django_pim.models import ProductAttribute, ProductVariantGroup, ProductVariantGroupProduct
from django_regional.models import Country, Currency, Language

from django_matrix.dto.view.product_variants import ProductVariantDTO, ProductVariantGroupDTO
from django_matrix.models import Channel, ProductRepresentation


class ProductVariantGroups:
    channel: Channel
    language: Language

    def __init__(self, channel: Channel, language: Language, country: Country = None, currency: Currency = None):
        self.channel = channel
        self.language = language
        self.country = country
        self.currency = currency

    def get_language_iso(self) -> str:
        return self.language.iso2.lower()

    def build_for_skus(self, skus: list[str], asdict: bool = True) -> dict:
        """Return {sku: [variant group dicts]} for the requested SKUs (only those that own a group)."""
        iso = self.get_language_iso()

        owned_groups = ProductVariantGroup.objects.filter(
            owner__real_product__sku__in=skus,
            shop__idx=self.channel.idx,
            feature__isnull=False,
        ).select_related("feature", "owner__real_product")

        groups_by_id = {}
        groups_for_sku: dict[str, list] = {}
        for group in owned_groups:
            groups_by_id[group.id] = group
            groups_for_sku.setdefault(group.owner.real_product.sku, []).append(group)

        if not groups_by_id:
            return {}

        feature_ids = {group.feature_id for group in groups_by_id.values()}

        members_by_group: dict[int, list] = {}
        member_ids: set[int] = set()
        member_skus: set[str] = set()
        member_links = (
            ProductVariantGroupProduct.objects.filter(group_id__in=groups_by_id.keys(), product__is_enabled=True)
            .select_related("product__real_product")
            .order_by("group_id", "position")
        )
        for link in member_links:
            members_by_group.setdefault(link.group_id, []).append(link)
            member_ids.add(link.product_id)
            member_skus.add(link.product.real_product.sku)

        # Owner values are needed too: `selected` is decided by feature-value match against the owner,
        # not by member SKU. Magento's per-SKU cross sometimes returns a sibling SKU (wrong other-axis)
        # for the owner's own value, so a SKU-equality check never marks the current variant as selected.
        owner_ids = {group.owner_id for group in groups_by_id.values()}
        owner_skus = set(groups_for_sku.keys())

        value_by_product_feature = {}
        for pa in ProductAttribute.objects.filter(
            product_id__in=member_ids | owner_ids, feature_id__in=feature_ids, attribute__isnull=False
        ).select_related("attribute"):
            value_by_product_feature[(pa.product_id, pa.feature_id)] = pa.attribute

        on_stock_by_sku = dict(
            ProductRepresentation.objects.filter(channel=self.channel, sku__in=member_skus | owner_skus).values_list(
                "sku", "on_stock"
            )
        )

        result: dict[str, list] = {}
        for sku, groups in groups_for_sku.items():
            group_dtos = []
            for group in groups:
                owner_attribute = value_by_product_feature.get((group.owner_id, group.feature_id))
                variants = []
                for link in members_by_group.get(group.id, []):
                    member_sku = link.product.real_product.sku
                    attribute = value_by_product_feature.get((link.product_id, group.feature_id))
                    if attribute is None:
                        continue  # no value for the differentiating feature -> can't render a label
                    # The chip represents the current variant when its feature value matches the owner's,
                    # regardless of which sibling SKU import stored. Point that chip back at the owner so
                    # highlight and navigation are correct even when the stored member SKU is a
                    # wrong-other-axis sibling (Magento per-SKU cross inconsistency).
                    is_selected = owner_attribute is not None and attribute.id == owner_attribute.id
                    variant_sku = sku if is_selected else member_sku
                    # on_stock_by_sku is built from this channel's ProductRepresentation, so
                    # absence means the SKU has no page here (disabled or not published).
                    # Rendering the chip anyway would link the customer straight into a 404.
                    if variant_sku not in on_stock_by_sku:
                        continue
                    variants.append(
                        ProductVariantDTO(
                            sku=variant_sku,
                            label=attribute.name_lang(iso),
                            selected=is_selected,
                            on_stock=bool(on_stock_by_sku[variant_sku]),
                        )
                    )

                if len(variants) < 2:
                    continue

                dto = ProductVariantGroupDTO(
                    attribute_label=group.feature.name_lang(iso),
                    attribute_idx=group.feature.idx,
                    variants=variants,
                )
                group_dtos.append(dto.asdict() if asdict else dto)

            if group_dtos:
                result[sku] = group_dtos

        return result
