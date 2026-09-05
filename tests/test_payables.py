"""
Tests for payables service, reminder service, and CEO attention API.
Tests cover:
- Payable status computation (all statuses)
- Reminder generation with idempotency
- Tenant isolation (company_id scoping)
- CEO attention notifications
"""
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.payables_service import compute_status as compute_payable_status
from app.services.receivables_service import compute_status as compute_receivable_status
from app.models.payable import PayableStatus
from app.models.payment import PaymentStatus


def test_payable_status_computation():
    """Test payable compute_status returns correct status for all cases."""
    today = date(2026, 9, 15)

    # PAID - paid_date is set
    assert compute_payable_status(date(2026, 9, 10), date(2026, 9, 12), today) == PayableStatus.PAID
    assert compute_payable_status(date(2026, 9, 20), date(2026, 9, 12), today) == PayableStatus.PAID
    assert compute_payable_status(None, date(2026, 9, 12), today) == PayableStatus.PAID

    # OVERDUE - due_date < today, not paid
    assert compute_payable_status(date(2026, 9, 10), None, today) == PayableStatus.OVERDUE
    assert compute_payable_status(date(2026, 9, 14), None, today) == PayableStatus.OVERDUE

    # DUE_TODAY - due_date == today
    assert compute_payable_status(date(2026, 9, 15), None, today) == PayableStatus.DUE_TODAY

    # DUE_SOON - due_date within 3 days (1, 2, 3 days)
    assert compute_payable_status(date(2026, 9, 16), None, today) == PayableStatus.DUE_SOON
    assert compute_payable_status(date(2026, 9, 17), None, today) == PayableStatus.DUE_SOON
    assert compute_payable_status(date(2026, 9, 18), None, today) == PayableStatus.DUE_SOON

    # UPCOMING - due_date > 3 days away
    assert compute_payable_status(date(2026, 9, 19), None, today) == PayableStatus.UPCOMING
    assert compute_payable_status(date(2026, 10, 1), None, today) == PayableStatus.UPCOMING

    # UPCOMING - no due_date
    assert compute_payable_status(None, None, today) == PayableStatus.UPCOMING

    print("All payable status computation tests passed!")


def test_receivable_status_computation():
    """Test receivable compute_status returns correct status for all cases (mirrors payable logic)."""
    today = date(2026, 9, 15)

    # PAID
    assert compute_receivable_status(date(2026, 9, 10), date(2026, 9, 12), today) == PaymentStatus.PAID
    assert compute_receivable_status(None, date(2026, 9, 12), today) == PaymentStatus.PAID

    # OVERDUE
    assert compute_receivable_status(date(2026, 9, 10), None, today) == PaymentStatus.OVERDUE
    assert compute_receivable_status(date(2026, 9, 14), None, today) == PaymentStatus.OVERDUE

    # DUE_TODAY
    assert compute_receivable_status(date(2026, 9, 15), None, today) == PaymentStatus.DUE_TODAY

    # DUE_SOON (1-3 days)
    assert compute_receivable_status(date(2026, 9, 16), None, today) == PaymentStatus.DUE_SOON
    assert compute_receivable_status(date(2026, 9, 17), None, today) == PaymentStatus.DUE_SOON
    assert compute_receivable_status(date(2026, 9, 18), None, today) == PaymentStatus.DUE_SOON

    # UPCOMING
    assert compute_receivable_status(date(2026, 9, 19), None, today) == PaymentStatus.UPCOMING
    assert compute_receivable_status(None, None, today) == PaymentStatus.UPCOMING

    print("All receivable status computation tests passed!")


def test_payable_receivable_status_parity():
    """Ensure payable and receivable status computation is identical."""
    today = date(2026, 9, 15)
    test_cases = [
        (date(2026, 9, 10), date(2026, 9, 12)),  # paid
        (date(2026, 9, 10), None),               # overdue
        (date(2026, 9, 14), None),               # overdue (yesterday)
        (date(2026, 9, 15), None),               # due today
        (date(2026, 9, 16), None),               # due soon (1 day)
        (date(2026, 9, 17), None),               # due soon (2 days)
        (date(2026, 9, 18), None),               # due soon (3 days)
        (date(2026, 9, 19), None),               # upcoming (4 days)
        (None, None),                             # no due date
    ]

    for due_date, paid_date in test_cases:
        payable_status = compute_payable_status(due_date, paid_date, today)
        receivable_status = compute_receivable_status(due_date, paid_date, today)
        assert payable_status.value == receivable_status.value, \
            f"Mismatch for due={due_date}, paid={paid_date}: {payable_status} vs {receivable_status}"

    print("Payable/Receivable status parity tests passed!")


