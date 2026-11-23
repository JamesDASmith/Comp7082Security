Defects:

|Defect Number|Location|What can go wrong|Fix|
|-|-|-|-|
|1|cart.py (add\_item \& remove\_item)|No validation for quantity. Allows 0, negative numbers, Booleans and floats.<br />Can lead to negative line totals, or removing negative items increases item quantity.|Ensure quantity is a + int, and raise error if not.|
|2|cart.py (add\_item)|Stock is only chacked against newly added quantities. Ignores items already in self.lines. Ie if Stock of 5 items, can add 3, twice|product.stock < (existing\_quantity + quantity) instead of product.stock < quantity|
|3|cart.py (total, apply\_discount)|apply\_discount catches a static self.discounted\_total, which total() returns, so adding or removing items after adding a discount leaves total at old ammount|Storing discount code and compute total() from current subtotal each time.|
|4|cart.py (apply\_discount)|apply\_discount starts from self.total() and not .subtotal().<br />So you can keep calling discounts over and over.|Apply only one self.discount\_code to the subtotal. And replace prior coupons.|
|5|cart.py(subtotal, apply\_discount)|SAVE15 subtracts 15 without checking if it will cause negative number. |clamp discount to a minimum of 0.00|
|6|cart.py (load)|load() appends saved rows through add\_item() w/out clearing lines first.<br />So Calling load twices doubles the cart|Clear existing cart lines and discount state at start of load()|
|7|repository.py(get\_product, get\_saved\_cart)|Queries interpolate sku and user\_id directly into SQL strings. Leads to SQL injection vulnerability and breaking on quotes|Replace string interpolation w/ parameterized ? queries|
|8|repository.py (list\_orders)|list\_orders(self, user\_id) ignores its user\_id parameter and selects all rows from oders leaking into other customers history|Filter w/ WHERE user\_id = ? using user\_id|
|9|repository.py (update\_stock, and DB methods)|update\_stock subtracts stock w/out checking stock > quantity allowing negative inventory quants. And connections are closed w/out checking context, causing leaks|Add AND stock >= ? to UPDATE<br /><br />return if row was updated or not.|
|10|Checkout.py (checkout)|Stock decremented before calling payment\_gateway.charge() w/out reverifying database stock or using a shared transaction.<br />Therefore decline payments, gateway errors, or stock changes cause lost inventory|Verify stock before charging, and charge the gatewat first and on the paid status. Atomically decrement stock for all lines, save order, and clear saved cart inside one SQLLite transaction|
|11|checkout.py(checkout)|cart.lines.clear(), cart.discounted\_total = None, and cart.save() run even when payment is declined or payment error occurs.<br />Wipes users cart on failure.|Only clear cart and saved cart when status is 'paid'|
|12|checkout.py (checkout)|request\_id isn't checked for repeating checkout requests. Leading to double charges and double stock reductions|Require non-empty request\_id check for existing order w/ that id before continuing.|



Assumptions:

* Quantity Validation: adding, removing items or updating stock expect positive ints only and throw errors otherwise. 
* Adding items with a preexisting SKU increments the quantity of the item of that SKU rather than prompting for a confirmation.
* Only one discount code can be active at one time



Console Output:

python -m pytest -q

...................                                      \[100%]

19 passed in 0.69s



GitHub Actions URL: 
https://github.com/JamesDASmith/Comp7082Security/actions/runs/45097585636

