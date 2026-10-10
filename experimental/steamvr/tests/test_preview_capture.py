"""Native mirror adapter fixtures use original BGRA pixels; no helper is executed."""
from io import BytesIO
import unittest
from unittest.mock import Mock, patch
from PIL import Image
from vrization_host.capture import CaptureConfig
from vrization_steamvr.capture import MirrorCaptureSource


class PreviewCaptureTests(unittest.TestCase):
    def fixture(self):
        child=Mock();child.poll.return_value=None
        reader=Mock()
        # Two distinct stereo halves, BGRA input with a known top/bottom green gradient.
        pixels=b"".join(bytes((10,30+y,220,255) if x<64 else (220,30+y,10,255))
                        for y in range(64) for x in range(128))
        sample=(128,64,pixels,1000)
        reader.read.return_value=sample
        processes=Mock(return_value=child);readers=Mock(return_value=reader)
        source=MirrorCaptureSource(process_factory=processes,reader_factory=readers,helper=lambda name:"owned-mirror.exe")
        return source,child,reader,processes,readers,sample

    def test_gpu_bounded_stereo_pixels_are_encoded_without_any_cpu_resize(self):
        source,child,reader,processes,_,_=self.fixture()
        with patch.object(Image.Image,"resize",side_effect=AssertionError("Do not rescale packed eyes on CPU")):
            frame=source.read(CaptureConfig(width=3840,quality=90))
        args=processes.call_args.args[1]
        self.assertEqual(args[args.index("--width")+1],1920)
        image=Image.open(BytesIO(frame.jpeg)).convert("RGB")
        self.assertEqual((frame.width,frame.height,image.size),(128,64,(128,64)))
        self.assertGreater(image.getpixel((32,16))[0],210)
        self.assertGreater(image.getpixel((96,16))[2],210)
        self.assertGreater(image.getpixel((32,48))[1],image.getpixel((32,16))[1])
        source.close();child.close.assert_called_once();reader.close.assert_called_once()

    def test_same_native_tick_reuses_jpeg_but_quality_changes_reencode(self):
        source,_,_,processes,_,_=self.fixture()
        first=source.read(CaptureConfig(quality=45));second=source.read(CaptureConfig(quality=45))
        self.assertIs(first,second)
        changed=source.read(CaptureConfig(quality=90))
        self.assertIsNot(first,changed)
        self.assertNotEqual(first.jpeg,changed.jpeg)
        self.assertEqual(processes.call_count,1)
        source.close()

    def test_missing_native_sample_does_not_republish_the_stale_saved_frame(self):
        source,_,reader,_,_,_=self.fixture()
        self.assertIsNotNone(source.read(CaptureConfig()))
        reader.read.return_value=None
        self.assertIsNone(source.read(CaptureConfig()))
        self.assertIsNone(source.frame)
        source.close()

    def test_width_or_fps_change_releases_both_owned_resources_before_restart(self):
        source,child,reader,processes,readers,_=self.fixture()
        source.read(CaptureConfig(width=641,fps=30))
        self.assertEqual(source.key,(640,30))
        source.read(CaptureConfig(width=960,fps=60))
        child.close.assert_called_once();reader.close.assert_called_once()
        self.assertEqual(processes.call_count,2);self.assertEqual(readers.call_count,2)
        self.assertEqual(source.key,(960,60))
        source.close()

    def test_child_exit_and_startup_timeout_are_honest_capture_errors(self):
        source,child,reader,_,_,_=self.fixture()
        child.poll.return_value=3
        with self.assertRaisesRegex(OSError,"mirror exited"):
            source.read(CaptureConfig())
        source.close()
        source,_,reader,_,_,_=self.fixture();reader.read.return_value=None
        with patch("vrization_steamvr.capture.time.perf_counter",return_value=100):
            self.assertIsNone(source.read(CaptureConfig()))
        with patch("vrization_steamvr.capture.time.perf_counter",return_value=166):
            with self.assertRaisesRegex(TimeoutError,"no Phone HMD compositor frames"):
                source.read(CaptureConfig())
        source.close()

    def test_reader_is_released_even_if_owned_child_close_reports_an_error(self):
        source,child,reader,_,_,_=self.fixture();source.read(CaptureConfig())
        child.close.side_effect=OSError("owned child teardown")
        with self.assertRaises(OSError):
            source.close()
        reader.close.assert_called_once()
        self.assertIsNone(source.process)
        self.assertIsNone(source.reader)
        self.assertIsNone(source.frame)


if __name__ == "__main__":
    unittest.main()
