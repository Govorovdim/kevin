from decimal import Decimal

from sqlmodel import Session

from kevin.models.asset import Asset
from kevin.models.household import Household


def create_household(session: Session, name: str = "Test household") -> Household:
    household = Household(name=name)
    session.add(household)
    session.commit()
    session.refresh(household)
    return household


def create_asset(
    session: Session,
    household_id: int,
    year: int,
    month: int,
    *,
    title: str = "Brokerage",
    price: Decimal = Decimal("100.00"),
    amount: Decimal | None = Decimal("10.0000"),
    carried_forward: bool = False,
    previous_asset_id: int | None = None,
) -> Asset:
    asset = Asset(
        household_id=household_id,
        year=year,
        month=month,
        title=title,
        price=price,
        amount=amount,
        carried_forward=carried_forward,
        previous_asset_id=previous_asset_id,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset
