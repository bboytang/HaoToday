"""独立配置工具测试；只使用临时假密钥，不读取服务器文件。"""
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("shopping_key",Path(__file__).resolve().parents[1]/"deploy/configure-shopping-key.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class KeyTests(unittest.TestCase):
    def test_private_file_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"key"
            module.save_key(path,"fixture-only")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            self.assertEqual(path.read_text(),"fixture-only")
            with self.assertRaises(FileExistsError):
                module.save_key(path,"another-fixture")
            self.assertEqual(path.read_text(),"fixture-only")

    def test_reject_bad_input_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"key"
            for key in ("","bad\nvalue","bad value","坏", "x"*513):
                with self.assertRaises(ValueError):
                    module.save_key(path,key)
                self.assertFalse(path.exists())
            target=Path(directory)/"target"
            target.write_text("untouched")
            path.symlink_to(target)
            with self.assertRaises(FileExistsError):
                module.save_key(path,"fixture-only")
            self.assertEqual(target.read_text(),"untouched")


if __name__=="__main__":
    unittest.main()
