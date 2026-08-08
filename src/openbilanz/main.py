"""Startpunkt der OpenBilanz-Anwendung."""

from openbilanz.ui.main_window import MainWindow


def main() -> None:
    """Startet OpenBilanz."""

    window = MainWindow()
    window.mainloop()


if __name__ == "__main__":
    main()
    
    