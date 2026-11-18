// Cinematic bank-heist cutscene.
//
// The server sends an ordered list of beats ({"id", "text", "duration"}). This
// module renders them as a small self-contained Three.js film: a bank facade,
// the crew, and the props each beat needs. It draws in its own overlay canvas,
// so the live city keeps running behind it and the cutscene can never break
// gameplay rendering.
//
// Success : the crew walks out counting the money, the leader takes his
//           glasses off, then the bank explodes (visual only).
// Failure : sirens, police van, the crew dragged out in cuffs, the leader's
//           empty bag in the gutter, then the van doors slam.
import * as THREE from "../vendor/three.module.js";

const BANK_Z = -7;
const DOOR_Z = BANK_Z + 2.4;
const KNEEL_Y = -0.35;

// Camera setups, one per beat id. The camera eases toward the active shot so
// cuts feel like a film rather than a teleport.
const SHOTS = {
  arrival: { pos: [0, 2.4, 16], look: [0, 2.1, BANK_Z + 1] },
  vault: { pos: [0, 1.9, BANK_Z + 2.0], look: [0, 1.8, BANK_Z - 6] },
  bags: { pos: [-4.6, 2.2, 4.5], look: [0, 1.4, DOOR_Z - 1] },
  exit: { pos: [0, 3.1, 12.5], look: [0, 1.4, DOOR_Z - 2] },
  count: { pos: [3.6, 1.9, 8.6], look: [0, 1.3, 3.2] },
  glasses: { pos: [1.5, 1.85, 5.6], look: [0, 1.72, 2.6] },
  explode: { pos: [0, 4.4, 18], look: [0, 2.4, BANK_Z] },
  alarm: { pos: [0, 2.2, 12.5], look: [0, 2.2, BANK_Z] },
  surround: { pos: [0, 3.4, 16.5], look: [0, 1.6, 1] },
  cuffed: { pos: [2.8, 1.6, 6.2], look: [0, 1.0, 2.4] },
  bag: { pos: [1.5, 0.65, 4.8], look: [0.4, 0.2, 2.6] },
  van: { pos: [-5.0, 2.3, 6.4], look: [-3.2, 1.4, 2.2] },
  outro: { pos: [0, 5.6, 25], look: [0, 2.0, BANK_Z] },
};

