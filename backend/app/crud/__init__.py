"""
CRUD package.
"""

from app.crud.apiary import (
    count_hives_in_apiary,
    create_apiary,
    delete_apiary,
    get_apiary_by_id,
    list_apiaries_by_beekeeper,
    update_apiary,
)
from app.crud.beekeeper import (
    create_beekeeper_profile,
    get_beekeeper_by_code,
    get_beekeeper_by_user_id,
    update_beekeeper_profile,
)
from app.crud.hive import (
    count_harvests_for_hive,
    create_hive,
    delete_hive,
    get_hive_by_code_in_apiary,
    get_hive_by_id,
    list_hives_by_apiary,
    update_hive,
)
from app.crud.honey_batch import (
    create_batch,
    get_batch_by_code,
    get_batch_by_id,
    list_batches_by_beekeeper,
    update_batch,
)
from app.crud.honey_harvest import (
    create_harvest,
    get_allocated_batch_quantity,
    get_harvest_by_id,
    list_harvests_by_hive,
)
from app.crud.honey_product import (
    create_honey_product,
    get_product_by_id,
    get_product_by_serial,
    get_product_by_token,
    list_products_by_batch,
    list_products_by_beekeeper,
    update_product_status,
)
from app.crud.cart import (
    add_item_to_cart,
    clear_cart,
    get_or_create_buyer_cart,
    remove_item_from_cart,
)
from app.crud.iot import (
    InvalidAlertStateError,
    TelemetryConflictError,
    acknowledge_alert,
    create_hive_device,
    get_alert_by_id,
    get_device_by_token_hash,
    get_hive_device_by_hardware_id,
    get_hive_device_by_id,
    get_latest_hive_telemetry,
    list_devices_by_hive,
    list_hive_alerts,
    list_hive_telemetry,
    record_hive_telemetry,
    resolve_alert,
    touch_device_last_seen,
)
from app.crud.order import (
    confirm_order_payment,
    create_order_from_cart,
    get_order_by_id,
    get_order_by_number,
    list_orders_by_buyer,
)
from app.crud.traceability_event import (
    list_events_for_batch,
    list_events_for_product,
    record_event,
)
from app.crud.user import create_user, get_user_by_email, get_user_by_id

__all__ = [
    "get_user_by_email",
    "get_user_by_id",
    "create_user",
    "get_beekeeper_by_user_id",
    "get_beekeeper_by_code",
    "create_beekeeper_profile",
    "update_beekeeper_profile",
    "get_apiary_by_id",
    "list_apiaries_by_beekeeper",
    "create_apiary",
    "update_apiary",
    "delete_apiary",
    "count_hives_in_apiary",
    "get_hive_by_id",
    "get_hive_by_code_in_apiary",
    "list_hives_by_apiary",
    "create_hive",
    "update_hive",
    "delete_hive",
    "count_harvests_for_hive",
    "get_harvest_by_id",
    "list_harvests_by_hive",
    "create_harvest",
    "get_allocated_batch_quantity",
    "get_batch_by_id",
    "get_batch_by_code",
    "list_batches_by_beekeeper",
    "create_batch",
    "update_batch",
    "create_honey_product",
    "get_product_by_id",
    "get_product_by_serial",
    "get_product_by_token",
    "list_products_by_batch",
    "list_products_by_beekeeper",
    "update_product_status",
    "record_event",
    "list_events_for_product",
    "list_events_for_batch",
]
