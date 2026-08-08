"""Startpunkt der OpenBilanz-Anwendung."""

import tkinter as tk

from openbilanz.database.company_repository import (
    CompanyRepository,
)
from openbilanz.database.database import (
    create_database,
    create_session,
)
from openbilanz.ui.main_window import MainWindow
from openbilanz.ui.start_dialog import StartDialog


def main() -> None:
    """Startet OpenBilanz."""

    create_database()

    root = tk.Tk()
    root.title("OpenBilanz")

    session = create_session()

    try:
        repository = CompanyRepository(
            session
        )

        dialog = StartDialog(
            root,
            repository=repository,
        )

        root.withdraw()

        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()

        root.wait_window(dialog)

        if dialog.result is None:
            root.destroy()
            return

        context = dialog.result

    finally:
        session.close()

    root.destroy()

    window = MainWindow(
        context=context,
    )
    window.mainloop()


if __name__ == "__main__":
    main()
    
    