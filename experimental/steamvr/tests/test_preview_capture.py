"""Native mirror adapter fixtures use original BGRA pixels; no helper is executed."""
from io import BytesIO
import unittest
from unittest.mock import Mock, patch
from PIL import Image
from vrization_host.capture import CaptureConfig, CaptureWorker, output_size
from vrization_steamvr.capture import MirrorCaptureSource, overlay_config


class PreviewCaptureTests(unittest.TestCase):
    def test_overlay_capture_bounds_both_axes_for_portrait_and_non_widescreen_displays(self):
        for source in ((1920,1200),(1920,1080),(1080,1920),(2560,2560),(5120,1440),
                       (3440,1440),(1200,1600),(600,800),(100,300)):
            for ceiling in (640,960,1280,1600,1920):
                with self.subTest(source=source,ceiling=ceiling):
                    original=CaptureConfig(monitor=2,width=ceiling,fps=30,quality=90)
                    changed=overlay_config(original,{"width":source[0],"height":source[1]})
                    width,height=output_size(*source,changed.width)
                    self.assertLessEqual(width,1920)
                    self.assertLessEqual(height,1080)
                    self.assertLessEqual(max(width,height),ceiling)
                    self.assertLessEqual(width,source[0])
                    self.assertLessEqual(height,source[1])
                    self.assertEqual((changed.monitor,changed.fps,changed.quality),(2,30,90))
                    self.assertEqual(original.width,ceiling)
        changed=overlay_config(CaptureConfig(width=1920),{"width":1920,"height":1200})
        self.assertEqual(output_size(1920,1200,changed.width),(1728,1080))
        portrait=overlay_config(CaptureConfig(width=1920),{"width":1080,"height":1920})
        self.assertEqual(output_size(1080,1920,portrait.width),(608,1080))

    def test_overlay_capture_refuses_unavailable_display_dimensions(self):
        for width,height in ((0,1080),(1920,0),(-1,1080),(1920,-1)):
            with self.subTest(width=width,height=height):
                with self.assertRaisesRegex(ValueError,"unavailable"):
                    overlay_config(CaptureConfig(),{"width":width,"height":height})

    def fixture(self):
        child=Mock();child.poll.return_value=None
        reader=Mock()
        # Two distinct stereo halves, BGRA input with a known top/bottom green gradient.
        pixels=b"".join(bytes((10,30+y,220,255) if x<64 else (220,30+y,10,255))
                        for y in range(64) for x in range(128))
        sample=(128,64,pixels,1000,2)
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

    def test_same_native_publication_is_not_resent_but_quality_changes_and_new_ticks_encode_once(self):
        source,_,reader,processes,_,sample=self.fixture()
        with patch("vrization_steamvr.capture.Image.frombytes",wraps=Image.frombytes) as convert:
            first=source.read(CaptureConfig(quality=45))
            for _ in range(8):self.assertIsNone(source.read(CaptureConfig(quality=45)))
            self.assertIs(source.frame,first,"Skipped polls must retain the JPEG cache")
            self.assertEqual(convert.call_count,1,"Duplicates must not reconvert or encode the image")
            changed=source.read(CaptureConfig(quality=90))
            self.assertIsNot(first,changed)
            self.assertNotEqual(first.jpeg,changed.jpeg)
            self.assertIsNone(source.read(CaptureConfig(quality=90)))
            self.assertIs(source.frame,changed)
            self.assertEqual(convert.call_count,2)
            reader.read.return_value=(*sample[:3],sample[3]+1,sample[4]+2)
            fresh=source.read(CaptureConfig(quality=90))
            self.assertIsNotNone(fresh)
            self.assertIsNot(fresh,changed)
            self.assertIsNone(source.read(CaptureConfig(quality=90)))
            self.assertEqual(convert.call_count,3)
        self.assertEqual(processes.call_count,1)
        source.close()

    def test_distinct_publications_with_the_same_coarse_tick_are_not_dropped(self):
        source,_,reader,_,_,sample=self.fixture()
        first=source.read(CaptureConfig())
        pixels=bytes((24,99,200,255))*(sample[0]*sample[1])
        reader.read.return_value=(sample[0],sample[1],pixels,sample[3],sample[4]+2)
        fresh=source.read(CaptureConfig())
        self.assertIsNotNone(fresh)
        self.assertNotEqual(first.jpeg,fresh.jpeg)
        self.assertIsNone(source.read(CaptureConfig()))
        self.assertEqual((source.last_tick,source.last_sequence),(1000,4))
        source.close()

    def test_unsigned_sequence_wrap_is_a_new_publication_not_an_old_frame_replay(self):
        source,_,reader,_,_,sample=self.fixture()
        reader.read.return_value=(*sample[:4],0xfffffffe)
        before=source.read(CaptureConfig())
        reader.read.return_value=(*sample[:4],0)
        wrapped=source.read(CaptureConfig())
        self.assertIsNotNone(wrapped)
        self.assertIsNot(before,wrapped)
        self.assertIsNone(source.read(CaptureConfig()))
        self.assertEqual(source.last_sequence,0)
        source.close();self.assertIsNone(source.last_sequence)

    def test_reader_missing_a_publication_sequence_cannot_invent_fresh_frames(self):
        source,_,reader,_,_,sample=self.fixture()
        reader.read.return_value=sample[:4]
        with self.assertRaises(ValueError):source.read(CaptureConfig())
        self.assertIsNone(source.frame)
        self.assertIsNone(source.last_sequence)
        source.close()

    def test_missing_native_sample_does_not_republish_the_stale_saved_frame(self):
        source,_,reader,_,_,_=self.fixture()
        self.assertIsNotNone(source.read(CaptureConfig()))
        reader.read.return_value=None
        self.assertIsNone(source.read(CaptureConfig()))
        self.assertIsNone(source.frame)
        source.close()

    def test_capture_worker_publishes_three_native_updates_not_six_polling_iterations(self):
        source,child,reader,_,_,sample=self.fixture()
        identities=((1000,2),(1000,2),(1000,4),(1000,4),(1000,4),(1000,6))
        polls=[0];now=[0.];callbacks=[];published=[]
        def read():
            identity=identities[polls[0]];polls[0]+=1
            if polls[0]==len(identities):worker.stop_event.set()
            return (*sample[:3],*identity)
        reader.read.side_effect=read
        loop=Mock();loop.call_soon_threadsafe.side_effect=callbacks.append
        buffer=Mock();buffer.publish.side_effect=published.append
        worker=CaptureWorker(source,lambda:CaptureConfig(fps=60),loop,buffer,self.fail)
        worker.active.set()
        def drain():
            while callbacks:callbacks.pop(0)()
        def sleep(delay):now[0]+=delay;drain()
        with patch("vrization_host.capture.time.perf_counter",side_effect=lambda:now[0]), \
             patch("vrization_host.capture.time.sleep",side_effect=sleep):
            worker._run();drain()
        self.assertEqual(polls[0],6)
        self.assertEqual(len(published),3,"Native updates alone must advance the network buffer")
        self.assertEqual(len({id(frame) for frame in published}),3)
        self.assertTrue(all(frame.width==128 and frame.height==64 for frame in published))
        child.close.assert_called_once();reader.close.assert_called_once()
        self.assertIsNone(source.frame)

    def test_width_or_fps_change_releases_both_owned_resources_before_restart(self):
        source,child,reader,processes,readers,_=self.fixture()
        first=source.read(CaptureConfig(width=641,fps=30))
        self.assertEqual(source.key,(640,30))
        restarted=source.read(CaptureConfig(width=960,fps=60))
        self.assertIsNotNone(restarted,"The new helper's matching tick/sequence is not the old session")
        self.assertIsNot(first,restarted)
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
