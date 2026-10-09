"""Windows DPI startup fallbacks, with no real APIs or windows invoked."""
import ctypes
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from vrization_host.gui import configure_dpi_awareness


class DpiCompatibilityTests(unittest.TestCase):
    def test_modern_per_monitor_v2_does_not_use_older_apis(self):
        modern = Mock(return_value=1)
        loader = Mock(return_value=SimpleNamespace(SetProcessDpiAwarenessContext=modern))
        self.assertEqual(configure_dpi_awareness(loader), "per-monitor-v2")
        self.assertEqual(modern.call_args.args[0].value, ctypes.c_void_p(-4).value)
        loader.assert_called_once_with("user32")

    def test_missing_modern_api_uses_windows_10_per_monitor_fallback(self):
        legacy = Mock(return_value=0)
        loader = Mock(side_effect=lambda name: SimpleNamespace(SetProcessDpiAwareness=legacy)
                      if name == "shcore" else SimpleNamespace())
        self.assertEqual(configure_dpi_awareness(loader), "per-monitor")
        legacy.assert_called_once_with(2)

    def test_failed_modern_context_still_tries_per_monitor(self):
        modern, legacy = Mock(return_value=0), Mock(return_value=0)
        loader = Mock(side_effect=lambda name: SimpleNamespace(SetProcessDpiAwareness=legacy)
                      if name == "shcore" else SimpleNamespace(SetProcessDpiAwarenessContext=modern))
        self.assertEqual(configure_dpi_awareness(loader), "per-monitor")
        self.assertEqual(modern.call_count, 1)
        legacy.assert_called_once_with(2)

    def test_missing_shcore_uses_system_awareness_without_crashing(self):
        system = Mock(return_value=1)
        def load(name):
            if name == "shcore":
                raise OSError("unavailable")
            return SimpleNamespace(SetProcessDPIAware=system)
        self.assertEqual(configure_dpi_awareness(load), "system")
        system.assert_called_once_with()

    def test_already_configured_or_unavailable_apis_are_nonfatal(self):
        modern, legacy, system = Mock(return_value=0), Mock(return_value=-2147024891), Mock(return_value=0)
        loader = Mock(side_effect=lambda name: SimpleNamespace(SetProcessDpiAwareness=legacy)
                      if name == "shcore" else SimpleNamespace(SetProcessDpiAwarenessContext=modern,
                                                               SetProcessDPIAware=system))
        self.assertEqual(configure_dpi_awareness(loader), "unchanged")
        self.assertEqual(configure_dpi_awareness(Mock(side_effect=OSError("unavailable"))), "unchanged")


if __name__ == "__main__":
    unittest.main()
