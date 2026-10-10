from collections.abc import Sequence

from sqlalchemy import Select
from sqlalchemy.orm import Session


class Repository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def all(self, statement: Select, *, limit: int = 100) -> Sequence:
        return self.session.scalars(statement.limit(limit)).all()
