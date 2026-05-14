from kevin.models.expense import Expense
from kevin.repositories.base import BaseRepository


class ExpenseRepository(BaseRepository[Expense]):
    model = Expense
