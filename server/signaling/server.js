const fs = require("fs");
const http = require("http");
const path = require("path");
const WebSocket = require("ws");

const PORT = Number(process.env.SIGNAL_PORT || 8080);
const VIEWER_DIR = "/viewer";
const SHARED_DIR = "/shared";
const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8",
};

const rooms = new Map();

function getRoom(roomId) {
  if (!rooms.has(roomId)) {
    rooms.set(roomId, { viewer: null, target: null });
  }
  return rooms.get(roomId);
}

function cleanRoom(roomId) {
  const room = rooms.get(roomId);
  if (!room) {
    return;
  }
  if (!room.viewer && !room.target) {
    rooms.delete(roomId);
  }
}

function send(ws, message) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
  }
}

function getPeer(room, role) {
  return role === "viewer" ? room.target : room.viewer;
}

function serveFile(res, filename) {
  const ext = path.extname(filename);
  const mime = MIME_TYPES[ext] || "text/plain; charset=utf-8";
  fs.readFile(filename, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }
    res.writeHead(200, { "Content-Type": mime });
    res.end(data);
  });
}

const server = http.createServer((req, res) => {
  const pathname = new URL(req.url, "http://127.0.0.1").pathname;

  if (pathname === "/" || pathname === "/index.html") {
    serveFile(res, path.join(VIEWER_DIR, "index.html"));
    return;
  }

  if (pathname === "/viewer.js") {
    serveFile(res, path.join(VIEWER_DIR, "viewer.js"));
    return;
  }

  if (pathname === "/protocol.json") {
    serveFile(res, path.join(SHARED_DIR, "protocol.json"));
    return;
  }

  if (pathname === "/healthz") {
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  res.writeHead(404);
  res.end("Not found");
});

const wss = new WebSocket.Server({ server, path: "/ws" });

wss.on("connection", (ws) => {
  ws.on("message", (raw) => {
    let message;
    try {
      message = JSON.parse(String(raw));
    } catch (error) {
      send(ws, { type: "error", message: "invalid json" });
      return;
    }

    if (message.type === "join") {
      const roomId = String(message.room || "").trim();
      const role = message.role === "viewer" ? "viewer" : "target";
      if (!roomId) {
        send(ws, { type: "error", message: "room is required" });
        return;
      }

      const room = getRoom(roomId);
      if (room[role] && room[role] !== ws) {
        send(ws, { type: "error", message: `${role} already connected` });
        return;
      }

      ws.roomId = roomId;
      ws.role = role;
      room[role] = ws;

      const peerPresent = Boolean(getPeer(room, role));
      send(ws, { type: "joined", room: roomId, role, peerPresent });
      if (peerPresent) {
        send(getPeer(room, role), { type: "peer-ready", room: roomId, role });
      }
      return;
    }

    if (!ws.roomId || !ws.role) {
      send(ws, { type: "error", message: "join first" });
      return;
    }

    const room = getRoom(ws.roomId);
    const peer = getPeer(room, ws.role);
    if (!peer) {
      send(ws, { type: "error", message: "peer not connected yet" });
      return;
    }

    if (["offer", "answer", "ice-candidate"].includes(message.type)) {
      send(peer, { ...message, room: ws.roomId });
      return;
    }

    send(ws, { type: "error", message: `unsupported message type: ${message.type}` });
  });

  ws.on("close", () => {
    if (!ws.roomId || !ws.role) {
      return;
    }
    const room = getRoom(ws.roomId);
    if (room[ws.role] === ws) {
      room[ws.role] = null;
    }
    send(getPeer(room, ws.role), { type: "peer-left", room: ws.roomId, role: ws.role });
    cleanRoom(ws.roomId);
  });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`signaling server listening on :${PORT}`);
});
