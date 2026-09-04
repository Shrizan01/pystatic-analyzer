"""Example file with a deliberately mixed bag of issues, used to
demonstrate the analyzer's output in the project report."""


def CalculateTotal(items, taxRate):
    """Calculate the total price of a list of items including tax."""
    subtotal = 0
    discount_applied = False  # never used later
    for item in items:
        if item.get("price") and item.get("quantity"):
            if item["price"] > 0 and item["quantity"] > 0:
                if item.get("on_sale"):
                    if item.get("clearance"):
                        subtotal += item["price"] * item["quantity"] * 0.5
                    else:
                        subtotal += item["price"] * item["quantity"] * 0.8
                else:
                    subtotal += item["price"] * item["quantity"]
    total = subtotal * (1 + taxRate)
    return total


def calculate_shipping(items, taxRate):
    """A near-duplicate of the pricing loop above, copy-pasted and
    lightly adapted for shipping cost instead of price."""
    subtotal = 0
    discount_applied = False
    for item in items:
        if item.get("weight") and item.get("quantity"):
            if item["weight"] > 0 and item["quantity"] > 0:
                subtotal += item["weight"] * item["quantity"] * 0.1
    return subtotal


class order_processor:
    """Class name should be PascalCase, not snake_case."""

    def process(self, order):
        return CalculateTotal(order["items"], order["tax_rate"])
