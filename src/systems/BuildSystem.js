import * as THREE from 'three';
import {
  catalogItem,
  isShelfType,
  normalizeRotation,
  productAllowed,
  validatePlacement,
  shelfDataFromSpot,
  shelfPosition,
  nextFreeSpot
} from '../data/build.js';
import { maxSpots, PRODUCTS } from '../data/products.js';
import { createShelfMesh, disposeShelfMesh } from '../world/ShelfFactory.js';
import { createFixtureMesh } from '../world/FixtureFactory.js';
import { disposeObject3D } from '../utils/dispose.js';
import { rounded } from '../utils/math.js';

export default class BuildSystem {
  constructor(game) {
    this.game = game;
    this.enabled = false;
    this.catalogType = 'shelf';
    this.productId = 'milk'; // changed by the build bar's product picker
    this.rotation = 0;
    this.ghost = null;
    this.ghostValid = false;
    this.moveTarget = null; // { kind: 'fixture'|'shelf', id }
    this.selectionBox = null;
    this.selectionTarget = null;
    this._forward = new THREE.Vector3();
  }

  start() {
    this.enabled = true;
    this.game.setMode('playing'); // keep playing movement
    this.game.input?.touch?.setBuildMode?.(true);
    this.ensureGhost();
    this.updateGhost();
    this.game.ui?.buildUI?.show?.();
    // Do this last: a failed lock pauses and hides the bar again.
    this.game.input?.restoreLockOrPause?.();
  }

  stop() {
    this.enabled = false;
    this.game.input?.touch?.setBuildMode?.(false);
    this.removeGhost();
    this.moveTarget = null;
    this.removeSelection();
    this.game.ui?.buildUI?.hide?.();
    this.game.input?.restoreLockOrPause?.();
  }

  toggle() {
    if (this.enabled) this.stop();
    else this.start();
  }

  setCatalog(type) {
    if (!catalogItem(type)) return;
    this.catalogType = type;
    this.endMove();
    this.ensureGhost();
    this.updateGhost();
  }

  setProduct(pid) {
    if (!productAllowed(this.game, pid)) return;
    this.productId = pid;
  }

  rotate() {
    this.rotation = normalizeRotation(this.rotation + Math.PI / 2);
    this.updateGhost();
  }

  removeGhost() {
    if (!this.ghost) return;
    this.game.scene.remove(this.ghost);
    disposeObject3D(this.ghost);
    this.ghost = null;
  }

