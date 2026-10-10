import unittest
from archive_releases import stable_public_releases

class ChannelTests(unittest.TestCase):
    def test_newer_preview_is_never_selected_for_stable_archive(self):
        stable={"draft":False,"tag_name":"v0.4.0-alpha","assets":[{"name":"VRization-Windows-x64.zip"}]}
        preview={"draft":False,"tag_name":"v0.5.0-steamvr-preview","assets":[{"name":"VRization-SteamVR-Windows-x64.zip"}]}
        self.assertEqual(stable_public_releases([preview,stable]),[stable])
    def test_draft_and_nonwindows_releases_do_not_replace_runnable_latest(self):
        self.assertEqual(stable_public_releases([{"draft":True,"assets":[{"name":"VRization-Windows-x64.zip"}]},{"draft":False,"assets":[]}]),[])
