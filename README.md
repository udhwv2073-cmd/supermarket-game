# FRESH MART v2.0

A complete 3D supermarket simulator built with **Three.js + Vite**. The original procedural geometry/textures remain as fallbacks; Blender-exported GLB models in `public/models/` enhance the store, props, characters and products. Sound effects are generated procedurally — no external audio assets.

## Run

```bash
npm install
npm run dev
```

Open the URL printed by Vite (default `http://localhost:5173`).

Production build and checks:

```bash
npm run build          # production bundle
npm run preview        # serve dist locally
npm test               # unit tests (node --test)
npm run lint           # ESLint
npm run format:check   # Prettier
npm run test:e2e       # Playwright (run npx playwright install chromium once)
```

`.github/workflows/ci.yml` runs lint, formatting, unit tests, production build and E2E tests on pushes and pull requests.

## Controls

| Input          | Action                                                            |
| -------------- | ----------------------------------------------------------------- |
| WASD / Arrows  | Move                                                              |
| Shift          | Sprint                                                            |
| Mouse          | Look around                                                       |
| E              | Interact (pick up box, stock shelf, checkout, terminal, dumpster) |
| Q              | Drop the box you are carrying                                     |
| L              | Retry mouse lock after a denied/expired Pointer Lock request      |
| Esc            | Pause / settings                                                  |
| Touch joystick | Move (mobile/tablet)                                              |
| Drag on screen | Look around (mobile/tablet)                                       |
| Touch buttons  | Interact / Drop / Sprint (mobile/tablet)                          |

Movement is relative to the camera yaw (W always goes where you look). Keys are
cleared on focus loss, and the game pauses when the window loses focus or the
mouse lock is released. On touch devices the Pointer Lock UI is replaced by
on-screen controls automatically.

## Gameplay loop

1. Pick up delivery boxes outside (glowing beacon marks new deliveries).
2. Carry a box to a shelf with the matching product and press **E** to restock.
3. Empty boxes become flattened trash — carry them to the dumpster for a recycling bonus.
4. Customers take items and queue at the register. Press **E** at the register to check out:
   - **Card:** enter the exact total.
   - **Cash:** click bill/coin denominations to give exact change.
   - A hired **cashier** checks out customers automatically.
5. Use the **Store Terminal** to:
   - **📦 Order Stock** — buy wholesale boxes (prices fluctuate daily).
   - **💲 Pricing** — set each product's shelf price (±$0.10, reset). You cannot sell below the current wholesale cost; the margin and margin % are shown.
   - **📜 Licenses** — unlock new product lines.
   - **🔨 Build / Furniture** — the in-game build bar (**B**) places shelves ($150), refrigerators ($280) and freezers ($360) anywhere on the unlocked floor, with a product picker for shelf stock. The store starts with 12 shelf spots; each expansion adds a room, a doorway and 4 more spots (levels 1–7, 36 spots total).
   - **👥 Staff** — hire a restocker and/or cashier (wages charged daily).
   - **🎨 Customize** — rename the 3D store sign.
   - **📊 Analytics** — lifetime totals, average net profit, best day, satisfaction rate and a last-7-days profit chart.
   - **🏆 Achievements** — seven persistent milestones with unlock status.
6. The day runs 8:00 AM → 9:00 PM. At closing, review the daily report (revenue, stock costs, wages, rent & utilities, recycling, objective bonus, new achievements) and start the next day with fresh prices and deliveries.

## Systems

