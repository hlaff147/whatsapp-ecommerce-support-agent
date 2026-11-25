"""CLI idempotente para popular dados sintéticos no MySQL."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from pawdesk.adapters.outbound.persistence.mysql.engine import (
    create_mysql_engine,
    create_session_factory,
)
from pawdesk.adapters.outbound.persistence.mysql.mappers import to_mysql_naive_utc
from pawdesk.adapters.outbound.persistence.mysql.models import (
    CustomerModel,
    OrderItemModel,
    OrderModel,
    ProductModel,
    ShipmentEventModel,
    ShipmentModel,
)
from pawdesk.bootstrap.seed_data import build_seed_dataset
from pawdesk.bootstrap.settings import get_settings


async def seed_database() -> None:
    settings = get_settings()
    dataset = build_seed_dataset(datetime.now(UTC), settings.pseudonym_secret)
    engine = create_mysql_engine(settings.mysql_dsn, null_pool=True)
    factory = create_session_factory(engine)
    try:
        async with factory() as session, session.begin():
            for prod in dataset.products:
                if await session.get(ProductModel, prod.sku) is None:
                    session.add(
                        ProductModel(
                            sku=prod.sku,
                            name=prod.name,
                            species=prod.species,
                            category=prod.category,
                            price_amount=prod.price.amount,
                            in_stock=prod.in_stock,
                            weight_kg=prod.weight_kg,
                            description=prod.description,
                        )
                    )

            for cust in dataset.customers:
                existing = (
                    await session.execute(
                        select(CustomerModel).where(CustomerModel.id == cust.id.value)
                    )
                ).scalar_one_or_none()
                if existing is None:
                    session.add(
                        CustomerModel(
                            id=cust.id.value,
                            first_name=cust.first_name,
                            phone_e164=cust.phone.value,
                            cpf_last3=cust.cpf_last3,
                            cpf_hash=cust.cpf_hash,
                        )
                    )

            for order in dataset.orders:
                if await session.get(OrderModel, order.number.value) is None:
                    session.add(
                        OrderModel(
                            number=order.number.value,
                            customer_id=order.customer_id.value,
                            status=order.status.value,
                            total_amount=order.total.amount,
                            currency=order.total.currency,
                            placed_at=to_mysql_naive_utc(order.placed_at),
                            delivered_at=to_mysql_naive_utc(order.delivered_at),
                            estimated_delivery_at=to_mysql_naive_utc(order.estimated_delivery_at),
                            items=[
                                OrderItemModel(
                                    sku=item.sku,
                                    name=item.name,
                                    quantity=item.quantity,
                                    unit_price=item.unit_price.amount,
                                    category=item.category,
                                    returnable=item.returnable,
                                )
                                for item in order.items
                            ],
                        )
                    )

            for ship in dataset.shipments:
                if await session.get(ShipmentModel, ship.order_number.value) is None:
                    session.add(
                        ShipmentModel(
                            order_number=ship.order_number.value,
                            carrier_name=ship.carrier_name,
                            tracking_code=ship.tracking_code.value,
                            tracking_url=ship.tracking_url,
                            status=ship.status.value,
                            estimated_delivery_at=to_mysql_naive_utc(ship.estimated_delivery_at),
                            delivered_at=to_mysql_naive_utc(ship.delivered_at),
                            events=[
                                ShipmentEventModel(
                                    occurred_at=to_mysql_naive_utc(ev.occurred_at),
                                    status=ev.status,
                                    location=ev.location,
                                    description=ev.description,
                                )
                                for ev in ship.events
                            ],
                        )
                    )
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(seed_database())
    print("Seed sintético concluído com sucesso.")


if __name__ == "__main__":
    main()
