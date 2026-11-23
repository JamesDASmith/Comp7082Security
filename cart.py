"""Business logic. Several design and correctness issues are intentional."""
from models import CartLine
from decimal import Decimal, ROUND_HALF_UP

VALID_DISCOUNT_CODES = {'WELCOME10', 'STUDENT20', 'SAVE15', 'FREESHIP'}

def _validate_positive_int(value, field_name='quantity'):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError('Invalid quantity')

def _round_money(amount: Decimal) -> float:
    return float(amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

class ShoppingCart:
    def __init__(self, user_id, repository):
        self.user_id = user_id
        self.repository = repository
        self.lines = []
        self.discount_code = None

    def add_item(self, sku, quantity):
        _validate_positive_int(quantity, 'quantity')
        product = self.repository.get_product(sku)

        if not product:
            print('Unknown product')
            return False

        existing = next((x for x in self.lines if x.sku == sku), None)
        new_quantity = (existing.quantity if existing else 0) + quantity

        if product.stock < new_quantity:
            print('Not enough stock')
            return False

        if existing:
            existing.quantity = new_quantity
            existing.unit_price = product.price
            existing.name = product.name
        else:
            self.lines.append(CartLine(sku, product.name, product.price, quantity))
        return True

    def remove_item(self, sku, quantity=None):
        if quantity is not None:
            _validate_positive_int(quantity, 'quantity')

        for line in self.lines:
            if line.sku == sku:
                if quantity is None or quantity >= line.quantity:
                    self.lines.remove(line)
                else:
                    line.quantity -= quantity
                if not self.lines:
                    self.discount_code = None
                return True
        print('Item not found')
        return False

    def _subtotal_decimal(self) -> Decimal:
        return sum(
            (Decimal(str(line.unit_price)) * line.quantity for line in self.lines),
            Decimal('0.00'),
        )

    def subtotal(self) -> float:
        return _round_money(self._subtotal_decimal())

    def total(self) -> float:
        amount = self._subtotal_decimal()
        if amount <= Decimal('0.00'):
            return 0.0

        if self.discount_code == 'WELCOME10':
            amount *= Decimal('0.9')
        elif self.discount_code == 'STUDENT20':
            amount *= Decimal('0.8')
        elif self.discount_code == 'SAVE15':
            amount = max(Decimal('0.00'), amount - Decimal('15'))
        elif self.discount_code == 'FREESHIP':
            pass

        return _round_money(amount)

    def apply_discount(self, code):
        if code not in VALID_DISCOUNT_CODES:
            return False
        self.discount_code = code
        return True

    def clear(self):
        self.lines.clear()
        self.discount_code = None

    def load(self):
        self.clear()
        for sku, quantity in self.repository.get_saved_cart(self.user_id):
            if not isinstance(quantity, bool) and isinstance(quantity, int) and quantity > 0:
                self.add_item(sku, quantity)

    def save(self):
        self.repository.save_cart(self.user_id, self.lines)