- **Reputation (⭐ 0–5)** — happy customers raise it, angry ones (empty shelves, long queues, wrong change) lower it. It scales how often new customers arrive (0 → 0.5×, 5 → 1.5×) and is shown in the top HUD.
- **Daily objective (🎯)** — one rotating goal per day (serve N happy customers / earn $N / recycle N boxes). Completing it pays a bonus at closing; progress is shown in the terminal's Pricing tab and the daily report.
- **Analytics (📊)** — each closed day is stored in `state.history` (last 60 days); the terminal shows lifetime totals, average net, best day, satisfaction rate and a 7-day profit chart. Today's runtime stats are included in the dashboard before closing.
- **Achievements (🏆)** — seven persistent milestones (first day, $1,000 cash, 5 stars, 50 happy customers, 20 recycled boxes, 4 licenses, flawless day). They unlock at day close, during autosave, or when an old save is loaded; new unlocks appear as a toast and in the daily report.
- **Customer preferences & patience** — each shopper has a favourite aisle (buying from it makes them happier) and a limited patience in the checkout queue before they leave angry.
- **Operating costs** — rent ($80/day) plus utilities per refrigerator ($6/day) are deducted at closing.
- **Dynamic pricing** — wholesale prices move daily; your shelf price is independent and clamped between cost and 4× the default markup.
- **Checkout math** — the displayed bill, required change and card validation all come from `checkoutMath.js`, so what the UI says and what the game accepts cannot drift apart.
- **Settings** — pause menu offers mouse sensitivity, master **volume** and **graphics** (low/medium/high: shadows + pixel ratio).
- **WebGL safety** — a small probe runs before Three.js creates a renderer. Unsupported browsers get a readable error overlay instead of a blank canvas; `webglcontextlost` pauses the game, and `webglcontextrestored` hides the overlay and resumes cleanly.

Progress auto-saves to `localStorage` (save schema v4, older saves migrate automatically and corrupt values fall back to safe defaults). Schema v4 adds validated `fixtures` and `businesses` data and expands the shelf layout to 36 physical spots across seven store levels. Every expansion unlocks a real room with a doorway, floor, ceiling and rebuilt wall colliders; shelves and fixtures are placed through the build bar, and saving/loading preserves the store level. The five neighbouring businesses — Sunrise Bakery, Velvet Bean Café, GreenLeaf Pharmacy, Thread & Co. Clothing and Volt Electronics — each have an interactable counter, changing daily offers and an optional paid shift. Gameplay saves are debounced into a single write and flushed on page hide; manual saves and day transitions write immediately. Use the pause menu to save manually or reset progress.

## 3D assets (Blender → GLB)

`public/models/` contains the Blender 5.2 → glTF 2.0 asset set: the store shell, display stands, checkout counter, player, cashier, car, street kit, house, one model per product, and **twelve fully rigged supermarket customers** in `public/models/customers/` (6 male, 6 female across six age tiers from children to seniors, including middle-aged shoppers). Each customer has a 22-bone humanoid rig, 18 baked actions (idle, walk, basket/cart walk, turns, pick/place, checkout, look-around and more) and ~20k triangles. `src/utils/AssetLoader.js` caches them and clones rigs with `SkeletonUtils.clone`; `src/entities/Customer.js` picks characters by weight and drives their animation state, and `CustomerProps.js` adds the hand basket or shopping cart. The full character pipeline is documented in [`assets/characters/README.md`](assets/characters/README.md). If a model is missing, the original procedural mesh is kept, so the game still runs.

## Project structure

```text
src/
  main.js                 bootstrap + WebGL guard wiring
  style.css               HUD + overlays
  core/                   Game loop, input, audio, save system, WebGL guard
  world/                  Store world, lighting, shelf factory (shared asset cache)
  entities/               Player, customer AI/model, staff
  systems/                Interaction, delivery, checkout + checkout math, economy,
                          pricing, reputation, objectives, analytics,
                          achievements
  ui/                     HUD/terminal/pause/checkout/summary UI
  data/                   Products, licenses, layout constants, build catalog, businesses, tuning
  utils/                  Math, canvas textures, mesh helpers, GLB loader
public/
  models/                 Blender-exported GLBs (store, props, products, 12 rigged customers)
assets/characters/        Blender sources, GLB exports, metadata, renders and pipeline docs
tests/
  smoke.test.js           data/economy/objective + GLB export sanity checks (node:test)
  controls.test.js        yaw-relative movement, key normalization, sprint, lock errors
  save.test.js            save migration/validation + debounced write scheduling
  progression.test.js     analytics aggregation + one-time achievement unlocks
  customers.test.js       roster, rig, animation and weighted-spawn checks
  checkout.test.js        bill choice, rounded change, card amount validation
  webgl.test.js           WebGL probe, unavailable/lost/restored states
e2e/
  game.spec.js            Playwright boot, terminal tabs, ordering, day close
.github/
  workflows/ci.yml        lint, format, unit, build and E2E checks
```

`npm test` runs all 46 unit tests with zero test dependencies (`node --test`). `npm run test:e2e` runs four Playwright journeys against a production build.
