"""PyInstaller entry point: `nsko-quant-engine` runs the engine, `nsko-quant-engine --watchdog` the watchdog."""
import sys

if __name__ == "__main__":
    if "--watchdog" in sys.argv:
        sys.argv.remove("--watchdog")
        from nsq.watchdog import main
    else:
        from nsq.__main__ import main
    main()
