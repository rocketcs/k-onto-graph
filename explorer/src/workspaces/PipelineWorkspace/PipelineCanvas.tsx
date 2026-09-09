import { displayText } from "../../i18n";
import { t as tr } from "../../i18n";
import { flowAriaLabels } from "../../flowLocale";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  Panel,
  MarkerType,
  applyNodeChanges,
  type NodeChange,
  type ReactFlowInstance,
  type Node,
  type Edge,
  type NodeProps,
  type Connection,
} from "@xyflow/react";
import {
  FileScan,
  Scissors,
  Sparkles,
  GitMerge,
  ShieldCheck,
  Database,
  ChartNoAxesCombined,
  LayoutGrid,
  CircleCheck,
  CircleAlert,
  LoaderCircle,
  Clock3,
  Ban,
  Pause,
} from "lucide-react";
import "@xyflow/react/dist/style.css";
import { labels, statuses, type Config, type Step } from "./api";

type Data = {
  name: string;
  status: string;
  duration?: number;
  error?: string;
  index: number;
  metric?: string;
};
type FlowNode = Node<Data, "step">;
const icons = {
  parse: FileScan,
  split: Scissors,
  extract: Sparkles,
  normalize: GitMerge,
  validate: ShieldCheck,
  store: Database,
  statistics: ChartNoAxesCombined,
};
function StepNode({ id, data, selected }: NodeProps<FlowNode>) {
  const Icon = icons[id as keyof typeof icons] || Database;
  const StatusIcon =
    data.status === "failed"
      ? CircleAlert
      : ["completed", "reused"].includes(data.status)
        ? CircleCheck
        : ["running", "retrying"].includes(data.status)
          ? LoaderCircle
          : data.status === "blocked"
            ? Ban
            : ["cancelled", "interrupted"].includes(data.status)
              ? Pause
          : Clock3;
  return (
    <div
      className={`pl-node ${selected ? "selected" : ""}`}
      data-status={data.status}
      aria-label={`${data.name}: ${statuses[data.status] || data.status}`}
    >
      <Handle
        type="target"
        position={Position.Left}
        isConnectable={id !== "parse"}
      />
      <div className="pl-node-top">
        <span className="pl-node-index">
          {String(data.index + 1).padStart(2, "0")}
        </span>
        <span className="pl-node-status">
          <StatusIcon size={12} />
          {displayText(String(statuses[data.status] || data.status))}
        </span>
      </div>
      <strong>
        <span className="pl-node-icon"><Icon size={19} /></span>
        {data.name}
      </strong>
      <div className="pl-node-footer">
        <span title={data.error}>
          {data.error ? tr("Processing error") : data.metric || statuses[data.status] || "—"}
        </span>
        <span>
          {data.duration === undefined ? "" : `${data.duration.toFixed(2)} s`}
        </span>
      </div>
      <div className="pl-node-activity" aria-hidden="true"><span /></div>
      <Handle
        type="source"
        position={Position.Right}
        isConnectable={id !== "store"}
      />
    </div>
  );
}
const nodeTypes = { step: memo(StepNode) };
const fitOptions = { padding: 0.08, maxZoom: 1 };
const initialViewport = { x: 40, y: 100, zoom: 1 };

