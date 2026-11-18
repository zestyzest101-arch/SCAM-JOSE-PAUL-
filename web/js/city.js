// Deterministic city layout generator.
//
// The same city code always produces the same streets and buildings, so a city
// feels like a real place and can later be shared between players. This module
// only produces plain data (no Three.js), so the phone map and the 3D world can
// both draw from one source of truth.

const BLOCK = 30;
const ROAD = 14;
const GRID = 4;
const CELL = BLOCK + ROAD;
const SIZE = GRID * CELL;

const PALETTES = {
  perambur: ["#d9773f", "#e0a45a", "#b4643f", "#e8c07a", "#c98a55"],
  nungambakkam: ["#f0dcc0", "#c8a8d8", "#e6dcf0", "#b9c9e8", "#f2e2c8"],
  egmore: ["#e3c9a0", "#c9d3a8", "#e8b9a0", "#a8bcd3", "#dfc6a8"],
  anna_nagar: ["#f5e6c8", "#e8c8a8", "#d8e0c8", "#c8d8e8", "#f0d8b0"],
  kilpauk: ["#d8c0a0", "#b8c8b0", "#e0c8b8", "#c0b0c8", "#cdbfa2"],
};

const TRIM = {
  perambur: "#7a3f24",
  nungambakkam: "#6a4f86",
  egmore: "#6b5a44",
  anna_nagar: "#8a6a3c",
  kilpauk: "#5d5340",
};

