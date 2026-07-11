# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import csv
from typing import AnyStr

from django.db import IntegrityError
from process_logger import ProcessLogger

from django_matrix.models.product_representation import ProductRepresentation

logger_process = ProcessLogger("FILL_PRODUCTS_MAGENTO_IDS")


def read_from_csv(absolute_path: AnyStr) -> (list, AnyStr):
    if absolute_path is not None:
        path = absolute_path
    else:
        return [], "Need to define csv path"
    with open(path) as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        data = []
        for row in reader:
            row_dict = {}
            for h, v in zip(headers, row):
                if v is None:
                    v = ""
                row_dict[h] = v
            data.append(row_dict)
    return data, "Loaded"


def creating_in_db_for_each_line(data, channel_idx):
    errors = 0
    number_ids_csv = len(data)
    products_to_update = []
    for row, product_data in enumerate(data):
        magento_id = product_data.get("id", None)
        product_sku = product_data.get("sku", None)
        logger_process.add_log_param("row", row)
        logger_process.add_log_param("magento_id", magento_id)
        logger_process.add_log_param("sku", product_sku)
        if not magento_id or not product_sku:
            errors += 1
            logger_process.error("Record skip. Data needed")
            continue

        products_sku = ProductRepresentation.objects.filter(sku=product_sku)
        if channel_idx:
            products_sku = products_sku.filter(channel__idx=channel_idx)
        if products_sku:
            for product in products_sku:
                products_to_update.append(ProductRepresentation(id=product.id, magento_id=magento_id))
        else:
            errors += 1
            logger_process.error("Record skip. This sku doesn't exists in ProductRepresentation")
        logger_process.delete_log_param("row")
        logger_process.delete_log_param("magento_id")
        logger_process.delete_log_param("sku")

    if products_to_update:
        try:
            ProductRepresentation.objects.bulk_update(products_to_update, ["magento_id"], batch_size=10000)
        except IntegrityError:
            error_list = []
            for product_to_update in products_to_update:
                try:
                    product_to_update.save(update_fields=["magento_id"])
                except IntegrityError as e:
                    errors += 1
                    error_sku_data = {
                        "sku": product_to_update.sku,
                        "magento_id": product_to_update.magento_id,
                        "message": str(e),
                    }
                    error_list.append(error_sku_data)
                if error_list:
                    logger_process.add_log_param_once("error_list", error_list)
                    logger_process.error("Errors while importing magento_id's")
    else:
        logger_process.add_log_param_once("data", data)
        logger_process.info("Nothing to update")

    return errors, number_ids_csv


def import_ids_from_csv(file_path: str, channel_idx: str):
    data, msg = read_from_csv(file_path)
    errors, number_ids_csv = creating_in_db_for_each_line(data, channel_idx)
    return errors, number_ids_csv
