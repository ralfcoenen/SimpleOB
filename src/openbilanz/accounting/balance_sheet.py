from dataclasses import dataclass


@dataclass
class AccountBalance:
    account_number: str

    debit: float = 0.0
    credit: float = 0.0

    @property
    def balance(self):
        return self.debit - self.credit
