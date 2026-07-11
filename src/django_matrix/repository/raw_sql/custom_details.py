# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django_utils.api.exceptions import BadRequest
from django_utils.api.utils import make_media_url

from django_matrix import settings
from django_matrix.dto.view.picture import Picture as PictureDTO
from django_matrix.dto.view.picture import SourceSet
from django_matrix.enums import ProductType
from django_matrix.models import ProductRepresentation


class CustomDetails:
    def __init__(self, params, channel, language, country, currency):
        self.params = params
        self.channel = channel
        self.language = language
        self.country = country
        self.currency = currency

    def get_attributes_details(self):

        from django_pim.models import FeatureType, ProductAttribute

        try:
            from django_pricemanager.output_custom import get_product_custom_price_for_country_and_currency
        except ImportError:
            raise Exception("Custom product pricing requires django_pricemanager")

        # find product custom
        product_custom = ProductRepresentation.objects.filter(
            sku=self.params.basic_sku, product_type=ProductType.PRODUCT_CUSTOM, channel=self.channel
        ).first()

        if not product_custom:
            raise Exception("Product custom not found")
        product_custom_sku = product_custom.sku
        msg = []

        # get choosen/default attributes for custom
        attrs_choosen_or_default_custom, all_attr_modifier, errors = ProductAttribute.objects.get_custom_attributes_idx(
            product_custom_sku, [v for k, v in self.params.chosen_f9e_to_a9e.items()], channel_idx=self.channel.idx
        )
        attrs_choosen_or_default_custom = attrs_choosen_or_default_custom.values_list("idx", "feature__idx")

        lowered_iso2_language = self.language.iso2.lower()

        product_attr_specification_sorted = ProductAttribute.objects.get_custom_attributes_details(
            self.params.basic_sku, all_attr_modifier, self.channel.idx, lowered_iso2_language
        )
        attr_specification = []
        for feature, attr in product_attr_specification_sorted.items():
            attr_specification.append(
                {
                    "sku": product_custom_sku,
                    "feature_idx": feature,
                    "feature_name": attr[1],
                    "feature_type": FeatureType.labelFromId(attr[2]),
                    "attribute_value": attr[0],
                    "attribute_idx": None,
                }
            )

        # get price for custom product
        price = get_product_custom_price_for_country_and_currency(
            product_custom_sku,
            [attr[0] for attr in attrs_choosen_or_default_custom],
            self.channel.idx,
            self.country.iso2,
            self.currency.iso3,
        )["price"]

        return attr_specification, attrs_choosen_or_default_custom, price, msg, errors

    def get_pictures(self, attr_result_list):

        try:
            from django_pim.models import Picture, PictureRole, PictureThumb, Product, ProductAttributeCustomImage
            from django_pim.utils.pim_image_resizer import PimImageResizer
        except ImportError:
            raise BadRequest("django_matrix does not have access to django_pim module")

        product = Product.objects.get(real_product__sku=self.params.basic_sku, shop__idx=self.channel.idx)
        product_picture = ProductAttributeCustomImage.objects.get_or_create_image(product, attr_result_list)

        worker = PimImageResizer()
        config = settings.THUMBS_CONFIG
        if config is None:
            raise BadRequest("Image resizer config is invalid")
        worker.resize_pictures([product_picture], config)

        source_set = [
            SourceSet(
                source=make_media_url(str(product_picture.image)),
                width=product_picture.width,
                height=product_picture.height,
            )
        ]
        picture_thumbs: list[PictureThumb] = product_picture.picture_thumbs.all()

        for picture_thumb in picture_thumbs:
            source_set.append(
                SourceSet(
                    source=make_media_url(str(picture_thumb.thumb.image)),
                    width=picture_thumb.thumb.width,
                    height=picture_thumb.thumb.height,
                )
            )

        picture_dto = PictureDTO(
            position=product.main_product_picture.position,
            role=PictureRole.labelFromId(product.main_product_picture.picture_role),
            source_set=source_set,
        )
        return picture_dto.asdict(), []