function hashSeed(text) {
  let hash = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function makeRng(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const pick = (rng, list) => list[Math.floor(rng() * list.length) % list.length];

/**
 * Build the layout for a city.
 * @param {{preset?: string, code?: string, name?: string}} options
 */
export function buildCity({ preset = "egmore", code = "GLOBAL_HUB", name = "City" } = {}) {
  const palette = PALETTES[preset] || PALETTES.egmore;
  const trim = TRIM[preset] || TRIM.egmore;
  const rng = makeRng(hashSeed(`${preset}:${code}`));

  const blockCenter = (index) => -SIZE / 2 + index * CELL + CELL / 2;
  const roadLine = (index) => -SIZE / 2 + index * CELL;

  const blocks = [];
  const buildings = [];
  const trees = [];
  const lamps = [];
  const cars = [];

  // Blocks: (1,1) is the casino plaza, (0,3) holds the starter house.
  const CASINO_BLOCK = { i: 1, j: 1 };
  const HOUSE_BLOCK = { i: 0, j: 3 };

  for (let i = 0; i < GRID; i += 1) {
    for (let j = 0; j < GRID; j += 1) {
      blocks.push({ x: blockCenter(i), z: blockCenter(j), size: BLOCK });
    }
  }

  const houseCenter = { x: blockCenter(HOUSE_BLOCK.i), z: blockCenter(HOUSE_BLOCK.j) };
  const casinoCenter = { x: blockCenter(CASINO_BLOCK.i), z: blockCenter(CASINO_BLOCK.j) };

  const distanceFromCentre = (x, z) => Math.hypot(x, z) / (SIZE / 2);

  for (let i = 0; i < GRID; i += 1) {
    for (let j = 0; j < GRID; j += 1) {
      const cx = blockCenter(i);
      const cz = blockCenter(j);
      const isHouse = i === HOUSE_BLOCK.i && j === HOUSE_BLOCK.j;
      const isCasino = i === CASINO_BLOCK.i && j === CASINO_BLOCK.j;

      if (isHouse) {
        buildings.push({
          x: cx,
          z: cz,
          w: 12,
          d: 10,
          h: 6.4,
          rotY: 0,
          color: "#f2e0c0",
          trimColor: "#8a6a3c",
          kind: "house",
          label: "YOUR HOUSE",
        });
        // Small front garden hedge blocks on either side of the door.
        trees.push({ x: cx - 5.6, z: cz + 6.4, s: 0.9 });
        trees.push({ x: cx + 5.6, z: cz + 6.4, s: 0.9 });
        continue;
      }

      if (isCasino) {
        buildings.push({
          x: cx,
          z: cz,
          w: 20,
          d: 16,
          h: 15,
          rotY: 0,
          color: "#2a2140",
          trimColor: "#f6c445",
          kind: "casino",
          label: "CASINO",
        });
        lamps.push({ x: cx - 12, z: cz + 10 });
        lamps.push({ x: cx + 12, z: cz + 10 });
        continue;
      }

      // 2x2 sub-cells per block, some left empty as courtyards or car parks.
      const sub = BLOCK / 2;
      for (let a = 0; a < 2; a += 1) {
        for (let b = 0; b < 2; b += 1) {
          if (rng() < 0.18) {
            if (rng() < 0.5) {
              trees.push({
                x: cx - sub / 2 + a * sub + (rng() - 0.5) * 4,
                z: cz - sub / 2 + b * sub + (rng() - 0.5) * 4,
                s: 0.8 + rng() * 0.5,
              });
            }
            continue;
          }

          const w = sub * (0.62 + rng() * 0.24);
          const d = sub * (0.62 + rng() * 0.24);
          const distance = distanceFromCentre(cx, cz);
          const maxHeight = 26 - distance * 14;
          const h = Math.max(6, 5 + rng() * maxHeight);
          const kind = h > 12 ? "tower" : h > 8 ? "apartment" : "shop";

          buildings.push({
            x: cx - sub / 2 + a * sub + (rng() - 0.5) * 1.2,
            z: cz - sub / 2 + b * sub + (rng() - 0.5) * 1.2,
            w,
            d,
            h,
            rotY: 0,
            color: pick(rng, palette),
            trimColor: trim,
            kind,
            label: null,
          });
        }
      }
    }
  }

  // Street lamps at every road intersection, cars parked along the kerbs.
  for (let i = 0; i <= GRID; i += 1) {
    for (let j = 0; j <= GRID; j += 1) {
      lamps.push({ x: roadLine(i) + ROAD * 0.32, z: roadLine(j) + ROAD * 0.32 });
    }
  }

  for (let i = 1; i < GRID; i += 1) {
    for (let j = 0; j < GRID; j += 1) {
      if (rng() < 0.55) {
        cars.push({
          x: roadLine(i) + (rng() < 0.5 ? -ROAD * 0.28 : ROAD * 0.28),
          z: blockCenter(j) + (rng() - 0.5) * BLOCK * 0.6,
          rotY: 0,
          color: pick(rng, ["#d94f4f", "#4f7fd9", "#f2c14e", "#4fbf8b", "#e8e8e8", "#8b5cf6"]),
        });
      }
      if (rng() < 0.4) {
        cars.push({
          x: blockCenter(j) + (rng() - 0.5) * BLOCK * 0.6,
          z: roadLine(i) + (rng() < 0.5 ? -ROAD * 0.28 : ROAD * 0.28),
          rotY: Math.PI / 2,
          color: pick(rng, ["#d94f4f", "#4f7fd9", "#f2c14e", "#4fbf8b", "#e8e8e8", "#8b5cf6"]),
        });
      }
    }
  }

  const colliders = buildings.map((building) => ({
    minX: building.x - building.w / 2,
    maxX: building.x + building.w / 2,
    minZ: building.z - building.d / 2,
    maxZ: building.z + building.d / 2,
    height: building.h,
  }));

  // Points of interest the player can use (E on a keyboard, tap on mobile).
  const doorOf = (building, offset = 1.6) => ({
    x: building.x,
    z: building.z + building.d / 2 + offset,
  });

  const houseDoor = doorOf(houseCenter);

  // Spawn on the doorstep of the starter house, looking at the door, so the
  // "Enter your house" prompt is already in reach when the world finishes
  // loading (the flow is login → lobby → character → world → starter house).
  // The camera looks down -Z, so yaw 0 faces the house (yaw PI would face away).
  const spawn = {
    x: houseDoor.x,
    z: houseDoor.z + 3,
    yaw: 0,
  };
  const spawnDistance = (building) =>
    (building.x - spawn.x) * (building.x - spawn.x) +
    (building.z - spawn.z) * (building.z - spawn.z);
  const nearestShop = buildings
    .filter((building) => building.kind === "shop")
    .sort((a, b) => spawnDistance(a) - spawnDistance(b))[0];

  const pois = [
    {
      id: "house",
      kind: "house",
      label: "Enter your house",
      x: houseDoor.x,
      z: houseDoor.z,
      radius: 4.6,
    },
  ];
  if (nearestShop) {
    const shopDoor = doorOf(nearestShop, 2.2);
    pois.push({
      id: "shop",
      kind: "shop",
      label: "Shop for furniture",
      x: shopDoor.x,
      z: shopDoor.z,
      radius: 4.6,
    });
  }
  const casinoDoor = doorOf(casinoCenter, 2.6);
  pois.push({
    id: "casino",
    kind: "casino",
    label: "Casino",
    x: casinoDoor.x,
    z: casinoDoor.z,
    radius: 5,
  });

  return {
    preset,
    code,
    name,
    seed: hashSeed(`${preset}:${code}`),
    size: SIZE,
    road: ROAD,
    block: BLOCK,
    grid: GRID,
    blocks,
    buildings,
    trees,
    lamps,
    cars,
    casino: casinoCenter,
    house: houseCenter,
    spawn,
    pois,
    colliders,
    palette,
    trimColor: trim,
    roadLines: Array.from({ length: GRID + 1 }, (_, index) => roadLine(index)),
  };
}
