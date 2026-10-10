"""Resource lifecycle checks without running SteamVR or registering a driver."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock
from vrization_steamvr.runtime import OwnedProcess,DriverManager,discover_runtime
from vrization_steamvr.ipc import FRAME,decode_frame


class RuntimeTests(unittest.TestCase):
    def test_graceful_child_close_signals_then_waits_and_never_terminates(self):
        order=[];event=Mock(name="event");event.name="Local\\VRizationStop-"+"a"*32
        event.signal.side_effect=lambda:order.append("signal")
        child=Mock();child.poll.return_value=None;child.wait.side_effect=lambda **kwargs:order.append("wait")
        popen=Mock(return_value=child)
        process=OwnedProcess("owned.exe",["--frame-map","unique"],popen=popen,event_factory=lambda:event)
        process.close();process.close()
        self.assertEqual(order,["signal","wait"]);child.terminate.assert_not_called();child.kill.assert_not_called()
        event.close.assert_called_once()
        self.assertEqual(popen.call_args.args[0][-2:],["--stop-event",event.name])

    def test_stuck_child_fallback_only_uses_the_owned_popen_handle(self):
        event=Mock();event.name="Local\\owned";child=Mock();child.poll.return_value=None
        child.wait.side_effect=[subprocess.TimeoutExpired("owned",2),None]
        process=OwnedProcess("owned.exe",[],popen=lambda *args,**kwargs:child,event_factory=lambda:event)
        process.close();child.terminate.assert_called_once();child.kill.assert_not_called();event.close.assert_called_once()

    def test_failed_child_creation_releases_stop_event(self):
        event=Mock();event.name="Local\\owned"
        with self.assertRaises(OSError):OwnedProcess("missing.exe",[],popen=Mock(side_effect=OSError()),event_factory=lambda:event)
        event.signal.assert_called_once();event.close.assert_called_once()

    def test_driver_registration_changes_exact_owned_path_only(self):
        with tempfile.TemporaryDirectory() as temp:
            driver=Path(temp)/"drivers/vrization_phone";driver.mkdir(parents=True)
            (driver/"driver.vrdrivermanifest").write_text('{}')
            run=Mock(return_value=Mock(returncode=0,stdout="ok",stderr=""))
            manager=DriverManager(runtime=Path(temp)/"runtime",driver=driver,run=run)
            manager.change(True);manager.change(False)
            commands=[call.args[0] for call in run.call_args_list]
            self.assertEqual([command[1] for command in commands],["adddriver","removedriver"])
            self.assertTrue(all(command[2]==str(driver.resolve()) for command in commands))
            self.assertTrue(all(len(command)==3 for command in commands))

    def test_discovery_reads_inventory_but_never_creates_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);inventory=root/"openvrpaths.vrpath"
            self.assertIsNone(discover_runtime(inventory));self.assertFalse(inventory.exists())
            executable=root/"runtime/bin/win64/vrpathreg.exe";executable.parent.mkdir(parents=True);executable.touch()
            inventory.write_text(json.dumps({"runtime":[str(root/"missing"),str(root/"runtime")],"external_drivers":["other-driver"]}))
            before=inventory.read_bytes();self.assertEqual(discover_runtime(inventory),root/"runtime")
            self.assertEqual(before,inventory.read_bytes())

    def test_frame_layout_and_stale_guard(self):
        header=FRAME.pack(b"VRF1",1,64,2,4,2,16,1,1000,bytes(24));pixels=bytes(32)
        self.assertEqual(decode_frame(header,pixels,1500,stereo=True),(4,2,pixels,1000))
        self.assertIsNone(decode_frame(header,pixels,1501,stereo=True))
        self.assertIsNone(decode_frame(header,pixels,999,stereo=True))
        odd=FRAME.pack(b"VRF1",1,64,2,3,2,12,1,1000,bytes(24))
        with self.assertRaises(ValueError):decode_frame(odd,bytes(24),1000,stereo=True)
        torn=FRAME.pack(b"VRF1",1,64,3,4,2,16,1,1000,bytes(24))
        with self.assertRaises(ValueError):decode_frame(torn,pixels,1000,stereo=True)

    def test_windows_shared_map_reader_observes_writer_and_inactive_close(self):
        import os
        if os.name!="nt":self.skipTest("Windows-only owned named memory")
        from vrization_steamvr.ipc import FrameWriter,FrameReader,frame_name
        name=frame_name();writer=FrameWriter(name);reader=FrameReader(name,stereo=True)
        try:
            pixels=bytes([17,29,61,255])*8;writer.publish(4,2,pixels)
            sample=reader.read();self.assertEqual(sample[:3],(4,2,pixels))
            writer.close();self.assertIsNone(reader.read())
        finally:writer.close();reader.close()

    def test_windows_stop_event_can_be_released_twice(self):
        import os
        if os.name!="nt":self.skipTest("Windows-only owned named event")
        from vrization_steamvr.ipc import StopEvent
        event=StopEvent();self.assertTrue(event.name.startswith("Local\\VRizationStop-"));event.signal();event.close();event.close()
