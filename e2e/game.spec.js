import { test, expect } from '@playwright/test';

async function startGame(page) {
  // Headless software WebGL is very slow. Simulate a hidden tab so the game
  // skips its render loop while DOM/state interactions stay testable.
  await page.addInitScript(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
  });
  await page.goto('/?e2e=1');
  await page.locator('#startBtn').click();
  await expect(page.locator('#startOverlay')).toBeHidden();
  await expect(page.locator('#loading')).toBeHidden();
}

test('boots into the game without a fatal graphics error', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));

  await startGame(page);

  await expect(page.locator('#fatalOverlay')).toBeHidden();
  await expect(page.locator('#hud')).toBeVisible();
  await expect(page.locator('#cashText')).toBeVisible();
  expect(errors).toEqual([]);
});

test('terminal renders stock, analytics and achievements tabs', async ({ page }) => {
  await startGame(page);
  await page.evaluate(() => window.freshMart.ui.openTerminal());

  await expect(page.locator('#terminalOverlay')).toBeVisible();
  await expect(page.locator('#tabContent')).toContainText('Wholesale boxes');

  await page.locator('[data-tab="analytics"]').click();
  await expect(page.locator('#tabContent')).toContainText('Store Analytics');

  await page.locator('[data-tab="achievements"]').click();
  await expect(page.locator('#tabContent')).toContainText('Achievements');
  await expect(page.locator('#tabContent')).toContainText('unlocked');

  await page.locator('#termClose').click();
  await expect(page.locator('#terminalOverlay')).toBeHidden();
});

test('ordering a box spends cash and spawns a delivery', async ({ page }) => {
  await startGame(page);
  await page.evaluate(() => window.freshMart.ui.openTerminal());

  const before = await page.evaluate(() => ({
    cash: window.freshMart.state.cash,
    boxes: window.freshMart.runtime.boxes.length
  }));
  await page.locator('#tabContent [data-buy]').first().click();
  const after = await page.evaluate(() => ({
    cash: window.freshMart.state.cash,
    boxes: window.freshMart.runtime.boxes.length
  }));

  expect(after.cash).toBeLessThan(before.cash);
  expect(after.boxes).toBeGreaterThan(before.boxes);
});

test('cash and card checkout pay the correct total and reject wrong amounts', async ({ page }) => {
  await startGame(page);

  const cash = await page.evaluate(() => {
    const g = window.freshMart;
    g.ui.hideAll();
    g.mode = 'playing';
    const customer = {
      basket: ['milk', 'bread'],
      state: 'queue',
      queueIndex: 0,
      character: { height: 1.7 },
      emoji: { material: { map: { dispose() {} } } }
    };
    g.runtime.customers.push(customer);
    const before = g.state.cash;
    const revenueBefore = g.state.lifetimeRevenue;
    const random = Math.random;
    Math.random = () => 0.9;
    g.checkout.open(customer);
    Math.random = random;

    const body = document.querySelector('#checkoutBody');
    const total = Number(body.querySelector('.stat b').textContent.replace('$', ''));
    const change = parseFloat(
      body.textContent
        .split('Give exact change:')[1]
        .split('Change given')[0]
        .replace(/[^0-9.]/g, '')
    );
    body.querySelector('.den[data-v="100"]').click();
    body.querySelector('#confirmCash').click();
    const wrong = { cash: g.state.cash, mode: g.mode };
    body.querySelector('#clearChange').click();

    let cents = Math.round(change * 100);
    for (const d of [100, 50, 20, 10, 5, 2, 1, 0.5, 0.25, 0.1, 0.05, 0.01]) {
      const dc = Math.round(d * 100);
      while (cents >= dc) {
        body.querySelector(`.den[data-v="${d}"]`).click();
        cents -= dc;
      }
    }
    body.querySelector('#confirmCash').click();
    return {
      before,
      revenueBefore,
      total,
      change,
      wrong,
      leftovers: cents,
      after: g.state.cash,
      revenueAfter: g.state.lifetimeRevenue,
      state: customer.state,
      mode: g.mode
    };
  });

  expect(cash.total).toBeGreaterThan(0);
  expect(cash.wrong.cash).toBe(cash.before);
  expect(cash.wrong.mode).toBe('modal');
  expect(cash.leftovers).toBe(0);
  expect(cash.after).toBeCloseTo(cash.before + cash.total, 2);
  expect(cash.revenueAfter).toBeCloseTo(cash.revenueBefore + cash.total, 2);
  expect(cash.state).toBe('happy');
  expect(cash.mode).toBe('playing');

  const card = await page.evaluate(() => {
    const g = window.freshMart;
    const customer = {
      basket: ['milk'],
      state: 'queue',
      queueIndex: 0,
      character: { height: 1.7 },
      emoji: { material: { map: { dispose() {} } } }
    };
    g.runtime.customers.push(customer);
    const before = g.state.cash;
    const revenueBefore = g.state.lifetimeRevenue;
    const random = Math.random;
    Math.random = () => 0.1;
    g.checkout.open(customer);
    Math.random = random;

    const body = document.querySelector('#checkoutBody');
    const total = Number(body.querySelector('.stat b').textContent.replace('$', ''));
    body.querySelector('#cardInput').value = String(total + 1);
    body.querySelector('#confirmCard').click();
    const wrong = { cash: g.state.cash, mode: g.mode };
    body.querySelector('#cardInput').value = total.toFixed(2);
    body.querySelector('#confirmCard').click();
    return {
      before,
      revenueBefore,
      total,
      wrong,
      after: g.state.cash,
      revenueAfter: g.state.lifetimeRevenue,
      state: customer.state
    };
  });

  expect(card.wrong.cash).toBe(card.before);
  expect(card.wrong.mode).toBe('modal');
  expect(card.after).toBeCloseTo(card.before + card.total, 2);
  expect(card.revenueAfter).toBeCloseTo(card.revenueBefore + card.total, 2);
  expect(card.state).toBe('happy');
});

test('placing a shelf survives saving and reloading the page', async ({ page }) => {
  await startGame(page);

  const placed = await page.evaluate(() => {
    const g = window.freshMart;
    g.ui.hideAll();
    g.mode = 'playing';
    g.player.setView('first');
    const build = g.buildSystem;
    build.enabled = true;
    build.setCatalog('shelf');
    build.setProduct('milk');
    build.rotation = 0;
    const before = g.state.shelves.length;

    let spot = null;
    for (const [x, z] of [
      [0, 0],
      [3, 0],
      [-3, 0],
      [0, -3],
      [3, -3],
      [-3, -3],
      [0, 3]
    ]) {
      g.player.pos.set(x, 1.7, z + 2.2);
      g.player.yaw = 0;
      g.player.pitch = 0;
      g.player.updateCamera(1.7);
      if (build.validateAt(x, z, 0).ok) {
        spot = [x, z];
        break;
      }
    }
    if (!spot) return { ok: false };
    build.confirmPlace();
    g.save(true, true);
    return { ok: true, before, after: g.state.shelves.length, shelf: g.state.shelves.at(-1) };
  });

  expect(placed.ok).toBe(true);
  expect(placed.after).toBe(placed.before + 1);
  expect(placed.shelf.productId).toBe('milk');

  await page.reload();
  const loaded = await page.evaluate(() => {
    const g = window.freshMart;
    return { shelves: g.state.shelves, runtime: g.runtime.shelves.length };
  });
  expect(loaded.shelves).toHaveLength(placed.after);
  expect(loaded.shelves.at(-1)).toMatchObject({
    productId: 'milk',
    x: placed.shelf.x,
    z: placed.shelf.z,
    rot: placed.shelf.rot
  });
  expect(loaded.runtime).toBe(placed.after);
});

test('every neighbouring business opens its counter with working offers', async ({ page }) => {
  await startGame(page);

  const shops = await page.evaluate(() => {
    const g = window.freshMart;
    g.ui.hideAll();
    g.mode = 'playing';
    g.player.setView('first');
    const results = [];
    for (const shop of g.city.shopWorld.shops.values()) {
      const business = shop.business;
      g.scene.updateMatrixWorld(true);
      g.player.pos.set(business.entrance.x, 1.7, business.counter.z - 1.5);
      g.player.yaw = Math.PI;
      g.player.pitch = -0.4;
      g.player.updateCamera(1.7);
      g.onPrimaryAction();
      const ui = g.ui.shopUI;
      results.push({
        id: business.id,
        open: ui.isOpen(),
        title: ui.el?.querySelector('#shopTitle')?.textContent,
        offers: ui.el?.querySelectorAll('[data-offer]').length ?? 0
      });
      ui.hide?.();
    }
    return results;
  });

  expect(shops.map((s) => s.id).sort()).toEqual([
    'bakery',
    'cafe',
    'clothing',
    'electronics',
    'pharmacy'
  ]);
  for (const shop of shops) {
    expect(shop.open, `${shop.id} counter should open`).toBe(true);
    expect(shop.title?.length, `${shop.id} should render its name`).toBeGreaterThan(2);
    expect(shop.offers, `${shop.id} should list offers`).toBeGreaterThan(1);
  }
});

test('closing the day shows the report and advances to the next day', async ({ page }) => {
  await startGame(page);
  const day = await page.evaluate(() => window.freshMart.state.day);

  await page.evaluate(() => window.freshMart.closeStore());
  await expect(page.locator('#summaryOverlay')).toBeVisible();
  await expect(page.locator('#summaryBody')).toContainText('Total Revenue');

  await page.locator('#nextDayBtn').click();
  await expect(page.locator('#summaryOverlay')).toBeHidden();
  await expect.poll(() => page.evaluate(() => window.freshMart.state.day)).toBe(day + 1);
});
