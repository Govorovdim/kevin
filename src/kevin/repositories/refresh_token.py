from datetime import datetime, timezone

from sqlmodel import Session, select

from kevin.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, refresh_token: RefreshToken) -> RefreshToken:
        self.session.add(refresh_token)
        self.session.commit()
        self.session.refresh(refresh_token)
        return refresh_token

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.session.exec(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        ).first()

    def revoke(self, refresh_token: RefreshToken) -> None:
        refresh_token.revoked = True
        self.session.add(refresh_token)
        self.session.commit()

    def revoke_all_for_user(self, user_id: int) -> None:
        tokens = self.session.exec(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
            )
        ).all()
        for token in tokens:
            token.revoked = True
            self.session.add(token)
        self.session.commit()
