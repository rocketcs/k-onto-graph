"""Versioned workflow schemas and server-owned processor contracts."""
from __future__ import annotations
from copy import deepcopy

STEPS = ['parse', 'split', 'extract', 'normalize', 'validate', 'store']
LABELS = {'parse': '文档解析', 'split': '文本分块', 'extract': '知识抽取', 'normalize': '实体归一',
          'validate': '规则校验', 'store': '候选结果', 'statistics': '统计摘要'}
# Larger, row-aware chunks keep a doctor's full履历/简介 together while the
# splitter still refuses silent truncation for oversized paragraphs.
FLOW = {'steps': STEPS, 'positions': {}, 'chunk_size': 8000, 'overlap': 400}
EXTRACTION = {
    'entity_types': ['实体', '组织', '人员', '地点', '产品', '项目', '主题', '属性'],
    'relation_types': ['相关', '隶属', '位于', '参与', '负责', '提供', '属于', '关联'],
    'instructions': '抽取文档明确陈述的机构、五级设施布局、五大特色、合作和培训项目、地点、规划数量和年份。'
                    '使用原文中的实体名称，不改写并列短语。包含机构从整体指向下属机构。'
                    '规划和目标不等于已实现，合作不等于已运营。为每条事实提供原文段落编号。'
                    '数量和年份填quantity_text、year_text，无值用null。寿命目标也需要数量和单位。'
                    '按工作表、列名和行号保留表格语义；按用户提供的领域模板提取实体和关系。逐项保留原文事实，不要概括或合并。',
    'examples': [],
}
RULES = {
    'statement_relations': ['相关', '隶属', '位于', '参与', '负责', '提供', '属于', '关联'],
    'operational_markers': ['已投入运营', '正式运营', '已运营', '已开业'],
    'construction_markers': ['建设中', '启动建设'],
    'relation_aliases': {'合作开设': '合作', '合作提供培训': '合作', '计划建设': '规划建设', '计划布局': '规划建设'},
    'aliases': {}, 'forbidden_merges': [], 'require_target_in_evidence': True,
    'require_goal_quantity': True, 'review_isolated_entities': True,
    'required_mentions': [],
}
SEEDS = [('flow', '文档入库', FLOW), ('extraction', '医院介绍', EXTRACTION), ('rules', '医院事实校验', RULES)]


def validate_definition(kind, value):
    if not isinstance(value, dict):
        raise ValueError('Definition must be a JSON object')
    defaults = {'flow': FLOW, 'extraction': EXTRACTION, 'rules': RULES}
    if kind not in defaults or set(value) - set(defaults[kind]):
        raise ValueError('Unknown definition kind or unsupported configuration field')
    config = {**deepcopy(defaults[kind]), **deepcopy(value)}
    if kind == 'flow':
        steps = config['steps']
        if not isinstance(steps, list) or len(steps) != len(set(steps)):
            raise ValueError('Each processor may appear once')
        if [n for n in steps if n != 'statistics'] != STEPS:
            raise ValueError('Required typed processors must retain parse → split → extract → normalize → validate → store order')
        if set(steps) - set(LABELS):
            raise ValueError('Unregistered processor')
        if 'statistics' in steps and not steps.index('normalize') < steps.index('statistics') < steps.index('validate'):
            raise ValueError('Statistics accepts normalized candidates only')
        if type(config['chunk_size']) is not int or not 300 <= config['chunk_size'] <= 12000:
            raise ValueError('chunk_size must be 300-12000')
        if type(config['overlap']) is not int or not 0 <= config['overlap'] < config['chunk_size']:
            raise ValueError('Invalid overlap')
        if not isinstance(config['positions'], dict):
            raise ValueError('Invalid node positions')
        for node, position in config['positions'].items():
            import math
            if node not in LABELS or not isinstance(position, dict) or set(position) != {'x', 'y'}:
                raise ValueError('Invalid node position')
            if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 100000 for v in position.values()):
                raise ValueError('Invalid canvas coordinate')
    elif kind == 'extraction':
        for field in ('entity_types', 'relation_types'):
            if not isinstance(config[field], list) or not 1 <= len(config[field]) <= 80 or any(not isinstance(x, str) or not x.strip() for x in config[field]):
                raise ValueError('Types must be nonempty string arrays')
        if not isinstance(config['instructions'], str) or len(config['instructions']) > 24000:
            raise ValueError('Invalid extraction instructions')
        if not isinstance(config['examples'], list) or len(config['examples']) > 20:
            raise ValueError('At most 20 examples')
    else:
        for field in ('statement_relations', 'operational_markers', 'construction_markers', 'required_mentions'):
            if not isinstance(config[field], list) or any(not isinstance(x, str) or not x for x in config[field]):
                raise ValueError('Rule lists must contain nonempty strings')
        for field in ('relation_aliases', 'aliases'):
            if not isinstance(config[field], dict) or any(not isinstance(k, str) or not isinstance(v, str) or not k or not v for k, v in config[field].items()):
                raise ValueError('Alias maps must contain strings')
        for field in ('require_target_in_evidence', 'require_goal_quantity', 'review_isolated_entities'):
            if type(config[field]) is not bool:
                raise ValueError('Rule switches must be booleans')
        if not isinstance(config['forbidden_merges'], list) or any(not isinstance(p, list) or len(p) != 2 or any(not isinstance(x, str) for x in p) for p in config['forbidden_merges']):
            raise ValueError('forbidden_merges must be pairs of names')
    return config
