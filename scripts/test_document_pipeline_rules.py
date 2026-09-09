"""Focused regression checks for the document experiment's business rules."""
import json
import unittest
from pathlib import Path

from document_pipeline_rules import apply_rules

ROOT = Path(__file__).parent / 'pipeline_templates'
TEMPLATE = json.loads((ROOT / 'hospital_intro.json').read_text())
RULES = json.loads((ROOT / 'hospital_rules.json').read_text())


class RulesTest(unittest.TestCase):
    def check_record(self, evidence, **overrides):
        record = {'source': '甲医院', 'target': '乙学院', 'type': '合作', 'status': '已运营',
                  'evidence': evidence, 'quantity_text': None, 'year_text': None, **overrides}
        return apply_rules(record, evidence, {'甲医院', '乙学院'}, TEMPLATE, RULES)

    def test_cooperation_does_not_imply_operation(self):
        result, audit = self.check_record('甲医院与乙学院合作提供培训')
        self.assertEqual(result['status'], '文档陈述')
        self.assertEqual(audit[0]['rule'], 'statement_is_not_operational_status')

    def test_unsupported_operation_is_quarantined(self):
        result, audit = self.check_record('甲医院包含乙学院', type='包含机构')
        self.assertIsNone(result)
        self.assertEqual(audit[-1]['rule'], 'operational_evidence_required')

    def test_explicit_operation_is_retained(self):
        result, _ = self.check_record('乙学院已投入运营', type='包含机构')
        self.assertEqual(result['status'], '已运营')

    def test_fabricated_year_is_quarantined(self):
        result, audit = self.check_record('计划于2028年建设乙学院', type='规划建设', year_text='2030年')
        self.assertIsNone(result)
        self.assertEqual(audit[-1]['rule'], 'year_text_unsupported')

    def test_planned_quantity_is_preserved(self):
        result, _ = self.check_record('计划布局30+家乙学院', type='计划建设', quantity_text='30+家')
        self.assertEqual((result['type'], result['status'], result['quantity_text']), ('规划建设', '规划', '30+家'))

    def test_generic_evidence_cannot_support_named_target(self):
        result, audit = self.check_record('重点发展5大领域', type='重点发展')
        self.assertIsNone(result)
        self.assertEqual(audit[-1]['rule'], 'target_missing_from_evidence')

    def test_reverse_containment_is_quarantined(self):
        record = {'source': '迪拜分院', 'target': '国际医院', 'type': '包含机构',
                  'evidence': '国际医院的迪拜分院已投入运营', 'status': '已运营'}
        result, audit = apply_rules(record, record['evidence'], {'迪拜分院', '国际医院'}, TEMPLATE, RULES,
                                    {'迪拜分院': '机构', '国际医院': '设施类型'})
        self.assertIsNone(result)
        self.assertEqual(audit[-1]['rule'], 'reversed_facility_containment')


if __name__ == '__main__':
    unittest.main()
