import { displayText, errorText, t, type MessageKey } from '../../i18n';

const patterns: [RegExp, MessageKey][] = [
  [/^(.*) is missing a comment or definition\.$/, '{0} is missing a comment or definition.'],
  [/^(\d+)\/(\d+) labeled, (\d+)\/(\d+) documented, (\d+)\/(\d+) defined\.$/, '{0}/{1} labeled, {2}/{3} documented, {4}/{5} defined.'],
  [/^(\d+) properties are missing explicit ranges\.$/, '{0} properties are missing explicit ranges.'],
  [/^(\d+)\/(\d+) classes or properties have an alignment\.$/, '{0}/{1} classes or properties have an alignment.'],
];

export function healthText(message: string): string {
  for (const [pattern, key] of patterns) {
    const match = message.match(pattern);
    if (match) return t(key, Object.fromEntries(match.slice(1).map((value, index) => [index, value])));
  }
  if (message.startsWith('Graph has ') && message.includes('SHACL')) {
    return t('SHACL violations: {0}; warnings: {1}.', {
      0: message.match(/(\d+) SHACL violation/)?.[1] ?? '0',
      1: message.match(/(\d+) SHACL warning/)?.[1] ?? '0',
    });
  }
  if (message.startsWith('Live SHACL validation failed:')) return errorText(message);
  return displayText(message);
}
