import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import BuildSystem from '../src/systems/BuildSystem.js';
import { createFixtureMesh } from '../src/world/FixtureFactory.js';

function fakeGame() {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera();
  camera.rotation.order = 'YXZ';
  camera.position.set(0, 1.7, 0);
  const interactables = [];
  const game = {
    scene,
    camera,
    player: { pos: new THREE.Vector3(0, 0, 0), yaw: 0 },
    state: { level: 1, cash: 500, shelves: [], fixtures: [], licenses: [] },
    runtime: { shelves: [], fixtures: [] },
    rebuilt: 0,
    toasts: [],
    interactables,
    ui: {
      toast: (msg) => game.toasts.push(msg),
      updateHUD() {},
      buildUI: { syncSelection() {} }
    },
    world: {
      storeColliders: [],
      tagInteract(obj, type, prompt) {
        obj.userData.interact = { type, prompt };
        interactables.push(obj);
      },
      untagInteract(obj) {
        const i = interactables.indexOf(obj);
        if (i >= 0) interactables.splice(i, 1);
      },
      rebuildColliders() {
        game.rebuilt++;
      }
    },
    setMode() {},
    save() {},
    syncShelfData() {}
  };
  game.build = new BuildSystem(game);
  game.build.enabled = true;
  return game;
}

test('startMove picks up the fixture in front and Place moves it', () => {
  const game = fakeGame();
  const fx = { id: 'plant_1', type: 'plant', x: 0, z: -2.2, rot: 0 };
  fx.group = createFixtureMesh(fx);
  game.scene.add(fx.group);
  game.runtime.fixtures.push({ ...fx });
  game.state.fixtures.push({ id: fx.id, type: fx.type, x: fx.x, z: fx.z, rot: fx.rot });

  const bs = game.build;
  bs.startMove();
  assert.deepEqual(bs.moveTarget, { kind: 'fixture', id: 'plant_1' });
  assert.equal(game.runtime.fixtures[0].group, fx.group, 'nothing moved yet');

  // Look along -X so the new spot is (-2.2, 0).
  game.camera.rotation.y = Math.PI / 2;
  bs.confirmPlace();

  assert.equal(bs.moveTarget, null);
  assert.equal(game.state.fixtures[0].x, -2, 'saved position follows the move');
  assert.ok(Math.abs(game.state.fixtures[0].z) < 1e-9, 'z snapped to 0');
  assert.equal(game.runtime.fixtures[0].x, -2);
  assert.equal(game.runtime.fixtures[0].group.position.x, -2, 'mesh rebuilt at the new spot');
  assert.ok(game.rebuilt > 0, 'colliders rebuilt');
  assert.equal(fx.group.parent, null, 'old mesh detached');
});

test('startMove targets a shelf, keeps its type and highlights it', () => {
  const game = fakeGame();
  const group = new THREE.Group();
  group.position.set(0, 0, -2.2);
  group.add(new THREE.Mesh(new THREE.BoxGeometry(2.2, 2.4, 1), new THREE.MeshBasicMaterial()));
  game.scene.add(group);
  let synced = 0;
  game.ui.buildUI.syncSelection = () => synced++;
  game.runtime.shelves.push({
    spot: 0,
    productId: 'milk',
    stock: 3,
    capacity: 12,
    x: 0,
    z: -2.2,
    rot: Math.PI / 2,
    freezer: true,
    group
  });
  const bs = game.build;
  bs.startMove();
  assert.deepEqual(bs.moveTarget, { kind: 'shelf', id: 0 });
  assert.equal(bs.catalogType, 'freezer');
  assert.equal(bs.rotation, Math.PI / 2);
  assert.equal(bs.ghost.visible, true);
  assert.equal(bs.selectionTarget, group);
  assert.equal(bs.selectionBox.visible, true);
  assert.ok(Math.abs(bs.selectionBox.position.z + 2.2) < 1e-9, 'marker sits on the shelf');
  assert.ok(synced > 0, 'build bar synced with the picked type');
});

