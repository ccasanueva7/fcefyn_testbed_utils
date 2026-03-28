"""Entry point: python3 -m testbed_status"""

from .app import TestbedStatusApp


def main() -> None:
    app = TestbedStatusApp()
    app.run()


if __name__ == "__main__":
    main()
