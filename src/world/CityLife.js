import * as THREE from 'three';
import {
  BUS_ROUTES,
  CAR_ROUTES,
  CITY_DESTINATIONS,
  INTERSECTIONS,
  PEDESTRIAN_ROUTES,
  crossingAt,
  pedestriansMayCross,
  stopLineFor,
  trafficPhase
} from '../data/city.js';
import { makeCustomerModel } from '../entities/CustomerModel.js';
import { cloneCharacter, cloneModel } from '../utils/AssetLoader.js';
import { CITY_PEDESTRIAN_CHARACTERS } from '../data/customers.js';

function rand(a, b) {
  return a + Math.random() * (b - a);
}
function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

const CAR_COLORS = {
  'city/car_red.glb': 0xb33b3b,
  'city/car_blue.glb': 0x3b5fb3,
  'city/car_white.glb': 0xe4e4dc,
  'city/taxi.glb': 0xd9b23a,
  'city/van.glb': 0x9aa3a8
};

// Rigged walkers cost more than the old procedural bodies, so the pavement
// population is capped lower; the same six GLBs are preloaded for shoppers.
const MAX_PEDS = 6;

export default class CityLife {
  constructor(game, cityWorld) {
    this.game = game;
    this.city = cityWorld;
    this.peds = [];
    this.vehicles = [];
    this.active = true;
    this._pedTimer = 0;
  }

  // -------------------------------------------------------------------------
  // Spawn
  // -------------------------------------------------------------------------
  build() {
    for (let i = 0; i < 5; i++) this.spawnPed();
    this.buildFleet();
  }

  pickSpawn() {
    const player = this.game.player?.pos;
    for (let attempt = 0; attempt < 8; attempt++) {
      const spot = pick(CITY_DESTINATIONS);
      if (!player || Math.hypot(spot.x - player.x, spot.z - player.z) > 14) return spot;
    }
    return pick(CITY_DESTINATIONS);
  }

  spawnPed() {
    if (this.peds.length >= MAX_PEDS) return null;
    const spot = this.pickSpawn();
    if (!spot) return null;
    const group = new THREE.Group();
    group.position.set(spot.x, 0, spot.z);
    this.city.group.add(group);
    const ped = {
      group,
      character: pick(CITY_PEDESTRIAN_CHARACTERS),
      mixer: null,
      actions: null,
      anim: null,
      rig: null,
      speed: rand(0.9, 1.45),
      phase: rand(0, 6),
      path: null,
      idx: 0,
      wait: rand(0, 2),
      lightWait: 0,
      target: spot,
      moving: false
    };
    this.peds.push(ped);
    this.planPed(ped);
    this.dressPed(ped);
    return ped;
  }

  // Sidewalk walkers use the same rigged customer GLBs as the store, cloned per
  // instance so each has its own skeleton and animation mixer. The procedural
  // body is only a load-failure fallback.
  dressPed(ped) {
    cloneCharacter(ped.character.file)
      .then((model) => {
        if (!this.peds.includes(ped)) return; // recycled while the GLB loaded
        if (!model) {
          this.dressFallbackPed(ped);
          return;
        }
        const mixer = new THREE.AnimationMixer(model);
        const actions = {};
        for (const clip of model.userData.animations || []) {
          if (clip.name !== 'Walk' && clip.name !== 'Idle') continue;
          const action = mixer.clipAction(clip);
          action.setLoop(THREE.LoopRepeat, Infinity);
          action.setEffectiveWeight(0);
          action.play();
          actions[clip.name] = action;
        }
        // Only attach once the mixer is ready, so a failure cannot leave the
        // GLB and the procedural fallback in the same group.
        ped.mixer = mixer;
        ped.actions = actions;
        ped.group.add(model);
        this.playPed(ped, ped.moving ? 'Walk' : 'Idle', 0);
      })
      .catch((err) => {
        console.warn('[CityLife] Pedestrian GLB skipped', err);
        if (this.peds.includes(ped)) this.dressFallbackPed(ped);
      });
  }

  dressFallbackPed(ped) {
    const model = makeCustomerModel();
    ped.rig = model.rig;
    ped.armL = model.armL;
    ped.armR = model.armR;
    ped.legL = model.legL;
    ped.legR = model.legR;
    ped.group.add(model.root);
  }

