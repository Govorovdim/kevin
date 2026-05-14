from kevin.models.liability import Liability
from kevin.repositories.base import BaseRepository


class LiabilityRepository(BaseRepository[Liability]):
    model = Liability
