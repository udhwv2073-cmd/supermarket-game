import { BUSINESSES, canUseOffer, offersUsedToday, shiftsServedToday } from '../data/businesses.js';
import { SHOP_ACTIVITIES } from '../data/shopActivities.js';

function percent(value) {
  return `${(value * 100).toFixed(2)}%`;
}

export default class ShopUI {
  constructor(game) {
    this.game = game;
    this.el = null;
    this.currentBusinessId = null;
    this.tab = 'counter';
    this.timing = null;
    this.marker = 0;
    this.frame = 0;
    this.lastGrade = null;
  }

  ensureEl() {
    if (this.el) return;
    const wrap = document.createElement('div');
    wrap.id = 'shopOverlay';
    wrap.className = 'overlay';
    wrap.innerHTML = `
      <div class="card shop-card">
        <div class="shop-head">
          <div>
            <h1 id="shopTitle">Shop</h1>
            <p id="shopTagline" class="shop-tagline"></p>
          </div>
          <div id="shopStatus" class="shop-status"></div>
        </div>
        <div class="shop-tabs" role="tablist">
          <button type="button" class="shop-tab" data-shoptab="counter">Counter</button>
          <button type="button" class="shop-tab" data-shoptab="activity">Work a shift</button>
        </div>
        <div id="shopBody"></div>
        <div class="row shop-actions">
          <button type="button" class="btn gray" id="shopCloseBtn">Leave shop (Esc)</button>
        </div>
      </div>
    `;
    document.body.appendChild(wrap);
    this.el = wrap;
    wrap.querySelector('#shopCloseBtn').onclick = () => this.hide();
    wrap.querySelectorAll('[data-shoptab]').forEach((button) => {
      button.onclick = () => this.switchTab(button.dataset.shoptab);
    });
  }

  isOpen() {
    return !!this.el?.classList.contains('show');
  }

  show(businessId, tab = 'counter') {
    this.ensureEl();
    const business = BUSINESSES[businessId];
    if (!business) return;
    if (this.currentBusinessId && this.currentBusinessId !== businessId) this.cancelActivity();
    this.currentBusinessId = businessId;
    this.tab = tab === 'activity' ? 'activity' : 'counter';
    this.el.querySelector('#shopTitle').textContent = business.name;
    this.el.querySelector('#shopTagline').textContent = business.tagline || '';
    this.el.classList.add('show');
    this.game.setMode('modal');
    this.game.input?.exitLock?.();
    this.render();
  }

  switchTab(tab) {
    if (tab === this.tab) return;
    if (this.tab === 'activity') this.cancelActivity();
    this.tab = tab;
    this.render();
  }

  cancelActivity() {
    this.stopTiming();
    this.game.shopActivities?.cancel?.();
    this.lastGrade = null;
  }

  hide() {
    if (!this.el) return;
    this.stopTiming();
    this.game.shopActivities?.cancel?.();
    this.el.classList.remove('show');
    this.currentBusinessId = null;
    this.lastGrade = null;
    if (this.game.mode === 'modal') this.game.startPlaying();
  }

  // The shift counter lives above the tabs, so it must refresh when a shift
  // settles instead of waiting for the shop to be reopened.
  renderStatus() {
    if (!this.el) return;
    const business = BUSINESSES[this.currentBusinessId];
    if (!business) return;
    const activity = SHOP_ACTIVITIES[business.id];
    const served = shiftsServedToday(this.game.state, business.id);
    const limit = activity?.dailyLimit || 0;
    this.el.querySelector('#shopStatus').innerHTML = `
      <div><span class="shop-status-label">STAFF</span> ${business.staff.name}</div>
      <div><span class="shop-status-label">SHIFTS</span> ${served}/${limit} today</div>
    `;
  }

  render() {
    if (!this.el) return;
    const business = BUSINESSES[this.currentBusinessId];
    if (!business) return;
    const activity = SHOP_ACTIVITIES[business.id];
    this.renderStatus();
    this.el.querySelectorAll('[data-shoptab]').forEach((button) => {
      button.classList.toggle('active', button.dataset.shoptab === this.tab);
      button.disabled = button.dataset.shoptab === 'activity' && !activity;
    });
    if (this.tab === 'counter') this.renderCounter(business);
    else this.renderActivity(business);
  }

