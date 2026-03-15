const state = {
  nodes: [],
  edges: [],
  simNodes: [],
  simEdges: [],
  width: 0,
  height: 0,
  raf: null,
  refreshTimer: null,
};

const canvas = document.getElementById("graphCanvas");
const ctx = canvas.getContext("2d");
const graphEmpty = document.getElementById("graphEmpty");

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = rect.width * ratio;
  canvas.height = rect.height * ratio;
  state.width = rect.width;
  state.height = rect.height;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function formatTime(iso) {
  if (!iso) return "暂无";
  const time = new Date(iso);
  return time.toLocaleString("zh-CN", { hour12: false });
}

function updateSummary(payload) {
  setText("generatedAt", `最后更新 ${formatTime(payload.generated_at)}`);
  setText(
    "windowLabel",
    `蓝牙窗口 ${payload.windows.presence_seconds}s / 消息窗口 ${payload.windows.message_minutes}min`
  );
  setText("broadcastingDevices", payload.stats.broadcasting_devices);
  setText("bluetoothActiveDevices", payload.stats.bluetooth_active_devices);
  setText("visibleDevices", payload.stats.visible_devices);
  setText("bluetoothEdges", payload.stats.bluetooth_edges);
  setText("friendshipEdges", payload.stats.friendship_edges);
  setText("activeTempSessions", payload.stats.active_temp_sessions);
}

function updateHighlights(items) {
  const wrap = document.getElementById("highlights");
  const tpl = document.getElementById("highlightTemplate");
  wrap.innerHTML = "";

  items.forEach((item) => {
    const fragment = tpl.content.cloneNode(true);
    fragment.querySelector(".highlight-name").textContent = item.label;
    fragment.querySelector(".highlight-meta").textContent =
      `连接度 ${item.degree} / 好友 ${item.friend_degree}`;
    fragment.querySelector(".highlight-badge").textContent = item.is_broadcasting
      ? "广播中"
      : "静默";
    wrap.appendChild(fragment);
  });
}

function rebuildSimulation(nodes, edges) {
  state.nodes = nodes;
  state.edges = edges;
  const radius = Math.min(state.width, state.height) * 0.34;
  const centerX = state.width / 2;
  const centerY = state.height / 2;

  state.simNodes = nodes.map((node, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(nodes.length, 1);
    return {
      ...node,
      x: centerX + Math.cos(angle) * radius * (0.55 + (index % 5) * 0.08),
      y: centerY + Math.sin(angle) * radius * (0.55 + (index % 5) * 0.08),
      vx: 0,
      vy: 0,
      mass: 1 + Math.min(node.degree, 8) * 0.06,
      radius: node.is_broadcasting ? 8 : 6,
    };
  });

  const nodeMap = new Map(state.simNodes.map((node) => [node.id, node]));
  state.simEdges = edges
    .map((edge) => ({
      ...edge,
      sourceNode: nodeMap.get(edge.source),
      targetNode: nodeMap.get(edge.target),
    }))
    .filter((edge) => edge.sourceNode && edge.targetNode);

  graphEmpty.style.display = state.simNodes.length ? "none" : "grid";
}

function stepSimulation() {
  const centerX = state.width / 2;
  const centerY = state.height / 2;

  for (const node of state.simNodes) {
    node.vx += (centerX - node.x) * 0.0009;
    node.vy += (centerY - node.y) * 0.0009;
  }

  for (let i = 0; i < state.simNodes.length; i += 1) {
    const a = state.simNodes[i];
    for (let j = i + 1; j < state.simNodes.length; j += 1) {
      const b = state.simNodes[j];
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      let distSq = dx * dx + dy * dy;
      if (distSq < 0.01) distSq = 0.01;
      const force = 1800 / distSq;
      const dist = Math.sqrt(distSq);
      dx /= dist;
      dy /= dist;
      a.vx -= dx * force / a.mass;
      a.vy -= dy * force / a.mass;
      b.vx += dx * force / b.mass;
      b.vy += dy * force / b.mass;
    }
  }

  for (const edge of state.simEdges) {
    const a = edge.sourceNode;
    const b = edge.targetNode;
    let dx = b.x - a.x;
    let dy = b.y - a.y;
    const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 0.001);
    const target = edge.kind === "friendship" ? 118 : 92;
    const spring = (dist - target) * 0.0034;
    dx /= dist;
    dy /= dist;
    a.vx += dx * spring;
    a.vy += dy * spring;
    b.vx -= dx * spring;
    b.vy -= dy * spring;
  }

  for (const node of state.simNodes) {
    node.vx *= 0.9;
    node.vy *= 0.9;
    node.x += node.vx;
    node.y += node.vy;
    node.x = Math.max(28, Math.min(state.width - 28, node.x));
    node.y = Math.max(28, Math.min(state.height - 28, node.y));
  }
}

function drawGraph() {
  ctx.clearRect(0, 0, state.width, state.height);

  for (const edge of state.simEdges) {
    const { sourceNode, targetNode } = edge;
    ctx.beginPath();
    ctx.moveTo(sourceNode.x, sourceNode.y);
    ctx.lineTo(targetNode.x, targetNode.y);
    ctx.strokeStyle =
      edge.kind === "friendship" ? "rgba(255,255,255,0.56)" : "rgba(99,255,155,0.55)";
    ctx.lineWidth = edge.kind === "friendship" ? 1.4 : 1.8;
    ctx.stroke();
  }

  for (const node of state.simNodes) {
    ctx.beginPath();
    ctx.arc(node.x, node.y, node.radius + 8, 0, Math.PI * 2);
    ctx.fillStyle = node.is_broadcasting ? "rgba(99,255,155,0.12)" : "rgba(255,255,255,0.06)";
    ctx.fill();

    ctx.beginPath();
    ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
    ctx.fillStyle = node.is_broadcasting ? "#63ff9b" : "rgba(255,255,255,0.82)";
    ctx.fill();

    ctx.fillStyle = "#f5fff7";
    ctx.font = "12px 'Segoe UI', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(node.label, node.x, node.y - 14);
  }
}

function animate() {
  stepSimulation();
  drawGraph();
  state.raf = requestAnimationFrame(animate);
}

async function refresh() {
  try {
    const response = await fetch("/api/live", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    updateSummary(payload);
    updateHighlights(payload.highlights || []);
    rebuildSimulation(payload.nodes || [], payload.edges || []);
    if (!state.refreshTimer) {
      state.refreshTimer = setInterval(refresh, (payload.refresh_seconds || 5) * 1000);
    }
  } catch (error) {
    setText("generatedAt", `数据读取失败: ${error.message}`);
  }
}

async function boot() {
  resizeCanvas();
  await refresh();
  if (!state.raf) {
    animate();
  }
}

window.addEventListener("resize", () => {
  resizeCanvas();
  rebuildSimulation(state.nodes, state.edges);
});

window.addEventListener("load", boot);
