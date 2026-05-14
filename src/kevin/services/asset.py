from datetime import datetime, timezone
from decimal import Decimal

from kevin.exceptions import NotFoundError
from kevin.models.asset import Asset
from kevin.repositories.asset import AssetRepository


class AssetService:
    def __init__(self, repository: AssetRepository) -> None:
        self.repository = repository

    def list(self, household_id: int, year: int, month: int) -> list[Asset]:
        return self.repository.list(household_id, year, month)

    def get(self, asset_id: int, household_id: int, year: int, month: int) -> Asset:
        asset = self.repository.get(asset_id, household_id)
        if not asset or asset.year != year or asset.month != month:
            raise NotFoundError(f"Asset {asset_id} not found")
        return asset

    def create(
        self,
        household_id: int,
        year: int,
        month: int,
        title: str,
        ticker: str | None,
        amount: Decimal | None,
        bought_price: Decimal | None,
        current_price: Decimal | None,
    ) -> Asset:
        return self.repository.create(
            Asset(
                household_id=household_id,
                year=year,
                month=month,
                title=title,
                ticker=ticker,
                amount=amount,
                bought_price=bought_price,
                current_price=current_price,
            )
        )

    def update(
        self,
        asset_id: int,
        household_id: int,
        year: int,
        month: int,
        title: str,
        ticker: str | None,
        amount: Decimal | None,
        bought_price: Decimal | None,
        current_price: Decimal | None,
    ) -> Asset:
        asset = self.get(asset_id, household_id, year, month)
        asset.title = title
        asset.ticker = ticker
        asset.amount = amount
        asset.bought_price = bought_price
        asset.current_price = current_price
        asset.updated_at = datetime.now(timezone.utc)
        return self.repository.update(asset)

    def update_price(
        self,
        asset_id: int,
        household_id: int,
        year: int,
        month: int,
        current_price: Decimal,
    ) -> Asset:
        asset = self.get(asset_id, household_id, year, month)
        asset.current_price = current_price
        asset.updated_at = datetime.now(timezone.utc)
        return self.repository.update(asset)

    def delete(self, asset_id: int, household_id: int, year: int, month: int) -> None:
        asset = self.get(asset_id, household_id, year, month)
        self.repository.delete(asset)

    def portfolio_value(self, household_id: int, year: int, month: int) -> Decimal:
        """Total current value of all assets (amount * current_price)."""
        return sum(
            (
                a.amount * a.current_price
                for a in self.list(household_id, year, month)
                if a.amount is not None and a.current_price is not None
            ),
            Decimal(0),
        )

    def total_gain_loss(self, household_id: int, year: int, month: int) -> Decimal:
        """Total unrealised gain/loss across all assets ((current - bought) * amount)."""
        return sum(
            (
                (a.current_price - a.bought_price) * a.amount
                for a in self.list(household_id, year, month)
                if a.amount is not None
                and a.bought_price is not None
                and a.current_price is not None
            ),
            Decimal(0),
        )