  renderCounter(business) {
    const body = this.el.querySelector('#shopBody');
    let html = `<p class="small shop-intro">Browse the counter, or head to the work station for a paid shift.</p><div class="grid">`;
    for (const offer of business.offers || []) {
      const used = offersUsedToday(this.game.state, business.id, offer.id);
      const limit = offer.dailyLimit || 1;
      const check = canUseOffer(this.game, business, offer);
      const disabled = !check.ok || used >= limit;
      html += `<div class="tile shop-offer">
        <h3>${offer.label}</h3>
        <div class="small">${offer.description || ''}</div>
        <div class="shop-offer-meta">Cost: <span class="money">$${offer.cost || 0}</span> · ${used}/${limit} today</div>
        <button class="btn" type="button" data-offer="${offer.id}" ${disabled ? 'disabled' : ''}>${
          disabled ? (check.ok ? 'Used' : check.reason) : 'Buy / Use'
        }</button>
      </div>`;
    }
    html += `</div>`;
    body.innerHTML = html;
    body.querySelectorAll('[data-offer]').forEach((button) => {
      button.onclick = () => {
        const ok = this.game.businessSystem?.useOffer(this.currentBusinessId, button.dataset.offer);
        if (ok) this.render();
      };
    });
  }

  renderActivity(business) {
    const body = this.el.querySelector('#shopBody');
    const activity = SHOP_ACTIVITIES[business.id];
    if (!activity) {
      body.innerHTML = `<p class="small">This work station is still being set up.</p>`;
      return;
    }
    const session = this.game.shopActivities?.session;
    const active = session && session.businessId === business.id;
    if (!active || session.finished) {
      if (active && session.finished && session.summary) {
        this.renderSummary(business, activity, session);
        return;
      }
      const served = this.game.shopActivities?.servedToday(business.id) ?? 0;
      const left = Math.max(0, activity.dailyLimit - served);
      body.innerHTML = `
        <div class="shop-activity">
          <div class="shop-activity-head">
            <div>
              <h2>${activity.title}</h2>
              <p class="small">${activity.description}</p>
            </div>
            <div class="shop-activity-badge">${left} left today</div>
          </div>
          <div class="shop-progress">
            ${Array.from(
              { length: activity.rounds },
              (_, i) => `<span class="shop-dot${i < served ? ' done' : ''}"></span>`
            ).join('')}
            <span class="small">Each shift is ${activity.rounds} quick rounds. Staff handle the rest.</span>
          </div>
          <div class="shop-steps">
            <div><b>1</b> Listen or watch for the cue.</div>
            <div><b>2</b> Act at the right moment or pick the matching answer.</div>
            <div><b>3</b> Finish the shift for cash and reputation.</div>
          </div>
          <button class="btn shop-start" type="button" id="shopStart" ${
            left <= 0 ? 'disabled' : ''
          }>${left <= 0 ? 'No walk-ins left today' : 'Start a shift'}</button>
        </div>`;
      const start = body.querySelector('#shopStart');
      if (start) {
        start.onclick = () => {
          const result = this.game.shopActivities?.start(business.id);
          if (!result?.ok) {
            this.game.ui.toast(result?.reason || 'Cannot start a shift');
            return;
          }
          this.lastGrade = null;
          this.render();
        };
      }
      return;
    }

    const round = session.round;
    const progress = `${session.roundIndex + 1} / ${activity.rounds}`;
    if (round.kind === 'timing') {
      body.innerHTML = `
        <div class="shop-activity shop-timing">
          <div class="shop-activity-head">
            <div>
              <h2>${activity.title}</h2>
              <p class="small">${round.flavor}</p>
            </div>
            <div class="shop-activity-badge">Round ${progress}</div>
          </div>
          <div class="shop-meter-label"><span>${round.meterLabel}</span><span>${round.zoneLabel}</span></div>
          <div class="shop-meter" id="shopMeter">
            <span class="shop-meter-zone" style="left:${percent(Math.max(0, round.center - round.zone / 2))};width:${percent(round.zone)}"></span>
            <span class="shop-meter-marker" id="shopMarker"></span>
          </div>
          <div class="shop-meter-hint">Stop it while the marker is inside the highlighted band.</div>
          <button class="btn shop-start" type="button" id="shopStop">${activity.actionLabel}</button>
        </div>`;
      const stop = body.querySelector('#shopStop');
      stop.onclick = () => this.stopRound();
      this.startTiming(round);
    } else {
      body.innerHTML = `
        <div class="shop-activity shop-choice">
          <div class="shop-activity-head">
            <div>
              <h2>${activity.title}</h2>
              <p class="small">${round.prompt}</p>
            </div>
            <div class="shop-activity-badge">Round ${progress}</div>
          </div>
          <div class="shop-choices">
            ${round.options
              .map(
                (option, index) =>
                  `<button type="button" class="shop-choice" data-choice="${index}">${option.label}</button>`
              )
              .join('')}
          </div>
          <div class="shop-meter-hint">${activity.actionLabel} — you can only choose once.</div>
        </div>`;
      body.querySelectorAll('[data-choice]').forEach((button) => {
        button.onclick = () => {
          const option = round.options[Number(button.dataset.choice)];
          if (!option) return;
          const quality = option.correct ? 1 : 0;
          this.game.ui.toast(option.correct ? round.success : round.failure);
          this.game.audio?.play(option.correct ? 'success' : 'error');
          this.submitRound(quality);
        };
      });
    }
  }

  renderSummary(business, activity, session) {
    const body = this.el.querySelector('#shopBody');
    const summary = session.summary;
    const quality = summary?.quality ?? 0;
    const label = quality > 0.9 ? 'Perfect shift' : quality > 0.6 ? 'Good shift' : 'Rough shift';
    const remaining = this.game.shopActivities?.remaining(business.id) ?? 0;
    body.innerHTML = `
      <div class="shop-activity shop-summary">
        <h2>${label}</h2>
        <p class="small">${activity.title} at ${business.name}</p>
        <div class="shop-receipt">
          <div><span>Cash earned</span><b class="money">$${summary?.pay ?? 0}</b></div>
          <div><span>Reputation</span><b>+${(summary?.rep ?? 0).toFixed(2)}</b></div>
          <div><span>Shifts today</span><b>${summary?.served ?? 0} / ${summary?.limit ?? activity.dailyLimit}</b></div>
        </div>
        <div class="row">
          <button class="btn" type="button" id="shopAgain" ${remaining <= 0 ? 'disabled' : ''}>${
            remaining <= 0 ? 'Shop closed for today' : 'Serve another'
          }</button>
          <button class="btn alt" type="button" id="shopDone">Back to the counter</button>
        </div>
      </div>`;
    body.querySelector('#shopDone').onclick = () => this.switchTab('counter');
    const again = body.querySelector('#shopAgain');
    if (again) {
      again.onclick = () => {
        const result = this.game.shopActivities?.start(business.id);
        if (!result?.ok) {
          this.game.ui.toast(result?.reason || 'Cannot start a shift');
          return;
        }
        this.render();
      };
    }
  }

  startTiming(round) {
    this.stopTiming();
    this.timing = { round, started: performance.now() };
    this.marker = 0;
    const marker = this.el.querySelector('#shopMarker');
    if (!marker) return;
    marker.style.left = '0%';
    const tick = (now) => {
      if (!this.timing || this.timing.round !== round) return;
      const elapsed = (now - this.timing.started) / 1000;
      const cycle = (elapsed * round.speed) % 2;
      this.marker = cycle < 1 ? cycle : 2 - cycle;
      marker.style.left = percent(this.marker);
      this.frame = requestAnimationFrame(tick);
    };
    this.frame = requestAnimationFrame(tick);
  }

  stopTiming() {
    if (this.frame) cancelAnimationFrame(this.frame);
    this.frame = 0;
    this.timing = null;
  }

  stopRound() {
    if (!this.timing) return;
    const round = this.timing.round;
    const marker = this.marker;
    this.stopTiming();
    const distance = Math.abs(marker - round.center);
    let quality = 0;
    if (distance <= round.perfect) quality = 1;
    else if (distance <= round.good) quality = 0.65;
    else if (distance <= round.good * 2) quality = 0.25;
    if (quality === 1) this.game.audio?.play('success');
    else if (quality === 0) this.game.audio?.play('error');
    else this.game.audio?.play('scan');
    this.submitRound(quality);
  }

  submitRound(quality) {
    const result = this.game.shopActivities?.submit(quality);
    if (!result?.ok) return;
    if (result.finished) {
      this.lastGrade = result.summary?.quality ?? 0;
      this.renderStatus();
      this.renderSummary(
        BUSINESSES[this.currentBusinessId],
        SHOP_ACTIVITIES[this.currentBusinessId],
        result.session
      );
    } else {
      this.renderActivity(BUSINESSES[this.currentBusinessId]);
    }
  }
}