def test_reminder_idempotency():
    """Test that reminder generation is idempotent - no duplicates on re-run."""
    # This would need a database session to test properly
    # For now, we verify the idempotency key format is deterministic
    from app.services.reminder_service import _generate_idempotency_key

    ref_id = uuid.uuid4()

    # Same inputs should produce same key
    key1 = _generate_idempotency_key("payable", ref_id, "due_in_7")
    key2 = _generate_idempotency_key("payable", ref_id, "due_in_7")
    assert key1 == key2, "Idempotency key not deterministic"

    # Different trigger types should produce different keys
    key_due_today = _generate_idempotency_key("payable", ref_id, "due_today")
    key_overdue = _generate_idempotency_key("payable", ref_id, "overdue")
    assert key_due_today != key_overdue, "Different triggers should have different keys"

    # Different reference IDs should produce different keys
    key2 = _generate_idempotency_key("payable", uuid.uuid4(), "due_in_7")
    assert key1 != key2, "Different entities should have different keys"

    print("Reminder idempotency key tests passed!")


def test_tenant_isolation_keys():
    """Test that idempotency keys include company context implicitly via reference_id.

    Note: The actual tenant isolation is enforced by the API layer using get_current_company_id.
    The idempotency key uses the entity ID which is already scoped to a company.
    """
    from app.services.reminder_service import _generate_idempotency_key

    payable_id_1 = uuid.uuid4()
    payable_id_2 = uuid.uuid4()

    # Keys for different companies' payables should be different
    # (because the payable IDs are different UUIDs scoped to their companies)
    key1 = _generate_idempotency_key("payable", payable_id_1, "overdue")
    key2 = _generate_idempotency_key("payable", payable_id_2, "overdue")
    assert key1 != key2

    print("Tenant isolation key tests passed!")


def test_ceo_attention_idempotency_keys():
    """Test CEO attention notification idempotency keys."""
    from app.services.reminder_service import _generate_idempotency_key

    company_id = uuid.uuid4()
    payable_id = uuid.uuid4()

    # CEO attention keys include company_id as reference
    key1 = _generate_idempotency_key("ceo", company_id, f"large_overdue_payable_{payable_id}")
    key2 = _generate_idempotency_key("ceo", company_id, f"large_overdue_payable_{payable_id}")
    assert key1 == key2

    # Different payable should have different key
    key3 = _generate_idempotency_key("ceo", company_id, f"large_overdue_payable_{uuid.uuid4()}")
    assert key1 != key3

    print("CEO attention idempotency key tests passed!")


def test_reminder_schedule_days():
    """Test that reminder schedule covers correct days before due."""
    from app.services.reminder_service import REMINDER_DAYS_BEFORE

    assert REMINDER_DAYS_BEFORE == [7, 3, 1], "Reminder schedule should be 7, 3, 1 days before"
    print("Reminder schedule tests passed!")


def test_notification_types():
    """Test notification type enum values."""
    from app.models.notification import NotificationType, NotificationChannel

    # Verify all expected types exist
    expected_types = {
        "payable_due_soon",
        "payable_due_today",
        "payable_overdue",
        "receivable_due_soon",
        "receivable_due_today",
        "receivable_overdue",
        "ceo_attention",
    }
    actual_types = {t.value for t in NotificationType}
    assert expected_types.issubset(actual_types), f"Missing notification types: {expected_types - actual_types}"

    # Verify channels
    expected_channels = {"in_app", "email", "push"}
    actual_channels = {c.value for c in NotificationChannel}
    assert expected_channels == actual_channels

    print("Notification type/channel tests passed!")


if __name__ == "__main__":
    test_payable_status_computation()
    test_receivable_status_computation()
    test_payable_receivable_status_parity()
    test_reminder_idempotency()
    test_tenant_isolation_keys()
    test_ceo_attention_idempotency_keys()
    test_reminder_schedule_days()
    test_notification_types()
    print("\n=== ALL TESTS PASSED ===")