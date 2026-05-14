from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import delete as sa_delete
from sqlmodel import Session, SQLModel, select

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """Generic repository providing common CRUD operations."""

    model: type[T]

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, household_id: int, year: int, month: int) -> list[T]:
        return list(
            self.session.exec(
                select(self.model).where(
                    self.model.household_id == household_id,
                    self.model.year == year,
                    self.model.month == month,
                )
            ).all()
        )

    def list_by_year(self, household_id: int, year: int) -> list[T]:
        return list(
            self.session.exec(
                select(self.model).where(
                    self.model.household_id == household_id,
                    self.model.year == year,
                )
            ).all()
        )

    def get(self, item_id: int, household_id: int) -> T | None:
        return self.session.exec(
            select(self.model).where(
                self.model.id == item_id,
                self.model.household_id == household_id,
            )
        ).first()

    def create(self, item: T) -> T:
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def update(self, item: T) -> T:
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete(self, item: T) -> None:
        self.session.delete(item)
        self.session.commit()

    def delete_by_household(self, household_id: int) -> None:
        self.session.execute(
            sa_delete(self.model).where(self.model.household_id == household_id)
        )
        self.session.commit()
