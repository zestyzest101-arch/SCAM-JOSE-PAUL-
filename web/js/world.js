// Builds the playable 3D city and runs the render loop.
import * as THREE from "../vendor/three.module.js";
import { PlayerControls } from "./controls.js";

const SKY_COLOR = "#8ec9f0";
const textureCache = new Map();

function canvas2d(width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

function facadeTexture(baseColor, kind) {
  const key = `${baseColor}|${kind}`;
  if (textureCache.has(key)) return textureCache.get(key);

  const canvas = canvas2d(128, 256);
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = baseColor;
  ctx.fillRect(0, 0, 128, 256);

  const shade = ctx.createLinearGradient(0, 0, 0, 256);
  shade.addColorStop(0, "rgba(255,255,255,0.20)");
  shade.addColorStop(1, "rgba(0,0,0,0.18)");
  ctx.fillStyle = shade;
  ctx.fillRect(0, 0, 128, 256);

  const cols = kind === "tower" ? 4 : 3;
  const rows = kind === "tower" ? 9 : 5;
  const padX = 10;
  const padY = 14;
  const cellW = (128 - padX * 2) / cols;
  const cellH = (256 - padY * 2) / rows;

  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const lit = Math.random() < 0.45;
      ctx.fillStyle = lit ? "rgba(255,228,150,0.95)" : "rgba(38,50,68,0.55)";
      ctx.fillRect(
        padX + col * cellW + 3,
        padY + row * cellH + 4,
        cellW - 6,
        cellH - 8
      );
    }
  }

  // Ground floor band so shops read as shops.
  ctx.fillStyle = "rgba(0,0,0,0.22)";
  ctx.fillRect(0, 256 - 30, 128, 30);
  ctx.fillStyle = "rgba(255,255,255,0.10)";
  ctx.fillRect(0, 256 - 30, 128, 3);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  textureCache.set(key, texture);
  return texture;
}

function roadTexture() {
  if (textureCache.has("road")) return textureCache.get("road");
  const canvas = canvas2d(64, 256);
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#3b3f47";
  ctx.fillRect(0, 0, 64, 256);
  ctx.fillStyle = "#33373e";
  for (let i = 0; i < 40; i += 1) {
    ctx.fillRect(Math.random() * 64, Math.random() * 256, 2, 2);
  }
  ctx.fillStyle = "#e8d36a";
  for (let y = 0; y < 256; y += 64) {
    ctx.fillRect(30, y + 10, 4, 32);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.colorSpace = THREE.SRGBColorSpace;
  textureCache.set("road", texture);
  return texture;
}

function signTexture(text, background, foreground) {
  const key = `sign|${text}|${background}|${foreground}`;
  if (textureCache.has(key)) return textureCache.get(key);
  const canvas = canvas2d(512, 128);
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, 512, 128);
  ctx.strokeStyle = foreground;
  ctx.lineWidth = 8;
  ctx.strokeRect(6, 6, 500, 116);
  ctx.fillStyle = foreground;
  ctx.font = "bold 64px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 256, 68);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  textureCache.set(key, texture);
  return texture;
}

const AVATAR_COLORS = ["#ff3d81", "#7b5cff", "#3ddc97", "#ffcc55", "#42a5f5", "#ef6c00"];

function avatarColor(key) {
  const text = String(key || "player");
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) hash = (hash * 31 + text.charCodeAt(i)) % 997;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

// Floating name tag above another player.
function nameTexture(name) {
  const key = `name|${name}`;
  if (textureCache.has(key)) return textureCache.get(key);

  const canvas = canvas2d(256, 64);
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "rgba(8, 6, 14, 0.7)";
  ctx.fillRect(0, 0, 256, 64);
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 30px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(String(name).slice(0, 14), 128, 34);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  textureCache.set(key, texture);
  return texture;
}

export class World {
  constructor(container, { onLockChange = () => {}, onError = () => {} } = {}) {
    this.container = container;
    this.onLockChange = onLockChange;
    this.onError = onError;
    this.layout = null;
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.running = false;
    this._raf = 0;
    this._clock = null;
    this.remotes = new Map();
    this._resizeHandler = () => this._resize();
  }

