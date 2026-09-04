"""Example file demonstrating exact duplicate-block detection."""


def report_sales(records):
    total = 0
    count = 0
    for record in records:
        total += record["amount"]
        count += 1
    average = total / count if count else 0
    print(f"Sales total: {total}, average: {average}")
    return total


def report_returns(records):
    total = 0
    count = 0
    for record in records:
        total += record["amount"]
        count += 1
    average = total / count if count else 0
    print(f"Returns total: {total}, average: {average}")
    return total
