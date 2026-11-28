import test from 'node:test';
import assert from 'node:assert/strict';
import ShopActivities from '../src/systems/ShopActivities.js';
import { SHOP_ACTIVITIES, activityRound } from '../src/data/shopActivities.js';
import { BUSINESSES } from '../src/data/businesses.js';

function fakeGame() {
  return {
    state: {
      cash: 500,
      reputation: 3,
      lifetimeRevenue: 0,
      businesses: { activities: {} }
    },
    runtime: { stats: { revenue: 0 } },
    businessSystem: { ensureDay() {} },
    ui: { updateHUD() {} },
    audio: { play() {} },
    save() {}
  };
}

test('all five businesses expose a complete three-round shift', () => {
  assert.deepEqual(Object.keys(SHOP_ACTIVITIES).sort(), Object.keys(BUSINESSES).sort());
  for (const [id, activity] of Object.entries(SHOP_ACTIVITIES)) {
    assert.ok(['timing', 'choice'].includes(activity.type), `${id} has a known type`);
    assert.equal(activity.rounds, 3, `${id} runs three rounds`);
    assert.ok(activity.pay > 0, `${id} pays`);
    assert.ok(activity.dailyLimit > 0, `${id} has a daily limit`);
    assert.ok(activity.title && activity.description && activity.actionLabel, `${id} has copy`);
    if (activity.type === 'timing') {
      assert.ok(activity.timing.speed > 0 && activity.timing.zone > 0, `${id} timing is valid`);
      assert.ok(activity.timing.flavors.length >= 3, `${id} has round flavor text`);
    } else {
      assert.ok(activity.cases.length >= 3, `${id} has enough cases`);
      for (const item of activity.cases) {
        assert.equal(item.options.length, 4, `${id} offers four answers`);
        assert.ok(item.answer >= 0 && item.answer < 4, `${id} answer is in range`);
      }
    }
  }
});

test('choice rounds always contain exactly one correct answer', () => {
  for (const [id, activity] of Object.entries(SHOP_ACTIVITIES)) {
    if (activity.type !== 'choice') continue;
    const round = activityRound(activity, 0, [0]);
    assert.equal(round.options.length, 4, id);
    assert.equal(round.options.filter((o) => o.correct).length, 1, id);
    assert.ok(round.prompt && round.success && round.failure, `${id} has round copy`);
  }
});

test('a perfect shift on every business pays, counts and respects the daily limit', () => {
  for (const id of Object.keys(SHOP_ACTIVITIES)) {
    const game = fakeGame();
    const system = new ShopActivities(game);
    const cashBefore = game.state.cash;
    const repBefore = game.state.reputation;

    assert.equal(system.start(id).ok, true, `${id} starts`);
    let result;
    for (let round = 0; round < 3; round += 1) {
      assert.ok(system.session.round, `${id} has round ${round + 1}`);
      result = system.submit(1);
      assert.equal(result.ok, true);
    }

    assert.equal(result.finished, true, `${id} finishes`);
    assert.equal(result.summary.quality, 1);
    assert.equal(result.summary.pay, SHOP_ACTIVITIES[id].pay);
    assert.equal(game.state.cash, cashBefore + result.summary.pay);
    assert.ok(game.state.reputation > repBefore);
    assert.equal(game.state.businesses.activities[id], 1);
    assert.equal(result.summary.served, 1);
    assert.equal(result.summary.limit, SHOP_ACTIVITIES[id].dailyLimit);
    assert.equal(game.runtime.stats.revenue, result.summary.pay);
    assert.equal(system.remaining(id), SHOP_ACTIVITIES[id].dailyLimit - 1);
  }
});

test('a shop at its daily limit refuses new shifts without blocking the others', () => {
  const game = fakeGame();
  const system = new ShopActivities(game);
  game.state.businesses.activities.bakery = SHOP_ACTIVITIES.bakery.dailyLimit;

  const blocked = system.start('bakery');
  assert.equal(blocked.ok, false);
  assert.match(blocked.reason, /walk-ins|tomorrow/i);
  assert.equal(system.start('cafe').ok, true, 'another shop still opens');
  system.cancel();
});
