from kevin.models.income import Income
from kevin.repositories.base import BaseRepository


class IncomeRepository(BaseRepository[Income]):
    model = Income
