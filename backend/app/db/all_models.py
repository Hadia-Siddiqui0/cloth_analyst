"""
Import every model here so Alembic's autogenerate can see the full
schema. This file is intentionally separate from app/db/base.py --
importing models here happens AFTER Base is already fully defined,
so there's no circular import.

Only alembic/env.py should import this file. Application code (API
routes, services) should import each model directly from its own
module (e.g. `from app.models.company import Company`), never from
here.
"""
from app.models.company import Company  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.upload import Upload  # noqa: F401
from app.models.department import Department  # noqa: F401
from app.models.supplier import Supplier  # noqa: F401
from app.models.raw_material import RawMaterial  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.purchase import Purchase  # noqa: F401
from app.models.production_batch import ProductionBatch  # noqa: F401
from app.models.batch_department_step import BatchDepartmentStep  # noqa: F401
from app.models.inventory_snapshot import InventorySnapshot  # noqa: F401
from app.models.production_run import ProductionRun  # noqa: F401
from app.models.customer import Customer  # noqa: F401
from app.models.sale import Sale  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.payable import Payable  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.contractor_ledger import ContractorLedgerEntry  # noqa: F401
from app.models.expense import Expense  # noqa: F401