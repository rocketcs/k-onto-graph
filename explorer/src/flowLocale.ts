import { locale, t } from "./i18n";

export const flowAriaLabels = {
  'controls.zoomIn.ariaLabel': t("Zoom in"),
  'controls.zoomOut.ariaLabel': t("Zoom out"),
  'controls.fitView.ariaLabel': t("Fit view"),
  'controls.interactive.ariaLabel': locale === 'zh-CN' ? '切换交互' : 'Toggle interactivity',
  'controls.ariaLabel': locale === 'zh-CN' ? '图形控件' : 'Graph controls',
  'handle.ariaLabel': locale === 'zh-CN' ? '连接点' : 'Connection handle',
  'node.a11yDescription.keyboardDisabled': locale === 'zh-CN' ? '按 Enter 或空格选择节点，按 Escape 取消选择。' : 'Press Enter or Space to select a node, or Escape to cancel selection.',
  'node.a11yDescription.ariaLiveMessage': ({ x, y }: { direction: string; x: number; y: number }) => locale === 'zh-CN' ? `节点位置：${x}, ${y}` : `Node position: ${x}, ${y}`,
  'minimap.ariaLabel': locale === 'zh-CN' ? '缩略图' : 'Minimap',
  'node.a11yDescription.default': locale === 'zh-CN' ? '选择节点，按方向键移动，按 Delete 删除，按 Escape 取消选择。' : 'Select a node. Use arrow keys to move, Delete to remove, and Escape to cancel selection.',
  'edge.a11yDescription.default': locale === 'zh-CN' ? '选择关系，按 Delete 删除或按 Escape 取消选择。' : 'Select an edge. Press Delete to remove or Escape to cancel selection.',
};
