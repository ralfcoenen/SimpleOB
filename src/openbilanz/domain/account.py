from dataclasses import dataclass

from openbilanz.domain.account_role import AccountRole
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.template_account import TemplateAccount


@dataclass(frozen=True, slots=True)
class Account:
    template: TemplateAccount
    is_active: bool = True
    account_role: AccountRole | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.template, TemplateAccount):
            raise TypeError("template must be a TemplateAccount")

        if not isinstance(self.is_active, bool):
            raise TypeError("is_active must be a bool")

        if (
            self.account_role is not None
            and not isinstance(
                self.account_role,
                AccountRole,
            )
        ):
            raise TypeError(
                "account_role must be an AccountRole or None"
            )

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
