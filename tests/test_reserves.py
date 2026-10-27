"""名录和当前观测分开测试；所有快照均为模拟，不连接游戏。"""
import unittest
import copy
import json
from pathlib import Path
import tempfile
from services.reserves import CATALOG,RESERVES,load_catalog,species_for,unexpected_species,mission_species
from services.species import chinese,canonical

class ReserveTests(unittest.TestCase):
    def test_catalogs_and_unknown_reserve(self):
        self.assertEqual(len(species_for('layton')),9)
        self.assertEqual(len(species_for('medved')),8)
        self.assertNotIn('blacktail deer',species_for('medved'))
        self.assertNotIn('roosevelt elk',species_for('medved'))
        self.assertIn('gray wolf',species_for('medved'))
        self.assertEqual(species_for(None,['moose','moose']),('moose',))
        self.assertEqual(species_for(None),())
        self.assertEqual(unexpected_species('medved',['moose','blacktail deer']),('blacktail deer',))
        for reserve in RESERVES:
            for name in species_for(reserve):
                self.assertNotIn('未识别',chinese(name))

    def test_all_19_reviewed_counts_and_key_updates(self):
        # 按公开来源独立复核的基准，防止漏区、误删补充物种、亚种替换退回旧版。
        expected = {'hirschfelden':9,'layton':9,'medved':8,'vurhonga':10,'parque':8,
                    'yukon':8,'cuatro':11,'silver':9,'te_awaroa':10,'rancho':10,
                    'mississippi':10,'revontuli':19,'new_england':15,'emerald':14,
                    'sundarpatan':13,'salzwiesen':15,'askiy':19,'scotland':17,'intisuyu':14}
        self.assertEqual({key:len(value[1]) for key,value in RESERVES.items()},expected)
        self.assertEqual(len({s for _,names in RESERVES.values() for s in names}),128)
        for reserve,name in [('hirschfelden','ring necked pheasant'),('layton','wild turkey'),
                             ('medved','gray wolf'),('vurhonga','eurasian wigeon'),
                             ('parque','collared peccary'),('yukon','canada goose'),
                             ('te_awaroa','mallard'),('te_awaroa','himalayan tahr'),
                             ('rancho','pronghorn'),('rancho','desert bighorn sheep'),
                             ('mississippi','green winged teal'),('intisuyu','taruca')]:
            self.assertIn(name,species_for(reserve))
        self.assertNotIn('rocky mountain bighorn sheep',species_for('rancho'))
        self.assertNotIn('moose',species_for('te_awaroa'))
        self.assertEqual(mission_species('te_awaroa'),('moose',))
        self.assertEqual(unexpected_species('te_awaroa',['moose']),())

    def test_corrupt_catalog_is_rejected(self):
        def missing(data): data['reserves'].pop()
        def duplicate_id(data): data['reserves'][1]['id'] = data['reserves'][0]['id']
        def duplicate_species(data): data['reserves'][0]['species'][1] = data['reserves'][0]['species'][0]
        def unknown_species(data): data['reserves'][0]['species'][0] = 'invented species'
        def missing_source(data): data['reserves'][0]['sources'] = ['missing']
        def wrong_count(data): data['reserves'][0]['expected_count'] = 100
        def wrong_version(data): data['schema_version'] = 999
        def duplicate_mission(data): data['reserves'][8]['mission_only'] = ['moose','moose']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'catalog.json'
            for mutation in (missing,duplicate_id,duplicate_species,unknown_species,missing_source,
                             wrong_count,wrong_version,duplicate_mission):
                with self.subTest(mutation=mutation.__name__):
                    data = copy.deepcopy(CATALOG)
                    mutation(data)
                    path.write_text(json.dumps(data),encoding='utf-8')
                    with self.assertRaises(ValueError): load_catalog(path)

    def test_name_variants_do_not_merge_distinct_subspecies(self):
        self.assertEqual(canonical('Ring-Necked_Pheasant'),'ring necked pheasant')
        self.assertEqual(canonical('Mountain Reindeer'),'reindeer')
        for a,b in [('bobcat','mexican bobcat'),('feral pig','wild hog'),
                    ('mountain lion','puma'),('grant caribou','woodland caribou'),
                    ('desert bighorn sheep','rocky mountain bighorn sheep')]:
            self.assertNotEqual(canonical(a),canonical(b))

    def test_published_report_matches_current_catalog(self):
        from catalog_report import render_catalog
        import config
        self.assertEqual(config.CATALOG_REPORT_FILE.read_text(encoding='utf-8'),render_catalog())
