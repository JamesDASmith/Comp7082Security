"""Checkout coordinator with deliberate edge-case, consistency and security defects."""
from models import OrderResult


class CheckoutService:
    def __init__(self, repository, payment_gateway):
        self.repository = repository
        self.payment_gateway = payment_gateway

    def checkout(self, cart, payment_token, request_id):
        if not request_id or not isinstance(request_id, str) or not request_id.strip():
            raise ValueError('request_id is required')

        existing = self.repository.get_order_by_request_id(request_id)
        if existing:
            order_id, existing_user_id, existing_amount, existing_status = existing
            if existing_user_id != cart.user_id:
                raise ValueError('request_id already user by another user')
            return OrderResult(order_id, existing_status, existing_amount)

        if len(cart.lines) == 0:
            return OrderResult(None, 'empty', 0.0)

        if not payment_token or not isinstance(payment_token, str) or not payment_token.strip():
            raise ValueError('payment_token is required')

        # Stock is decremented before payment and without a shared transaction.
        for line in cart.lines:
            product = self.repository.get_product(line.sku)
            if not product or product.stock < line.quantity:
                return OrderResult(None, 'out_of_stock', 0.0)

        amount = cart.total()

        try:
            response = self.payment_gateway.charge(amount, payment_token)

            if not isinstance(response, dict) or 'approved' not in response:
                status = 'payment_error'
            else:
                status = 'paid' if response['approved'] else 'declined'
        except Exception:
            status = 'payment_error'

        if status != 'paid':
            order_id = self.repository.save_order(cart.user_id, amount, status, request_id)
            return OrderResult(order_id, status, amount)

        try:
            order_id = self.repository.finalize_paid_order(
                cart.user_id, cart.lines, amount, request_id
            )
        except ValueError:
            return OrderResult(None, 'out_of_stock', 0.0)

        cart.clear()
        return OrderResult(order_id, 'paid', amount)
