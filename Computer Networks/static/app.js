// Network Performance Monitor Frontend Logic

let ws;
let isTrafficActive = false;

// Chart instances
let bandwidthChart, latencyChart, packetChart, socketChart;

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function initCharts() {
  const commonLineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: {
      x: {
        grid: { color: "rgba(255, 255, 255, 0.05)" },
        ticks: { color: "#8a99ad", maxTicksLimit: 8 },
      },
      y: {
        beginAtZero: true,
        grid: { color: "rgba(255, 255, 255, 0.05)" },
        ticks: { color: "#8a99ad" },
      },
    },
    plugins: {
      legend: {
        labels: { color: "#f0f4f8", boxWidth: 12 },
      },
    },
  };

  // 1. Bandwidth Chart
  const ctxBw = document.getElementById("bandwidthChart").getContext("2d");
  bandwidthChart = new Chart(ctxBw, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Download (Mbps)",
          borderColor: "#00e676",
          backgroundColor: "rgba(0, 230, 118, 0.1)",
          data: [],
          borderWidth: 2,
          pointRadius: 0,
          fill: true,
          tension: 0.3,
        },
        {
          label: "Upload (Mbps)",
          borderColor: "#00e5ff",
          backgroundColor: "rgba(0, 229, 255, 0.1)",
          data: [],
          borderWidth: 2,
          pointRadius: 0,
          fill: true,
          tension: 0.3,
        },
      ],
    },
    options: commonLineOptions,
  });

  // 2. Latency Chart
  const ctxLat = document.getElementById("latencyChart").getContext("2d");
  latencyChart = new Chart(ctxLat, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Google DNS (8.8.8.8)",
          borderColor: "#ffd600",
          backgroundColor: "transparent",
          data: [],
          borderWidth: 2,
          pointRadius: 1,
          tension: 0.2,
        },
        {
          label: "Cloudflare (1.1.1.1)",
          borderColor: "#b388ff",
          backgroundColor: "transparent",
          data: [],
          borderWidth: 2,
          pointRadius: 1,
          tension: 0.2,
        },
      ],
    },
    options: commonLineOptions,
  });

  // 3. Packet Rate Chart
  const ctxPkt = document.getElementById("packetChart").getContext("2d");
  packetChart = new Chart(ctxPkt, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "RX Pkts/sec",
          borderColor: "#00e676",
          backgroundColor: "transparent",
          data: [],
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.2,
        },
        {
          label: "TX Pkts/sec",
          borderColor: "#00e5ff",
          backgroundColor: "transparent",
          data: [],
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.2,
        },
      ],
    },
    options: commonLineOptions,
  });

  // 4. Socket State Doughnut Chart
  const ctxSock = document.getElementById("socketChart").getContext("2d");
  socketChart = new Chart(ctxSock, {
    type: "doughnut",
    data: {
      labels: ["ESTABLISHED", "LISTEN", "TIME_WAIT", "CLOSE_WAIT", "OTHER"],
      datasets: [
        {
          data: [0, 0, 0, 0, 0],
          backgroundColor: ["#00e676", "#ffd600", "#00e5ff", "#ff5252", "#b388ff"],
          borderColor: "#0b0f19",
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: { color: "#f0f4f8", boxWidth: 12 },
        },
      },
    },
  });
}

function updateKPIs(data) {
  const bw = data.bandwidth;
  const totals = data.totals;
  const lats = data.latencies_ms;
  const socks = data.sockets;

  // Bandwidth
  document.getElementById("kpiDlSpeed").innerHTML = `${bw.download_mbps.toFixed(2)} <small>Mbps</small>`;
  document.getElementById("kpiUlSpeed").innerHTML = `${bw.upload_mbps.toFixed(2)} <small>Mbps</small>`;
  document.getElementById("kpiDlTotal").textContent = `Total: ${formatBytes(totals.bytes_recv)}`;
  document.getElementById("kpiUlTotal").textContent = `Total: ${formatBytes(totals.bytes_sent)}`;

  // Latency
  const gLat = lats["8.8.8.8"] ?? -1;
  const cLat = lats["1.1.1.1"] ?? -1;
  document.getElementById("kpiLatGoogle").innerHTML =
    gLat >= 0 ? `${gLat.toFixed(1)} <small>ms</small>` : `-- <small>ms</small>`;
  document.getElementById("kpiLatCloudflare").textContent =
    cLat >= 0 ? `Cloudflare: ${cLat.toFixed(1)} ms` : "Cloudflare: -- ms";

  // Sockets
  document.getElementById("kpiTotalSockets").textContent = socks.total || 0;
  const estab = socks.by_status?.ESTABLISHED || 0;
  document.getElementById("kpiEstablishedSockets").textContent = `Established: ${estab}`;

  // System
  if (data.system) {
    document.getElementById("cpuVal").textContent = `${data.system.cpu_percent.toFixed(1)}%`;
    document.getElementById("ramVal").textContent = `${data.system.memory_percent.toFixed(1)}%`;
  }
}

