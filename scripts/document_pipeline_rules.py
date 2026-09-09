"""Deterministic validation for configurable document extraction experiments."""
import copy
import re


def apply_rules(record, text, valid_names, template, rules, entity_types=None):
    record = copy.deepcopy(record)
    audit = []

    def change(field, value, rule):
        if record.get(field) != value:
            audit.append({'rule': rule, 'field': field, 'before': record.get(field), 'after': value})
            record[field] = value

    def reject(reason):
        return None, audit + [{'rule': reason, 'action': 'review', 'record': record}]

    evidence = record.get('evidence')
    if not isinstance(evidence, str) or not evidence or evidence not in text:
        return reject('verbatim_evidence_required')
    if record.get('source') not in valid_names or record.get('target') not in valid_names:
        return reject('valid_endpoints_required')
    for endpoint in ('source', 'target'):
        if rules.get(f'require_{endpoint}_in_evidence') and record[endpoint] not in evidence:
            return reject(f'{endpoint}_missing_from_evidence')
    change('type', rules['relation_aliases'].get(record.get('type'), record.get('type')), 'canonical_relation')
    if record.get('type') not in template['relation_types']:
        return reject('relation_type_not_allowed')
    if (rules.get('reject_reverse_facility_containment') and record['type'] == '包含机构'
        and entity_types and entity_types.get(record['source']) == '机构'
        and entity_types.get(record['target']) == '设施类型'):
        return reject('reversed_facility_containment')
    if record.get('status') not in rules['statuses']:
        return reject('status_not_allowed')
    if record['type'] in rules['statement_relations']:
        change('status', '文档陈述', 'statement_is_not_operational_status')
    elif record['type'] == '发展目标':
        change('status', '目标', 'goal_is_not_achievement')
    elif record['type'] == '规划建设':
        if not any(marker in evidence for marker in rules['planning_markers']):
            return reject('planning_evidence_required')
        change('status', '规划', 'planned_capacity_is_not_existing_capacity')
    elif record['status'] == '已运营' and not any(marker in evidence for marker in rules['operational_markers']):
        return reject('operational_evidence_required')
    elif record['status'] == '建设中' and not any(marker in evidence for marker in rules['construction_markers']):
        return reject('construction_evidence_required')
    for field, pattern in [('quantity_text', r'\d+(?:\.\d+)?(?:[-~]\d+)?(?:万)?\+?(?:家|岁|公里|平方米)'),
                           ('year_text', r'(?:19|20)\d{2}年')]:
        value = record.get(field)
        if value is not None and (not isinstance(value, str) or value not in evidence or not re.fullmatch(pattern, value)):
            return reject(f'{field}_unsupported')
    return record, audit