  playPed(ped, name, fade = 0.22) {
    if (!ped.actions) return;
    const next = ped.actions[name];
    if (!next || ped.anim === name) return;
    const prev = ped.actions[ped.anim];
    if (prev) prev.fadeOut(fade);
    next.reset();
    next.setEffectiveWeight(1);
    if (fade > 0) next.fadeIn(fade);
    next.play();
    ped.anim = name;
  }

  // Route a walker to a random destination through the city nav grid, so it
  // stays on pavement and only crosses where there is a marked crossing.
  planPed(ped) {
    const nav = this.city.nav;
    const from = ped.group.position;
    if (!nav) {
      this.fallbackPath(ped);
      return false;
    }
    for (let attempt = 0; attempt < 4; attempt++) {
      const candidate = this.pickSpawn();
      const found = nav.findPath(from.x, from.z, candidate.x, candidate.z);
      if (found && found.length > 1) {
        ped.target = candidate;
        ped.path = found;
        ped.idx = 1;
        ped.wait = 0;
        ped.retryAt = 0;
        return true;
      }
    }
    // A* can come back empty when the kerb is pinched; walk a fixed sidewalk
    // route instead and only ask the grid again after a cooldown. Replanning
    // every frame here is what froze the main thread.
    this.fallbackPath(ped);
    return false;
  }

  fallbackPath(ped) {
    const route = pick(PEDESTRIAN_ROUTES);
    const from = ped.group.position;
    const nearest = route.reduce(
      (best, point) => {
        const d = Math.hypot(point.x - from.x, point.z - from.z);
        return d < best.d ? { point, d } : best;
      },
      { point: route[0], d: Infinity }
    );
    ped.path = [nearest.point, ...route];
    ped.idx = 1;
    ped.wait = 0;
    ped.retryAt = 8;
    ped.fallback = true;
  }

  // -------------------------------------------------------------------------
  // Vehicles
  // -------------------------------------------------------------------------
  buildFleet() {
    for (const v of this.vehicles) this.city.group.remove(v.group);
    this.vehicles.length = 0;
    CAR_ROUTES.forEach((route, i) => this.spawnVehicle(route, false, i));
    BUS_ROUTES.forEach((route, i) => this.spawnVehicle(route, true, i));
  }

  spawnVehicle(route, isBus, index) {
    const length = Math.abs(route.to - route.from);
    const group = new THREE.Group();
    group.add(
      isBus ? this.makeBusFallback() : this.makeCarFallback(CAR_COLORS[route.file] ?? 0x8a8f94)
    );
    this.city.group.add(group);
    const file = route.file;
    if (file) {
      cloneModel(file).then((model) => {
        if (!model) return;
        model.traverse((o) => {
          if (o.isMesh) {
            o.castShadow = true;
            o.receiveShadow = true;
          }
        });
        group.clear();
        group.add(model);
      });
    }
    const stopUs = INTERSECTIONS.map((it) => {
      const line = stopLineFor(route, it);
      return route.direction > 0 ? line - route.from : route.from - line;
    }).filter((u) => u > 2 && u < length - 2);
    const busStopUs = (route.stops || [])
      .map((stop) => (route.direction > 0 ? stop - route.from : route.from - stop))
      .filter((u) => u > 0 && u < length);
    this.vehicles.push({
      group,
      route,
      isBus,
      length,
      // Buses start half a lap away so they never spawn on top of a car.
      u: ((index * 41 + (isBus ? 96 : 12)) % length) + 4,
      stopUs,
      busStopUs,
      serviced: new Set(),
      dwell: 0,
      color: CAR_COLORS[route.file] ?? 0x8a8f94
    });
    this.placeVehicle(this.vehicles[this.vehicles.length - 1]);
  }

