"""在无网络环境中用真实pip解析器验证Windows依赖文件编码。"""
from pathlib import Path
import unittest
from unittest.mock import patch


class RequirementsTests(unittest.TestCase):
    def test_pip_reads_requirements_with_gbk_locale(self):
        from pip._internal.req.req_file import parse_requirements
        from pip._internal.network.session import PipSession
        root = Path(__file__).resolve().parents[1]
        # 依赖文件仅ASCII，兼容旧版pip在中文Windows的默认GBK读取。
        for name in ('requirements.txt','requirements-dev.txt'):
            (root/name).read_bytes().decode('ascii')
        with patch('locale.getpreferredencoding',return_value='cp936'):
            with PipSession() as session:
                requirements = list(parse_requirements(str(root/'requirements-dev.txt'),session=session))
        self.assertEqual([r.requirement for r in requirements],
                         ['PySide6-Essentials==6.8.3','pytest>=8,<10'])