  start(layout) {
    this.layout = layout;

    try {
      this.renderer = new THREE.WebGLRenderer({ antialias: true });
    } catch (error) {
      this.onError("3D graphics are not available in this browser.");
      return false;
    }

    const width = this.container.clientWidth || window.innerWidth;
    const height = this.container.clientHeight || window.innerHeight;

    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(width, height);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(SKY_COLOR);
    this.scene.fog = new THREE.Fog(SKY_COLOR, 95, 250);

    this.camera = new THREE.PerspectiveCamera(70, width / height, 0.1, 700);

    this._addLights();
    this._addGround();
    this._addRoads();
    this._addBuildings();
    this._addProps();

    this.controls = new PlayerControls(this.camera, this.renderer.domElement, {
      colliders: layout.colliders,
      bounds: layout.size / 2 + 12,
      onLockChange: this.onLockChange,
    });
    this.controls.setSpawn(layout.spawn);
    this.controls.setEnabled(true);

    window.addEventListener("resize", this._resizeHandler);
    this._clock = new THREE.Clock();
    this.running = true;
    this._loop();
    return true;
  }

  _addLights() {
    const hemi = new THREE.HemisphereLight(0xd6ecff, 0x5f6b4a, 1.05);
    this.scene.add(hemi);

    const sun = new THREE.DirectionalLight(0xfff1cf, 1.75);
    sun.position.set(70, 110, 55);
    sun.castShadow = true;
    sun.shadow.mapSize.width = 2048;
    sun.shadow.mapSize.height = 2048;
    sun.shadow.camera.left = -110;
    sun.shadow.camera.right = 110;
    sun.shadow.camera.top = 110;
    sun.shadow.camera.bottom = -110;
    sun.shadow.camera.near = 1;
    sun.shadow.camera.far = 320;
    sun.shadow.bias = -0.0006;
    this.scene.add(sun);
    this.scene.add(sun.target);
    this.sun = sun;
  }

  _addGround() {
    const layout = this.layout;
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(layout.size * 2, layout.size * 2),
      new THREE.MeshLambertMaterial({ color: "#7f9c5c" })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    this.scene.add(ground);

    // Sidewalk slabs under each block.
    const sidewalkMaterial = new THREE.MeshLambertMaterial({ color: "#bdb8aa" });
    for (const block of layout.blocks) {
      const slab = new THREE.Mesh(
        new THREE.BoxGeometry(block.size + 5, 0.16, block.size + 5),
        sidewalkMaterial
      );
      slab.position.set(block.x, 0.08, block.z);
      slab.receiveShadow = true;
      this.scene.add(slab);
    }
  }

  _addRoads() {
    const layout = this.layout;
    const roadMaterial = new THREE.MeshLambertMaterial({ map: roadTexture() });
    const length = layout.size + layout.road * 2;

    for (const line of layout.roadLines) {
      const alongZ = new THREE.Mesh(new THREE.PlaneGeometry(layout.road, length), roadMaterial);
      alongZ.rotation.x = -Math.PI / 2;
      alongZ.position.set(line, 0.02, 0);
      alongZ.receiveShadow = true;
      this.scene.add(alongZ);

      const alongX = new THREE.Mesh(new THREE.PlaneGeometry(layout.road, length), roadMaterial);
      alongX.rotation.x = -Math.PI / 2;
      alongX.rotation.z = Math.PI / 2;
      alongX.position.set(0, 0.021, line);
      alongX.receiveShadow = true;
      this.scene.add(alongX);
    }
  }

