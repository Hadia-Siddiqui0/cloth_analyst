"""
Defines the SQLAlchemy declarative base ONLY. Nothing else.

Every model does `from app.db.base import Base` -- if this file also
imported the models back (like it used to), any model that gets
imported first (e.g. from an API route) would trigger a circular
import: model -> this file -> back to that same model, which is
still mid-load and doesn't have its class defined yet.

To register every model for Alembic's autogenerate, see
app/db/all_models.py instead -- that file imports everything AFTER
this one is fully loaded, so there's no cycle.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass