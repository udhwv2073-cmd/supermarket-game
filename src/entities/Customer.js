import * as THREE from 'three';
import { MAX_CUSTOMERS, CATEGORIES, PRODUCTS } from '../data/products.js';
import { pick, rand, rounded } from '../utils/math.js';
import { emojiTexture } from '../utils/textures.js';
import { currentSellPrice } from '../systems/Pricing.js';
import { onHappyCustomer, onAngryCustomer } from '../systems/Reputation.js';
import { cloneCharacter, loadModel } from '../utils/AssetLoader.js';
import { refreshShelfVisual } from '../world/ShelfFactory.js';
import { CITY_PEDESTRIAN_CHARACTERS, pickCustomerCharacter } from '../data/customers.js';
import { makeCarryProp, releaseCarryProp } from './CustomerProps.js';

// Clips that play once and clamp; everything else loops.
const ONE_SHOT = new Set([
  'PickItem',
  'PlaceItem',
  'Checkout',
  'Greet',
  'Stop',
  'TurnLeft',
  'TurnRight',
  'ReachHigh'
]);

const WALK_SPEED = (character) =>
  character.speed * (character.carry === 'cart' ? 0.82 : character.carry === 'basket' ? 0.92 : 1);

function makeEmoji(height) {
  const s = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: emojiTexture('😊'),
      transparent: true,
      depthTest: false
    })
  );
  s.scale.set(0.7, 0.7, 1);
  s.position.y = height + 0.55;
  s.visible = false;
  return s;
}

export function showEmoji(c, emoji, sec = 2.2) {
  c.emoji.material.map.dispose();
  c.emoji.material.map = emojiTexture(emoji);
  c.emoji.material.needsUpdate = true;
  c.emoji.visible = true;
  c.emojiTimer = sec;
}

function setupAnimations(c, model, clips) {
  c.mixer = new THREE.AnimationMixer(model);
  c.actions = {};
  for (const clip of clips || []) {
    try {
      const action = c.mixer.clipAction(clip);
      if (ONE_SHOT.has(clip.name)) {
        action.setLoop(THREE.LoopOnce, 1);
        action.clampWhenFinished = true;
      } else {
        action.setLoop(THREE.LoopRepeat, Infinity);
      }
      c.actions[clip.name] = action;
    } catch (err) {
      console.warn('[Customer] clipAction failed', clip.name, err);
    }
  }
  c.currentAnim = null;
  c.animLock = 0;
  c.lockedAnim = null;
  playAnim(c, 'Idle', 0);
}

export function playAnim(c, name, fade = 0.22, lock = 0) {
  if (!c.actions) return;
  if (c.animLock > 0 && name !== c.lockedAnim) return;
  const next = c.actions[name];
  if (!next) return;
  if (c.currentAnim === name && c.animLock <= 0) return;
  const prev = c.currentAnim ? c.actions[c.currentAnim] : null;
  next.reset();
  next.setEffectiveTimeScale(1);
  next.setEffectiveWeight(1);
  next.fadeIn(fade);
  next.play();
  if (prev && prev !== next) prev.fadeOut(fade);
  c.currentAnim = name;
  if (lock > 0) {
    c.animLock = lock;
    c.lockedAnim = name;
  }
}

function desiredAnim(c) {
  if (c.animLock > 0) return c.lockedAnim;
  if (c.moving) {
    if (c.character.carry === 'cart') return 'WalkCart';
    if (c.character.carry === 'basket') return 'WalkBasket';
    return 'Walk';
  }
  if (c.state === 'wait' || c.state === 'queue') return 'Wait';
  if (c.state === 'browse' && c.lookTimer > 0) return 'LookAround';
  if (c.character.carry === 'cart' && c.actions.IdleCart) return 'IdleCart';
  if (c.character.carry === 'basket' && c.actions.IdleBasket) return 'IdleBasket';
  return 'Idle';
}

function updateAnim(c, dt) {
  if (c.mixer) c.mixer.update(dt);
  if (c.animLock > 0) {
    c.animLock -= dt;
    if (c.animLock <= 0) c.lockedAnim = null;
    return;
  }
  playAnim(c, desiredAnim(c));
}

function spawnSpot(game, pending) {
  for (let attempt = 0; attempt < 12; attempt += 1) {
    const x = rand(-3.4, 3.4);
    const z = 15.2 + rand(0, 1.8);
    const clear =
      game.runtime.customers.every(
        (c) => Math.hypot(c.group.position.x - x, c.group.position.z - z) > 1.05
      ) && pending.every((p) => Math.hypot(p[0] - x, p[1] - z) > 1.05);
    if (clear) return [x, z];
  }
  return null;
}