  vehicleSpeedLimit(v, time) {
    const route = v.route;
    let limit = route.speed;
    const phase = trafficPhase(time);
    const signal = route.axis === 'x' ? phase.ew : phase.ns;
    if (signal !== 'green') {
      const nextStop = v.stopUs
        .filter((u) => u > v.u - 0.6)
        .reduce((best, u) => (u < best ? u : best), Infinity);
      if (Number.isFinite(nextStop) && nextStop - v.u < 16) {
        // Ease to a halt instead of snapping at the line.
        limit = Math.min(limit, Math.max(0, (nextStop - v.u - 0.8) * 1.2));
      }
    }
    // Keep a gap to whatever is ahead in the same lane.
    for (const other of this.vehicles) {
      if (other === v) continue;
      if (other.route.axis !== route.axis || other.route.lane !== route.lane) continue;
      if (other.route.direction !== route.direction) continue;
      let gap = other.u - v.u;
      if (gap < 0) gap += v.length;
      if (gap > 0 && gap < 9) limit = Math.min(limit, Math.max(0, (gap - 2.4) * 1.4));
    }
    if (v.dwell > 0) limit = 0;
    return limit;
  }

  placeVehicle(v) {
    const route = v.route;
    const coord = route.from + route.direction * v.u;
    if (route.axis === 'x') {
      v.group.position.set(coord, 0, route.lane);
      v.group.rotation.y = route.direction > 0 ? Math.PI / 2 : -Math.PI / 2;
    } else {
      v.group.position.set(route.lane, 0, coord);
      v.group.rotation.y = route.direction > 0 ? 0 : Math.PI;
    }
  }

  updateVehicle(v, dt, time) {
    if (v.dwell > 0) {
      v.dwell -= dt;
    } else {
      const limit = this.vehicleSpeedLimit(v, time);
      v.u += Math.min(v.route.speed, limit) * dt;
      for (const stopU of v.busStopUs) {
        if (!v.serviced.has(stopU) && Math.abs(stopU - v.u) < 1.1) {
          v.serviced.add(stopU);
          v.dwell = v.route.dwell ?? 4;
        }
      }
    }
    if (v.u >= v.length) {
      v.u -= v.length;
      v.serviced.clear();
    }
    this.placeVehicle(v);
  }

