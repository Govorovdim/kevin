import uuid

from kevin.exceptions import NotFoundError
from kevin.models.household import Household
from kevin.repositories.household import HouseholdRepository
from kevin.repositories.user_household import UserHouseholdRepository


class HouseholdService:
    def __init__(
        self,
        household_repo: HouseholdRepository,
        user_household_repo: UserHouseholdRepository,
    ) -> None:
        self.household_repo = household_repo
        self.user_household_repo = user_household_repo

    def list(self, user_id: int) -> list[Household]:
        return self.household_repo.list_by_user(user_id)

    def get(self, household_id: int) -> Household:
        household = self.household_repo.get(household_id)
        if not household:
            raise NotFoundError(f"Household {household_id} not found")
        return household

    def create(self, user_id: int, name: str, currency: str = "USD") -> Household:
        household = self.household_repo.create(Household(name=name, currency=currency))
        self.user_household_repo.create(user_id, household.id)
        return household

    def update(self, household_id: int, name: str) -> Household:
        household = self.get(household_id)
        household.name = name
        return self.household_repo.update(household)

    def delete(self, household_id: int) -> None:
        household = self.get(household_id)
        # With ON DELETE CASCADE on foreign keys, deleting the household
        # will cascade to related records. We still explicitly clean up
        # the user_household join table and cascade children for safety.
        self.user_household_repo.delete_by_household(household_id)
        self.household_repo.delete(household)

    def leave(self, user_id: int, household_id: int) -> None:
        self.get(household_id)  # raises NotFoundError if household doesn't exist
        self.user_household_repo.remove(user_id, household_id)

    def generate_invite(self, household_id: int) -> Household:
        """Generate (or regenerate) an invite token for the household. Returns updated Household."""
        household = self.get(household_id)
        household.invite_token = str(uuid.uuid4())
        return self.household_repo.update(household)

    def join_by_invite(self, user_id: int, token: str) -> Household:
        """Add the user to the household identified by the invite token.
        Raises NotFoundError if token is invalid.
        If the user is already a member, just returns the household silently.
        """
        household = self.household_repo.get_by_invite_token(token)
        if not household:
            raise NotFoundError("Invite token is invalid or has been revoked")
        if not self.user_household_repo.exists(user_id, household.id):
            self.user_household_repo.create(user_id, household.id)
        return household

    def get_by_invite_token(self, token: str) -> Household:
        """Public lookup — just verify the token exists and return household info."""
        household = self.household_repo.get_by_invite_token(token)
        if not household:
            raise NotFoundError("Invite token is invalid or has been revoked")
        return household
