"""Dados sintéticos determinísticos alinhados às personas e casos de uso do PawDesk."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from pawdesk.domain.constants import OrderStatus, ShipmentStatus
from pawdesk.domain.entities.customer import Customer
from pawdesk.domain.entities.order import Order, OrderItem
from pawdesk.domain.entities.product import Product
from pawdesk.domain.entities.shipment import Shipment, ShipmentEvent
from pawdesk.domain.value_objects.ids import CustomerId, OrderNumber
from pawdesk.domain.value_objects.money import Money
from pawdesk.domain.value_objects.phone import PhoneE164
from pawdesk.domain.value_objects.tracking_code import TrackingCode
from pawdesk.shared.utils.dates import add_business_days
from pawdesk.shared.utils.hashing import hmac_sha256


@dataclass(frozen=True)
class SeedDataset:
    customers: tuple[Customer, ...]
    orders: tuple[Order, ...]
    shipments: tuple[Shipment, ...]
    products: tuple[Product, ...]


def build_seed_dataset(now: datetime, pseudonym_secret: str) -> SeedDataset:
    """Constrói personas (Marina, Carlos, Bia), pedidos, rastreios e catálogo sintético."""
    customers = (
        Customer(
            id=CustomerId("CUS_MARINA_001"),
            first_name="Marina",
            phone=PhoneE164("+5511999990001"),
            cpf_last3="456",
            cpf_hash=hmac_sha256("12345678456", pseudonym_secret),
        ),
        Customer(
            id=CustomerId("CUS_CARLOS_002"),
            first_name="Carlos",
            phone=PhoneE164("+5511999990002"),
            cpf_last3="789",
            cpf_hash=hmac_sha256("23456789789", pseudonym_secret),
        ),
        Customer(
            id=CustomerId("CUS_BIA_003"),
            first_name="Bia",
            phone=PhoneE164("+5511999990003"),
            cpf_last3="321",
            cpf_hash=hmac_sha256("34567890321", pseudonym_secret),
        ),
    )

    today_0840 = now.replace(hour=11, minute=40, second=0, microsecond=0)  # 08:40 BRT em UTC
    today_1800 = now.replace(hour=21, minute=0, second=0, microsecond=0)  # 18:00 BRT em UTC
    if today_1800 <= now:
        today_1800 = now + timedelta(hours=6)

    # 5 dias úteis atrás (Bia - pedido criticamente atrasado -> dispara RN-04 handoff)
    late_5bd_eta = now - timedelta(days=8)
    # 1 dia útil atrás (Bia - atraso leve <= 3 dias úteis -> informa sem handoff automático)
    late_1bd_eta = now - timedelta(days=1)

    orders = (
        # Marina: saiu para entrega hoje (exemplo do documento de negócio!)
        Order(
            number=OrderNumber("PD-104822"),
            customer_id=CustomerId("CUS_MARINA_001"),
            status=OrderStatus.OUT_FOR_DELIVERY,
            items=(
                OrderItem(
                    sku="RAC-GAT-10KG",
                    name="Ração Premium Gatos Castrados 10kg",
                    quantity=1,
                    unit_price=Money(Decimal("189.90")),
                    category="RACAO",
                    returnable=True,
                ),
            ),
            total=Money(Decimal("189.90")),
            placed_at=now - timedelta(days=2),
            estimated_delivery_at=today_1800,
        ),
        # Marina: pedido anterior entregue
        Order(
            number=OrderNumber("PD-104510"),
            customer_id=CustomerId("CUS_MARINA_001"),
            status=OrderStatus.DELIVERED,
            items=(
                OrderItem(
                    sku="ARE-HIG-4KG",
                    name="Areia Higiênica Biodegradável 4kg",
                    quantity=2,
                    unit_price=Money(Decimal("49.90")),
                    category="HIGIENE",
                    returnable=True,
                ),
            ),
            total=Money(Decimal("99.80")),
            placed_at=now - timedelta(days=12),
            delivered_at=now - timedelta(days=9),
            estimated_delivery_at=now - timedelta(days=9),
        ),
        # Carlos: tutor de primeira viagem, pedido em separação
        Order(
            number=OrderNumber("PD-104901"),
            customer_id=CustomerId("CUS_CARLOS_002"),
            status=OrderStatus.PICKING,
            items=(
                OrderItem(
                    sku="RAC-FIL-3KG",
                    name="Ração Super Premium Cães Filhotes 3kg",
                    quantity=1,
                    unit_price=Money(Decimal("119.90")),
                    category="RACAO",
                    returnable=True,
                ),
                OrderItem(
                    sku="BRQ-MOR-01",
                    name="Brinquedo Mordedor Filhote Macio",
                    quantity=1,
                    unit_price=Money(Decimal("39.90")),
                    category="ACESSORIO",
                    returnable=True,
                ),
            ),
            total=Money(Decimal("159.80")),
            placed_at=now - timedelta(hours=6),
            estimated_delivery_at=add_business_days(now, 2),
        ),
        # Bia: pedido muito atrasado (> 3 dias úteis) -> RN-04 handoff
        Order(
            number=OrderNumber("PD-104300"),
            customer_id=CustomerId("CUS_BIA_003"),
            status=OrderStatus.SHIPPED,
            items=(
                OrderItem(
                    sku="RAC-CAE-15KG",
                    name="Ração Cães Adultos Porte Médio 15kg",
                    quantity=1,
                    unit_price=Money(Decimal("239.90")),
                    category="RACAO",
                    returnable=True,
                ),
            ),
            total=Money(Decimal("239.90")),
            placed_at=now - timedelta(days=14),
            estimated_delivery_at=late_5bd_eta,
        ),
        # Bia: pedido com atraso leve (1 dia)
        Order(
            number=OrderNumber("PD-104750"),
            customer_id=CustomerId("CUS_BIA_003"),
            status=OrderStatus.SHIPPED,
            items=(
                OrderItem(
                    sku="PET-NAT-100G",
                    name="Petisco Natural Frango Desidratado 100g",
                    quantity=2,
                    unit_price=Money(Decimal("24.90")),
                    category="PETISCO",
                    returnable=True,
                ),
            ),
            total=Money(Decimal("49.80")),
            placed_at=now - timedelta(days=4),
            estimated_delivery_at=late_1bd_eta,
        ),
    )

    shipments = (
        Shipment(
            order_number=OrderNumber("PD-104822"),
            carrier_name="PetLog Express",
            tracking_code=TrackingCode("PL104822BR"),
            tracking_url="https://rastreio.pawdesk.example/PL104822BR",
            status=ShipmentStatus.OUT_FOR_DELIVERY,
            estimated_delivery_at=today_1800,
            events=(
                ShipmentEvent(
                    occurred_at=now - timedelta(days=1),
                    status="IN_TRANSIT",
                    location="Centro de Distribuição São Paulo - SP",
                    description="Pedido em trânsito para a base local.",
                ),
                ShipmentEvent(
                    occurred_at=today_0840,
                    status="OUT_FOR_DELIVERY",
                    location="São Paulo - SP",
                    description="Saiu para entrega ao destinatário.",
                ),
            ),
        ),
        Shipment(
            order_number=OrderNumber("PD-104510"),
            carrier_name="PetLog Express",
            tracking_code=TrackingCode("PL104510BR"),
            tracking_url="https://rastreio.pawdesk.example/PL104510BR",
            status=ShipmentStatus.DELIVERED,
            estimated_delivery_at=now - timedelta(days=9),
            delivered_at=now - timedelta(days=9),
            events=(
                ShipmentEvent(
                    occurred_at=now - timedelta(days=9),
                    status="DELIVERED",
                    location="São Paulo - SP",
                    description="Entregue com assinatura no recebimento.",
                ),
            ),
        ),
        Shipment(
            order_number=OrderNumber("PD-104901"),
            carrier_name="PetLog Express",
            tracking_code=TrackingCode("PL104901BR"),
            tracking_url="https://rastreio.pawdesk.example/PL104901BR",
            status=ShipmentStatus.LABEL_CREATED,
            estimated_delivery_at=add_business_days(now, 2),
            events=(
                ShipmentEvent(
                    occurred_at=now - timedelta(hours=3),
                    status="LABEL_CREATED",
                    location="Armazém Barueri - SP",
                    description="Pedido em separação no estoque.",
                ),
            ),
        ),
        Shipment(
            order_number=OrderNumber("PD-104300"),
            carrier_name="BrasilPet Encomendas",
            tracking_code=TrackingCode("BP104300BR"),
            tracking_url="https://rastreio.pawdesk.example/BP104300BR",
            status=ShipmentStatus.DELAYED,
            estimated_delivery_at=late_5bd_eta,
            events=(
                ShipmentEvent(
                    occurred_at=now - timedelta(days=6),
                    status="DELAYED",
                    location="Hub Campinas - SP",
                    description="Retido em triagem operacional com atraso na rota.",
                ),
            ),
        ),
        Shipment(
            order_number=OrderNumber("PD-104750"),
            carrier_name="PetLog Express",
            tracking_code=TrackingCode("PL104750BR"),
            tracking_url="https://rastreio.pawdesk.example/PL104750BR",
            status=ShipmentStatus.DELAYED,
            estimated_delivery_at=late_1bd_eta,
            events=(
                ShipmentEvent(
                    occurred_at=now - timedelta(hours=14),
                    status="IN_TRANSIT",
                    location="Unidade Osasco - SP",
                    description="Em transferência para entrega final.",
                ),
            ),
        ),
    )

    products = (
        Product(
            sku="RAC-GAT-10KG",
            name="Ração Premium Gatos Castrados 10kg",
            species="GATO",
            category="RACAO",
            price=Money(Decimal("189.90")),
            in_stock=True,
            weight_kg=10.0,
            description="Alimento completo para gatos adultos castrados sabor salmão.",
        ),
        Product(
            sku="RAC-FIL-3KG",
            name="Ração Super Premium Cães Filhotes 3kg",
            species="CAO",
            category="RACAO",
            price=Money(Decimal("119.90")),
            in_stock=True,
            weight_kg=3.0,
            description="Nutrição balanceada para cães filhotes até 12 meses.",
        ),
        Product(
            sku="RAC-CAE-15KG",
            name="Ração Cães Adultos Porte Médio 15kg",
            species="CAO",
            category="RACAO",
            price=Money(Decimal("239.90")),
            in_stock=True,
            weight_kg=15.0,
            description="Ração para cães adultos de porte médio.",
        ),
        Product(
            sku="ARE-HIG-4KG",
            name="Areia Higiênica Biodegradável 4kg",
            species="GATO",
            category="HIGIENE",
            price=Money(Decimal("49.90")),
            in_stock=True,
            weight_kg=4.0,
            description="Formação rápida de torrões e controle de odor.",
        ),
        Product(
            sku="BRQ-MOR-01",
            name="Brinquedo Mordedor Filhote Macio",
            species="CAO",
            category="ACESSORIO",
            price=Money(Decimal("39.90")),
            in_stock=True,
            weight_kg=0.3,
            description="Borracha atóxica para filhotes em fase de dentição.",
        ),
        Product(
            sku="PET-NAT-100G",
            name="Petisco Natural Frango Desidratado 100g",
            species="CAO",
            category="PETISCO",
            price=Money(Decimal("24.90")),
            in_stock=True,
            weight_kg=0.1,
            description="100% peito de frango desidratado sem conservantes.",
        ),
    )

    return SeedDataset(
        customers=customers,
        orders=orders,
        shipments=shipments,
        products=products,
    )