  // -------------------------------------------------------------------------
  // Props
  // -------------------------------------------------------------------------
  makeCarFallback(color) {
    const g = new THREE.Group();
    const body = new THREE.MeshStandardMaterial({ color, metalness: 0.35, roughness: 0.4 });
    const glass = new THREE.MeshStandardMaterial({ color: 0x22303a, roughness: 0.2 });
    const add = (w, h, d, mat, x, y, z) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
      m.position.set(x, y, z);
      m.castShadow = true;
      g.add(m);
      return m;
    };
    add(1.8, 0.55, 3.7, body, 0, 0.62, 0);
    add(1.55, 0.6, 1.9, glass, 0, 1.22, 0.1);
    add(1.7, 0.18, 1.4, body, 0, 1.5, 0.15);
    for (const x of [-0.8, 0.8]) {
      for (const z of [-1.2, 1.2]) {
        const wheel = new THREE.Mesh(
          new THREE.CylinderGeometry(0.34, 0.34, 0.24, 10),
          new THREE.MeshStandardMaterial({ color: 0x22262a, roughness: 0.9 })
        );
        wheel.rotation.z = Math.PI / 2;
        wheel.position.set(x, 0.36, z);
        g.add(wheel);
      }
    }
    return g;
  }

  makeBusFallback() {
    const g = new THREE.Group();
    const body = new THREE.MeshStandardMaterial({ color: 0x2f7fa8, roughness: 0.55 });
    const trim = new THREE.MeshStandardMaterial({ color: 0xe8eef0, roughness: 0.6 });
    const glass = new THREE.MeshStandardMaterial({ color: 0x1d2b33, roughness: 0.2 });
    const add = (w, h, d, mat, x, y, z) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
      m.position.set(x, y, z);
      m.castShadow = true;
      g.add(m);
    };
    add(2.5, 2.1, 10.4, body, 0, 1.55, 0);
    add(2.55, 0.28, 10.4, trim, 0, 2.7, 0);
    add(2.3, 0.95, 9.6, glass, 0, 2.05, 0);
    add(2.2, 1.2, 0.12, glass, 0, 1.95, 5.2);
    add(2.2, 0.9, 0.12, glass, 0, 2.0, -5.2);
    for (const z of [3.6, -3.4]) {
      for (const x of [-1.15, 1.15]) {
        const wheel = new THREE.Mesh(
          new THREE.CylinderGeometry(0.46, 0.46, 0.3, 12),
          new THREE.MeshStandardMaterial({ color: 0x212528, roughness: 0.9 })
        );
        wheel.rotation.z = Math.PI / 2;
        wheel.position.set(x, 0.48, z);
        g.add(wheel);
      }
    }
    return g;
  }

  // -------------------------------------------------------------------------
  // Frame update
  // -------------------------------------------------------------------------
  update(dt, time = 0) {
    const player = this.game.player?.pos;
    const active = !player || (Math.abs(player.x) < 90 && Math.abs(player.z) < 80);
    this.active = active;
    if (!active) return;

    this._pedTimer += dt;
    if (this._pedTimer > 5) {
      this._pedTimer = 0;
      this.spawnPed();
    }

    this.updatePeds(dt, time);
    for (const v of this.vehicles) this.updateVehicle(v, dt, time);
  }

  updatePeds(dt, time) {
    for (let i = this.peds.length - 1; i >= 0; i--) {
      const ped = this.peds[i];
      const pos = ped.group.position;
      ped.moving = false;

      // Walkers far behind the player are recycled instead of piling up.
      if (
        this.peds.length > 4 &&
        Math.hypot(pos.x - this.game.player.pos.x, pos.z - this.game.player.pos.z) > 130
      ) {
        ped.mixer?.stopAllAction();
        this.city.group.remove(ped.group);
        this.peds.splice(i, 1);
        continue;
      }

      ped.retryAt = Math.max(0, (ped.retryAt || 0) - dt);
      if (ped.wait > 0) {
        ped.wait -= dt;
        if (ped.wait <= 0 && !ped.path && ped.retryAt === 0) this.planPed(ped);
      } else if (!ped.path && ped.retryAt === 0) {
        this.planPed(ped);
      }

      if (ped.path && ped.idx < ped.path.length) {
        const next = ped.path[ped.idx];
        const dx = next.x - pos.x;
        const dz = next.z - pos.z;
        const dist = Math.hypot(dx, dz);
        if (dist < 0.3) {
          ped.idx++;
        } else {
          const step = Math.min(dist, ped.speed * dt);
          const nx = pos.x + (dx / dist) * step;
          const nz = pos.z + (dz / dist) * step;
          const crossing = crossingAt(nx, nz);
          // Wait at the kerb for the walk signal; after a while, cross anyway
          // so a walker can never be stuck forever in a corner case.
          if (crossing && !pedestriansMayCross(crossing, time) && ped.lightWait < 14) {
            ped.lightWait += dt;
          } else {
            ped.group.position.set(nx, 0, nz);
            ped.group.rotation.y = Math.atan2(dx, dz);
            ped.moving = true;
            ped.lightWait = 0;
          }
        }
      } else if (ped.path) {
        ped.path = null;
        ped.wait = rand(2.5, 6);
        ped.retryAt = 0;
        ped.fallback = false;
      }

      if (ped.mixer) {
        this.playPed(ped, ped.moving ? 'Walk' : 'Idle');
        ped.mixer.update(dt);
      } else {
        this.animatePed(ped, dt);
      }
    }
  }

  animatePed(ped, dt) {
    ped.phase += dt * (ped.moving ? 8 : 2);
    const sw = Math.sin(ped.phase);
    if (ped.rig) {
      if (ped.moving) {
        if (ped.armL) ped.armL.rotation.x = sw * 0.35;
        if (ped.armR) ped.armR.rotation.x = -sw * 0.35;
        if (ped.legL) ped.legL.rotation.x = -sw * 0.4;
        if (ped.legR) ped.legR.rotation.x = sw * 0.4;
        ped.rig.position.y = Math.abs(sw) * 0.02;
      } else {
        if (ped.armL) ped.armL.rotation.x *= 0.9;
        if (ped.armR) ped.armR.rotation.x *= 0.9;
        if (ped.legL) ped.legL.rotation.x *= 0.85;
        if (ped.legR) ped.legR.rotation.x *= 0.85;
        ped.rig.position.y = Math.sin(ped.phase) * 0.005;
      }
    }
  }
}
