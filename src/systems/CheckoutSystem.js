import { DENOMS, PRODUCTS } from '../data/products.js';
import { money, rounded } from '../utils/math.js';
import { basketTotal, showEmoji, reindexQueue } from '../entities/Customer.js';
import { currentSellPrice } from './Pricing.js';
import { onHappyCustomer, onAngryCustomer } from './Reputation.js';
import { pickBill, changeDue, isExactChange, isExactCardAmount } from './checkoutMath.js';

export default class CheckoutSystem {
  constructor(game) {
    this.game = game;
  }

  open(c) {
    const game = this.game;
    game.runtime.checkoutCustomer = c;
    game.setMode('modal');
    game.input.exitLock();
    const total = basketTotal(game, c);
    const list = c.basket
      .map((pid) => `<li>${PRODUCTS[pid].name} — ${money(currentSellPrice(game, pid))}</li>`)
      .join('');
    const byCard = Math.random() < 0.5;
    let html = `<p>Customer basket:</p><ul style="margin-left:20px;line-height:1.7">${list || '<li>(nothing)</li>'}</ul>
      <div class="stat"><span>Total due</span><b>${money(total)}</b></div>`;

    if (byCard) {
      html += `<h2>💳 Card Payment</h2><p>Enter the exact total amount to charge the card.</p>
        <input type="number" id="cardInput" step="0.01" placeholder="0.00">
        <div class="row"><button class="btn" id="confirmCard">Charge Card</button><button class="btn gray" id="cancelCheckout">Cancel</button></div>`;
    } else {
      html += `<h2>💵 Cash Payment</h2><p>Customer hands you a <b>${money(pickBill(total))}</b> bill. Give exact change: <b>${money(changeDue(total))}</b>.</p>
        <div class="stat"><span>Change given</span><b id="changeGiven">$0.00</b></div>
        <div class="denoms">${DENOMS.map((d) => `<button class="btn alt den" data-v="${d}">${d < 1 ? d : '$' + d}</button>`).join('')}</div>
        <div class="row"><button class="btn" id="confirmCash">Give Change</button><button class="btn gray" id="clearChange">Clear</button><button class="btn gray" id="cancelCheckout">Cancel</button></div>`;
    }
    game.ui.showCheckout(html);

    if (byCard) {
      document.getElementById('confirmCard').onclick = () => {
        if (isExactCardAmount(document.getElementById('cardInput').value, total))
          this.finish(c, true, total);
        else {
          game.audio.play('error');
          game.ui.toast('Incorrect amount — try again');
        }
      };
    } else {
      let given = 0;
      const disp = document.getElementById('changeGiven');
      document.querySelectorAll('#checkoutBody .den').forEach((b) => {
        b.onclick = () => {
          given = rounded(given + parseFloat(b.dataset.v));
          disp.textContent = money(given);
          game.audio.play('coin');
        };
      });
      document.getElementById('clearChange').onclick = () => {
        given = 0;
        disp.textContent = '$0.00';
      };
      document.getElementById('confirmCash').onclick = () => {
        if (isExactChange(given, total)) this.finish(c, true, total);
        else {
          game.audio.play('error');
          game.ui.toast('Change is not exact — try again');
        }
      };
    }
    document.getElementById('cancelCheckout').onclick = () => this.cancel();
  }

  cancel() {
    const game = this.game;
    game.runtime.checkoutCustomer = null;
    game.startPlaying();
  }

  finish(c, ok, total) {
    const game = this.game;
    game.runtime.checkoutCustomer = null;
    game.startPlaying();
    if (ok) {
      game.state.cash = rounded(game.state.cash + total);
      game.state.lifetimeRevenue = rounded(game.state.lifetimeRevenue + total);
      game.runtime.stats.revenue += total;
      game.runtime.stats.happy++;
      onHappyCustomer(game);
      game.audio.play('success');
      showEmoji(c, '😊', 2.5);
      c.state = 'happy';
    } else {
      game.runtime.stats.angry++;
      onAngryCustomer(game);
      game.audio.play('error');
      showEmoji(c, '😠', 2.5);
      c.state = 'angry';
    }
    game.ui.updateHUD();
    game.save();
    reindexQueue(game);
  }
}
