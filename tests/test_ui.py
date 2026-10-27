"""安装 PySide6 后可离屏执行；缺少依赖则明确跳过。"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import importlib.util
import unittest

@unittest.skipUnless(importlib.util.find_spec('PySide6'),'PySide6 未安装，UI 未验证')
class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        from services.fonts import setup_fonts
        setup_fonts(cls.app)

    def test_chinese_font_has_required_glyphs(self):
        import config
        if not config.UI_FONT_PATH.is_file():
            self.skipTest('本机未找到配置的中文字体')
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(self.app.font())
        self.assertTrue(all(metrics.inFontUcs4(ord(c)) for c in '黑尾鹿白北南123'))

    def test_paused_reconnect_shows_resume_instruction(self):
        from ui.main_window import MainWindow
        window = MainWindow(source='mock',start_scanner=False)
        try:
            window.toggle_pause()
            window.reconnect()
            self.assertTrue(window.scanner.paused.is_set())
            self.assertIn('恢复刷新',window.summary.text())
            self.assertIn('仍暂停',window.state.text())
            window.toggle_pause()
            self.assertFalse(window.scanner.paused.is_set())
            self.assertEqual(window.state.text(),'等待新采样')
        finally:
            window.close()

    def test_unexpected_scanner_exit_clears_waiting_state(self):
        from ui.main_window import MainWindow
        window = MainWindow(source='mock',start_scanner=False)
        try:
            window.reconnect()
            window.scanner_finished()
            self.assertIn('后台扫描已停止',window.state.text())
            self.assertIsNone(window.radar.player)
            self.assertFalse(window.reconnect_button.isEnabled())
        finally:
            window.close()

    def test_reserve_switch_drops_old_frame_and_excludes_foreign_species(self):
        from dataclasses import replace
        from ui.main_window import MainWindow
        from services.mock import MockSource
        window = MainWindow(source='field_test',start_scanner=False)
        try:
            old = MockSource().scan()
            window.receive(old)
            window.reserve.setCurrentIndex(window.reserve.findData('medved'))
            self.assertEqual(window.species.findData('blacktail deer'),-1)
            self.assertGreater(window.species.findData('reindeer'),0)
            self.assertIsNone(window.radar.player)
            window.receive(old)
            self.assertIsNone(window.radar.player)
            fresh = replace(old,generation=window.scanner.generation,scene_changed=True)
            window.receive(fresh)
            self.assertEqual(window.selected_reserve,'medved')
            self.assertTrue(window.display_regions)
            self.assertTrue(all(r.species == 'moose' for r in window.display_regions))
            self.assertIn('名录外候选',window.state.text())
            self.assertTrue(window.reserve_confirm.isEnabled())
            window.confirm_reserve()
            self.assertTrue(window.radar.north_up)
            window.reconnect()
            self.assertTrue(window.radar.north_up)
            self.assertEqual(window.selected_reserve,'medved')
        finally:
            window.close()

    def test_unknown_reserve_menu_replaces_observations_and_scene_preserves_selection(self):
        from dataclasses import replace
        from ui.main_window import MainWindow
        from services.mock import MockSource
        window = MainWindow(source='field_test',start_scanner=False)
        try:
            old = MockSource().scan()
            window.receive(old)
            self.assertGreater(window.species.findData('blacktail deer'),0)
            window.receive(replace(old,animals=tuple(a for a in old.animals if a.species == 'moose')))
            self.assertEqual(window.species.findData('blacktail deer'),-1)
            window.reserve.setCurrentIndex(window.reserve.findData('medved'))
            current = replace(old,generation=window.scanner.generation,scene_id='first')
            window.receive(current)
            window.receive(replace(current,scene_id='second',scene_changed=True))
            self.assertEqual(window.selected_reserve,'medved')
            self.assertEqual(window.reserve.currentData(),'medved')
            self.assertFalse(window.reserve.isEnabled())
            self.assertIn('更换保护区',window.state.text())
        finally:
            window.close()

    def test_all_reserve_menus_and_mission_exception(self):
        from dataclasses import replace
        from ui.main_window import MainWindow
        from services.reserves import RESERVES
        from services.mock import MockSource
        from PySide6.QtTest import QSignalSpy
        window = MainWindow(source='field_test',start_scanner=False)
        try:
            self.assertEqual(window.reserve.count(),20)  # 19区加未确认项
            for key,(_,names) in RESERVES.items():
                with self.subTest(reserve=key):
                    window.reserve.setCurrentIndex(window.reserve.findData(key))
                    self.assertEqual([window.species.itemData(i) for i in range(1,window.species.count())],list(names))
                    self.assertIsNone(window.radar.player)
                    self.assertTrue(window.reserve_confirm.isEnabled())
                    window.confirm_reserve()
                    self.assertTrue(window.radar.north_up)
            window.reserve.setCurrentIndex(window.reserve.findData('te_awaroa'))
            self.assertEqual(window.species.findData('moose'),-1)
            sample = MockSource().scan()
            sample = replace(sample,animals=tuple(a for a in sample.animals if a.species == 'moose'),
                             generation=window.scanner.generation)
            window.receive(sample)
            index = window.species.findData('moose')
            self.assertGreater(index,0)
            self.assertIn('任务专属',window.species.itemText(index))
            self.assertIn('任务专属候选',window.state.text())
            self.assertTrue(window.display_regions)
            spy = QSignalSpy(window.species.model().modelReset)
            window.receive(sample)
            self.assertEqual(spy.count(),0)
            window.receive(replace(sample,animals=()))
            self.assertEqual(window.species.findData('moose'),-1)
        finally:
            window.close()

    def test_region_selection_survives_refresh(self):
        from ui.main_window import MainWindow
        from services.mock import MockSource
        window = MainWindow(source='mock',start_scanner=False)
        snapshot = MockSource().scan()
        window.receive(snapshot)
        region = window.display_regions[0]
        window.select_region(region)
        window.receive(snapshot)
        self.assertEqual(window.radar.target,region.key)
        self.assertIn('探索目标',window.target.text())
        window.close()

    def test_corpse_filter_and_details_clear_when_entity_disappears(self):
        from dataclasses import replace
        from ui.main_window import MainWindow
        from services.mock import MockSource
        window = MainWindow(source='mock',start_scanner=False)
        source = MockSource()
        source.tick = 9
        snapshot = source.scan()
        try:
            window.receive(snapshot)
            corpse = next(r for r in window.display_regions if r.vital_status == 'dead')
            window.select_region(corpse)
            self.assertEqual(window.details.rowCount(),1)
            self.assertEqual(window.details.item(0,1).text(),'已死亡')
            self.assertEqual(window.details.item(0,3).text(),'0.0%')
            window.life_filter.setCurrentIndex(window.life_filter.findData('dead'))
            self.assertTrue(all(r.vital_status == 'dead' for r in window.display_regions))
            window.receive(replace(snapshot,animals=tuple(a for a in snapshot.animals if a.vital_status != 'dead')))
            self.assertEqual(window.details.rowCount(),0)
            self.assertEqual(window.display_regions,[])
            self.assertIsNone(window.radar.target)
            # 未验证字段必须在详情里保持未知，不能沿用先前个体属性。
            window.life_filter.setCurrentIndex(0)
            unknown = replace(snapshot.animals[1],vital_status='unknown',health_percent=None,
                              sex=None,fur_color=None,difficulty=None,details_source='unknown')
            window.receive(replace(snapshot,animals=(unknown,)))
            window.select_region(window.display_regions[0])
            self.assertEqual([window.details.item(0,c).text() for c in range(1,6)],['未知']*5)
            window.toggle_pause()
            self.assertEqual(window.details.rowCount(),0)
        finally:
            window.close()

    def test_field_test_session_end_discards_queued_snapshots(self):
        from ui.main_window import MainWindow
        from services.mock import MockSource
        window = MainWindow(source='field_test',start_scanner=False)
        window.reserve.setCurrentIndex(window.reserve.findData('layton'))
        from dataclasses import replace
        snapshot = MockSource().scan()
        snapshot = replace(snapshot,generation=window.scanner.generation)
        window.receive(snapshot)
        self.assertEqual(window.species.currentData(),None)
        self.assertFalse(window.radar.north_up)
        window.confirm_reserve()
        self.assertTrue(window.radar.north_up)
        self.assertIn('已加载',window.summary.text())
        self.assertFalse(window.radar.grab().isNull())
        window.end_session()
        window.receive(snapshot)
        self.assertIsNone(window.radar.player)
        self.assertEqual(window.radar.regions,[])
        self.assertFalse(window.reconnect_button.isEnabled())
        window.close()

    def test_filter_pause_clear_render(self):
        from dataclasses import replace
        from PySide6.QtWidgets import QApplication
        from ui.main_window import MainWindow
        from services.mock import MockSource
        from models.player import Snapshot
        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        window.scanner.stop()
        self.assertTrue(window.scanner.wait(3000))
        snapshot = replace(MockSource().scan(),generation=window.scanner.generation)
        window.receive(snapshot)
        window.species.setCurrentIndex(1)
        self.assertTrue(all(r.species == 'blacktail deer' for r in window.display_regions))
        window.radar.resize(600,600)
        self.assertFalse(window.radar.grab().isNull())
        window.toggle_pause()
        self.assertIsNone(window.radar.player)
        window.toggle_pause()
        window.receive(Snapshot(None,(),snapshot.timestamp,'断开',False,generation=window.scanner.generation))
        self.assertEqual(window.radar.regions,[])
        window.close()
        app.processEvents()

    def test_old_queued_snapshots_cannot_reappear_after_controls(self):
        from dataclasses import replace
        from ui.main_window import MainWindow
        from services.mock import MockSource
        window = MainWindow(source='mock',start_scanner=False)
        old = MockSource().scan()
        window.receive(old)
        self.assertIsNotNone(window.radar.player)
        window.toggle_pause()
        window.toggle_pause()
        window.receive(old)
        self.assertIsNone(window.radar.player)
        fresh = replace(old,generation=window.scanner.generation)
        window.receive(fresh)
        self.assertIsNotNone(window.radar.player)
        window.reconnect()
        window.receive(fresh)
        self.assertIsNone(window.radar.player)
        window.close()

    def test_scene_change_clears_target_but_preserves_manual_reserve_and_direction(self):
        from dataclasses import replace
        from ui.main_window import MainWindow
        from services.mock import MockSource
        window = MainWindow(source='field_test',start_scanner=False)
        window.reserve.setCurrentIndex(window.reserve.findData('layton'))
        old = replace(MockSource().scan(),scene_id='1:a',generation=window.scanner.generation)
        window.receive(old)
        window.confirm_reserve()
        window.select_region(window.display_regions[0])
        window.receive(replace(old,scene_id='1:b',scene_changed=True))
        self.assertIsNone(window.radar.target)
        self.assertTrue(window.reserve_confirmed)
        self.assertTrue(window.radar.north_up)
        self.assertEqual(window.selected_reserve,'layton')
        window.close()

    def test_locked_reserve_survives_failure_recovery_pause_and_explicit_reconnect(self):
        from dataclasses import replace
        import time
        from models.player import Snapshot
        from ui.main_window import MainWindow
        from services.mock import MockSource
        window = MainWindow(source='field_test',start_scanner=False)
        try:
            window.reserve.setCurrentIndex(window.reserve.findData('medved'))
            self.assertTrue(window.reserve_lock.isChecked())
            self.assertFalse(window.reserve.isEnabled())
            window.confirm_reserve()
            sample = replace(MockSource().scan(),generation=window.scanner.generation,scene_id='old')
            window.receive(sample)
            window.select_region(window.display_regions[0])
            window.receive(Snapshot(None,(),time.time(),'短暂读取失败',False,generation=window.scanner.generation))
            self.assertEqual(window.selected_reserve,'medved')
            self.assertTrue(window.reserve_confirmed)
            self.assertIsNone(window.radar.player)
            self.assertEqual(window.details.rowCount(),0)
            self.assertIsNone(window.radar.target)
            recovered = replace(sample,scene_id='new',scene_changed=True)
            window.receive(recovered)
            self.assertEqual(window.reserve.currentData(),'medved')
            self.assertTrue(window.radar.north_up)
            window.toggle_pause()
            window.toggle_pause()
            window.reconnect()
            self.assertEqual(window.selected_reserve,'medved')
            self.assertTrue(window.reserve_confirmed)
            self.assertTrue(window.radar.north_up)
            self.assertIsNone(window.radar.player)
            # 必须明确解锁并改选，才清除旧方向和实体。
            window.reserve_lock.click()
            self.assertTrue(window.reserve.isEnabled())
            window.reserve.setCurrentIndex(window.reserve.findData('intisuyu'))
            self.assertFalse(window.reserve.isEnabled())
            self.assertEqual(window.selected_reserve,'intisuyu')
            self.assertFalse(window.reserve_confirmed)
            self.assertFalse(window.radar.north_up)
            self.assertIsNone(window.radar.player)
            window.reserve_lock.click()
            window.reserve.setCurrentIndex(0)
            self.assertIsNone(window.selected_reserve)
            self.assertTrue(window.reserve.isEnabled())
        finally:
            window.close()

    def test_session_timer_is_optional(self):
        from unittest.mock import patch
        from ui.main_window import MainWindow
        from services.mock import MockSource
        for seconds in (0,300):
            with patch('config.FIELD_TEST_SESSION_SECONDS',seconds),patch('services.live.LiveSource',side_effect=lambda **_:MockSource()):
                window = MainWindow(source='field_test')
                self.assertEqual(window.session_timer.isActive(),seconds > 0)
                window.close()
