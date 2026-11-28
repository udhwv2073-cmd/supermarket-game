# Customer character build report

Generated: 2026-11-27
Roster revised: 2026-11-28 (`_04` adults, `_05` middle-aged; four rebuilt)
Blender: 5.2.0 LTS (headless, factory startup)
Exporter: glTF 2.0 binary, Actions mode, baked animation

## Result

12 of 12 characters authored, rigged, animated, exported and copied into
`public/models/customers/`. Each GLB carries one skin with 22 joints, 18 clips,
20–24 material slots and 18–22k triangles. Total geometry across the set is
234,412 triangles.

| ID                   | Age         | Height |   Tris | Bones | Clips | Carry  |
| -------------------- | ----------- | -----: | -----: | ----: | ----: | ------ |
| `male_customer_01`   | child       | 1.31 m | 19,486 |    22 |    18 | —      |
| `male_customer_02`   | teen        | 1.63 m | 19,734 |    22 |    18 | —      |
| `male_customer_03`   | young adult | 1.77 m | 18,370 |    22 |    18 | basket |
| `male_customer_04`   | adult       | 1.80 m | 18,810 |    22 |    18 | —      |
| `male_customer_05`   | middle-aged | 1.73 m | 19,310 |    22 |    18 | cart   |
| `male_customer_06`   | senior      | 1.69 m | 18,914 |    22 |    18 | —      |
| `female_customer_01` | child       | 1.29 m | 19,046 |    22 |    18 | —      |
| `female_customer_02` | teen        | 1.60 m | 19,722 |    22 |    18 | —      |
| `female_customer_03` | young adult | 1.68 m | 18,830 |    22 |    18 | basket |
| `female_customer_04` | adult       | 1.71 m | 20,078 |    22 |    18 | —      |
| `female_customer_05` | middle-aged | 1.60 m | 21,512 |    22 |    18 | cart   |
| `female_customer_06` | senior      | 1.57 m | 20,600 |    22 |    18 | —      |

Roster: 6 male / 6 female; 2 children, 2 teenagers, 2 young adults, 2 adults,
2 middle-aged and 2 seniors. Spawn weights are in `src/data/customers.js` and
mirrored in each character's JSON metadata.

## What was built

- **Faces:** shaped head with jaw, cheek and brow planes, nose bridge/tip,
  ears, inset eye whites, irises, pupils, lashes, brows, lips and mouth. The
  mature specs add soft nasolabial folds and two forehead creases.
- **Middle-aged details:** grey streaks are woven into the hair fringe and
  curls, the man has a moustache built from swept tubes, and both characters
  use a heavier frame, slower stride and slight stoop.
- **Hair:** short, bowl, undercut, side part, quiff, spiky, bob, ponytail,
  bun, long straight, wavy and curly variants built from lofted caps and locks.
- **Clothing:** hoodies, sweaters, shirts, blouses, cardigans, coats and
  jackets with collars, lapels, cuffs, hems and pockets; trousers, jeans,
  skirts and shorts; sneakers, boots and loafers with soles and laces.
- **Accessories:** backpacks, tote bags, handbags, glasses, caps, beanies,
  headphones, watches, belts, buttons and scarves.
- **Rig:** 22-bone humanoid armature (`Root`, `Hips`, `Spine`, `Chest`, `Neck`,
  `Head`, shoulders, arms, hands, thighs, shins, feet, toes), vertex-group
  weights assigned at mesh build time, no automatic-weight cleanup.
- **Animation:** 18 actions at 24 fps — `Idle`, `IdleBasket`, `IdleCart`,
  `Walk`, `WalkBasket`, `WalkCart`, `Wait`, `LookAround`, `TurnLeft`,
  `TurnRight`, `Stop`, `PickItem`, `PlaceItem`, `Checkout`, `Run`, `Greet`,
  `Inspect`, `ReachHigh`. Loops use matching first/last keys; easing is a
  monotone PCHIP so knees and elbows do not overshoot.

## Visual QA

- Full lineup render: `assets/characters/renders/lineup.png` (1800×700),
  re-rendered 2026-11-28 from the current GLBs.
- In-game frame: `assets/characters/renders/gameplay.png`.
- Checked for: distinct silhouettes and heights, varied skin tones, hair
  volumes that read from behind, clothing colour separation, no interpenetrating
  limbs at rest, feet on the floor, faces readable at 2–4 m.