  _addBuildings() {
    const layout = this.layout;

    for (const building of layout.buildings) {
      const geometry = new THREE.BoxGeometry(building.w, building.h, building.d);
      const material = new THREE.MeshLambertMaterial({
        map: facadeTexture(building.color, building.kind),
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(building.x, building.h / 2, building.z);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      this.scene.add(mesh);

      if (building.kind === "house") {
        const roof = new THREE.Mesh(
          new THREE.ConeGeometry(Math.max(building.w, building.d) * 0.8, 4.2, 4),
          new THREE.MeshLambertMaterial({ color: "#b4463c" })
        );
        roof.position.set(building.x, building.h + 2.1, building.z);
        roof.rotation.y = Math.PI / 4;
        roof.castShadow = true;
        this.scene.add(roof);

        const door = new THREE.Mesh(
          new THREE.BoxGeometry(1.8, 2.6, 0.3),
          new THREE.MeshLambertMaterial({ color: "#7a4a2b" })
        );
        door.position.set(building.x, 1.3, building.z + building.d / 2 + 0.15);
        this.scene.add(door);

        this._addSign("YOUR HOUSE", "#f6efd8", "#6b4a24", {
          x: building.x,
          y: 5.6,
          z: building.z + building.d / 2 + 0.2,
          width: 7,
          height: 1.7,
        });
      } else if (building.kind === "casino") {
        const trim = new THREE.Mesh(
          new THREE.BoxGeometry(building.w + 1.4, 1.1, building.d + 1.4),
          new THREE.MeshLambertMaterial({ color: "#f6c445" })
        );
        trim.position.set(building.x, building.h - 0.4, building.z);
        this.scene.add(trim);

        this._addSign("CASINO", "#1b1430", "#ffd75e", {
          x: building.x,
          y: building.h - 4.2,
          z: building.z + building.d / 2 + 0.25,
          width: 12,
          height: 3,
          glow: true,
        });

        const step = new THREE.Mesh(
          new THREE.BoxGeometry(building.w + 6, 0.4, 4),
          new THREE.MeshLambertMaterial({ color: "#3a2f52" })
        );
        step.position.set(building.x, 0.2, building.z + building.d / 2 + 2.5);
        this.scene.add(step);
      } else {
        const roof = new THREE.Mesh(
          new THREE.BoxGeometry(building.w + 0.5, 0.6, building.d + 0.5),
          new THREE.MeshLambertMaterial({ color: building.trimColor || "#6b5a44" })
        );
        roof.position.set(building.x, building.h + 0.3, building.z);
        roof.castShadow = true;
        this.scene.add(roof);

        if (building.kind === "shop") {
          const awning = new THREE.Mesh(
            new THREE.BoxGeometry(building.w * 0.86, 0.3, 1.5),
            new THREE.MeshLambertMaterial({ color: "#d0544a" })
          );
          awning.position.set(building.x, 3.3, building.z + building.d / 2 + 0.6);
          awning.castShadow = true;
          this.scene.add(awning);
        }
      }
    }
  }

  _addSign(text, background, foreground, { x, y, z, width, height, glow = false }) {
    const material = glow
      ? new THREE.MeshBasicMaterial({ map: signTexture(text, background, foreground) })
      : new THREE.MeshLambertMaterial({ map: signTexture(text, background, foreground) });
    const sign = new THREE.Mesh(new THREE.PlaneGeometry(width, height), material);
    sign.position.set(x, y, z);
    this.scene.add(sign);
  }

  _addProps() {
    const layout = this.layout;

    // Trees
    const trunkMaterial = new THREE.MeshLambertMaterial({ color: "#6b4a2b" });
    const leafMaterials = [
      new THREE.MeshLambertMaterial({ color: "#4f8f3f" }),
      new THREE.MeshLambertMaterial({ color: "#63a84c" }),
      new THREE.MeshLambertMaterial({ color: "#3f7a36" }),
    ];
    for (const tree of layout.trees) {
      const group = new THREE.Group();
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.24, 1.9, 6), trunkMaterial);
      trunk.position.y = 0.95;
      trunk.castShadow = true;
      group.add(trunk);

      const leaves = new THREE.Mesh(
        new THREE.IcosahedronGeometry(1.35, 0),
        leafMaterials[Math.floor(Math.random() * leafMaterials.length)]
      );
      leaves.position.y = 2.5;
      leaves.castShadow = true;
      group.add(leaves);

      group.position.set(tree.x, 0.1, tree.z);
      group.scale.setScalar(tree.s || 1);
      this.scene.add(group);
    }

    // Street lamps
    const poleMaterial = new THREE.MeshLambertMaterial({ color: "#4a4f57" });
    const bulbMaterial = new THREE.MeshBasicMaterial({ color: "#ffe9a8" });
    for (const lamp of layout.lamps) {
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.13, 4.4, 6), poleMaterial);
      pole.position.set(lamp.x, 2.2, lamp.z);
      pole.castShadow = true;
      this.scene.add(pole);

