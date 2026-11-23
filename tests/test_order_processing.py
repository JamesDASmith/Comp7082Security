import pytest

from cart import ShoppingCart
from checkout import CheckoutService
from models import OrderResult
from payments import FakePaymentGateway
from repository import StoreRepository
from setup_db import initialize

@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / 'test)shop.db'
    initialize(str(db_file))
    return StoreRepository(str(db_file))

class FailingPaymentGateway:
    def charge(self, amount, payment_token):
        raise RuntimeError('Simulated gateway timeout')

class MalformedPaymentGateway:
    def charge(selfself, amount, payment_token):
        return {'unexpected': 'payload'}

# Cart Tests

@pytest.mark.parametrize('bad_qty', [0, -1, -10, 1.5, True, '2'])
def test_add_item_rejects_invalid_quantities(repo, bad_qty):
    cart = ShoppingCart('u1', repo)
    with pytest.raises(ValueError):
        cart.add_item('USB-01', bad_qty)

def test_add_item_merges_duplicates_and_enforces_cumulative_stock(repo):
    cart = ShoppingCart('u1', repo)
    assert cart.add_item('LAP-01', 3) is True
    assert cart.add_item('LAP-01', 3) is False
    assert cart.add_item('LAP-01', 2) is True
    assert len(cart.lines) == 1
    assert cart.lines[0].quantity == 5

def test_remove_item_partial_full_missing_and_invalid_quantity(repo):
    cart = ShoppingCart('u1', repo)
    cart.add_item('MOU-01', 3)

    with pytest.raises(ValueError):
        cart.remove_item('MOU-01', -1)

    assert cart.remove_item('NO-SKU') is False
    assert cart.remove_item('MOU-01', 1) is True
    assert cart.lines[0].quantity == 2
    assert cart.remove_item('MOU-01') is True
    assert cart.lines == []

def test_discount_recalculates_after_cart_edits(repo):
    cart = ShoppingCart('u1', repo)
    cart.add_item('MOU-01', 2)
    assert cart.apply_discount('WELCOME10') is True
    assert cart.total() == 53.91

    cart.add_item('MOU-01', 1)
    assert cart.total() == 80.87

    cart.remove_item('MOU-01')
    assert cart.total() == 0.0
    assert cart.discount_code is None

def test_discount_does_not_stack_when_applied_repeatedly(repo):
    cart = ShoppingCart('u1', repo)
    cart.add_item('LAP-01', 1)

    assert cart.apply_discount('WELCOME10') is True
    first_total = cart.total()
    assert cart.apply_discount('WELCOME10') is True
    assert cart.total() == first_total == 899.99

    assert cart.apply_discount('STUDENT20') is True
    assert cart.total() == 799.99

def test_save15_discount_floors_at_zero_and_rejects_invalid_code(repo):
    cart = ShoppingCart('u1', repo)
    cart.add_item('USB-01', 1)

    assert cart.apply_discount('BADCODE') is False
    assert cart.apply_discount('SAVE15') is True
    assert cart.total() == 0.0

def test_saved_cart_repeated_load_does_not_duplicate_items(repo):
    cart = ShoppingCart('u1', repo)
    cart.add_item('USB-01', 2)
    cart.save()

    reloaded = ShoppingCart('u1', repo)
    reloaded.load()
    reloaded.load()

    assert len(reloaded.lines) == 1
    assert reloaded.lines[0].sku == 'USB-01'
    assert reloaded.lines[0].quantity == 2

# Repository Tests
def test_repository_prevents_sql_injection(repo):
    cart = ShoppingCart('victim', repo)
    cart.add_item('USB-01', 1)
    cart.save()

    assert repo.get_product("' OR '1'='1") is None
    assert repo.get_saved_cart("' OR '1'=1") == []

def test_list_orders_returns_only_requested_user_orders(repo):
    repo.save_order('alice', 29.95, 'paid', 'req-a1')
    repo.save_order('bob', 99.99, 'paid', 'req-b1')

    alice_orders = repo.list_orders('alice')
    assert len(alice_orders) == 1
    assert alice_orders[0][1] == 'alice'

def test_update_stock_prevents_negative_inventory(repo):
    assert repo.update_stock('LAP-01', 6) is False
    assert repo.get_product('LAP-01').stock == 5

    assert repo.update_stock('LAP-01', 5) is True
    assert repo.get_product('LAP-01').stock == 0

# Checkout Tests
def test_checkout_empty_cart_does_not_charge(repo):
    cart = ShoppingCart('u1', repo)
    gateway = FakePaymentGateway(should_approve=True)

    result = CheckoutService(repo, gateway).checkout(cart, 'TEST_TOKEN', 'req-empty')
    assert result == OrderResult(None, 'empty', 0.0)
    assert gateway.calls == []

def test_checkout_declined_payment_preserves_stock_and_cart(repo):
    cart = ShoppingCart('u1', repo)
    cart.add_item('MOU-01', 2)
    gateway = FakePaymentGateway(should_approve=False)

    result = CheckoutService(repo, gateway).checkout(cart, 'TESt_TOKEN', 'req-declined')
    assert result.status == 'declined'
    assert repo.get_product('MOU-01').stock == 20
    assert len(cart.lines) == 1
    assert cart.lines[0].quantity == 2