- Fixed during QA: Catmull-Rom uneven spacing (knee ridges), swept-tube frame
  roll (diagonal creases), torso ending below the neck, rounded-box size
  semantics, backpack strap stubs, flat pocket shading, missing brow material.

## In-game check

Automated headless Chromium run against the Vite dev server (1024×640 WebGL
via SwiftShader), with the screenshots in `renders/gameplay.png` and
`.tmp-blender/game_closeup.png`:

- Started the game and reached `mode: playing`.
- Spawned 7 shoppers (the store cap). The set was distinct — no repeated
  character in the wave — and their spawn points were more than 1.05 m apart.
- Every spawned model reported 18 actions. Active clips matched the carry
  style: `WalkCart` for the cart shoppers, `WalkBasket` for the basket shopper,
  `Walk` for everyone else; position Y was 0 (feet on the ground).
- Rendered frame shows varied heights, faces, outfits, baskets and the wire
  carts in the store entrance area.

This was an automated render/state check, not a manual playthrough: input
handling, checkout flow and long sessions were covered by the existing unit
suite and gameplay code, not replayed in the browser.

## Carry grip and render budget

- Carrier arms are solved per rig against the real bone lengths, instead of
  fixed angles. Cart shoppers target the bar at local ±0.17 m, y 1.05 m,
  z 0.38 m; basket shoppers target the side rims at ±0.17 m,
  y = height/2 + 0.21 m, z 0.36 m. The solved poses keep the elbows clear of
  the torso (elbow x ≥ 0.20 m).
- All four carrier GLBs carry `grip_gap` in their JSON metadata: under 0.1 mm.
  In-game, with `IdleCart`/`IdleBasket` playing, the measured palm gap is 4–8 mm
  through the idle loop for both carry styles.
- Close-up renders: `renders/cart-grip.png` and `renders/basket-grip.png`.
- Character parts are merged at load: 21 material slots become vertex colours
  grouped by finish into at most four skinned meshes, with one shared material
  per finish across shoppers. Baskets and carts are merged once per material
  and reused (cart → 3 draw calls, basket → 2).
- Seven shoppers in one frozen frame: 321 draw calls with them visible vs 285
  with them hidden, so the whole crowd costs 36 calls (~5 each) and 139.5k
  triangles (~19.9k each). A lighter wave with two carriers measured 28 calls
  (~4 each). Before batching, the same protocol measured 25.2 calls per
  shopper; the crowd is now ~80% cheaper.
- Current roster re-probe (2026-11-28): seven shoppers measured 322 calls /
  147,060 tris (288 / 11,802 with them hidden); six GLB pedestrians measured
  280 / 126,652 (258 / 9,722 hidden), so the crowd costs 34 calls and the
  pedestrians 22. Each of the six pedestrian GLBs was requested once.
- Frame times here come from a software WebGL renderer and are not
  representative of GPU performance; draw calls and triangles are the
  meaningful figures.

## Validation

- `npm test` — 86/86 passing, including `tests/customers.test.js`, which checks
  the roster split, one skin with ≥20 joints, all required clips, camera-free
  export, feet at Y=0, height within 12 cm of the roster, metadata agreement,
  a ≤2 cm solved grip for every carrier and weighted coverage over 6,000 draws.
- `npm run build` — Vite production build succeeds (final run after the
  integration, cart and basket changes).
- GLB inspection — every file parses, 1 skin, 22 joints, 18 animations,
  21–22 material slots, no cameras or lights.
- Live browser session (2026-11-28) — five GLB pedestrians walked and idled;
  shoppers spawned with 18 clips; the bakery counter, a paid shift, all five
  neighbour counters, cash and card checkout (including rejected wrong
  amounts), build place/move/rotate/remove and save/reload were exercised. A
  unit test now plays a perfect shift at every shop and checks its reward,
  limit and round data. Draw-call and GLB-request counts are recorded above.

## Rebuild

```bash
cd fresh-mart
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
  -b --factory-startup -P tools/blender/build_customers.py
```

The build writes `.blend`, `.glb` and `.json` for every character plus
`manifest.json`, then copies the game-ready GLBs to
`public/models/customers/`. See `README.md` for the pipeline API and game
integration notes.
