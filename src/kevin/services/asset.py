from datetime import datetime, timezone
from decimal import Decimal

from kevin.exceptions import NotFoundError
from kevin.models.asset import Asset
from kevin.repositories.asset import AssetRepository


class AssetService:
    def __init__(self, repository: AssetRepository) -> None:
        self.repository = repository

    def carry_forward_previous_month(
        self, household_id: int, year: int, month: int
    ) -> None:
        previous_year, previous_month = self._previous_month(year, month)
        previous_assets = self.repository.list(
            household_id, previous_year, previous_month
        )
        now = datetime.now(timezone.utc)

        try:
            for asset in previous_assets:
                if asset.carried_forward or asset.id is None:
                    continue
                if self.repository.get_successor(asset.id):
                    asset.carried_forward = True
                    asset.updated_at = now
                    self.repository.update_without_commit(asset)
                    continue

                asset.carried_forward = True
                asset.updated_at = now
                self.repository.update_without_commit(asset)

                self.repository.create_without_commit(
                    Asset(
                        household_id=asset.household_id,
                        year=year,
                        month=month,
                        title=asset.title,
                        price=asset.price,
                        amount=asset.amount,
                        carried_forward=False,
                        previous_asset_id=asset.id,
                    )
                )
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise

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
        price: Decimal,
        amount: Decimal | None,
        carried_forward: bool = False,
    ) -> Asset:
        return self.repository.create(
            Asset(
                household_id=household_id,
                year=year,
                month=month,
                title=title,
                price=price,
                amount=amount,
                carried_forward=carried_forward,
            )
        )

    def update(
        self,
        asset_id: int,
        household_id: int,
        year: int,
        month: int,
        title: str,
        price: Decimal,
        amount: Decimal | None,
        carried_forward: bool | None = None,
    ) -> Asset:
        asset = self.get(asset_id, household_id, year, month)
        asset.title = title
        asset.price = price
        asset.amount = amount
        if carried_forward is not None:
            asset.carried_forward = carried_forward
        asset.updated_at = datetime.now(timezone.utc)
        return self.repository.update(asset)

    def delete(self, asset_id: int, household_id: int, year: int, month: int) -> None:
        asset = self.get(asset_id, household_id, year, month)
        previous_asset = self._get_linked_previous_asset(asset)
        if previous_asset:
            previous_asset.carried_forward = True
            previous_asset.updated_at = datetime.now(timezone.utc)
            self.repository.update(previous_asset)
        self.repository.delete(asset)

    def _get_linked_previous_asset(self, asset: Asset) -> Asset | None:
        if asset.previous_asset_id is not None:
            return self.repository.get(asset.previous_asset_id, asset.household_id)
        return None

    def _previous_month(self, year: int, month: int) -> tuple[int, int]:
        if month == 1:
            return year - 1, 12
        return year, month - 1

    def portfolio_value(self, household_id: int, year: int, month: int) -> Decimal:
        """Total value of all assets, treating a missing/zero amount as one."""
        return sum((a.value for a in self.list(household_id, year, month)), Decimal(0))