const CREW_COLORS = ["#f0b429", "#e05a47", "#4aa3df", "#7bc86c", "#b07cd6", "#e88ab5"];

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function textTexture(text, { bg = "#101725", fg = "#ffe9b0", size = 96 } = {}) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 128;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = fg;
  ctx.font = `bold ${size}px system-ui, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function box(width, height, depth, color, { roughness = 0.75, metalness = 0.05 } = {}) {
  return new THREE.Mesh(
    new THREE.BoxGeometry(width, height, depth),
    new THREE.MeshStandardMaterial({ color, roughness, metalness })
  );
}

export class HeistCutscene {
  constructor({ overlay, canvas, subtitle, title, result, flash, skip, onFinish }) {
    this.overlay = overlay;
    this.canvas = canvas;
    this.subtitle = subtitle;
    this.title = title;
    this.result = result;
    this.flash = flash;
    this.skipButton = skip;
    this.onFinish = onFinish || (() => {});

    this.heist = null;
    this.beats = [];
    this.playing = false;
    this.beatIndex = -1;
    this.beatElapsed = 0;
    this.elapsed = 0;
    this.total = 0;
    this.raf = 0;
    this.actors = [];

    this._tick = this._tick.bind(this);
    this._resize = this._resize.bind(this);

    if (this.skipButton) {
      this.skipButton.addEventListener("click", () => this.skip());
    }
    window.addEventListener("resize", this._resize);
  }

  /* ------------------------------------------------------------- lifecycle */

  play(heist) {
    if (!heist || !Array.isArray(heist.beats) || heist.beats.length === 0) return false;

    this._disposeScene();
    this.heist = heist;
    this.beats = heist.beats;
    this.total = this.beats.reduce((sum, beat) => sum + (beat.duration || 3), 0);
    this.elapsed = 0;
    this.beatIndex = -1;
    this.beatElapsed = 0;
    this.walkStart = null;
    this.vanStart = null;
    this.explodeStart = null;
    this.glassesTossed = false;

    this._buildScene();

    if (this.title) this.title.textContent = heist.success ? "HEIST SUCCESS" : "HEIST FAILED";
    if (this.result) {
      this.result.textContent = heist.success
        ? `\u20b9${Number(heist.loot || 0).toLocaleString()} each \u00b7 crew of ${heist.crew.length}`
        : `\u20b9${Number(heist.fine || 0).toLocaleString()} fine \u00b7 ${heist.lockup_seconds}s lockup`;
    }
    if (this.flash) this.flash.style.opacity = "0";
    if (this.subtitle) this.subtitle.textContent = "";

    this.overlay.classList.remove("hidden");
    this.overlay.setAttribute("aria-hidden", "false");
    this.overlay.classList.toggle("failed", !heist.success);

    this.playing = true;
    this._last = performance.now();
    this.raf = requestAnimationFrame(this._tick);
    return true;
  }

  skip() {
    if (!this.playing) return;
    this._finish();
  }

  stop() {
    this.playing = false;
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = 0;
    this._disposeScene();
    this.overlay.classList.add("hidden");
    this.overlay.setAttribute("aria-hidden", "true");
  }

  _finish() {
    const heist = this.heist;
    this.playing = false;
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = 0;
    this._disposeScene();
    this.overlay.classList.add("hidden");
    this.overlay.setAttribute("aria-hidden", "true");
    if (this.flash) this.flash.style.opacity = "0";
    this.onFinish(heist);
  }

  /* ----------------------------------------------------------------- scene */

  _buildScene() {
    const renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer = renderer;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(this.heist.success ? "#0d1420" : "#140d12");
    scene.fog = new THREE.Fog(scene.background, 34, 90);
    this.scene = scene;

    this.camera = new THREE.PerspectiveCamera(48, 1.6, 0.1, 220);
    this.camera.position.set(0, 2.4, 16);

    this.lookAt = new THREE.Vector3(0, 2.1, BANK_Z + 1);

    scene.add(new THREE.HemisphereLight(0xa8c8ff, 0x24222c, 1.15));
    const key = new THREE.DirectionalLight(0xffe3bd, 1.6);
    key.position.set(9, 15, 12);
    scene.add(key);

    this.blastLight = new THREE.PointLight(0xffa64d, 0, 60);
    this.blastLight.position.set(0, 3.4, BANK_Z);
    scene.add(this.blastLight);

    this.sirenLight = new THREE.PointLight(0xff2d4a, 0, 30);
    this.sirenLight.position.set(-6, 3.2, 2.5);
    scene.add(this.sirenLight);

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(160, 160),
      new THREE.MeshStandardMaterial({ color: "#2a2d35", roughness: 0.96 })
    );
    ground.rotation.x = -Math.PI / 2;
    scene.add(ground);

    const curb = box(60, 0.16, 60, "#33363f", { roughness: 0.9 });
    curb.position.set(0, 0.08, 8);
    scene.add(curb);

    this.bank = this._buildBank();
    scene.add(this.bank);

    this.money = this._buildMoney();
    this.money.visible = false;
    scene.add(this.money);

    this.explosion = this._buildExplosion();
    this.explosion.visible = false;
    scene.add(this.explosion);

    this.van = this._buildVan();
    this.van.visible = false;
    scene.add(this.van);

    this.gutterBag = box(0.42, 0.34, 0.3, "#c9b08a");
    this.gutterBag.position.set(0.45, 0.17, 3.4);
    this.gutterBag.visible = false;
    scene.add(this.gutterBag);

    this.actors = this._buildCrew(this.heist.crew || []);
    this.actors.forEach((actor) => scene.add(actor.group));

    this._resize();
  }

  _buildBank() {
    const group = new THREE.Group();

    const body = box(18, 10, 9, "#c9c2b4", { roughness: 0.9 });
    body.position.set(0, 5, BANK_Z);
    group.add(body);

    const cornice = box(19.2, 0.7, 10, "#efe9dc");
    cornice.position.set(0, 10.2, BANK_Z);
    group.add(cornice);

    for (let i = 0; i < 4; i += 1) {
      const column = new THREE.Mesh(
        new THREE.CylinderGeometry(0.52, 0.6, 8.4, 18),
        new THREE.MeshStandardMaterial({ color: "#f3eee2", roughness: 0.85 })
      );
      column.position.set(-6.6 + i * 4.4, 4.4, BANK_Z + 4.7);
      group.add(column);
    }

    // doorway: dark opening, then the glass doors in front of it
    const opening = box(4.6, 4.4, 0.5, "#161a22");
    opening.position.set(0, 2.3, BANK_Z + 4.55);
    group.add(opening);

    this.doors = new THREE.Group();
    for (let i = 0; i < 2; i += 1) {
      const leaf = new THREE.Mesh(
        new THREE.BoxGeometry(1.1, 3.9, 0.12),
        new THREE.MeshStandardMaterial({
          color: "#8fd0e8",
          roughness: 0.2,
          metalness: 0.4,
          transparent: true,
          opacity: 0.65,
        })
      );
      leaf.position.set(-0.62 + i * 1.24, 2.1, BANK_Z + 4.75);
      this.doors.add(leaf);
    }
    group.add(this.doors);

    const sign = new THREE.Mesh(
      new THREE.PlaneGeometry(7.4, 1.85),
      new THREE.MeshBasicMaterial({ map: textTexture("BANK"), transparent: true })
    );
    sign.position.set(0, 8.6, BANK_Z + 4.62);
    group.add(sign);

    const steps = box(9, 0.4, 2.6, "#b9b2a4");
    steps.position.set(0, 0.2, BANK_Z + 5.6);
    group.add(steps);

    return group;
  }

  _buildMoney() {
    const group = new THREE.Group();
    const material = new THREE.MeshStandardMaterial({
      color: "#8fe38f",
      emissive: "#2f7a3a",
      emissiveIntensity: 0.6,
      roughness: 0.5,
      side: THREE.DoubleSide,
    });
    this.bills = [];
    for (let i = 0; i < 22; i += 1) {
      const bill = new THREE.Mesh(new THREE.PlaneGeometry(0.26, 0.14), material);
      bill.position.set((Math.random() - 0.5) * 3.4, 1.2 + Math.random() * 1.6, 3.2 + Math.random() * 2.4);
      bill.rotation.set(Math.random() * 3, Math.random() * 3, Math.random() * 3);
      bill.userData.spin = (Math.random() - 0.5) * 2.2;
      bill.userData.rise = 0.16 + Math.random() * 0.3;
      this.bills.push(bill);
      group.add(bill);
    }
    return group;
  }

  _buildExplosion() {
    const group = new THREE.Group();
    group.position.set(0, 2.6, BANK_Z);

    this.fireball = new THREE.Mesh(
      new THREE.SphereGeometry(1, 24, 18),
      new THREE.MeshBasicMaterial({ color: 0xffb347, transparent: true, opacity: 1 })
    );
    group.add(this.fireball);

    this.shockRing = new THREE.Mesh(
      new THREE.RingGeometry(1.1, 1.5, 40),
      new THREE.MeshBasicMaterial({
        color: 0xffe9b0,
        transparent: true,
        opacity: 0.9,
        side: THREE.DoubleSide,
      })
    );
    this.shockRing.rotation.x = -Math.PI / 2;
    group.add(this.shockRing);

    this.debris = [];
    for (let i = 0; i < 16; i += 1) {
      const chunk = box(0.34, 0.34, 0.34, i % 2 ? "#8d8578" : "#4a4038");
      chunk.userData.velocity = new THREE.Vector3(
        (Math.random() - 0.5) * 9,
        3.2 + Math.random() * 6,
        1 + Math.random() * 7
      );
      this.debris.push(chunk);
      group.add(chunk);
    }

    return group;
  }

  _buildVan() {
    const group = new THREE.Group();
    group.position.set(-16, 0, 1.5);

    const body = box(2.9, 2.1, 5.6, "#1d2a44");
    body.position.y = 1.3;
    group.add(body);

    const cab = box(2.7, 1.3, 1.5, "#243352");
    cab.position.set(0, 1.15, 3.3);
    group.add(cab);

    const glass = box(2.5, 0.8, 0.12, "#8fd0e8");
    glass.position.set(0, 1.6, 4.02);
    group.add(glass);

    const bar = box(1.9, 0.22, 0.4, "#0d1119");
    bar.position.set(0, 2.45, 2.6);
    group.add(bar);

    this.sirenRed = box(0.55, 0.2, 0.3, "#ff2d4a");
    this.sirenRed.position.set(-0.6, 2.62, 2.6);
    group.add(this.sirenRed);

    this.sirenBlue = box(0.55, 0.2, 0.3, "#2d7dff");
    this.sirenBlue.position.set(0.6, 2.62, 2.6);
    group.add(this.sirenBlue);

    for (const z of [-1.7, 3.0]) {
      for (const x of [-1.4, 1.4]) {
        const wheel = new THREE.Mesh(
          new THREE.CylinderGeometry(0.52, 0.52, 0.32, 16),
          new THREE.MeshStandardMaterial({ color: "#0c0e13", roughness: 0.9 })
        );
        wheel.rotation.z = Math.PI / 2;
        wheel.position.set(x, 0.52, z);
        group.add(wheel);
      }
    }

    return group;
  }

  _buildCrew(names) {
    const list = [];
    const spread = Math.min(1.5, 3.4 / Math.max(1, names.length));
    names.forEach((name, index) => {
      const isLeader = index === 0;
      const color = CREW_COLORS[index % CREW_COLORS.length];
      const group = new THREE.Group();

      const torso = box(0.62, 0.86, 0.36, color);
      torso.position.y = 1.18;
      group.add(torso);

      const head = new THREE.Mesh(
        new THREE.SphereGeometry(0.26, 18, 14),
        new THREE.MeshStandardMaterial({ color: "#c9926b", roughness: 0.8 })
      );
      head.position.y = 1.78;
      group.add(head);

      const legs = [];
      for (let i = 0; i < 2; i += 1) {
        const leg = box(0.2, 0.82, 0.24, "#22262f");
        leg.position.set(i ? 0.16 : -0.16, 0.42, 0);
        legs.push(leg);
        group.add(leg);
      }

      const arms = [];
      for (let i = 0; i < 2; i += 1) {
        const arm = box(0.16, 0.7, 0.18, color);
        arm.position.set(i ? 0.42 : -0.42, 1.16, 0);
        arms.push(arm);
        group.add(arm);
      }

      const bag = box(0.44, 0.4, 0.32, "#b9a273");
      bag.position.set(0.44, 0.72, 0.06);
      bag.visible = isLeader || index % 2 === 0;
      group.add(bag);

      let glasses = null;
      if (isLeader) {
        glasses = box(0.44, 0.1, 0.08, "#0b0d12");
        glasses.position.set(0, 1.8, 0.23);
        group.add(glasses);
      }

      const baseX = (index - (names.length - 1) / 2) * spread;
      const baseZ = DOOR_Z + 1.0 + (index % 2) * 0.55;
      group.position.set(baseX, 0, baseZ);

      list.push({
        name,
        isLeader,
        group,
        torso,
        head,
        legs,
        arms,
        bag,
        glasses,
        baseX,
        baseZ,
        phase: Math.random() * Math.PI * 2,
      });
    });
    return list;
  }

  /* -------------------------------------------------------------- playback */

  _tick() {
    if (!this.playing) return;

    const now = performance.now();
    let dt = (now - this._last) / 1000;
    this._last = now;
    if (dt > 0.25) dt = 0.25; // a background tab must not fast-forward the film
    this.elapsed += dt;

    this._updateBeats();
    this._updateActors(dt);
    this._updateEffects(dt);
    this._updateCamera(dt);

    this.renderer.render(this.scene, this.camera);

    if (this.elapsed >= this.total) {
      this._finish();
      return;
    }
    this.raf = requestAnimationFrame(this._tick);
  }

  _updateBeats() {
    let acc = 0;
    let index = this.beats.length - 1;
    for (let i = 0; i < this.beats.length; i += 1) {
      const duration = this.beats[i].duration || 3;
      if (this.elapsed < acc + duration) {
        index = i;
        break;
      }
      acc += duration;
    }
    this.beatElapsed = this.elapsed - acc;

    if (index !== this.beatIndex) {
      this.beatIndex = index;
      this._enterBeat(this.beats[index] || {});
    }
  }

  _enterBeat(beat) {
    if (this.subtitle) this.subtitle.textContent = beat.text || "";

    if (beat.id === "exit") this.walkStart = this.elapsed;
    if (beat.id === "count") this.money.visible = true;
    if (beat.id === "alarm") this.sirenOn = true;
    if (beat.id === "surround") {
      this.van.visible = true;
      this.vanTargetX = -3.1;
    }
    if (beat.id === "bag") {
      this.gutterBag.visible = true;
      this.actors.forEach((actor) => {
        if (actor.isLeader && actor.bag) actor.bag.visible = false;
      });
    }
    if (beat.id === "van") this.vanStart = this.elapsed;
    if (beat.id === "explode") this.explodeStart = this.elapsed;
  }

  _updateActors(dt) {
    const beat = this.beats[this.beatIndex] || {};
    const kneel = !this.heist.success && ["cuffed", "bag", "van"].includes(beat.id);
    const handsUp = !this.heist.success && ["surround", "cuffed"].includes(beat.id);

    this.actors.forEach((actor) => {
      let targetX = actor.baseX;
      let targetZ = actor.baseZ;
      let walking = false;

      if (this.heist.success && this.walkStart !== null) {
        const p = clamp((this.elapsed - this.walkStart) / 5.5, 0, 1);
        targetZ = actor.baseZ + p * 4.4;
        walking = p < 0.995;
      }

      if (!this.heist.success && this.vanStart !== null) {
        const p = clamp((this.elapsed - this.vanStart) / 3.4, 0, 1);
        targetX = actor.baseX + (-3.1 - actor.baseX) * p;
        targetZ = actor.baseZ + (2.4 - actor.baseZ) * p;
        walking = p < 0.995;
        actor.group.visible = p < 0.94;
      }

      const ease = Math.min(1, dt * 5);
      actor.group.position.x += (targetX - actor.group.position.x) * ease;
      actor.group.position.z += (targetZ - actor.group.position.z) * ease;

      const targetY = kneel ? KNEEL_Y : 0;
      actor.group.position.y += (targetY - actor.group.position.y) * Math.min(1, dt * 3);

      // walk cycle
      actor.phase += dt * (walking ? 8.5 : 1.6);
      const swing = walking ? 0.62 : 0.06;
      actor.legs[0].rotation.x = Math.sin(actor.phase) * swing;
      actor.legs[1].rotation.x = -Math.sin(actor.phase) * swing;

      if (handsUp) {
        actor.arms[0].rotation.z = -2.1;
        actor.arms[1].rotation.z = 2.1;
        actor.arms[0].rotation.x = 0;
        actor.arms[1].rotation.x = 0;
      } else if (beat.id === "count") {
        // fanning the cash out: small circling hands
        actor.arms[0].rotation.x = -0.9 + Math.sin(actor.phase * 1.7) * 0.35;
        actor.arms[1].rotation.x = -0.9 + Math.cos(actor.phase * 1.7) * 0.35;
        actor.arms[0].rotation.z = 0;
        actor.arms[1].rotation.z = 0;
      } else {
        actor.arms[0].rotation.z = 0;
        actor.arms[1].rotation.z = 0;
        actor.arms[0].rotation.x = -Math.sin(actor.phase) * swing;
        actor.arms[1].rotation.x = Math.sin(actor.phase) * swing;
      }

      if (kneel) actor.torso.rotation.x = 0.32;
      else actor.torso.rotation.x += (0 - actor.torso.rotation.x) * Math.min(1, dt * 3);
    });

    // the leader removes his glasses and tosses them aside
    if (this.beatIndex >= 0 && this.beats[this.beatIndex].id === "glasses" && !this.glassesTossed) {
      if (this.beatElapsed > 1.3) {
        this.glassesTossed = true;
        const leader = this.actors[0];
        if (leader && leader.glasses) {
          leader.glasses.visible = false;
          const tossed = leader.glasses.clone();
          tossed.position.set(leader.baseX, 1.8, leader.baseZ + 0.3);
          this.scene.add(tossed);
          this.tossedGlasses = tossed;
          this.tossedAt = this.elapsed;
        }
      }
    }

    if (this.tossedGlasses) {
      const t = clamp((this.elapsed - this.tossedAt) / 1.6, 0, 1);
      this.tossedGlasses.position.set(
        this.actors[0].baseX + t * 1.1,
        1.8 + Math.sin(t * Math.PI) * 0.7 - t * 1.6,
        this.actors[0].baseZ + 0.3 + t * 0.9
      );
      this.tossedGlasses.rotation.z += dt * 7;
      this.tossedGlasses.rotation.x += dt * 4;
    }
  }

  _updateEffects(dt) {
    if (this.money.visible) {
      this.bills.forEach((bill) => {
        bill.rotation.y += dt * bill.userData.spin;
        bill.position.y += dt * bill.userData.rise;
        if (bill.position.y > 3.4) bill.position.y = 0.9;
      });
    }

    if (this.sirenOn) {
      const pulse = 0.5 + 0.5 * Math.sin(this.elapsed * 9);
      this.sirenLight.intensity = 2.4 + pulse * 3.4;
      this.sirenLight.color.setHex(pulse > 0.5 ? 0xff2d4a : 0x2d7dff);
      if (this.sirenRed) this.sirenRed.material.emissive?.setHex(pulse > 0.5 ? 0xff2d4a : 0x220000);
      if (this.sirenBlue) this.sirenBlue.material.emissive?.setHex(pulse > 0.5 ? 0x001133 : 0x2d7dff);
    }

    if (this.van.visible && this.vanTargetX !== undefined) {
      this.van.position.x += (this.vanTargetX - this.van.position.x) * Math.min(1, dt * 2.4);
    }

    if (this.explodeStart !== null) {
      const t = clamp((this.elapsed - this.explodeStart) / 2.8, 0, 1);
      this.explosion.visible = true;

      this.fireball.scale.setScalar(0.5 + t * 7.5);
      this.fireball.material.opacity = Math.max(0, 1 - t * 1.15);
      this.fireball.material.color.setHex(t < 0.45 ? 0xffd27a : 0xff7a3d);

      this.shockRing.scale.setScalar(1 + t * 12);
      this.shockRing.material.opacity = Math.max(0, 0.9 - t);

      this.debris.forEach((chunk) => {
        const velocity = chunk.userData.velocity;
        chunk.position.set(
          velocity.x * t * 2.2,
          Math.max(0.2, velocity.y * t - 9.8 * t * t),
          velocity.z * t * 1.6
        );
        chunk.rotation.x += dt * 3;
        chunk.rotation.z += dt * 2.4;
      });

      this.blastLight.intensity = 26 * Math.max(0, 1 - t * 1.6);

      if (this.flash) {
        const flash = t < 0.18 ? 1 - t / 0.18 : 0;
        this.flash.style.opacity = String(Math.max(0, flash * 0.9));
      }
    }
  }

  _updateCamera(dt) {
    const beat = this.beats[this.beatIndex] || {};
    const shot = SHOTS[beat.id] || SHOTS.arrival;

    const targetPos = new THREE.Vector3(shot.pos[0], shot.pos[1], shot.pos[2]);
    const targetLook = new THREE.Vector3(shot.look[0], shot.look[1], shot.look[2]);

    const ease = Math.min(1, dt * 2.6);
    this.camera.position.lerp(targetPos, ease);
    this.lookAt.lerp(targetLook, ease);

    // shake while the bank comes down
    if (this.explodeStart !== null) {
      const t = clamp((this.elapsed - this.explodeStart) / 2.8, 0, 1);
      const strength = (1 - t) * 0.35;
      this.camera.position.x += (Math.random() - 0.5) * strength;
      this.camera.position.y += (Math.random() - 0.5) * strength;
    }

    this.camera.lookAt(this.lookAt);
  }

  _resize() {
    if (!this.renderer || !this.canvas) return;
    const width = this.canvas.clientWidth || window.innerWidth;
    const height = this.canvas.clientHeight || window.innerHeight;
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / Math.max(1, height);
    this.camera.updateProjectionMatrix();
  }

  _disposeScene() {
    if (this.renderer) {
      this.renderer.dispose();
      this.renderer = null;
    }
    this.scene = null;
    this.camera = null;
    this.actors = [];
    this.bills = [];
    this.debris = [];
    this.tossedGlasses = null;
    this.sirenOn = false;
    this.vanTargetX = undefined;
  }
}
