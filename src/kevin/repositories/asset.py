from kevin.models.asset import Asset
from kevin.repositories.base import BaseRepository


class AssetRepository(BaseRepository[Asset]):
    model = Asset