test('changing the build type cancels a pending move and clears the highlight', () => {
  const game = fakeGame();
  const fx = { id: 'plant_1', type: 'plant', x: 0, z: -2.2, rot: 0 };
  fx.group = createFixtureMesh(fx);
  game.scene.add(fx.group);
  game.runtime.fixtures.push({ ...fx });
  game.state.fixtures.push({ id: fx.id, type: fx.type, x: fx.x, z: fx.z, rot: fx.rot });

  game.build.startMove();
  assert.ok(game.build.moveTarget);
  assert.equal(game.build.selectionBox.visible, true);

  game.build.setCatalog('bench');

  assert.equal(game.build.moveTarget, null);
  assert.equal(game.build.selectionBox.visible, false);
  assert.equal(game.build.catalogType, 'bench');
});

test('removeAtLook sells back a shelf, frees its spot and untags it', () => {
  const game = fakeGame();
  const shelf = {
    spot: 0,
    productId: 'milk',
    stock: 4,
    capacity: 12,
    x: 0,
    z: -2.2,
    rot: 0,
    fridge: false,
    freezer: false
  };
  const group = new THREE.Group();
  group.position.set(shelf.x, 0, shelf.z);
  group.add(new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshBasicMaterial()));
  game.scene.add(group);
  game.world.tagInteract(group, 'shelf', 'milk shelf');
  game.runtime.shelves.push({ ...shelf, group });
  game.state.shelves.push({ ...shelf });

  game.build.removeAtLook();

  assert.equal(game.state.shelves.length, 0);
  assert.equal(game.runtime.shelves.length, 0);
  assert.equal(
    game.state.cash,
    580,
    'half of the $150 shelf price plus half of the four milk units refunded'
  );
  assert.match(game.toasts.at(-1), /incl\. \$5 stock/, 'the toast explains the stock refund');
  assert.equal(game.interactables.length, 0, 'shelf no longer interactable');
  assert.equal(group.parent, null, 'shelf mesh detached');
  assert.ok(game.rebuilt > 0);
});

test('entering and leaving build restore the desktop mouse lock', () => {
  const game = fakeGame();
  let locked = 0;
  game.input = { restoreLockOrPause: () => locked++ };

  game.build.start();
  assert.equal(locked, 1, 'entering build re-checks the mouse lock');

  game.build.stop();
  assert.equal(locked, 2, 'leaving build re-checks the mouse lock');
});

test('build mode makes the touch action contextual and restores it on stop', () => {
  const game = fakeGame();
  const modes = [];
  game.input = { touch: { setBuildMode: (value) => modes.push(value) } };

  game.build.start();
  assert.deepEqual(modes, [true]);

  game.build.stop();
  assert.deepEqual(modes, [true, false]);
});

test('stop removes the ghost, selection marker and build mode', () => {
  const game = fakeGame();
  const fx = { id: 'plant_1', type: 'plant', x: 0, z: -2.2, rot: 0 };
  fx.group = createFixtureMesh(fx);
  game.scene.add(fx.group);
  game.runtime.fixtures.push({ ...fx });
  game.build.start();
  game.build.startMove();
  assert.ok(game.build.ghost, 'ghost created');
  assert.ok(game.build.selectionBox, 'selection marker created');
  assert.equal(game.build.enabled, true);
  game.build.stop();
  assert.equal(game.build.enabled, false);
  assert.equal(game.build.ghost, null);
  assert.equal(game.build.selectionBox, null);
});

test('removeAtLook explains when nothing is in reach', () => {
  const game = fakeGame();
  game.player.pos.set(6, 0, 6);
  game.camera.rotation.y = Math.PI;
  game.build.removeAtLook();
  assert.match(game.toasts.at(-1), /Aim at a shelf or fixture/);
});
