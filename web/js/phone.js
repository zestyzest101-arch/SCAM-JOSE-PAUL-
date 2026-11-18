// In-game phone: a map of the current city with the player marker and a
// navigation waypoint. Drawn on a 2D canvas from the same layout as the world.
export class Phone {
  constructor({ root, canvas, cityEl, closeButton, navigateButton, onNavigate }) {
    this.root = root;
    this.canvas = canvas;
    this.cityEl = cityEl;
    this.closeButton = closeButton;
    this.navigateButton = navigateButton;
    this.onNavigate = onNavigate || (() => {});

    this.layout = null;
    this.player = { x: 0, z: 0 };
    this.waypoint = null;
    this.open = false;

    this.closeButton.addEventListener("click", () => this.hide());
    this.navigateButton.addEventListener("click", () => {
      if (!this.layout) return;
      if (this.waypoint) {
        this.waypoint = null;
        this.navigateButton.textContent = "Navigate to Casino";
      } else {
        this.waypoint = { ...this.layout.casino, label: "CASINO" };
        this.navigateButton.textContent = "Stop navigating";
      }
      this.onNavigate(this.waypoint);
      this.draw();
    });
  }

  show(layout, playerPosition) {
    this.layout = layout;
    this.player = { x: playerPosition.x, z: playerPosition.z };
    this.open = true;
    this.root.classList.add("open");
    if (this.cityEl) this.cityEl.textContent = `${layout.name} · ${layout.code}`;
    this.draw();
  }

  hide() {
    this.open = false;
    this.root.classList.remove("open");
  }

  toggle(layout, playerPosition) {
    if (this.open) this.hide();
    else this.show(layout, playerPosition);
  }

  update(playerPosition) {
    this.player = { x: playerPosition.x, z: playerPosition.z };
    if (this.open) this.draw();
  }

  _toMap(x, z, scale, half) {
    return {
      x: this.canvas.width / 2 + x * scale,
      y: this.canvas.height / 2 + z * scale,
    };
  }

  draw() {
    if (!this.layout) return;
    const ctx = this.canvas.getContext("2d");
    const { width, height } = this.canvas;
    const half = this.layout.size / 2 + this.layout.road;
    const scale = Math.min(width, height) / (half * 2);

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#0f1a24";
    ctx.fillRect(0, 0, width, height);

    // Sidewalk blocks
    for (const block of this.layout.blocks) {
      const p = this._toMap(block.x, block.z, scale, half);
      const size = block.size * scale;
      ctx.fillStyle = "#26333f";
      ctx.fillRect(p.x - size / 2, p.y - size / 2, size, size);
    }

    // Roads
    ctx.strokeStyle = "#3d4d5c";
    ctx.lineWidth = Math.max(2, this.layout.road * scale);
    for (const line of this.layout.roadLines) {
      const vertical = this._toMap(line, -half, scale, half);
      ctx.beginPath();
      ctx.moveTo(vertical.x, 0);
      ctx.lineTo(vertical.x, height);
      ctx.stroke();

      const horizontal = this._toMap(-half, line, scale, half);
      ctx.beginPath();
      ctx.moveTo(0, horizontal.y);
      ctx.lineTo(width, horizontal.y);
      ctx.stroke();
    }

    // Buildings
    for (const building of this.layout.buildings) {
      const p = this._toMap(building.x, building.z, scale, half);
      const w = Math.max(2, building.w * scale);
      const d = Math.max(2, building.d * scale);
      if (building.kind === "casino") ctx.fillStyle = "#f6c445";
      else if (building.kind === "house") ctx.fillStyle = "#7ce0a0";
      else ctx.fillStyle = "#5a6f82";
      ctx.fillRect(p.x - w / 2, p.y - d / 2, w, d);
    }

    // Waypoint
    if (this.waypoint) {
      const target = this._toMap(this.waypoint.x, this.waypoint.z, scale, half);
      const me = this._toMap(this.player.x, this.player.z, scale, half);
      ctx.strokeStyle = "#5ee0ff";
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 5]);
      ctx.beginPath();
      ctx.moveTo(me.x, me.y);
      ctx.lineTo(target.x, target.y);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = "#5ee0ff";
      ctx.beginPath();
      ctx.moveTo(target.x, target.y - 7);
      ctx.lineTo(target.x + 6, target.y);
      ctx.lineTo(target.x, target.y + 7);
      ctx.lineTo(target.x - 6, target.y);
      ctx.closePath();
      ctx.fill();
    }

    // Player marker
    const me = this._toMap(this.player.x, this.player.z, scale, half);
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(me.x, me.y, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#0f1a24";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Frame
    ctx.strokeStyle = "#2f4453";
    ctx.lineWidth = 4;
    ctx.strokeRect(2, 2, width - 4, height - 4);
  }
}
