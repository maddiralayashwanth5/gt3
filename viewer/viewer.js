const roomInput = document.getElementById("room");
const connectButton = document.getElementById("connect");
const muteButton = document.getElementById("mute-mic");
const statusEl = document.getElementById("status");
const remoteVideo = document.getElementById("remoteVideo");

const queryRoom = new URLSearchParams(window.location.search).get("room");
if (queryRoom) {
  roomInput.value = queryRoom;
}

const remoteMedia = new MediaStream();
remoteVideo.srcObject = remoteMedia;

let ws;
let pc;
let inputChannel;
let localMicStream;
let micEnabled = true;
let connectedRoom = "";
let makingOffer = false;

function setStatus(text) {
  statusEl.textContent = text;
}

function signal(message) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
  }
}

function buildIceServers() {
  const host = window.location.hostname;
  return [
    { urls: [`stun:${host}:3478`] },
    { urls: [`turn:${host}:3478?transport=udp`], username: "demo", credential: "demopass" },
    { urls: [`turns:${host}:5349?transport=tcp`], username: "demo", credential: "demopass" },
  ];
}

async function ensureMicrophone() {
  if (!localMicStream) {
    localMicStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: false,
      },
      video: false,
    });
  }
  return localMicStream;
}

function installPeerHandlers() {
  pc.onicecandidate = ({ candidate }) => {
    if (candidate) {
      signal({ type: "ice-candidate", candidate: candidate.toJSON() });
    }
  };

  pc.onconnectionstatechange = () => {
    setStatus(`Peer ${pc.connectionState}`);
  };

  pc.ontrack = ({ track }) => {
    remoteMedia.addTrack(track);
    if (track.kind === "video") {
      setStatus("Receiving screen");
    }
  };

  pc.ondatachannel = ({ channel }) => {
    if (channel.label === "input") {
      inputChannel = channel;
      attachDataChannelHandlers();
    }
  };
}

function attachDataChannelHandlers() {
  if (!inputChannel) {
    return;
  }
  inputChannel.onopen = () => setStatus("Control channel ready");
  inputChannel.onclose = () => setStatus("Control channel closed");
}

async function createPeer() {
  if (pc) {
    return pc;
  }

  pc = new RTCPeerConnection({ iceServers: buildIceServers() });
  installPeerHandlers();

  const mic = await ensureMicrophone();
  for (const track of mic.getAudioTracks()) {
    pc.addTrack(track, mic);
  }

  inputChannel = pc.createDataChannel("input", { ordered: true });
  attachDataChannelHandlers();

  return pc;
}

async function startOffer() {
  if (makingOffer) {
    return;
  }
  makingOffer = true;
  try {
    const peer = await createPeer();
    const offer = await peer.createOffer();
    await peer.setLocalDescription(offer);
    signal({ type: "offer", sdp: peer.localDescription.sdp });
    setStatus("Offer sent");
  } finally {
    makingOffer = false;
  }
}

function getRemotePoint(event) {
  const width = remoteVideo.videoWidth;
  const height = remoteVideo.videoHeight;
  if (!width || !height) {
    return null;
  }

  const rect = remoteVideo.getBoundingClientRect();
  const videoAspect = width / height;
  const rectAspect = rect.width / rect.height;
  let drawWidth = rect.width;
  let drawHeight = rect.height;
  let offsetX = 0;
  let offsetY = 0;

  if (rectAspect > videoAspect) {
    drawWidth = rect.height * videoAspect;
    offsetX = (rect.width - drawWidth) / 2;
  } else {
    drawHeight = rect.width / videoAspect;
    offsetY = (rect.height - drawHeight) / 2;
  }

  const localX = Math.min(Math.max(event.clientX - rect.left - offsetX, 0), drawWidth);
  const localY = Math.min(Math.max(event.clientY - rect.top - offsetY, 0), drawHeight);

  return {
    x: Math.round((localX / drawWidth) * width),
    y: Math.round((localY / drawHeight) * height),
  };
}

