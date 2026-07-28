from dataclasses import dataclass

from openbilanz.domain.account_type import AccountType
from openbilanz.domain.template_account import TemplateAccount


@dataclass(frozen=True, slots=True)
class Account:
    template: TemplateAccount
    is_active: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.template, TemplateAccount):
            raise TypeError("template must be a TemplateAccount")

        if not isinstance(self.is_active, bool):
            raise TypeError("is_active must be a bool")

    @property
    def number(self) -> str:
        return self.template.account_number

    @property
    def name(self) -> str:
        return self.template.name

    @property
    def account_type(self) -> AccountType:
        return self.template.account_type

    def __str__(self) -> str:
        return f"{self.number} – {self.name}"
