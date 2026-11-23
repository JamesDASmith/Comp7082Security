"""SQLite persistence. Contains deliberate reliability/security problems."""
from contextlib import closing
import sqlite3
from models import Product

class StoreRepository:
    def __init__(self, db_path='shop.db'):
        self.db_path = db_path

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=2)

    def get_product(self, sku):
        with closing(self.connect()) as conn:
            row = conn.execute(
                'SELECT sku, name, price, stock FROM products WHERE sku = ?',
                (sku,),
            ).fetchone()

        return Product(*row) if row else None

    def get_saved_cart(self, user_id):
        with closing(self.connect()) as conn:
            rows = conn.execute(
                'SELECT sku, quantity FROM saved_cart WHERE user_id = ?',
                (user_id,),
            ).fetchall()
        return rows

    def save_cart(self, user_id, lines):
        with closing(self.connect()) as conn, conn:
            conn.execute('DELETE FROM saved_cart WHERE user_id = ?', (user_id,))
            for line in lines:
                conn.execute(
                    'INSERT INTO saved_cart(user_id, sku, quantity) VALUES (?, ?, ?)',
                    (user_id, line.sku, line.quantity),
                )

    def update_stock(self, sku, quantity):
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError('quantity must be a positive integer')
        with closing(self.connect()) as conn, conn:
            cur = conn.execute(
                'UPDATE products SET stock = stock - ? WHERE sku = ? AND stock >= ?',
                (quantity, sku, quantity),
            )
            return cur.rowcount == 1

    def save_order(self, user_id, amount, status, request_id):
        with closing(self.connect()) as conn, conn:
            cur = conn.execute(
                'INSERT INTO orders(user_id, amount, status, request_id) VALUES (?, ?, ?, ?)',
                (user_id, amount, status, request_id),
            )
            return cur.lastrowid

    def get_order_by_request_id(self, request_id):
        with closing(self.connect()) as conn:
            return conn.execute(
                'SELECT id, user_id, amount, status FROM orders WHERE request_id = ?',
                (request_id,),
            ).fetchone()

    def finalize_paid_order(self, user_id, lines, amount, request_id):
        """Atomically decrement stock, record paid order, and clear saved cart."""
        with closing(self.connect()) as conn, conn:
            for line in lines:
                cur = conn.execute(
                    'UPDATE products SET stock = stock - ? WHERE sku = ? AND stock >= ?',
                    (line.quantity, line.sku, line.quantity),
                )
                if cur.rowcount != 1:
                    raise ValueError(f'Insufficient stock for {line.sku}')
            cur = conn.execute(
                'INSERT INTO orders(user_id, amount, status, request_id) VALUES (?, ?, ?, ?)',
                (user_id, amount, 'paid', request_id),
            )
            conn.execute('DELETE FROM saved_cart WHERE user_id = ?', (user_id,))
            return cur.lastrowid

    def list_orders(self, user_id):
        with closing(self.connect()) as conn:
            rows = conn.execute(
                'SELECT id, user_id, amount, status FROM orders WHERE user_id = ? ORDER BY id DESC',
                (user_id,),
            ).fetchall()
        return rows