function updateInterfacesTable(interfaces) {
  const tbody = document.getElementById("interfacesTbody");
  document.getElementById("nicCount").textContent = `${interfaces.length} Adapters`;

  let html = "";
  for (const nic of interfaces) {
    if (!nic.is_up && nic.ipv4 === "-") continue; // Skip inactive virtual adapters
    const statusClass = nic.is_up ? "nic-up" : "nic-down";
    const statusText = nic.is_up ? "UP" : "DOWN";
    const speed = nic.speed_mbps > 0 ? `${nic.speed_mbps} Mbps` : "Auto";
    const drops = nic.errin + nic.errout + nic.dropin + nic.dropout;

    html += `
      <tr>
        <td><strong>${nic.name}</strong></td>
        <td><span class="nic-pill ${statusClass}">${statusText}</span></td>
        <td><code>${nic.ipv4}</code></td>
        <td><code>${nic.mac || "-"}</code></td>
        <td>${speed}</td>
        <td>${formatBytes(nic.bytes_recv)}</td>
        <td>${formatBytes(nic.bytes_sent)}</td>
        <td>${drops}</td>
      </tr>
    `;
  }

  tbody.innerHTML = html || '<tr><td colspan="8" class="text-center">No active interfaces found</td></tr>';
}

function updateSocketChart(byStatus) {
  const labels = ["ESTABLISHED", "LISTEN", "TIME_WAIT", "CLOSE_WAIT"];
  let otherCount = 0;
  const counts = labels.map((l) => byStatus[l] || 0);

  for (const [st, val] of Object.entries(byStatus)) {
    if (!labels.includes(st)) {
      otherCount += val;
    }
  }
  counts.push(otherCount);

  socketChart.data.datasets[0].data = counts;
  socketChart.update();
}

function pushChartPoint(ts, data) {
  const maxPoints = 40;

  // Bandwidth
  bandwidthChart.data.labels.push(ts);
  bandwidthChart.data.datasets[0].data.push(data.bandwidth.download_mbps);
  bandwidthChart.data.datasets[1].data.push(data.bandwidth.upload_mbps);
  if (bandwidthChart.data.labels.length > maxPoints) {
    bandwidthChart.data.labels.shift();
    bandwidthChart.data.datasets[0].data.shift();
    bandwidthChart.data.datasets[1].data.shift();
  }
  bandwidthChart.update();

  // Latency
  latencyChart.data.labels.push(ts);
  latencyChart.data.datasets[0].data.push(data.latencies_ms["8.8.8.8"] || 0);
  latencyChart.data.datasets[1].data.push(data.latencies_ms["1.1.1.1"] || 0);
  if (latencyChart.data.labels.length > maxPoints) {
    latencyChart.data.labels.shift();
    latencyChart.data.datasets[0].data.shift();
    latencyChart.data.datasets[1].data.shift();
  }
  latencyChart.update();

  // Packets
  packetChart.data.labels.push(ts);
  packetChart.data.datasets[0].data.push(data.packets.recv_rate);
  packetChart.data.datasets[1].data.push(data.packets.sent_rate);
  if (packetChart.data.labels.length > maxPoints) {
    packetChart.data.labels.shift();
    packetChart.data.datasets[0].data.shift();
    packetChart.data.datasets[1].data.shift();
  }
  packetChart.update();
}

function loadHistory(history) {
  const tsList = history.timestamps || [];
  const count = tsList.length;
  if (count === 0) return;

  const dlMbps = history.download_kbps.map((k) => k / 1000.0);
  const ulMbps = history.upload_kbps.map((k) => k / 1000.0);

  bandwidthChart.data.labels = [...tsList];
  bandwidthChart.data.datasets[0].data = [...dlMbps];
  bandwidthChart.data.datasets[1].data = [...ulMbps];
  bandwidthChart.update();

  latencyChart.data.labels = [...tsList];
  latencyChart.data.datasets[0].data = [...(history.latencies["8.8.8.8"] || [])];
  latencyChart.data.datasets[1].data = [...(history.latencies["1.1.1.1"] || [])];
  latencyChart.update();

  packetChart.data.labels = [...tsList];
  packetChart.data.datasets[0].data = [...(history.packets_recv || [])];
  packetChart.data.datasets[1].data = [...(history.packets_sent || [])];
  packetChart.update();
}

function setTrafficButtonState(active) {
  isTrafficActive = active;
  const btn = document.getElementById("trafficBtn");
  const text = document.getElementById("trafficBtnText");
  if (active) {
    btn.classList.add("active");
    text.textContent = "Stop Load Test";
  } else {
    btn.classList.remove("active");
    text.textContent = "Simulate Traffic";
  }
}

async function toggleTraffic() {
  const endpoint = isTrafficActive ? "/api/traffic/stop" : "/api/traffic/start";
  try {
    const res = await fetch(endpoint, { method: "POST" });
    const data = await res.json();
    setTrafficButtonState(data.active);
  } catch (err) {
    console.error("Traffic toggle error:", err);
  }
}

function connectWebSocket() {
  const statusEl = document.getElementById("connStatus");
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    statusEl.textContent = "LIVE STREAM";
    statusEl.style.color = "#00e676";
    statusEl.style.borderColor = "rgba(0, 230, 118, 0.4)";
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "init") {
        if (msg.history) loadHistory(msg.history);
        setTrafficButtonState(msg.traffic_active);
      } else if (msg.type === "tick") {
        const d = msg.data;
        updateKPIs(d);
        pushChartPoint(d.timestamp, d);
        updateInterfacesTable(d.interfaces);
        if (d.sockets && d.sockets.by_status) {
          updateSocketChart(d.sockets.by_status);
        }
        setTrafficButtonState(msg.traffic_active);
      }
    } catch (err) {
      console.error("Error processing websocket frame:", err);
    }
  };

  ws.onclose = () => {
    statusEl.textContent = "DISCONNECTED";
    statusEl.style.color = "#ff5252";
    statusEl.style.borderColor = "rgba(255, 82, 82, 0.4)";
    setTimeout(connectWebSocket, 2000);
  };

  ws.onerror = () => {
    ws.close();
  };
}

window.addEventListener("DOMContentLoaded", () => {
  initCharts();
  connectWebSocket();
});

