"""奖牌预测来源、边界、动态清理及主雷达/浮窗高亮测试；不连接游戏。"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import time
import unittest
from copy import deepcopy
from dataclasses import replace
import config
from models.animal import Animal
from models.player import Player,Snapshot
from services.attribute_resolver import AttributeResolver,SavedAttributes,unique_index
from services.coordinate import aggregate
from services.trophy import TrophyCatalog,region_quality,silver_or_better,trophy_text


def candidate(entity='a',score=180,species='moose',weight=450):
    identity = (weight,score,123456)
    resolver = AttributeResolver()
    resolver.index = unique_index([SavedAttributes(identity,'male',False)])
    resolver.save_timestamp = time.time()
    return resolver.enrich(Animal(entity,species,(120,0,120),time.time(),
                                  vital_status='alive',attribute_identity=identity))


class TrophyTests(unittest.TestCase):
    def test_mallard_and_coyote_use_species_specific_levels_and_score_thresholds(self):
        # 用户报告案例：同为难度2不能据此给出同一种奖牌。
        duck=candidate('duck',16,'mallard',1.6)
        small_coyote=candidate('coyote-low',35,'coyote',16.8)
        gold_coyote=candidate('coyote-high',50,'coyote',22)
        self.assertEqual(duck.difficulty,2)
        self.assertEqual(small_coyote.difficulty,2)
        self.assertEqual(gold_coyote.difficulty,6)
        self.assertEqual(duck.trophy_prediction,'gold')
        self.assertEqual(small_coyote.trophy_prediction,'bronze')
        self.assertEqual(gold_coyote.trophy_prediction,'gold')
        self.assertTrue(silver_or_better(duck))
        self.assertFalse(silver_or_better(small_coyote))
        self.assertTrue(silver_or_better(gold_coyote))
        # 已由评分决定的奖牌不随独立的难度显示字段改变。
        self.assertTrue(silver_or_better(replace(duck,difficulty=1)))
        self.assertFalse(silver_or_better(replace(small_coyote,difficulty=9)))

    def test_bird_and_predator_max_difficulty_and_silver_highlight_are_distinct(self):
        from services.attribute_resolver import estimate_difficulty
        resolver=AttributeResolver()
        duck_levels=resolver.catalog['mallard']['level']
        coyote_levels=resolver.catalog['coyote']['level']
        self.assertEqual(len(duck_levels),3)
        self.assertEqual(len(coyote_levels),9)
        self.assertEqual(estimate_difficulty(2,duck_levels,False),3)
        self.assertEqual(estimate_difficulty(26,coyote_levels,False),9)
        silver_duck=candidate('duck-silver',12,'mallard',1.2)
        self.assertEqual(silver_duck.trophy_prediction,'silver')
        self.assertTrue(silver_or_better(silver_duck))

    def test_current_catalog_and_score_thresholds(self):
        catalog = TrophyCatalog.load(config.TROPHY_THRESHOLDS_FILE)
        self.assertEqual(len(catalog.species),127)
        for score,expected in ((0,'none'),(86.228,'bronze'),(86.229,'silver'),
                               (194.093,'silver'),(194.094,'gold'),(274.993,'diamond')):
            self.assertEqual(catalog.predict('moose',score),expected)
        for value in (True,None,float('nan'),-1,10000):
            self.assertIsNone(catalog.predict('moose',value))
        self.assertIsNone(catalog.predict('unknown animal',100))
        self.assertEqual(catalog.predict('moose',280,great_one=True),'great_one')
        self.assertIsNone(catalog.predict('blacktail deer',180,great_one=True))

    def test_catalog_refuses_ambiguous_names_and_invalid_provenance(self):
        raw = json.loads(config.TROPHY_THRESHOLDS_FILE.read_text(encoding='utf-8'))
        bad = deepcopy(raw)
        bad['species']['blacktail'] = deepcopy(bad['species']['blacktail_deer'])
        bad['species']['blacktail']['bands']['silver']['min'] += 1
        catalog = TrophyCatalog(bad)
        self.assertIsNone(catalog.predict('blacktail deer',100))
        raw['source'] = 'unverified'
        with self.assertRaises(ValueError):
            TrophyCatalog(raw)
        for invalid in (None,[],{'schema_version':1,'source':'https://github.com/example','species':[]}):
            with self.assertRaises(ValueError):
                TrophyCatalog(invalid)

    def test_only_unique_save_join_produces_live_highlight(self):
        animal = candidate()
        self.assertEqual(animal.trophy_prediction,'silver')
        self.assertTrue(silver_or_better(animal))
        self.assertIn('预测',trophy_text(animal)[1])
        self.assertFalse(silver_or_better(replace(animal,trophy_source='unknown')))
        self.assertFalse(silver_or_better(replace(animal,attribute_identity=None)))
        self.assertFalse(silver_or_better(replace(animal,status='unloaded')))
        resolver = AttributeResolver()
        self.assertFalse(silver_or_better(resolver.enrich(animal)))
        identity = animal.attribute_identity
        resolver.index = unique_index([SavedAttributes(identity,'male',False)]*2)
        self.assertFalse(silver_or_better(resolver.enrich(animal)))

    def test_difficulty_does_not_imply_medal_and_region_count_is_exact(self):
        unknown = Animal('unknown','moose',(121,0,121),time.time(),difficulty=9)
        silver = candidate('silver')
        diamond = candidate('diamond',280)
        regions = aggregate((silver,diamond,unknown),(0,0,0))
        self.assertEqual(len(regions),2)  # 未知生命状态仍与活体分组
        live = next(r for r in regions if r.vital_status=='alive')
        self.assertEqual(region_quality(live),(2,'diamond'))
        self.assertEqual(region_quality(next(r for r in regions if r.vital_status=='unknown')),(0,None))
        self.assertEqual(aggregate((),(0,0,0)),[])
        corpses = aggregate((replace(diamond,vital_status='dead'),silver),(0,0,0))
        self.assertEqual(len(corpses),2)
        self.assertTrue(all(region_quality(r)[0]==1 for r in corpses))


class TrophyUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        from services.fonts import setup_fonts
        cls.app = QApplication.instance() or QApplication([])
        setup_fonts(cls.app)

    def test_main_and_compact_draw_visible_highlight_without_moving_region(self):
        from ui.radar_widget import RadarWidget
        player = Player((0,0,0),time.time())
        regions = aggregate((candidate(),),(0,0,0))
        for compact in (False,True):
            widget = RadarWidget(compact=compact)
            try:
                widget.resize(320,320) if compact else widget.resize(600,600)
                widget.set_data(player,regions)
                widget.highlight_trophies = False
                plain = widget.grab().toImage()
                position = widget.hits[0][0]
                widget.highlight_trophies = True
                bright = widget.grab().toImage()
                self.assertEqual(widget.hits[0][0],position)
                self.assertNotEqual(bytes(plain.constBits()),bytes(bright.constBits()))
            finally:
                widget.close()

    def test_details_filter_overlay_and_disconnect_clear_consistently(self):
        from ui.main_window import MainWindow
        window = MainWindow(source='mock',start_scanner=False)
        try:
            stamp = time.time()
            window.receive(Snapshot(Player((0,0,0),stamp),(candidate(),),stamp,'模拟'))
            self.assertIn('潜在白银+',window.regions.item(0).text())
            window.show_details(window.display_regions[0])
            self.assertIn('180.000',window.details.item(0,6).text())
            self.assertIn('预测',window.details.item(0,7).text())
            window.trophy_highlight.setChecked(False)
            self.assertNotIn('潜在白银+',window.regions.item(0).text())
            if window.overlay:
                self.assertFalse(window.overlay.radar.highlight_trophies)
            window.receive(Snapshot(None,(),time.time(),'已断开',False))
            self.assertEqual(window.display_regions,[])
            self.assertEqual(window.details.rowCount(),0)
        finally:
            window.close()

    def test_diamond_highlight_in_regions_and_details(self):
        from ui.main_window import MainWindow
        window = MainWindow(source='mock',start_scanner=False)
        try:
            stamp = time.time()
            diamond_animal = candidate('diamond-1',score=280,species='moose',weight=600)
            window.receive(Snapshot(Player((0,0,0),stamp),(diamond_animal,),stamp,'模拟'))
            self.assertIn('💎潜在钻石',window.regions.item(0).text())
            window.show_details(window.display_regions[0])
            self.assertIn('💎',window.details.item(0,7).text())
            self.assertIn('钻石',window.details.item(0,7).text())
        finally:
            window.close()