  ensureGhost() {
    this.removeGhost();
    const item = catalogItem(this.catalogType);
    if (!item) return;
    const g = new THREE.Group();
    // simple ghost mesh
    const color = isShelfType(this.catalogType) ? 0x6aa0ff : 0x9adf9a;
    const geo = new THREE.BoxGeometry(item.width, 0.6, item.depth);
    const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.45 });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.y = 0.3;
    g.add(mesh);
    g.visible = false;
    this.game.scene.add(g);
    this.ghost = g;
  }

  getWorldPositionFromPlayer() {
    const p = this.game.player.pos;
    const dir = this._forward.set(0, 0, -1).applyQuaternion(this.game.camera.quaternion);
    const dist = 2.2;
    return { x: p.x + dir.x * dist, z: p.z + dir.z * dist };
  }

  updateGhost() {
    if (!this.enabled || !this.ghost) return;
    const pos = this.getWorldPositionFromPlayer();
    const x = pos.x;
    const z = pos.z;
    this.ghost.position.set(x, 0, z);
    this.ghost.rotation.y = this.rotation;
    const res = this.validateAt(x, z, this.rotation);
    this.ghostValid = !!res.ok;
    const color = this.ghostValid ? 0x6bff8f : 0xff6b6b;
    this.ghost.traverse((o) => {
      if (o.isMesh && o.material) o.material.color.setHex(color);
    });
    this.ghost.visible = true;
  }

  syncUI() {
    this.game.ui?.buildUI?.syncSelection?.();
  }

  // A soft amber cage around the piece picked up for moving, so the player can
  // tell it apart from the placement ghost.
  ensureSelectionBox() {
    if (this.selectionBox) return this.selectionBox;
    const geo = new THREE.BoxGeometry(1, 1, 1);
    const box = new THREE.Group();
    box.add(
      new THREE.Mesh(
        geo,
        new THREE.MeshBasicMaterial({
          color: 0xffd76b,
          transparent: true,
          opacity: 0.14,
          depthWrite: false
        })
      ),
      new THREE.LineSegments(
        new THREE.EdgesGeometry(geo),
        new THREE.LineBasicMaterial({ color: 0xffe08a })
      )
    );
    box.visible = false;
    this.game.scene.add(box);
    this.selectionBox = box;
    return box;
  }

  markSelected(group) {
    if (!group) {
      this.clearSelected();
      return;
    }
    const bounds = new THREE.Box3().setFromObject(group);
    if (bounds.isEmpty()) {
      this.clearSelected();
      return;
    }
    const box = this.ensureSelectionBox();
    const size = bounds.getSize(new THREE.Vector3());
    box.position.copy(bounds.getCenter(new THREE.Vector3()));
    box.scale.set(size.x + 0.16, size.y + 0.16, size.z + 0.16);
    box.visible = true;
    this.selectionTarget = group;
  }

  clearSelected() {
    this.selectionTarget = null;
    if (this.selectionBox) this.selectionBox.visible = false;
  }

  removeSelection() {
    this.clearSelected();
    if (!this.selectionBox) return;
    this.game.scene.remove(this.selectionBox);
    disposeObject3D(this.selectionBox);
    this.selectionBox = null;
  }

  endMove() {
    this.moveTarget = null;
    this.clearSelected();
    this.syncUI();
  }

  // Nearest placed shelf or fixture to the build cursor (2.2m ahead).
  pickAtLook() {
    const pos = this.getWorldPositionFromPlayer();
    const near = (x, z) => Math.hypot(x - pos.x, z - pos.z) < 1.6;
    const fixture = (this.game.runtime.fixtures || []).find((f) => near(f.x, f.z));
    if (fixture) {
      return { kind: 'fixture', id: fixture.id, item: catalogItem(fixture.type), data: fixture };
    }
    const shelf = (this.game.runtime.shelves || []).find((s) => {
      const p = shelfPosition(s);
      return near(p.x, p.z);
    });
    if (!shelf) return null;
    const type = shelf.freezer ? 'freezer' : shelf.fridge ? 'fridge' : 'shelf';
    return { kind: 'shelf', id: shelf.spot, item: catalogItem(type), data: shelf };
  }

  // Pick up the furniture in front of the player so Place moves it instead of
  // buying a new one.
  startMove() {
    const target = this.pickAtLook();
    if (!target || !target.item) {
      this.game.ui.toast('Aim at a shelf or fixture to move it');
      return;
    }
    this.moveTarget = { kind: target.kind, id: target.id };
    this.catalogType = target.item.id;
    this.rotation =
      (target.kind === 'shelf' ? shelfPosition(target.data).rot : target.data.rot) || 0;
    this.ensureGhost();
    this.updateGhost();
    this.markSelected(target.data.group);
    this.syncUI();
    this.game.ui.toast('Moving — aim and press Place (E)');
  }

  disposePlaced(group, shelf = false) {
    if (!group) return;
    if (this.selectionTarget === group) this.clearSelected();
    this.game.scene.remove(group);
    this.game.world.untagInteract?.(group);
    if (shelf) disposeShelfMesh(group);
    else disposeObject3D(group);
  }

  validateAt(x, z, rot) {
    const item = catalogItem(this.catalogType);
    if (!item) return { ok: false, reason: 'Unknown item' };
    const game = this.game;
    const level = game.state.level || 1;
    const colliders = game.world.storeColliders || game.world.colliders || [];
    return validatePlacement({
      type: this.catalogType,
      x,
      z,
      rot,
      level,
      colliders,
      shelves: game.runtime.shelves,
      fixtures: game.runtime.fixtures || [],
      ignore: this.moveTarget
    });
  }

  confirmPlace() {
    if (!this.enabled) return;
    const item = catalogItem(this.catalogType);
    if (!item) return;
    const pos = this.getWorldPositionFromPlayer();
    const res = this.validateAt(pos.x, pos.z, this.rotation);
    if (!res.ok) {
      this.game.ui.toast(res.reason || 'Cannot place here');
      return;
    }
    const cost = item.cost || 0;

    if (this.moveTarget) {
      // Moving existing furniture: update the runtime entry and its saved
      // copy, then rebuild the visual and the colliders at the new spot.
      const target = this.moveTarget;
      let placed = false;
      if (target.kind === 'fixture') {
        const fx = (this.game.runtime.fixtures || []).find((f) => f.id === target.id);
        if (fx) {
          fx.x = res.x;
          fx.z = res.z;
          fx.rot = res.rot;
          this.disposePlaced(fx.group);
          fx.group = createFixtureMesh(fx);
          this.game.scene.add(fx.group);
          const saved = (this.game.state.fixtures || []).find((f) => f.id === fx.id);
          if (saved) Object.assign(saved, { x: fx.x, z: fx.z, rot: fx.rot });
          placed = true;
        }
      } else {
        const sh = this.game.runtime.shelves.find((s) => s.spot === target.id);
        if (sh) {
          sh.x = res.x;
          sh.z = res.z;
          sh.rot = res.rot;
          this.disposePlaced(sh.group, true);
          sh.group = createShelfMesh(sh, this.game);
          const saved = this.game.state.shelves.find((s) => s.spot === sh.spot);
          if (saved) Object.assign(saved, { x: sh.x, z: sh.z, rot: sh.rot });
          placed = true;
        }
      }
      this.endMove();
      this.game.world.rebuildColliders?.();
      this.game.syncShelfData?.();
      this.game.save(true, true);
      this.game.ui.toast(placed ? 'Moved' : 'That item is gone');
      this.updateGhost();
      return;
    }

    // Placing new: validate the product and destination before spending money.
    const shelfType = isShelfType(this.catalogType);
    let shelfSpot = -1;
    if (shelfType) {
      if (!productAllowed(this.game, this.productId)) {
        this.game.ui.toast('That product is not licensed');
        return;
      }
      if (this.game.state.shelves.length >= maxSpots(this.game.state.level || 1)) {
        this.game.ui.toast('Expand your store first');
        return;
      }
      shelfSpot = nextFreeSpot(this.game.state.level || 1, this.game.runtime.shelves);
      if (shelfSpot < 0) {
        this.game.ui.toast('No free shelf spots');
        return;
      }
    }
    if (cost > 0 && this.game.state.cash < cost) {
      this.game.ui.toast('Not enough cash');
      return;
    }
    if (cost > 0) {
      this.game.state.cash = rounded(this.game.state.cash - cost);
      if (!this.game.runtime.stats)
        this.game.runtime.stats = {
          revenue: 0,
          stockCost: 0,
          happy: 0,
          angry: 0,
          recycle: 0,
          buildCost: 0
        };
      this.game.runtime.stats.buildCost = (this.game.runtime.stats.buildCost || 0) + cost;
    }

    if (shelfType) {
      const fridge = !!item.fridge;
      const freezer = !!item.freezer;
      const shd = shelfDataFromSpot(shelfSpot, this.productId, { fridge, freezer });
      shd.x = res.x;
      shd.z = res.z;
      shd.rot = res.rot;
      this.game.state.shelves.push({ ...shd });
      const group = createShelfMesh(shd, this.game);
      this.game.runtime.shelves.push({ ...shd, group });
      this.game.world.rebuildColliders?.();
    } else {
      // fixture
      const id = `${this.catalogType}_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
      const fx = { id, type: this.catalogType, x: res.x, z: res.z, rot: res.rot };
      if (!this.game.state.fixtures) this.game.state.fixtures = [];
      this.game.state.fixtures.push({ ...fx });
      if (!this.game.runtime.fixtures) this.game.runtime.fixtures = [];
      const mesh = createFixtureMesh(fx);
      this.game.scene.add(mesh);
      this.game.runtime.fixtures.push({ ...fx, group: mesh });
      this.game.world.rebuildColliders?.();
    }

    this.game.ui.updateHUD?.();
    this.game.save(true, true);
    this.game.ui.toast('Placed');
    this.updateGhost();
  }

  cancel() {
    this.endMove();
    this.game.ui.toast('Cancelled');
    this.updateGhost();
  }

  // Sell back the shelf or fixture in front of the player for half its price.
  // Stock still on a shelf is bought back at half its wholesale value rather
  // than vanishing when the shelf is scrapped.
  removeAtLook() {
    const target = this.pickAtLook();
    if (!target || !target.item) {
      this.game.ui.toast('Aim at a shelf or fixture to remove it');
      return;
    }
    const stocked = target.kind === 'shelf' ? Math.max(0, target.data.stock || 0) : 0;
    const wholesale = target.kind === 'shelf' ? (PRODUCTS[target.data.productId]?.price ?? 0) : 0;
    const stockRefund = Math.floor(stocked * wholesale * 0.5);
    const refund = Math.floor((target.item.cost || 0) * 0.5) + stockRefund;
    this.game.state.cash = rounded(this.game.state.cash + refund);
    this.endMove();
    if (target.kind === 'shelf') {
      const sh = this.game.runtime.shelves.find((s) => s.spot === target.id);
      this.game.state.shelves = this.game.state.shelves.filter((s) => s.spot !== target.id);
      this.game.runtime.shelves = this.game.runtime.shelves.filter((s) => s.spot !== target.id);
      this.disposePlaced(sh?.group, true);
    } else {
      const fx = (this.game.runtime.fixtures || []).find((f) => f.id === target.id);
      this.game.state.fixtures = (this.game.state.fixtures || []).filter((f) => f.id !== target.id);
      this.game.runtime.fixtures = (this.game.runtime.fixtures || []).filter(
        (f) => f.id !== target.id
      );
      this.disposePlaced(fx?.group);
    }
    this.game.world.rebuildColliders?.();
    this.game.syncShelfData?.();
    this.game.ui.updateHUD?.();
    this.game.save(true, true);
    this.game.ui.toast(
      stockRefund > 0
        ? `Removed (+$${refund}, incl. $${stockRefund} stock)`
        : `Removed (+$${refund})`
    );
    this.updateGhost();
  }

  update() {
    if (!this.enabled) return;
    this.updateGhost();
  }
}
