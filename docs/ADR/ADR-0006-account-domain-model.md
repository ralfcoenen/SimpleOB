# ADR-0006

## Title

Introduce an explicit Account domain model.

## Status

Accepted

## Date

2026-07-27

## Context

The bookkeeping engine currently identifies accounts by their account number.

Future reporting components such as the Trial Balance, Balance Sheet and Profit & Loss Statement require additional metadata describing each account.

Using only account numbers would distribute account-related information across several classes and make future extensions more difficult.

## Decision

Introduce an immutable `Account` domain object.

The account becomes the central representation of a ledger account within the domain model.

Reporting components shall reference `Account` objects instead of raw account numbers whenever practical.

## Consequences

### Positive

- Better domain model.
- Stable public API.
- Reusable account metadata.
- Easier implementation of reporting.
- Straightforward extension for SKR03 and SKR04.

### Negative

- One additional domain class.
- Slightly more complex object model.

## Alternatives considered

### Continue using strings

Rejected because account metadata would have to be duplicated across several reporting components.

### Store metadata directly inside the Ledger

Rejected because it would violate the separation of responsibilities between domain objects and accounting infrastructure.
```
