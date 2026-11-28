// The twelve FRESH MART customer characters authored in Blender.
// Each entry mirrors assets/characters/exports/glb/<id>.json.
//
// Six age tiers per gender: child, teen, young adult, adult, middle-aged and
// senior. spawn weights keep a balanced mix while staying close to a 50/50
// gender split.

export const CUSTOMER_CHARACTERS = Object.freeze([
  {
    id: 'male_customer_01',
    name: 'Young Boy',
    file: 'customers/male_customer_01.glb',
    gender: 'male',
    ageGroup: 'child',
    height: 1.31,
    carry: 'none',
    speed: 1.3,
    weight: 0.9
  },
  {
    id: 'male_customer_02',
    name: 'Teenage Boy',
    file: 'customers/male_customer_02.glb',
    gender: 'male',
    ageGroup: 'teen',
    height: 1.63,
    carry: 'none',
    speed: 1.38,
    weight: 1.2
  },
  {
    id: 'male_customer_03',
    name: 'Young Man',
    file: 'customers/male_customer_03.glb',
    gender: 'male',
    ageGroup: 'young_adult',
    height: 1.77,
    carry: 'basket',
    speed: 1.36,
    weight: 1.6
  },
  {
    id: 'male_customer_04',
    name: 'Adult Man',
    file: 'customers/male_customer_04.glb',
    gender: 'male',
    ageGroup: 'adult',
    height: 1.8,
    carry: 'none',
    speed: 1.28,
    weight: 1.4
  },
  {
    id: 'male_customer_05',
    name: 'Middle-Aged Man',
    file: 'customers/male_customer_05.glb',
    gender: 'male',
    ageGroup: 'middle_aged',
    height: 1.73,
    carry: 'cart',
    speed: 1.12,
    weight: 1.4
  },
  {
    id: 'male_customer_06',
    name: 'Elderly Man',
    file: 'customers/male_customer_06.glb',
    gender: 'male',
    ageGroup: 'senior',
    height: 1.69,
    carry: 'none',
    speed: 1.05,
    weight: 1.1
  },
  {
    id: 'female_customer_01',
    name: 'Young Girl',
    file: 'customers/female_customer_01.glb',
    gender: 'female',
    ageGroup: 'child',
    height: 1.29,
    carry: 'none',
    speed: 1.3,
    weight: 0.9
  },
  {
    id: 'female_customer_02',
    name: 'Teenage Girl',
    file: 'customers/female_customer_02.glb',
    gender: 'female',
    ageGroup: 'teen',
    height: 1.6,
    carry: 'none',
    speed: 1.36,
    weight: 1.2
  },
  {
    id: 'female_customer_03',
    name: 'Young Woman',
    file: 'customers/female_customer_03.glb',
    gender: 'female',
    ageGroup: 'young_adult',
    height: 1.68,
    carry: 'basket',
    speed: 1.34,
    weight: 1.6
  },
  {
    id: 'female_customer_04',
    name: 'Adult Woman',
    file: 'customers/female_customer_04.glb',
    gender: 'female',
    ageGroup: 'adult',
    height: 1.71,
    carry: 'none',
    speed: 1.3,
    weight: 1.4
  },
  {
    id: 'female_customer_05',
    name: 'Middle-Aged Woman',
    file: 'customers/female_customer_05.glb',
    gender: 'female',
    ageGroup: 'middle_aged',
    height: 1.6,
    carry: 'cart',
    speed: 1.1,
    weight: 1.4
  },
  {
    id: 'female_customer_06',
    name: 'Elderly Woman',
    file: 'customers/female_customer_06.glb',
    gender: 'female',
    ageGroup: 'senior',
    height: 1.57,
    carry: 'none',
    speed: 1.0,
    weight: 1.1
  }
]);

export const CUSTOMER_FILES = CUSTOMER_CHARACTERS.map((c) => c.file);

export const AGE_GROUPS = Object.freeze([
  'child',
  'teen',
  'young_adult',
  'adult',
  'middle_aged',
  'senior'
]);

// The six highest-weighted characters are preloaded for city pedestrians, so
// sidewalk walkers reuse the same cached GLBs as the shoppers instead of
// fetching twelve more models at boot.
export const CITY_PEDESTRIAN_CHARACTERS = Object.freeze(
  [...CUSTOMER_CHARACTERS].sort((a, b) => b.weight - a.weight).slice(0, 6)
);

const TOTAL_WEIGHT = CUSTOMER_CHARACTERS.reduce((sum, c) => sum + c.weight, 0);

/** Weighted random character. Pass a seeded RNG for deterministic tests. */
export function pickCustomerCharacter(random = Math.random) {
  let roll = random() * TOTAL_WEIGHT;
  for (const character of CUSTOMER_CHARACTERS) {
    roll -= character.weight;
    if (roll <= 0) return character;
  }
  return CUSTOMER_CHARACTERS[CUSTOMER_CHARACTERS.length - 1];
}

export function customerById(id) {
  return CUSTOMER_CHARACTERS.find((c) => c.id === id) || null;
}

/** Roster summary used by the debug overlay, tests and docs. */
export function rosterSummary() {
  const counts = Object.fromEntries(AGE_GROUPS.map((g) => [g, 0]));
  const gender = { male: 0, female: 0 };
  for (const c of CUSTOMER_CHARACTERS) {
    counts[c.ageGroup] += 1;
    gender[c.gender] += 1;
  }
  return { total: CUSTOMER_CHARACTERS.length, ageGroups: counts, gender };
}
