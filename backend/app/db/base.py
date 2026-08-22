"""
Import every model here so that:
1. `Base.metadata.create_all()` (used in seed/dev scripts) knows about all tables.
2. Alembic's autogenerate can see the full schema when producing migrations.
Nothing else should import models directly from this file -- import from
app.models.<name> instead. This file exists purely for side-effect imports.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# noqa: F401 -- imported for side effects (model registration), not used directly
from app.models.company import Company  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.models.upload import Upload  # noqa: E402, F401
from app.models.department import Department  # noqa: E402, F401
from app.models.supplier import Supplier  # noqa: E402, F401
from app.models.raw_material import RawMaterial  # noqa: E402, F401
from app.models.product import Product  # noqa: E402, F401
from app.models.purchase import Purchase  # noqa: E402, F401
from app.models.production_batch import ProductionBatch  # noqa: E402, F401
from app.models.batch_department_step import BatchDepartmentStep  # noqa: E402, F401
from app.models.inventory_snapshot import InventorySnapshot  # noqa: E402, F401
from app.models.production_run import ProductionRun  # noqa: E402, F401
from app.models.customer import Customer  # noqa: E402, F401
from app.models.sale import Sale  # noqa: E402, F401
from app.models.payment import Payment  # noqa: E402, F401
from app.models.contractor_ledger import ContractorLedgerEntry  # noqa: E402, F401
from app.models.expense import Expense  # noqa: E402, F401