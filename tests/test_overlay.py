"""浮窗使用伪窗口查询器测试；不读取游戏、不注册全局快捷键。"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QRect,Qt
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.overlay import MiniRadar,load_settings
from services.mock import MockSource
from services.overlay_windows import match_monitor
from ctypes import wintypes as W


class FakeScreen:
    def __init__(self,name,geometry,ratio=1):
        self.label,self.rect,self.ratio = name,geometry,ratio
    def name(self):
        return self.label
    def geometry(self):
        return self.rect
    def devicePixelRatio(self):
        return self.ratio


class MonitorMatchTests(unittest.TestCase):
    def test_actual_friendly_names_two_equal_resolution_screens(self):
        screens = [FakeScreen('M27Q',QRect(0,0,2560,1440)),
                   FakeScreen('S2719DGF',QRect(2560,0,2560,1440))]
        self.assertIs(match_monitor(screens,W.RECT(0,0,2560,1440)),screens[0])
        self.assertIs(match_monitor(screens,W.RECT(2560,0,5120,1440)),screens[1])

    def test_mixed_dpi_negative_origin(self):
        screens = [FakeScreen('same model',QRect(-2560,-100,1707,960),1.5),
                   FakeScreen('same model',QRect(0,0,1920,1080),2)]
        self.assertIs(match_monitor(screens,W.RECT(-2560,-100,0,1340)),screens[0])
        self.assertIs(match_monitor(screens,W.RECT(0,0,3840,2160)),screens[1])

    def test_ambiguous_or_missing_match_rejected(self):
        screen = FakeScreen('M27Q',QRect(0,0,2560,1440))
        self.assertIsNone(match_monitor([screen,screen],W.RECT(0,0,2560,1440)))
        self.assertIsNone(match_monitor([screen],W.RECT(2560,0,5120,1440)))


class FakeWindows:
    error = ''
    result = (QRect(-1000,50,900,700),True)
    def locate(self,pid):
        return self.result if pid else None
    def close(self):
        pass


class OverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'layout.json'
        self.patch = patch('config.OVERLAY_SETTINGS_FILE',self.path)
        self.patch.start()
        self.status_patch = patch('config.OVERLAY_STATUS_FILE',Path(self.temp.name)/'status.json')
        self.status_patch.start()
        self.owner = MainWindow(source='mock',start_scanner=False)
        self.overlay = MiniRadar(self.owner,native=False)
        self.owner.overlay = self.overlay
        self.owner.game_pid = 123
        self.overlay.backend = FakeWindows()

    def tearDown(self):
        self.owner.close()
        self.patch.stop()
        self.status_patch.stop()
        self.temp.cleanup()

    def test_follows_client_hides_in_background_and_recovers(self):
        self.overlay.follow()
        self.assertTrue(self.overlay.isVisible())
        self.assertEqual(self.overlay.x(),-980)
        self.overlay.backend.result = (QRect(-1000,50,900,700),False)
        self.overlay.follow()
        self.assertFalse(self.overlay.isVisible())
        self.overlay.backend.result = None  # 游戏关闭或最小化，没有可见客户区
        self.overlay.follow()
        self.assertFalse(self.overlay.isVisible())
        self.overlay.backend.result = (QRect(400,200,1000,800),True)
        self.overlay.follow()
        self.assertTrue(self.overlay.isVisible())
        self.assertEqual(self.overlay.pos().x(),420)

    def test_same_filtered_snapshot_pause_and_stale_clear(self):
        self.owner.receive(MockSource().scan())
        self.assertEqual(self.overlay.radar.regions,self.owner.display_regions)
        self.owner.species.setCurrentIndex(self.owner.species.findData('blacktail deer'))
        self.assertTrue(self.overlay.radar.regions)
        self.assertTrue(all(r.species == 'blacktail deer' for r in self.overlay.radar.regions))
        self.owner.toggle_pause()
        self.assertIsNone(self.overlay.radar.player)
        self.assertEqual(self.overlay.radar.regions,[])
        self.owner.toggle_pause()
        from dataclasses import replace
        self.owner.receive(replace(MockSource().scan(),generation=self.owner.scanner.generation))
        self.owner.current = replace(self.owner.current,timestamp=time.time()-30)
        self.owner.check_stale()
        self.assertIsNone(self.overlay.radar.player)

    def test_lock_flags_settings_and_offscreen_recovery(self):
        self.assertTrue(self.overlay.windowFlags() & Qt.WindowType.WindowTransparentForInput)
        self.assertTrue(self.overlay.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus)
        self.overlay.follow()
        self.overlay.set_editing(True)
        self.assertFalse(self.overlay.windowFlags() & Qt.WindowType.WindowTransparentForInput)
        self.overlay.move(-900,120)
        self.overlay.change_alpha(80)
        self.overlay.set_editing(False)
        saved = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual((saved['x'],saved['y'],saved['alpha']),(100,70,80))
        self.assertEqual(set(saved),{'x','y','size','height','alpha','enabled'})
        self.overlay.settings.update(x=9999,y=9999)
        self.overlay.follow()
        self.assertLessEqual(self.overlay.geometry().right(),-101)
        self.assertLessEqual(self.overlay.geometry().bottom(),749)

    def test_region_markers_have_no_state_dependent_position_error(self):
        from ui.radar_widget import RadarWidget
        from services.coordinate import aggregate,radar_point
        from models.animal import Animal
        from models.player import Player
        from PySide6.QtCore import QPointF
        animals = [Animal(str(i),'moose',(110,0,10),time.time(),vital_status=state)
                   for i,state in enumerate(('alive','wounded','dead','unknown'))]
        regions = aggregate(animals,(0,0,0))
        for compact in (False,True):
            for north_up in (False,True):
                with self.subTest(compact=compact,north_up=north_up):
                    radar = RadarWidget(compact=compact)
                    radar.resize(320,300) if compact else radar.resize(600,600)
                    radar.north_up = north_up
                    radar.set_data(Player((0,0,0),time.time()),regions)
                    radar.show()
                    self.app.processEvents()
                    radar.grab()  # 实际触发绘制，检查最终命中锚点而非只测试转换函数
                    center = QPointF(radar.width()/2,radar.height()/2+6)
                    pixels = min(radar.width(),radar.height())/2-(35 if compact else 80)
                    dx,dy = radar_point(regions[0].position,(0,0,0),radar.radius,pixels)
                    expected = center+QPointF(dx,-dy if north_up else dy)
                    self.assertEqual(len(radar.hits),4)
                    for point,region in radar.hits:
                        self.assertAlmostEqual(point.x(),expected.x())
                        self.assertAlmostEqual(point.y(),expected.y())
                    radar.close()

    def test_invalid_settings_and_hotkey_scope(self):
        self.path.write_text('{broken',encoding='utf-8')
        self.assertEqual(load_settings(self.path)['size'],320)
        self.path.write_text(json.dumps({'size':True,'alpha':-1,'x':1e9}),encoding='utf-8')
        self.assertEqual(load_settings(self.path)['alpha'],180)
        self.overlay.backend.result = (QRect(0,0,1000,800),False)
        self.overlay.hotkey('toggle')
        self.assertTrue(self.overlay.settings['enabled'])
        self.overlay.backend.result = (QRect(0,0,1000,800),True)
        self.overlay.hotkey('toggle')
        self.assertFalse(self.overlay.settings['enabled'])
