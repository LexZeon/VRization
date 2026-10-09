import sys


def main():
    if "--usb-diagnostics" in sys.argv[1:]:
        from .usb_diagnostics import main as diagnostics_main
        return diagnostics_main(sys.argv[1:])
    from .gui import main as gui_main
    gui_main()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