export function PipelineCanvas({
  flow,
  steps,
  onSelect,
  onChange,
  editable,
  onError,
  selected,
}: {
  flow: Config;
  steps: Step[];
  onSelect: (id: string) => void;
  onChange: (flow: Config) => void;
  editable: boolean;
  onError: (error: string) => void;
  selected: string;
}) {
  const instance = useRef<ReactFlowInstance<FlowNode>>(null);
  const [small, setSmall] = useState(() => window.innerWidth < 760);
  useEffect(() => {
    const resize = () => setSmall(window.innerWidth < 760);
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);
  const definitionNodes = useMemo<FlowNode[]>(() => {
    const names = flow.steps as string[];
    return names.map((id, i) => {
      const step = steps.find((s) => s.id === id);
      return {
        id,
        type: "step",
        selected: selected === id,
        position: { x: i * 280, y: 0 },
        data: {
          name: labels[id],
          status: step?.status || "pending",
          duration: step?.duration,
          error: step?.error,
          index: i,
          metric: step?.metrics
            ? ["extract", "split"].includes(id)
              ? tr("{0} chunks", {0: step.metrics.chunks || 0})
              : ["normalize", "validate", "store", "statistics"].includes(id)
                ? tr("{0} entities · {1} relationships", {0: step.metrics.entities || 0, 1: step.metrics.relationships || 0})
                : ""
            : "",
        },
        deletable: editable && id === "statistics",
      };
    });
  }, [flow, steps, editable, selected]);
  const [nodeState, setNodeState] = useState({
    source: definitionNodes,
    nodes: definitionNodes,
  });
  // Reconcile metadata only when inputs change; drag updates retain library-owned state.
  if (nodeState.source !== definitionNodes) {
    const previous = new Map(nodeState.nodes.map((node) => [node.id, node]));
    setNodeState({
      source: definitionNodes,
      nodes: definitionNodes.map((node) => {
        const old = previous.get(node.id);
        return old
          ? {
              ...old,
              position: old.data.index === node.data.index ? old.position : node.position,
              data: node.data,
              selected: node.selected,
              deletable: node.deletable,
            }
          : node;
      }),
    });
  }
  const nodes = nodeState.nodes;
  const onNodesChange = useCallback((changes: NodeChange<FlowNode>[]) => {
    setNodeState((old) => ({
      ...old,
      nodes: applyNodeChanges(changes, old.nodes),
    }));
  }, []);
  const onInit = useCallback((value: ReactFlowInstance<FlowNode>) => {
    instance.current = value;
  }, []);
  const names = flow.steps as string[];
  const edges: Edge[] = useMemo(
    () =>
      names.slice(1).map((id, i) => {
        const source = steps.find((s) => s.id === names[i])?.status;
        const target = steps.find((s) => s.id === id)?.status;
        const active = ["completed", "reused"].includes(source || "") && ["running", "retrying"].includes(target || "");
        const complete = ["completed", "reused"].includes(target || "");
        const blocked = ["failed", "blocked", "cancelled", "interrupted"].includes(source || "") || ["blocked", "cancelled", "interrupted"].includes(target || "");
        return {
        id: `${names[i]}-${id}`,
        source: names[i],
        target: id,
        type: "smoothstep",
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 16,
          height: 16,
          color: active ? "#61d9e8" : complete ? "#4cc38a" : blocked ? "#536071" : "#52718e",
        },
        className: active ? "pl-edge-active" : complete ? "pl-edge-complete" : blocked ? "pl-edge-blocked" : "pl-edge-pending",
        animated: active,
      }; }),
    [names, steps],
  );

  function connect(connection: Connection) {
    if (!editable || !connection.source || !connection.target) return;
    const next = [
      ...edges.filter(
        (e) => e.source !== connection.source && e.target !== connection.target,
      ),
      {
        id: `${connection.source}-${connection.target}`,
        source: connection.source,
        target: connection.target,
      },
    ];
    const order = ["parse"];
    while (order.length <= nodes.length) {
      const edge = next.find((e) => e.source === order[order.length - 1]);
      if (!edge) break;
      if (order.includes(edge.target)) {
        onError(tr("Pipeline cannot contain cycles"));
        return;
      }
      order.push(edge.target);
    }
    if (order.length !== nodes.length || order[order.length - 1] !== "store") {
      onError(tr("Connections do not form a complete serial pipeline; changes were not saved"));
      return;
    }
    const required = order.filter((x) => x !== "statistics").join(",");
    if (required !== "parse,split,extract,normalize,validate,store") {
      onError(tr("Connection types are incompatible; required stages must retain their order"));
      return;
    }
    onChange({ ...flow, steps: order });
  }
  return (
    <ReactFlow<FlowNode>
      ariaLabelConfig={flowAriaLabels}
      key={small ? "mobile" : "desktop"}
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView={!small}
      fitViewOptions={fitOptions}
      onInit={onInit}
      defaultViewport={initialViewport}
      minZoom={0.25}
      maxZoom={1.8}
      nodesDraggable={editable}
      autoPanOnNodeDrag={false}
      nodesConnectable={editable}
      deleteKeyCode={null}
      onNodesChange={onNodesChange}
      onNodeDragStart={(_, node) => onSelect(node.id)}
      onNodeClick={(_, node) => {
        onSelect(node.id);
      }}
      onConnect={connect}
      onNodeDragStop={(_, node) =>
        onChange({
          ...flow,
          positions: {
            ...((flow.positions as Config) || {}),
            [node.id]: node.position,
          },
        })
      }
    >
      <Background gap={22} size={1} color="rgba(74,163,255,.2)" />
      <Controls showInteractive={false} />
      {steps.length > 0 && (
        <Panel position="top-left" className="pl-execution-summary">
          <div role="status">
            <span>{names.map((id) => steps.find((step) => step.id === id)).filter((step) => step && ["completed", "reused"].includes(step.status)).length} / {names.length}</span>
            <strong>{(() => {
              const current = steps.find((step) => ["failed", "running", "retrying", "interrupted", "cancelled"].includes(step.status));
              return current ? `${labels[current.id]} · ${statuses[current.status]}` : steps.every((step) => ["completed", "reused"].includes(step.status)) ? statuses.completed : statuses.pending;
            })()}</strong>
          </div>
          <div className="pl-execution-track" aria-hidden="true">
            {names.map((id) => <span key={id} data-status={steps.find((step) => step.id === id)?.status || "pending"} />)}
          </div>
        </Panel>
      )}
      <Panel position="top-right">
        <button
          title={tr("Auto-arrange layout")}
          aria-label={tr("Auto-arrange layout")}
          onClick={() => {
            setNodeState((old) => ({
              ...old,
              nodes: old.nodes.map((node, index) => ({
                ...node,
                position: { x: index * 280, y: 0 },
              })),
            }));
            if (editable) onChange({ ...flow, positions: {} });
            requestAnimationFrame(() =>
              requestAnimationFrame(() => {
                if (small) {
                  void instance.current?.setViewport(
                    initialViewport,
                    { duration: 250 },
                  );
                  return;
                }
                void instance.current?.fitView({
                  padding: 0.08,
                  maxZoom: 1,
                  duration: 250,
                });
              }),
            );
          }}
        >
          <LayoutGrid size={16} />
        </button>
      </Panel>
    </ReactFlow>
  );
}