/** Prefer a character that is not already in the store or still loading. */
function pickFreshCharacter(game, pending) {
  const present = new Set([...game.runtime.customers.map((c) => c.character.id), ...pending]);
  for (let attempt = 0; attempt < 6; attempt += 1) {
    const character = pickCustomerCharacter();
    if (!present.has(character.id)) return character;
  }
  return pickCustomerCharacter();
}

export function spawnCustomer(game) {
  const pending = (game.runtime.pendingSpawns ||= []);
  const pendingChars = (game.runtime.pendingCharacters ||= []);
  if (game.runtime.customers.length + pending.length >= MAX_CUSTOMERS) return;
  const spot = spawnSpot(game, pending);
  if (!spot) return;
  pending.push(spot);

  const character = pickFreshCharacter(game, pendingChars);
  pendingChars.push(character.id);
  const token = game.runtime.spawnToken || 0;
  const release = () => {
    const index = pending.indexOf(spot);
    if (index >= 0) pending.splice(index, 1);
    const charIndex = pendingChars.indexOf(character.id);
    if (charIndex >= 0) pendingChars.splice(charIndex, 1);
  };
  cloneCharacter(character.file)
    .then((model) => {
      release();
      // The store may have closed (or been reset) while the GLB was loading.
      if (!model || token !== (game.runtime.spawnToken || 0)) return;
      if (game.runtime.customers.length >= MAX_CUSTOMERS) return;

      const emoji = makeEmoji(character.height);
      model.add(emoji);
      model.position.set(spot[0], 0, spot[1]);
      model.scale.setScalar(1);
      model.rotation.y = Math.PI;
      game.scene.add(model);

      const prop = makeCarryProp(character.carry, character.height);
      if (prop) model.add(prop);

      const c = {
        group: model,
        character,
        height: character.height,
        carry: character.carry,
        prop,
        mixer: null,
        actions: null,
        currentAnim: null,
        animLock: 0,
        lockedAnim: null,
        lookTimer: 0,
        emoji,
        state: 'enter',
        timer: 0,
        basket: [],
        queueIndex: -1,
        emojiTimer: 0,
        visits: 0,
        moving: false,
        walkPhase: rand(0, 6),
        pref: pick(CATEGORIES),
        patience: rand(22, 40),
        prefFound: false,
        exitTarget: { x: rand(-1.6, 1.6), z: 16.5 }
      };
      const clips = model.userData?.animations || [];
      setupAnimations(c, model, clips);
      game.runtime.customers.push(c);
    })
    .catch((err) => {
      release();
      console.warn('[Customer] spawn failed', err);
    });
}

export const basketTotal = (game, c) =>
  rounded(c.basket.reduce((t, pid) => t + currentSellPrice(game, pid), 0));

function removeCustomer(game, c, index) {
  game.scene.remove(c.group);
  if (c.mixer) c.mixer.stopAllAction();
  if (c.emoji?.material) {
    c.emoji.material.map?.dispose();
    c.emoji.material.dispose();
  }
  releaseCarryProp(c.prop);
  game.runtime.customers.splice(index, 1);
}

export function clearCustomers(game) {
  game.runtime.spawnToken = (game.runtime.spawnToken || 0) + 1;
  game.runtime.pendingSpawns = [];
  game.runtime.pendingCharacters = [];
  for (const c of game.runtime.customers) {
    game.scene.remove(c.group);
    if (c.mixer) c.mixer.stopAllAction();
    if (c.emoji?.material) {
      c.emoji.material.map?.dispose();
      c.emoji.material.dispose();
    }
    releaseCarryProp(c.prop);
  }
  game.runtime.customers = [];
}

export function reindexQueue(game) {
  let n = 0;
  for (const c of game.runtime.customers) {
    if (c.state === 'queue' || c.state === 'wait') c.queueIndex = n++;
  }
}

export function waitingCustomer(game) {
  const w = game.runtime.customers.filter((c) => c.state === 'wait' && c.queueIndex === 0);
  return w.length ? w[0] : null;
}

export function doAutoCheckout(game, c) {
  const total = basketTotal(game, c);
  game.state.cash = rounded(game.state.cash + total);
  game.state.lifetimeRevenue = rounded(game.state.lifetimeRevenue + total);
  game.runtime.stats.revenue += total;
  game.runtime.stats.happy++;
  onHappyCustomer(game);
  showEmoji(c, '😊', 2);
  c.state = 'happy';
  game.audio.play('success');
  game.ui.updateHUD();
  game.save();
}

/** Begin loading the six models shared with the city pedestrians. */
export function warmCustomerModels() {
  return Promise.all(CITY_PEDESTRIAN_CHARACTERS.map((c) => loadModel(c.file))).catch((err) => {
    console.warn('[Customer] warm-up skipped', err);
  });
}