      const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.32, 10, 8), bulbMaterial);
      bulb.position.set(lamp.x, 4.5, lamp.z);
      this.scene.add(bulb);
    }

    // Parked cars
    const wheelMaterial = new THREE.MeshLambertMaterial({ color: "#1e1f22" });
    for (const car of layout.cars) {
      const group = new THREE.Group();
      const body = new THREE.Mesh(
        new THREE.BoxGeometry(1.9, 0.75, 3.9),
        new THREE.MeshLambertMaterial({ color: car.color })
      );
      body.position.y = 0.72;
      body.castShadow = true;
      group.add(body);

      const cabin = new THREE.Mesh(
        new THREE.BoxGeometry(1.6, 0.6, 1.9),
        new THREE.MeshLambertMaterial({ color: "#2b3442" })
      );
      cabin.position.set(0, 1.32, -0.15);
      cabin.castShadow = true;
      group.add(cabin);

      for (const [wx, wz] of [
        [-0.95, 1.3],
        [0.95, 1.3],
        [-0.95, -1.3],
        [0.95, -1.3],
      ]) {
        const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.33, 0.33, 0.24, 10), wheelMaterial);
        wheel.rotation.z = Math.PI / 2;
        wheel.position.set(wx, 0.33, wz);
        group.add(wheel);
      }

      group.position.set(car.x, 0.05, car.z);
      group.rotation.y = car.rotY || 0;
      this.scene.add(group);
    }
  }

  getPlayerPosition() {
    return this.controls ? this.controls.position : new THREE.Vector3();
  }

  getPlayerYaw() {
    return this.controls ? this.controls.yaw : 0;
  }

  // --------------------------------------------------------------- multiplayer
  // Other players are simple stand-in figures with a name tag: enough to see
  // and follow each other around the city until real character models exist.
  addRemotePlayer({ username, characterId } = {}) {
    if (!this.scene || !username || this.remotes.has(username)) return;

    const group = new THREE.Group();

    const body = new THREE.Mesh(
      new THREE.CylinderGeometry(0.42, 0.5, 1.25, 12),
      new THREE.MeshLambertMaterial({ color: avatarColor(characterId || username) })
    );
    body.position.y = 0.95;
    body.castShadow = true;
    group.add(body);

    const head = new THREE.Mesh(
      new THREE.SphereGeometry(0.34, 16, 12),
      new THREE.MeshLambertMaterial({ color: "#f0c9a6" })
    );
    head.position.y = 1.85;
    head.castShadow = true;
    group.add(head);

    const label = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: nameTexture(username), depthTest: false })
    );
    label.position.y = 2.55;
    label.scale.set(3.4, 0.85, 1);
    group.add(label);

    this.scene.add(group);
    this.remotes.set(username, { group, target: new THREE.Vector3(), yaw: 0 });
  }

  updateRemotePlayer({ username, x, y, z, yaw } = {}) {
    const remote = this.remotes.get(username);
    if (!remote) return;
    // y is the sender's eye height; the figure stands on the ground.
    remote.target.set(Number(x) || 0, 0, Number(z) || 0);
    remote.yaw = Number(yaw) || 0;
  }

  removeRemotePlayer(username) {
    const remote = this.remotes.get(username);
    if (!remote || !this.scene) return;
    this.scene.remove(remote.group);
    remote.group.traverse((child) => {
      child.geometry?.dispose?.();
      if (child.material && child.material !== undefined) {
        if (child.material.map && child.material.map !== nameTexture(username)) {
          child.material.map.dispose?.();
        }
        child.material.dispose?.();
      }
    });
    this.remotes.delete(username);
  }

  clearRemotePlayers() {
    for (const username of [...this.remotes.keys()]) this.removeRemotePlayer(username);
  }

  _updateRemotes() {
    for (const remote of this.remotes.values()) {
      // Smooth the jump between network updates so movement looks natural.
      remote.group.position.lerp(remote.target, 0.25);
      remote.group.rotation.y = remote.yaw;
    }
  }

  _resize() {
    if (!this.renderer || !this.camera) return;
    const width = this.container.clientWidth || window.innerWidth;
    const height = this.container.clientHeight || window.innerHeight;
    this.renderer.setSize(width, height);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  _loop() {
    if (!this.running) return;
    this._raf = requestAnimationFrame(() => this._loop());
    const dt = Math.min(this._clock.getDelta(), 0.05);
    if (this.controls) this.controls.update(dt);
    this.renderer.render(this.scene, this.camera);
  }

  stop() {
    this.running = false;
    if (this._raf) cancelAnimationFrame(this._raf);
    this._raf = 0;
    window.removeEventListener("resize", this._resizeHandler);
    if (this.controls) {
      this.controls.dispose();
      this.controls = null;
    }
    if (this.renderer) {
      this.renderer.dispose();
      if (this.renderer.domElement.parentNode) {
        this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
      }
      this.renderer = null;
    }
    this.scene = null;
    this.camera = null;
  }
}
