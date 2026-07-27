# Datei: `API.md`

````markdown
# Public API

## Domain

### EntrySide

Represents the debit or credit side of a booking line.

---

### BookingLine

Represents a single booking line.

---

### Booking

Represents a balanced accounting transaction.

Properties

- debit_total
- credit_total
- debit_lines
- credit_lines
- is_balanced

---

### Journal

Chronological collection of bookings.

Public API

```python
journal = Journal()

journal.add(booking)

journal.bookings

len(journal)

for booking in journal:

booking in journal
````

---

### Account

Represents a ledger account.

Public API

```python
Account(
    number: str,
    name: str,
    account_type: AccountType,
)
```

Properties

* number
* name
* account_type

Behaviour

```python
str(account)
```

---

### AccountType

Values

* ASSET
* LIABILITY
* EXPENSE
* REVENUE

---

## Services

### PostingService

Processes balanced bookings and posts them to a ledger.

```python
PostingService().post_booking(
    booking,
    ledger,
)
```

---

## Accounting

### Ledger

Stores postings and account balances.

### AccountBalance

Represents the balance of one account.

### TrialBalance

Planned.

### TrialBalanceService

Planned.

```
```
