from sqlmodel import select

from kevin.models.asset import Asset
from kevin.repositories.base import BaseRepository


class AssetRepository(BaseRepository[Asset]):
    model = Asset

    def get_successor(self, asset_id: int) -> Asset | None:
        return self.session.exec(
            select(Asset).where(Asset.previous_asset_id == asset_id)
        ).first()

    def create_without_commit(self, asset: Asset) -> Asset:
        self.session.add(asset)
        self.session.flush()
        return asset

    def update_without_commit(self, asset: Asset) -> Asset:
        self.session.add(asset)
        self.session.flush()
        return asset

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
