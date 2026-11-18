// First-person controls: pointer lock + WASD on desktop, virtual joystick and
// drag-to-look on touch devices. Collision keeps the player out of buildings.
import * as THREE from "../vendor/three.module.js";

const EYE_HEIGHT = 1.7;
const WALK_SPEED = 5.2;
const RUN_SPEED = 8.6;
const GRAVITY = -22;
const JUMP_SPEED = 7.4;
const PLAYER_RADIUS = 0.55;
const MAX_PITCH = 1.45;

export class PlayerControls {
  constructor(camera, domElement, { colliders = [], bounds = 110, onLockChange = () => {} } = {}) {
    this.camera = camera;
    this.dom = domElement;
    this.colliders = colliders;
    this.bounds = bounds;
    this.onLockChange = onLockChange;

    this.position = new THREE.Vector3(0, EYE_HEIGHT, 0);
    this.yaw = 0;
    this.pitch = 0;
    this.verticalVelocity = 0;
    this.onGround = true;
    this.enabled = false;

    this.keys = new Set();
    this.moveInput = { x: 0, y: 0 }; // joystick, -1..1
    this.lookDeltas = { x: 0, y: 0 };
    this.lookSensitivity = 0.0022;

    this._onMouseMove = this._onMouseMove.bind(this);
    this._onKeyDown = this._onKeyDown.bind(this);
    this._onKeyUp = this._onKeyUp.bind(this);
    this._onPointerLockChange = this._onPointerLockChange.bind(this);
    this._onClick = this._onClick.bind(this);

    this.dom.addEventListener("click", this._onClick);
    document.addEventListener("mousemove", this._onMouseMove);
    document.addEventListener("keydown", this._onKeyDown);
    document.addEventListener("keyup", this._onKeyUp);
    document.addEventListener("pointerlockchange", this._onPointerLockChange);
  }

  setSpawn({ x, z, yaw = 0 }) {
    this.position.set(x, EYE_HEIGHT, z);
    this.yaw = yaw;
    this.pitch = 0;
    this.verticalVelocity = 0;
    this.onGround = true;
    this._applyCamera();
  }

  /** Swap the collision world, e.g. from the city into a house interior. */
  setWorld(colliders = [], bounds = 110) {
    this.colliders = colliders;
    this.bounds = bounds;
  }

  get locked() {
    return document.pointerLockElement === this.dom;
  }

  requestLock() {
    if (this.dom.requestPointerLock) this.dom.requestPointerLock();
  }

  setEnabled(enabled) {
    this.enabled = enabled;
    if (!enabled && this.locked && document.exitPointerLock) document.exitPointerLock();
  }

  /** Called by the touch UI. */
  addLook(dx, dy) {
    this.lookDeltas.x += dx;
    this.lookDeltas.y += dy;
  }

  setMove(x, y) {
    this.moveInput.x = Math.max(-1, Math.min(1, x));
    this.moveInput.y = Math.max(-1, Math.min(1, y));
  }

  jump() {
    if (this.onGround) {
      this.verticalVelocity = JUMP_SPEED;
      this.onGround = false;
    }
  }

  _onClick() {
    if (!this.enabled) return;
    if (document.pointerLockElement !== this.dom) this.requestLock();
  }

  _onPointerLockChange() {
    this.onLockChange(this.locked);
  }

  _onMouseMove(event) {
    if (!this.locked || !this.enabled) return;
    this.yaw -= event.movementX * this.lookSensitivity;
    this.pitch -= event.movementY * this.lookSensitivity;
    this.pitch = Math.max(-MAX_PITCH, Math.min(MAX_PITCH, this.pitch));
  }

  _onKeyDown(event) {
    if (!this.enabled) return;
    this.keys.add(event.code);
    if (event.code === "Space") {
      event.preventDefault();
      this.jump();
    }
  }

  _onKeyUp(event) {
    this.keys.delete(event.code);
  }

  update(dt) {
    if (!this.enabled) return;

    // Touch look deltas
    if (this.lookDeltas.x || this.lookDeltas.y) {
      this.yaw -= this.lookDeltas.x * 0.004;
      this.pitch -= this.lookDeltas.y * 0.004;
      this.pitch = Math.max(-MAX_PITCH, Math.min(MAX_PITCH, this.pitch));
      this.lookDeltas.x = 0;
      this.lookDeltas.y = 0;
    }

    let forward = 0;
    let strafe = 0;
    if (this.keys.has("KeyW") || this.keys.has("ArrowUp")) forward += 1;
    if (this.keys.has("KeyS") || this.keys.has("ArrowDown")) forward -= 1;
    if (this.keys.has("KeyD") || this.keys.has("ArrowRight")) strafe += 1;
    if (this.keys.has("KeyA") || this.keys.has("ArrowLeft")) strafe -= 1;

    forward += -this.moveInput.y;
    strafe += this.moveInput.x;

    const length = Math.hypot(forward, strafe);
    if (length > 1) {
      forward /= length;
      strafe /= length;
    }

    const sprinting = this.keys.has("ShiftLeft") || this.keys.has("ShiftRight");
    const speed = sprinting ? RUN_SPEED : WALK_SPEED;
    const sin = Math.sin(this.yaw);
    const cos = Math.cos(this.yaw);

    // Camera looks down -Z, so forward is (-sin, -cos).
    const dx = (-sin * forward + cos * strafe) * speed * dt;
    const dz = (-cos * forward - sin * strafe) * speed * dt;

    this._moveWithCollision(dx, dz);

    this.verticalVelocity += GRAVITY * dt;
    this.position.y += this.verticalVelocity * dt;
    if (this.position.y <= EYE_HEIGHT) {
      this.position.y = EYE_HEIGHT;
      this.verticalVelocity = 0;
      this.onGround = true;
    }

    this.position.x = Math.max(-this.bounds, Math.min(this.bounds, this.position.x));
    this.position.z = Math.max(-this.bounds, Math.min(this.bounds, this.position.z));

    this._applyCamera();
  }

  _moveWithCollision(dx, dz) {
    const radius = PLAYER_RADIUS;

    // Resolve each axis separately so sliding along a wall feels natural.
    this.position.x += dx;
    for (const box of this.colliders) {
      if (this.position.y - EYE_HEIGHT > box.height) continue;
      if (
        this.position.x > box.minX - radius &&
        this.position.x < box.maxX + radius &&
        this.position.z > box.minZ - radius &&
        this.position.z < box.maxZ + radius
      ) {
        this.position.x = dx > 0 ? box.minX - radius : box.maxX + radius;
      }
    }

    this.position.z += dz;
    for (const box of this.colliders) {
      if (this.position.y - EYE_HEIGHT > box.height) continue;
      if (
        this.position.x > box.minX - radius &&
        this.position.x < box.maxX + radius &&
        this.position.z > box.minZ - radius &&
        this.position.z < box.maxZ + radius
      ) {
        this.position.z = dz > 0 ? box.minZ - radius : box.maxZ + radius;
      }
    }
  }

  _applyCamera() {
    this.camera.position.copy(this.position);
    this.camera.rotation.order = "YXZ";
    this.camera.rotation.set(this.pitch, this.yaw, 0);
  }

  dispose() {
    this.dom.removeEventListener("click", this._onClick);
    document.removeEventListener("mousemove", this._onMouseMove);
    document.removeEventListener("keydown", this._onKeyDown);
    document.removeEventListener("keyup", this._onKeyUp);
    document.removeEventListener("pointerlockchange", this._onPointerLockChange);
    this.keys.clear();
  }
}
