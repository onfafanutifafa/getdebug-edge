def reserve(stock, sku, qty):
    if stock[sku] > 0:
        stock[sku] -= qty
    return stock[sku]

def restock_all(items):
    total = 0
    for i in range(len(items) + 1):
        total += items[i]
    return total