export function updateCustomers(game, dt) {
  const { runtime, state } = game;
  reindexQueue(game);
  for (let i = runtime.customers.length - 1; i >= 0; i--) {
    const c = runtime.customers[i];
    c.moving = false;
    if (c.emojiTimer > 0) {
      c.emojiTimer -= dt;
      if (c.emojiTimer <= 0) c.emoji.visible = false;
    }
    if (c.lookTimer > 0) c.lookTimer -= dt;

    if (c.state === 'enter') {
      if (moveToward(c, pick([-4, -2, 0, 2, 4]), 7, WALK_SPEED(c.character), dt)) {
        c.state = 'browse';
        c.timer = 0;
        c.lookTimer = rand(2.5, 5);
      }
    } else if (c.state === 'browse') {
      c.timer -= dt;
      if (c.timer <= 0) {
        const available = runtime.shelves.filter((s) => s.stock > 0);
        if (available.length === 0) {
          showEmoji(c, '❓', 2.5);
          runtime.stats.angry++;
          onAngryCustomer(game);
          c.state = 'angry';
          game.audio.play('error');
        } else if (c.visits >= 3) {
          c.state = 'queue';
          c.timer = 0;
          if (basketTotal(game, c) > 15) showEmoji(c, '😠', 3);
        } else {
          const prefAvail = available.filter((s) => PRODUCTS[s.productId].category === c.pref);
          const sh = pick(prefAvail.length ? prefAvail : available);
          const [sx, sz] = game.spot(sh.spot);
          c.browseTarget = [sx, sz + 1.3, sh];
          c.state = 'toShelf';
        }
      }
    } else if (c.state === 'toShelf') {
      const t = c.browseTarget;
      if (moveToward(c, t[0], t[1], WALK_SPEED(c.character), dt)) {
        const sh = runtime.shelves.find((s) => s === t[2]);
        if (sh && sh.stock > 0) {
          sh.stock--;
          refreshShelfVisual(sh.spot, sh.group, sh, game);
          game.syncShelfData();
          c.basket.push(sh.productId);
          if (PRODUCTS[sh.productId].category === c.pref) c.prefFound = true;
          game.audio.play('scan');
          c.visits++;
          playAnim(c, 'PickItem', 0.12, 1.35);
        }
        c.state = 'browse';
        c.timer = rand(0.8, 1.6);
        c.lookTimer = rand(4, 9);
      }
    } else if (c.state === 'queue') {
      if (c.queueIndex < 0)
        c.queueIndex = runtime.customers.filter((x) => x.state === 'queue' && x !== c).length;
      if (moveToward(c, 7, 6.2 - c.queueIndex * 1.1, WALK_SPEED(c.character) * 0.95, dt)) {
        c.state = 'wait';
        c.timer = 0;
        if (c.queueIndex === 0) playAnim(c, 'Checkout', 0.2, 1.2);
      }
    } else if (c.state === 'wait') {
      c.patience -= dt;
      if (c.patience <= 0) {
        showEmoji(c, '😡', 2.5);
        runtime.stats.angry++;
        onAngryCustomer(game);
        game.audio.play('error');
        c.state = 'angry';
        reindexQueue(game);
        continue;
      }
      if (state.staff.cashier && !runtime.checkoutCustomer && c.queueIndex === 0) {
        c.timer += dt;
        if (c.timer > 1.4) doAutoCheckout(game, c);
      }
    } else if (c.state === 'happy' || c.state === 'angry') {
      const exit = c.exitTarget || { x: 0, z: 16.5 };
      if (moveToward(c, exit.x, exit.z, WALK_SPEED(c.character) * 1.35, dt)) {
        removeCustomer(game, c, i);
        reindexQueue(game);
        continue;
      }
    }
    updateAnim(c, dt);
  }
}

function moveToward(c, tx, tz, speed, dt) {
  const g = c.group;
  const dx = tx - g.position.x;
  const dz = tz - g.position.z;
  const d = Math.hypot(dx, dz);
  if (d < 0.15) {
    c.moving = false;
    return true;
  }
  const step = Math.min(d, speed * dt);
  g.position.x += (dx / d) * step;
  g.position.z += (dz / d) * step;
  const targetYaw = Math.atan2(dx, dz);
  let delta = targetYaw - g.rotation.y;
  while (delta > Math.PI) delta -= Math.PI * 2;
  while (delta < -Math.PI) delta += Math.PI * 2;
  const turn = Math.min(1, dt * 9);
  g.rotation.y += delta * turn;
  c.moving = true;
  return false;
}