function sendInput(payload) {
  if (!inputChannel || inputChannel.readyState !== "open") {
    return;
  }
  inputChannel.send(JSON.stringify(payload));
}

remoteVideo.addEventListener("mousemove", (event) => {
  const point = getRemotePoint(event);
  if (point) {
    sendInput({ type: "mouse", action: "move", ...point });
  }
});

remoteVideo.addEventListener("mousedown", (event) => {
  remoteVideo.focus();
  const point = getRemotePoint(event);
  if (point) {
    sendInput({
      type: "mouse",
      action: "down",
      button: event.button === 2 ? "right" : "left",
      ...point,
    });
  }
  event.preventDefault();
});

remoteVideo.addEventListener("mouseup", (event) => {
  const point = getRemotePoint(event);
  if (point) {
    sendInput({
      type: "mouse",
      action: "up",
      button: event.button === 2 ? "right" : "left",
      ...point,
    });
  }
  event.preventDefault();
});

remoteVideo.addEventListener("wheel", (event) => {
  const point = getRemotePoint(event);
  if (point) {
    sendInput({ type: "mouse", action: "wheel", deltaY: Math.sign(event.deltaY), ...point });
  }
  event.preventDefault();
});

remoteVideo.addEventListener("contextmenu", (event) => event.preventDefault());

window.addEventListener("keydown", (event) => {
  if (document.activeElement !== remoteVideo) {
    return;
  }
  sendInput({ type: "key", action: "down", key: event.key });
  event.preventDefault();
});

window.addEventListener("keyup", (event) => {
  if (document.activeElement !== remoteVideo) {
    return;
  }
  sendInput({ type: "key", action: "up", key: event.key });
  event.preventDefault();
});

function resetPeer() {
  remoteMedia.getTracks().forEach((track) => remoteMedia.removeTrack(track));
  if (pc) {
    pc.ontrack = null;
    pc.onicecandidate = null;
    pc.close();
    pc = null;
  }
  inputChannel = null;
}

async function handleSignal(message) {
  if (message.type === "joined") {
    setStatus(message.peerPresent ? "Peer present" : "Waiting for target");
    if (message.peerPresent) {
      await startOffer();
    }
    return;
  }

  if (message.type === "peer-ready") {
    await startOffer();
    return;
  }

  if (message.type === "answer") {
    await pc.setRemoteDescription({ type: "answer", sdp: message.sdp });
    setStatus("Connected");
    return;
  }

  if (message.type === "ice-candidate") {
    if (pc && message.candidate) {
      await pc.addIceCandidate(message.candidate);
    }
    return;
  }

  if (message.type === "peer-left") {
    resetPeer();
    setStatus("Peer left");
    return;
  }

  if (message.type === "error") {
    setStatus(`Error: ${message.message}`);
  }
}

async function connect() {
  connectedRoom = roomInput.value.trim() || "demo";
  history.replaceState({}, "", `/?room=${encodeURIComponent(connectedRoom)}`);

  resetPeer();
  if (ws) {
    ws.close();
  }

  setStatus("Connecting signaling");
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${scheme}://${window.location.host}/ws`);

  ws.onopen = () => {
    signal({ type: "join", room: connectedRoom, role: "viewer" });
  };

  ws.onmessage = async (event) => {
    try {
      await handleSignal(JSON.parse(event.data));
    } catch (error) {
      console.error(error);
      setStatus(`Signal error: ${error.message}`);
    }
  };

  ws.onclose = () => setStatus("Signaling disconnected");
}

connectButton.addEventListener("click", () => {
  connect().catch((error) => setStatus(`Connect failed: ${error.message}`));
});

muteButton.addEventListener("click", async () => {
  const stream = await ensureMicrophone();
  micEnabled = !micEnabled;
  stream.getAudioTracks().forEach((track) => {
    track.enabled = micEnabled;
  });
  muteButton.textContent = micEnabled ? "Mute mic" : "Unmute mic";
});
