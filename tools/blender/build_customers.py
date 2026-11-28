"""Build the 12 FRESH MART customer characters in Blender.

Run headless:
    blender -b --factory-startup -P tools/blender/build_customers.py -- [--only id] [--no-render]

Outputs (per character):
    assets/characters/blender_source/<id>.blend
    assets/characters/exports/glb/<id>.glb
    assets/characters/exports/glb/<id>.json
    public/models/customers/<id>.glb

The mesh is generated from analytical lofts so each vertex is weighted by
construction (no automatic-weight failures).  The skeleton is a 22-bone
humanoid chain that matches the game's animation naming.
"""

import bpy
import math
import json
import os
import sys
import time
from mathutils import Vector, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)

from blender_kit import (  # noqa: E402
    TAU,
    D,
    smoothstep,
    lerp,
    catmull,
    pchip,
    make_material,
    add_mesh,
    loft_z,
    tube,
    ellipsoid,
    rounded_box,
    torus,
    join_objects,
    apply_solidify,
    norm,
    blend,
    build_armature,
    bind_meshes,
    pose_quat,
    mirror_pose,
    key_pose,
    make_action,
    action_length,
)

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "assets", "characters", "blender_source")
OUT_GLB = os.path.join(ROOT, "assets", "characters", "exports", "glb")
OUT_GAME = os.path.join(ROOT, "public", "models", "customers")
OUT_TEX = os.path.join(ROOT, "assets", "characters", "textures")


# --------------------------------------------------------------------------- #
# character specifications
# --------------------------------------------------------------------------- #
SPECS = [
    dict(
        id="male_customer_01", name="Young Boy", sex="M", age=9, height=1.31,
        frame="slim", head_ratio=0.157, build=0.92,
        face=dict(width=0.98, jaw=0.94, chin=0.95, eyes=1.06, eye_size=1.08,
                  nose=0.92, lips=0.95, brow=1.0, mouth=1.0),
        skin=0xd9a77f, hair=0x3a2417, hair_style="short_textured",
        iris=0x5a3a22,
        top=dict(kind="hoodie", color=0x1f7f86, accent=0xf2c14e, sleeve="long"),
        bottom=dict(kind="jeans", color=0x35445e),
        shoes=dict(color=0xe8e4dc, accent=0xc23a3a),
        accessories=["backpack"], accent_color=0xc23a3a, carry="none",
        walk=dict(stride=0.92, arm=1.15, bounce=1.35, stoop=0.0, tempo=1.05),
        spawn_weight=0.9,
    ),
    dict(
        id="male_customer_02", name="Teenage Boy", sex="M", age=15, height=1.63,
        frame="slim", head_ratio=0.152, build=0.95,
        face=dict(width=0.97, jaw=1.02, chin=1.0, eyes=1.0, eye_size=1.0,
                  nose=1.04, lips=0.92, brow=1.08, mouth=0.95),
        skin=0xb9825c, hair=0x14100e, hair_style="undercut",
        iris=0x33261c,
        top=dict(kind="jacket", color=0x3d5240, accent=0x23282a, sleeve="long"),
        bottom=dict(kind="jeans", color=0x2c3542),
        shoes=dict(color=0xf0ece2, accent=0x2b2f36),
        accessories=["headphones"], accent_color=0x22262b, carry="none",
        walk=dict(stride=1.0, arm=1.0, bounce=1.1, stoop=0.0, tempo=1.0),
        spawn_weight=1.2,
    ),
    dict(
        id="male_customer_03", name="Young Man", sex="M", age=22, height=1.77,
        frame="average", head_ratio=0.137, build=1.0,
        face=dict(width=1.0, jaw=1.04, chin=1.02, eyes=0.99, eye_size=0.98,
                  nose=1.02, lips=0.95, brow=1.0, mouth=1.0),
        skin=0xe8c3a3, hair=0x9b6b3a, hair_style="side_part",
        iris=0x4a6b7c,
        top=dict(kind="polo", color=0x2f5d7c, accent=0xe9e5d8, sleeve="short"),
        bottom=dict(kind="chinos", color=0x8a7a5f),
        shoes=dict(color=0xf3efe6, accent=0x8b8f96),
        accessories=["watch"], accent_color=0x2c3440, carry="basket",
        walk=dict(stride=1.0, arm=1.0, bounce=1.0, stoop=0.0, tempo=1.0),
        spawn_weight=1.6,
    ),
    dict(
        id="male_customer_04", name="Adult Man", sex="M", age=34,
        height=1.80, frame="average", head_ratio=0.136, build=1.03,
        face=dict(width=1.02, jaw=1.06, chin=1.0, eyes=0.98, eye_size=0.97,
                  nose=1.05, lips=1.02, brow=1.06, mouth=1.01),
        skin=0x8a5a3c, hair=0x241c15, hair_style="side_part",
        iris=0x2e2118,
        top=dict(kind="shirt", color=0x3e5c72, accent=0xe9e5d8, sleeve="long"),
        bottom=dict(kind="trousers", color=0x3a3f4a),
        shoes=dict(color=0x3a2a22, accent=0x201814),
        accessories=["watch"], accent_color=0x2c3440,
        carry="none",
        walk=dict(stride=1.0, arm=0.94, bounce=0.94, stoop=0.6, tempo=0.98),
        spawn_weight=1.4,
    ),
    dict(
        id="male_customer_05", name="Middle-Aged Man", sex="M", age=56, height=1.73,
        frame="heavy", head_ratio=0.142, build=1.06,
        face=dict(width=1.05, jaw=1.04, chin=0.98, eyes=0.95, eye_size=0.93,
                  nose=1.08, lips=0.98, brow=1.0, mouth=1.0),
        skin=0xc09472, hair=0x726b61, hair_style="receding",
        iris=0x3b2c20, mature=True,
        top=dict(kind="cardigan", color=0x5c6659, accent=0xe6e0d0, sleeve="long"),
        bottom=dict(kind="chinos", color=0x6b6353),
        shoes=dict(color=0x3a2a22, accent=0x201814),
        accessories=["glasses", "moustache"], accent_color=0x2f343a, carry="cart",
        walk=dict(stride=0.9, arm=0.84, bounce=0.8, stoop=3.2, tempo=0.9),
        spawn_weight=1.4,
    ),
    dict(
        id="male_customer_06", name="Elderly Man", sex="M", age=71, height=1.69,
        frame="average", head_ratio=0.142, build=0.97,
        face=dict(width=1.0, jaw=0.97, chin=1.0, eyes=0.97, eye_size=0.94,
                  nose=1.06, lips=0.95, brow=0.9, mouth=0.98),
        skin=0xd8b294, hair=0xd8d4cc, hair_style="comb_over",
        iris=0x5a6a70,
        top=dict(kind="cardigan", color=0x6a6f78, accent=0xe8e4d8, sleeve="long"),
        bottom=dict(kind="trousers", color=0x4a4a4e),
        shoes=dict(color=0x3a2a22, accent=0x241c16),
        accessories=["glasses"], accent_color=0x35383d, carry="none",
        walk=dict(stride=0.8, arm=0.72, bounce=0.7, stoop=7.0, tempo=0.86),
        spawn_weight=1.1,
    ),
    dict(
        id="female_customer_01", name="Young Girl", sex="F", age=9, height=1.29,
        frame="petite", head_ratio=0.159, build=0.92,
        face=dict(width=0.98, jaw=0.92, chin=0.95, eyes=1.08, eye_size=1.1,
                  nose=0.9, lips=0.98, brow=0.95, mouth=1.02),
        skin=0xc99a72, hair=0x5a3520, hair_style="pigtails",
        iris=0x6a4a2c,
        top=dict(kind="hoodie", color=0xe0668f, accent=0xf7d34a, sleeve="long"),
        bottom=dict(kind="leggings", color=0x2a2d3a),
        shoes=dict(color=0xf0c6cf, accent=0xffffff),
        accessories=["backpack"], accent_color=0x8b5fb0, carry="none",
        walk=dict(stride=0.9, arm=1.2, bounce=1.4, stoop=0.0, tempo=1.06),
        spawn_weight=0.9,
    ),
    dict(
        id="female_customer_02", name="Teenage Girl", sex="F", age=15, height=1.6,
        frame="slim", head_ratio=0.152, build=0.96,
        face=dict(width=0.98, jaw=0.94, chin=0.97, eyes=1.03, eye_size=1.02,
                  nose=0.94, lips=1.02, brow=1.0, mouth=1.02),
        skin=0xd2a983, hair=0x1d1613, hair_style="long_straight",
        iris=0x3b2a20,
        top=dict(kind="jacket", color=0x3f5f86, accent=0xe9e5d8, sleeve="long"),
        bottom=dict(kind="jeans", color=0x3a4a63),
        shoes=dict(color=0xf1ece2, accent=0x3f5f86),
        accessories=["necklace"], accent_color=0xd8c48a, carry="none",
        walk=dict(stride=0.95, arm=0.95, bounce=1.05, stoop=0.0, tempo=1.0),
        spawn_weight=1.2,
    ),
    dict(
        id="female_customer_03", name="Young Woman", sex="F", age=23, height=1.68,
        frame="average", head_ratio=0.14, build=1.0,
        face=dict(width=0.98, jaw=0.92, chin=0.96, eyes=1.02, eye_size=1.02,
                  nose=0.93, lips=1.05, brow=1.0, mouth=1.04),
        skin=0xecc9ab, hair=0x7a3b1f, hair_style="ponytail",
        iris=0x3f6b4a,
        top=dict(kind="tee", color=0x2f8f8a, accent=0x1e6460, sleeve="short"),
        bottom=dict(kind="jeans", color=0x38465c),
        shoes=dict(color=0xf2eee4, accent=0x2f8f8a),
        accessories=[], accent_color=0x2f8f8a, carry="basket",
        walk=dict(stride=0.98, arm=0.95, bounce=1.0, stoop=0.0, tempo=1.0),
        spawn_weight=1.6,
    ),
    dict(
        id="female_customer_04", name="Adult Woman", sex="F",
        age=34, height=1.71, frame="average", head_ratio=0.137, build=1.0,
        face=dict(width=1.0, jaw=0.92, chin=0.96, eyes=1.0, eye_size=1.0,
                  nose=0.99, lips=1.06, brow=1.02, mouth=1.0),
        skin=0x8a5a3c, hair=0x2c1d14, hair_style="shoulder_wavy",
        iris=0x241a13,
        top=dict(kind="jacket", color=0x3b5464, accent=0xe8dfcc, sleeve="long"),
        bottom=dict(kind="trousers", color=0x3d3f47),
        shoes=dict(color=0x2b2a2a, accent=0x141313),
        accessories=["watch", "handbag"], accent_color=0x7a4a2c, carry="none",
        walk=dict(stride=1.0, arm=0.92, bounce=0.92, stoop=0.6, tempo=0.98),
        spawn_weight=1.4,
    ),
    dict(
        id="female_customer_05", name="Middle-Aged Woman", sex="F", age=56, height=1.60,
        frame="average", head_ratio=0.144, build=1.0,
        face=dict(width=1.01, jaw=0.94, chin=0.97, eyes=0.98, eye_size=0.96,
                  nose=1.0, lips=0.96, brow=0.92, mouth=0.98),
        skin=0xba8a63, hair=0x71675f, hair_style="curly_bob",
        iris=0x4a3a28, mature=True,
        top=dict(kind="cardigan", color=0x8a6a72, accent=0xf0ead8, sleeve="long"),
        bottom=dict(kind="skirt", color=0x4d4657, length=0.74),
        shoes=dict(color=0x4a3a30, accent=0xf0ece0),
        accessories=["glasses", "handbag"], accent_color=0x3a3630, carry="cart",
        walk=dict(stride=0.86, arm=0.8, bounce=0.8, stoop=2.6, tempo=0.9),
        spawn_weight=1.4,
    ),
    dict(
        id="female_customer_06", name="Elderly Woman", sex="F", age=72, height=1.57,
        frame="petite", head_ratio=0.148, build=0.96,
        face=dict(width=0.98, jaw=0.94, chin=0.98, eyes=0.98, eye_size=0.95,
                  nose=1.0, lips=0.9, brow=0.88, mouth=0.96),
        skin=0xdcc0a6, hair=0xe2ded6, hair_style="bun_white",
        iris=0x6a7478,
        top=dict(kind="cardigan", color=0xb87a8a, accent=0xf0ead8, sleeve="long"),
        bottom=dict(kind="skirt", color=0x5d4a63, length=0.72),
        shoes=dict(color=0x4a3a32, accent=0x2a201b),
        accessories=["glasses", "handbag"], accent_color=0x6b4a33, carry="none",
        walk=dict(stride=0.74, arm=0.68, bounce=0.65, stoop=8.0, tempo=0.84),
        spawn_weight=1.1,
    ),
]


# --------------------------------------------------------------------------- #
# proportions
# --------------------------------------------------------------------------- #
def proportions(spec):
    H = spec["height"]
    age = spec["age"]
    sex = spec["sex"]
    build = spec.get("build", 1.0)
    head_h = H * spec["head_ratio"]
    chin_z = H - head_h
    head_c = chin_z + head_h / 2
    shoulder_z = chin_z - (0.046 if age <= 10 else 0.052 if age <= 16 else 0.058) * H
    neck_base = shoulder_z + 0.006 * H

    crotch_z = H * (0.435 if age <= 10 else 0.455 if age <= 16 else 0.47)
    knee_z = H * (0.255 if age <= 10 else 0.275)
    ankle_z = H * 0.042
    hip_z = crotch_z + 0.055 * H
    waist_z = crotch_z + 0.105 * H
    chest_z = chin_z - 0.105 * H

    child = 0.98 if age <= 10 else 1.0
    shoulder_x = H * (0.121 if sex == "M" else 0.107) * build * child
    hip_x = H * (0.091 if sex == "M" else 0.098) * build * (0.97 if age <= 10 else 1.0)
    hip_d = hip_x * 0.74
    waist_x = hip_x * (0.87 if sex == "M" else 0.81)
    waist_d = waist_x * 0.72
    chest_x = shoulder_x * 0.85
    chest_d = (shoulder_x * 0.63) * (0.92 if sex == "F" else 1.0)
    neck_r = H * (0.027 if sex == "M" else 0.0245) * (0.86 if age <= 10 else 1.0)

    head_w = head_h * 0.69 * spec["face"]["width"]
    head_d = head_h * 0.79

    arm_len = H * 0.335 * (0.94 if age <= 10 else 1.0)
    shoulder_joint = Vector((shoulder_x * 0.9, 0, shoulder_z - 0.012))
    tilt = math.radians(9.0 if sex == "M" else 11.0)
    elbow = shoulder_joint + Vector((math.sin(tilt) * arm_len * 0.53, 0.004, -arm_len * 0.53))
    wrist = elbow + Vector((math.sin(tilt * 0.7) * arm_len * 0.47, -0.008, -arm_len * 0.47))
    hand_end = wrist + Vector((0.01, -0.006, -H * 0.095))

    hip_joint = Vector((hip_x * 0.53, 0, crotch_z + 0.022 * H))
    knee = Vector((hip_x * 0.51, 0.004, knee_z))
    ankle = Vector((hip_x * 0.49, 0.0, ankle_z))
    foot_len = H * (0.145 if sex == "M" else 0.14)
    toe = Vector((ankle.x, -foot_len * 0.9, ankle_z * 0.28))

    return dict(
        H=H, age=age, sex=sex, build=build,
        head_h=head_h, head_w=head_w, head_d=head_d, head_c=head_c,
        chin_z=chin_z, crown_z=H, shoulder_z=shoulder_z, neck_base=neck_base,
        neck_top=chin_z + 0.012, crotch_z=crotch_z, knee_z=knee_z,
        ankle_z=ankle_z, hip_z=hip_z, waist_z=waist_z, chest_z=chest_z,
        shoulder_x=shoulder_x, hip_x=hip_x, hip_d=hip_d,
        waist_x=waist_x, waist_d=waist_d, chest_x=chest_x, chest_d=chest_d,
        neck_r=neck_r,
        shoulder_joint=shoulder_joint, elbow=elbow, wrist=wrist, hand_end=hand_end,
        hip_joint=hip_joint, knee=knee, ankle=ankle, toe=toe, foot_len=foot_len,
        arm_len=arm_len,
    )


def torso_ctrl(P):
    H = P["H"]
    sex = P["sex"]
    belly = 0.012 if P["build"] > 1.02 else 0.0
    return [
        (P["crotch_z"] - 0.02 * H, P["hip_x"] * 0.94, P["hip_d"] * 0.92, 0.0),
        (P["hip_z"], P["hip_x"], P["hip_d"], 0.0),
        (P["waist_z"], P["waist_x"], P["waist_d"], -belly),
        (P["chest_z"] - 0.02 * H, P["chest_x"], P["chest_d"], 0.002),
        (P["shoulder_z"] - 0.012 * H, P["shoulder_x"] * 0.91, P["chest_d"] * 0.92, 0.004),
        (P["shoulder_z"], P["shoulder_x"] * 0.87, P["chest_d"] * 0.84, 0.006),
        (P["neck_base"], P["neck_r"] * 1.72, P["neck_r"] * 1.55, 0.005),
    ]


def sample_torso(P, z):
    """Return (rx, ry, yoff) of the body surface at height z."""
    ctrl = P["torso_ctrl"]
    return (pchip([(c[0], c[1]) for c in ctrl], z),
            pchip([(c[0], c[2]) for c in ctrl], z),
            pchip([(c[0], c[3]) for c in ctrl], z))


# --------------------------------------------------------------------------- #
# weights
# --------------------------------------------------------------------------- #
def weights_torso(P, z):
    zc, wz, ch, sh, nb = P["crotch_z"], P["waist_z"], P["chest_z"], P["shoulder_z"], P["neck_base"]
    a = smoothstep(zc, wz, z)
    b = smoothstep(wz, ch, z)
    c = smoothstep(sh, nb, z)
    hips = 1.0 - a
    spine = a * (1.0 - b)
    chest = b * (1.0 - c)
    neck = c
    return norm({"Hips": hips, "Spine": spine, "Chest": chest, "Neck": neck})


def weights_arm(P, t, side):
    s = "Shoulder_" + side
    ua = "UpperArm_" + side
    la = "LowerArm_" + side
    hand = "Hand_" + side
    upper = 1.0 - smoothstep(0.48, 0.62, t)
    lower = smoothstep(0.48, 0.62, t) * (1.0 - smoothstep(0.9, 1.0, t))
    hd = smoothstep(0.9, 1.0, t)
    top = 1.0 - smoothstep(0.0, 0.09, t)
    return norm({s: top * 0.45, ua: upper * (1.0 - top * 0.45), la: lower, hand: hd})


def weights_leg(P, t, side):
    th = "Thigh_" + side
    sh = "Shin_" + side
    ft = "Foot_" + side
    thigh = 1.0 - smoothstep(0.46, 0.6, t)
    shin = smoothstep(0.46, 0.6, t) * (1.0 - smoothstep(0.92, 1.0, t))
    foot = smoothstep(0.92, 1.0, t)
    return norm({th: thigh, sh: shin, ft: foot})


def weights_neck(P, z):
    t = smoothstep(P["neck_base"], P["chin_z"] + 0.01, z)
    return norm({"Neck": 1.0 - t, "Head": t})


# --------------------------------------------------------------------------- #
# head + face
# --------------------------------------------------------------------------- #
class HeadShape:
    def __init__(self, P, spec):
        self.P = P
        self.spec = spec
        self.hw = P["head_w"] / 2
        self.hd = P["head_d"] / 2
        self.hh = P["head_h"]
        f = spec["face"]
        self.wctrl = [
            (-1.0, 0.04), (-0.94, 0.36), (-0.84, 0.50 * f["jaw"]),
            (-0.68, 0.80 * f["jaw"]), (-0.45, 0.93), (-0.2, 1.0),
            (0.05, 0.99), (0.32, 0.95), (0.58, 0.88), (0.8, 0.7), (1.0, 0.03),
        ]
        self.dctrl = [
            (-1.0, 0.06), (-0.92, 0.42), (-0.8, 0.66), (-0.6, 0.84),
            (-0.3, 0.94), (0.0, 1.0), (0.3, 0.99), (0.62, 0.9), (0.85, 0.62),
            (1.0, 0.03),
        ]
        self.wsample = catmull(self.wctrl, 6)
        self.dsample = catmull(self.dctrl, 6)

    def _interp(self, rows, u):
        if u <= rows[0][0]:
            return rows[0][1]
        if u >= rows[-1][0]:
            return rows[-1][1]
        for i in range(len(rows) - 1):
            u0, v0 = rows[i]
            u1, v1 = rows[i + 1]
            if u0 <= u <= u1:
                t = (u - u0) / max(1e-6, u1 - u0)
                return lerp(v0, v1, t)
        return rows[-1][1]

    def width(self, u):
        return self._interp(self.wsample, u)

    def depth(self, u):
        return self._interp(self.dsample, u)

    def z_at(self, u):
        return self.P["chin_z"] + (u + 1.0) * 0.5 * self.P["head_h"]

    def point(self, u, theta, offset=0.0):
        w = self.width(u)
        d = self.depth(u)
        x = self.hw * w * math.sin(theta)
        y = -self.hd * d * math.cos(theta)
        z = self.z_at(u)
        # chin and brow shaping
        f = self.spec["face"]
        front = max(0.0, math.cos(theta))
        if u < -0.35:
            y -= front * self.hd * 0.13 * f["chin"] * (-u - 0.35)
        if 0.05 < u < 0.5:
            y -= front * self.hd * 0.020 * f["brow"] * math.exp(-((u - 0.24) ** 2) / 0.02)
        n = Vector((x, y, 0.0))
        if n.length > 1e-6 and offset:
            n.normalize()
            x += n.x * offset
            y += n.y * offset
        return Vector((x, y, z))

    def surface_y(self, x, u):
        """Front (-Y) surface at x for a given head row."""
        w = self.width(u) or 1e-4
        d = self.depth(u)
        s = min(1.0, abs(x) / (self.hw * w))
        y = -self.hd * d * math.sqrt(max(0.0, 1.0 - s * s))
        f = self.spec["face"]
        front = 1.0
        if u < -0.35:
            y -= front * self.hd * 0.13 * f["chin"] * (-u - 0.35)
        if 0.05 < u < 0.5:
            y -= self.hd * 0.020 * f["brow"] * math.exp(-((u - 0.24) ** 2) / 0.02)
        return y

    def u_of_z(self, z):
        return (z - self.P["chin_z"]) / max(1e-6, self.P["head_h"]) * 2.0 - 1.0


def build_head(P, spec, mats, objs):
    shape = HeadShape(P, spec)
    seg = 32
    rows = 26
    verts, faces = [], []
    ring_rows = []
    for i in range(1, rows):
        u = -1.0 + 2.0 * i / rows
        idx = []
        for j in range(seg):
            theta = TAU * j / seg
            verts.append(shape.point(u, theta))
            idx.append(len(verts) - 1)
        ring_rows.append(idx)
    top = len(verts)
    verts.append(Vector((0, 0, P["crown_z"])))
    bot = len(verts)
    verts.append(Vector((0, -shape.hd * 0.1, P["chin_z"])))
    for i in range(len(ring_rows) - 1):
        a, b = ring_rows[i], ring_rows[i + 1]
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((a[j], a[j2], b[j2], b[j]))
    for j in range(seg):
        j2 = (j + 1) % seg
        faces.append((top, ring_rows[-1][j2], ring_rows[-1][j]))
        faces.append((bot, ring_rows[0][j], ring_rows[0][j2]))
    head = add_mesh(spec["id"] + "_head", verts, faces, mats["skin"], {"Head": 1.0})
    objs.append(head)

    # neck
    neck_top_z = P["chin_z"] + 0.012
    path = [Vector((0, 0.004, P["neck_base"] - 0.01)),
            Vector((0, 0.002, lerp(P["neck_base"], neck_top_z, 0.55))),
            Vector((0, 0.0, neck_top_z))]
    radii = [P["neck_r"] * 1.15, P["neck_r"] * 0.95, P["neck_r"] * 0.92]
    wr = [weights_neck(P, p.z) for p in path]
    objs.append(tube(spec["id"] + "_neck", path, radii, [r * 0.96 for r in radii],
                     14, mats["skin"], wr, cap_start=False, cap_end=True))

    # ears
    for side, sx in (("L", 1), ("R", -1)):
        ex = sx * shape.hw * 0.97
        ez = P["chin_z"] + P["head_h"] * 0.56
        objs.append(ellipsoid(
            f"{spec['id']}_ear_{side}", Vector((ex, 0.004, ez)),
            shape.hw * 0.13, shape.hd * 0.15, P["head_h"] * 0.105,
            mats["skin"], {"Head": 1.0}, segments=12, rings=8))
        objs.append(ellipsoid(
            f"{spec['id']}_earin_{side}", Vector((ex - sx * 0.002, -0.004, ez)),
            shape.hw * 0.055, shape.hd * 0.02, P["head_h"] * 0.05,
            mats["skin_dark"], {"Head": 1.0}, segments=10, rings=6))

    build_face(P, spec, mats, objs, shape)
    return shape


def build_face(P, spec, mats, objs, shape):
    from mathutils import Matrix
    cid = spec["id"]
    f = spec["face"]
    hh = P["head_h"]
    hw = shape.hw
    eye_z = P["chin_z"] + hh * 0.525
    eye_dx = hw * 0.365 * f["eyes"]
    es = f["eye_size"] * (hh / 0.225)
    brow_z = eye_z + hh * 0.075
    nose_base_z = eye_z - hh * 0.155 * f["nose"]
    mouth_z = P["chin_z"] + hh * 0.255
    mouth_w = hw * 0.36 * f["mouth"]

    for side, sx in (("L", 1), ("R", -1)):
        x = sx * eye_dx
        u = shape.u_of_z(eye_z)
        y = shape.surface_y(x, u)
        rot = Matrix.Rotation(math.radians(-3.0 * sx), 3, "Y")
        # almond eye
        objs.append(ellipsoid(f"{cid}_eye_{side}", Vector((x, y - 0.0004, eye_z)),
                              hh * 0.044 * es, hh * 0.0032, hh * 0.024 * es,
                              mats["eye_white"], {"Head": 1.0}, segments=16, rings=8,
                              rotation=rot))
        objs.append(ellipsoid(f"{cid}_iris_{side}", Vector((x, y - 0.0038, eye_z)),
                              hh * 0.0270 * es, hh * 0.0022, hh * 0.0270 * es,
                              mats["iris" + side], {"Head": 1.0}, segments=14, rings=6,
                              rotation=rot))
        objs.append(ellipsoid(f"{cid}_pupil_{side}", Vector((x, y - 0.0049, eye_z)),
                              hh * 0.0120 * es, hh * 0.0018, hh * 0.0120 * es,
                              mats["pupil"], {"Head": 1.0}, segments=12, rings=6,
                              rotation=rot))
        objs.append(ellipsoid(f"{cid}_glint_{side}",
                              Vector((x + hh * 0.006, y - 0.0058, eye_z + hh * 0.006)),
                              hh * 0.0045, hh * 0.0010, hh * 0.0045, mats["eye_white"],
                              {"Head": 1.0}, segments=8, rings=5))
        objs.append(torus(f"{cid}_lidlo_{side}", Vector((x, y - 0.0013, eye_z - hh * 0.0015)),
                          hh * 0.040 * es, hh * 0.0014, mats["skin"], {"Head": 1.0},
                          axis="Y", major_seg=16, minor_seg=5,
                          scale=(1.0, 1.0, 0.68), start=math.pi + 0.30, end=TAU - 0.30))
        objs.append(torus(f"{cid}_lash_{side}", Vector((x, y - 0.0032, eye_z + hh * 0.0022)),
                          hh * 0.0425 * es, hh * 0.0016, mats["lash"], {"Head": 1.0},
                          axis="Y", major_seg=14, minor_seg=4,
                          scale=(1.0, 1.0, 0.74), start=0.40, end=math.pi - 0.40))
        if spec["sex"] == "F":
            for lash in range(3):
                lx = x + sx * hh * (0.030 + lash * 0.006)
                lz = eye_z + hh * (0.014 + lash * 0.002)
                objs.append(tube(f"{cid}_eyelash_{side}_{lash}",
                                 [Vector((lx, y - 0.006, lz)),
                                  Vector((lx + sx * hh * 0.010, y - 0.004, lz + hh * 0.008))],
                                 [hh * 0.0016, hh * 0.0008],
                                 [hh * 0.0016, hh * 0.0008], 4, mats["lash"],
                                 {"Head": 1.0}))
        pts = []
        bw = hw * 0.23 * f["brow"]
        for k in range(7):
            t = k / 6.0
            bx = x + (t - 0.5) * 2.0 * bw * sx
            arch = math.sin(t * math.pi)
            bz = brow_z + arch * hh * 0.012 * f["brow"]
            bu = shape.u_of_z(bz)
            by = shape.surface_y(bx, bu) - hh * 0.004
            pts.append(Vector((bx, by, bz)))
        radii = [hh * 0.0055 * (0.65 + math.sin(k / 6.0 * math.pi) * 0.6) for k in range(7)]
        objs.append(tube(f"{cid}_brow_{side}", pts, radii,
                         [r * 0.55 for r in radii], 7, mats["brow"], {"Head": 1.0}))

    # nose: short, rounded, with wings
    bridge_z = eye_z - hh * 0.02
    nb = shape.surface_y(0, shape.u_of_z(bridge_z))
    tip_y = nb - hh * 0.0145 * f["nose"]
    path = [
        Vector((0, nb - hh * 0.001, bridge_z)),
        Vector((0, nb - hh * 0.006 * f["nose"], bridge_z - hh * 0.035)),
        Vector((0, tip_y, nose_base_z + hh * 0.016)),
        Vector((0, tip_y + hh * 0.003, nose_base_z + hh * 0.004)),
        Vector((0, nb - hh * 0.007, nose_base_z - hh * 0.002)),
    ]
    rx = [hh * 0.0060, hh * 0.0070, hh * 0.0115, hh * 0.0120, hh * 0.0092]
    ry = [hh * 0.0040, hh * 0.0050, hh * 0.0085, hh * 0.0078, hh * 0.0052]
    objs.append(tube(f"{cid}_nose", path, rx, ry, 12, mats["skin"],
                     [{"Head": 1.0}] * 5))
    for side, sx in (("L", 1), ("R", -1)):
        objs.append(ellipsoid(
            f"{cid}_wing_{side}",
            Vector((sx * hh * 0.026 * (0.85 + 0.25 * f["nose"]),
                    tip_y + hh * 0.002, nose_base_z + hh * 0.007)),
            hh * 0.0115, hh * 0.0100, hh * 0.0085, mats["skin"], {"Head": 1.0},
            segments=12, rings=8))
        objs.append(ellipsoid(
            f"{cid}_nostril_{side}",
            Vector((sx * hh * 0.014, tip_y - hh * 0.004, nose_base_z + hh * 0.002)),
            hh * 0.0042, hh * 0.0020, hh * 0.0028, mats["skin_dark"],
            {"Head": 1.0}, segments=8, rings=6))

    # mouth: soft smiling bands
    smile = 0.008

    def arc(zc, depth, width=None):
        w = width or mouth_w
        pts = []
        for k in range(11):
            t = -1.0 + 2.0 * k / 10.0
            x = t * w
            z = zc + (t * t) * hh * smile
            u = shape.u_of_z(z)
            y = shape.surface_y(x, u) - depth
            pts.append(Vector((x, y, z)))
        return pts

    up = arc(mouth_z + hh * 0.007, hh * 0.0022)
    lo = arc(mouth_z - hh * 0.006, hh * 0.0028)
    line = arc(mouth_z + hh * 0.0015, hh * 0.0048)
    upr = [hh * 0.0054 * (0.55 + 0.45 * (1 - (k / 5.0 - 1) ** 2)) for k in range(11)]
    lor = [hh * 0.0072 * (0.6 + 0.4 * (1 - (k / 5.0 - 1) ** 2)) for k in range(11)]
    objs.append(tube(f"{cid}_lip_up", up, upr, [r * 0.55 for r in upr], 7,
                     mats["lips"], {"Head": 1.0}))
    objs.append(tube(f"{cid}_lip_lo", lo, lor, [r * 0.65 for r in lor], 7,
                     mats["lips"], {"Head": 1.0}))
    objs.append(tube(f"{cid}_mouth", line, [hh * 0.0015] * 11,
                     [hh * 0.0013] * 11, 5, mats["mouth"], {"Head": 1.0}))

    if spec.get("mature"):
        # Age is modelled, not just labelled: soft nasolabial folds frame the
        # mouth and two shallow forehead creases sit above the brows.
        for side, sx in (("L", 1), ("R", -1)):
            fold = []
            for k in range(5):
                t = k / 4.0
                fz = nose_base_z - hh * (0.012 + 0.078 * t)
                fx = sx * hw * (0.20 + 0.09 * t)
                fu = shape.u_of_z(fz)
                fold.append(Vector((fx, shape.surface_y(fx, fu) - hh * 0.0015, fz)))
            objs.append(tube(
                f"{cid}_nasolabial_{side}", fold,
                [hh * 0.0022, hh * 0.0024, hh * 0.0022, hh * 0.0018, hh * 0.0012],
                [hh * 0.0012] * 5, 5, mats["skin_dark"], {"Head": 1.0}))
        for k in range(2):
            z = brow_z + hh * (0.058 + 0.046 * k)
            pts = []
            for q in range(9):
                t = -1.0 + 2.0 * q / 8.0
                x = t * hw * 0.52
                zz = z + (t * t) * hh * 0.006
                u = shape.u_of_z(zz)
                pts.append(Vector((x, shape.surface_y(x, u) - hh * 0.0012, zz)))
            radii = [hh * 0.0016 * (0.5 + 0.5 * (1.0 - abs(-1.0 + 2.0 * q / 8.0)))
                     for q in range(9)]
            objs.append(tube(f"{cid}_forehead_{k}", pts, radii,
                             [hh * 0.0009] * 9, 4, mats["skin_dark"],
                             {"Head": 1.0}))


# --------------------------------------------------------------------------- #
# hair
# --------------------------------------------------------------------------- #
HAIRLINE = {
    "short_textured": (0.45, 0.27, 0.30),
    "undercut": (0.47, 0.31, 0.22),
    "side_part": (0.46, 0.28, 0.24),
    "curly_short": (0.44, 0.26, 0.26),
    "receding": (0.55, 0.24, 0.30),
    "comb_over": (0.48, 0.27, 0.26),
    "pigtails": (0.41, 0.22, 0.34),
    "long_straight": (0.41, 0.16, 0.52),
    "ponytail": (0.43, 0.19, 0.44),
    "curly_bob": (0.43, 0.16, 0.46),
    "shoulder_wavy": (0.43, 0.16, 0.46),
    "bun_white": (0.45, 0.22, 0.38),
}


def build_hair(P, spec, mats, objs, shape):
    cid = spec["id"]
    style = spec["hair_style"]
    hh = P["head_h"]
    hair = mats["hair"]
    front_u, side_u, back_drop = HAIRLINE.get(style, (0.44, 0.2, 0.28))
    seg = 32

    def hairline(theta):
        f = max(0.0, math.cos(theta))
        b = max(0.0, -math.cos(theta))
        return side_u + (front_u - side_u) * (f ** 1.25) - back_drop * b

    # skull-hugging cap, closed with a thin solidify shell
    rows = 10
    verts, faces, rings = [], [], []
    for i in range(rows + 1):
        v = i / rows
        idx = []
        for j in range(seg):
            theta = TAU * j / seg
            u = lerp(hairline(theta), 0.99, v)
            idx.append(len(verts))
            verts.append(shape.point(u, theta, offset=0.004 + 0.024 * v))
        rings.append(idx)
    for i in range(rows):
        a, b = rings[i], rings[i + 1]
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((a[j], a[j2], b[j2], b[j]))
    cap = add_mesh(cid + "_haircap", verts, faces, hair, {"Head": 1.0}, smooth=True)
    apply_solidify(cap, 0.0045)
    objs.append(cap)

    def strand(name, pts, r0, r1, sides=6):
        radii = [lerp(r0, r1, k / max(1, len(pts) - 1)) for k in range(len(pts))]
        objs.append(tube(name, pts, radii, [r * 0.9 for r in radii], sides,
                         hair, {"Head": 1.0}))

    def lock(prefix, i, theta0, u0, u1, r0, r1, sweep=0.0, lift=0.014, sides=5):
        pts = []
        for k in range(4):
            t = k / 3.0
            u = lerp(u0, u1, t)
            th = theta0 + sweep * t
            pts.append(shape.point(u, th, offset=lift + 0.003 * math.sin(math.pi * t)))
        strand(f"{cid}_{prefix}_{i}", pts, r0, r1, sides)

    if style in ("short_textured", "undercut", "side_part", "receding", "comb_over"):
        count = 42 if style == "short_textured" else 30
        for i in range(count):
            theta = -math.pi + TAU * (i + 0.5) / count
            edge = hairline(theta)
            u_start = 0.92 - 0.22 * ((i * 7) % 5) / 4.0
            u_end = max(edge + 0.10, u_start - 0.26)
            sweep = 0.16 * math.sin(i * 1.3)
            if style == "undercut":
                sweep = 0.34
                if math.cos(theta) < 0.3:
                    u_end = max(u_end, edge + 0.20)
            elif style == "side_part":
                sweep = 0.42 + 0.10 * math.sin(i)
            elif style == "receding":
                sweep = 0.24
                if math.cos(theta) > 0.55:
                    u_end = max(u_end, edge + 0.16)
            elif style == "comb_over":
                sweep = 0.58
            lock("lock", i, theta, u_start, u_end, hh * 0.013,
                 hh * 0.005, sweep, lift=0.010 + 0.004 * math.sin(i))


    elif style == "curly_short":
        for i in range(34):
            theta = TAU * (i / 34) + 0.21
            u = 0.15 + 0.78 * ((i * 7) % 13) / 12.0
            p = shape.point(u, theta, 0.024)
            r = hh * (0.024 + 0.007 * math.sin(i * 3.1))
            objs.append(ellipsoid(f"{cid}_curl_{i}", p, r, r * 1.03, r * 0.92, hair,
                                  {"Head": 1.0}, segments=8, rings=6))

    elif style == "pigtails":
        for i in range(7):
            theta = (i / 6.0 - 0.5) * 1.5
            lock("fringe", i, theta, 0.66, 0.40, hh * 0.016, hh * 0.008, 0.05)
        for side, sx in (("L", 1), ("R", -1)):
            base = Vector((sx * shape.hw * 0.94, 0.012, P["chin_z"] + hh * 0.52))
            objs.append(torus(f"{cid}_tie_{side}", base, hh * 0.036, hh * 0.010,
                              mats["accent"], {"Head": 1.0}, axis="Y",
                              major_seg=12, minor_seg=6, scale=(1, 1, 0.8)))
            for k in range(6):
                pts = []
                spread = (k - 2.5) * 0.012
                p = base + Vector((sx * 0.008, spread, 0.005))
                for s in range(4):
                    p = p + Vector((sx * 0.012 - sx * s * 0.004, spread * 0.3, -hh * 0.105))
                    pts.append(p.copy())
                strand(f"{cid}_tail_{side}_{k}", pts, hh * 0.017, hh * 0.011, 6)

    else:
        length = {
            "long_straight": 0.42, "ponytail": 0.30, "shoulder_wavy": 0.30,
            "curly_bob": 0.17, "bun_white": 0.10,
        }[style]
        count = 26 if style != "curly_bob" else 22
        for i in range(count):
            theta = math.radians(48) + (TAU - math.radians(96)) * (i / (count - 1))
            u = 0.30 + 0.55 * ((i * 5) % 11) / 10.0
            start = shape.point(u, theta, 0.018)
            pts = [start]
            p = start.copy()
            outward = Vector((start.x, start.y, 0))
            outward = outward.normalized() if outward.length > 1e-4 else Vector((0, 1, 0))
            drop = hh * (0.06 + length) * (0.85 + 0.3 * math.sin(i * 2.2))
            wave = 0.016 if style in ("shoulder_wavy", "curly_bob") else 0.004
            for k in range(4):
                step = drop / 4.0
                p = p + outward * (step * 0.10) + Vector((math.sin(i + k * 1.2) * wave, 0, -step))
                pts.append(p.copy())
            strand(f"{cid}_hair_{i}", pts, hh * 0.024, hh * 0.012, 6)
        if style == "ponytail":
            tie = Vector((0, shape.hd * 0.92, P["chin_z"] + hh * 0.74))
            objs.append(torus(f"{cid}_hairtie", tie, hh * 0.034, hh * 0.010,
                              mats["accent"], {"Head": 1.0}, axis="Y",
                              major_seg=12, minor_seg=6))
            for k in range(9):
                p = tie + Vector(((k - 4) * 0.007, 0.005, 0))
                pts = [p.copy()]
                for s in range(5):
                    p = p + Vector((0, 0.012 - s * 0.002, -hh * 0.10))
                    pts.append(p.copy())
                strand(f"{cid}_pony_{k}", pts, hh * 0.017, hh * 0.008, 6)
        if style == "bun_white":
            bun_c = Vector((0, shape.hd * 0.55, P["crown_z"] - hh * 0.13))
            objs.append(ellipsoid(f"{cid}_bun", bun_c, hh * 0.115, hh * 0.105, hh * 0.095,
                                  hair, {"Head": 1.0}, segments=16, rings=10))
            for k in range(7):
                a = TAU * k / 7
                pts = [bun_c + Vector((math.cos(a) * hh * 0.09, math.sin(a) * hh * 0.085, 0)),
                       bun_c + Vector((math.cos(a) * hh * 0.125, math.sin(a) * hh * 0.115, -hh * 0.045))]
                strand(f"{cid}_bunw_{k}", pts, hh * 0.012, hh * 0.005, 5)
        if style in ("long_straight", "shoulder_wavy"):
            for side, sx in (("L", 1), ("R", -1)):
                for k in range(3):
                    theta = sx * math.radians(58 + k * 9)
                    start = shape.point(0.44, theta, 0.02)
                    pts = [start]
                    p = start.copy()
                    for q in range(5):
                        p = p + Vector((sx * 0.004, -0.003, -hh * (0.10 + k * 0.01)))
                        pts.append(p.copy())
                    strand(f"{cid}_frame_{side}_{k}", pts, hh * 0.016, hh * 0.007, 5)
        if style == "curly_bob":
            for i in range(12):
                a = math.radians(40) + math.radians(280) * i / 11.0
                c = shape.point(0.0, a, 0.03) + Vector((0, 0, -hh * 0.05))
                curl_mat = mats["hair_grey"] if spec.get("mature") and i % 4 == 0 else hair
                objs.append(ellipsoid(f"{cid}_bobcurl_{i}", c, hh * 0.032, hh * 0.03,
                                      hh * 0.034, curl_mat, {"Head": 1.0},
                                      segments=8, rings=6))

    # soft fringe over the forehead seam
    if style not in ("curly_short",):
        for i in range(12):
            theta = (i / 11.0 - 0.5) * 1.7
            top_u = hairline(theta) + 0.05
            pts = []
            for k in range(4):
                t = k / 3.0
                u = lerp(top_u, hairline(theta) - 0.045, t)
                pts.append(shape.point(u, theta + 0.05 * math.sin(i + k * 0.7),
                                       0.0045 + 0.0035 * (1 - t)))
            rr = [hh * 0.0085, hh * 0.0072, hh * 0.0050, hh * 0.0022]
            fringe_mat = mats["hair_grey"] if spec.get("mature") and i % 3 == 0 else hair
            objs.append(tube(f"{cid}_fringe3_{i}", pts, rr, [r * 0.7 for r in rr],
                             5, fringe_mat, {"Head": 1.0}))


# --------------------------------------------------------------------------- #
# body, hands, legs
# --------------------------------------------------------------------------- #
def build_body(P, spec, mats, objs):
    cid = spec["id"]
    zs = []
    z = P["crotch_z"] - 0.02 * P["H"]
    while z < P["neck_base"]:
        zs.append(z)
        z += (P["neck_base"] - zs[0]) / 22.0
    profile = []
    wrings = []
    for zz in zs:
        rx, ry, yoff = sample_torso(P, zz)
        profile.append((zz, rx, ry, yoff))
        wrings.append(weights_torso(P, zz))
    objs.append(loft_z(cid + "_torso", profile, 28, mats["skin"], wrings,
                       cap_start=True, cap_end=True))

    for side, sx in (("L", 1), ("R", -1)):
        arm_path, arm_t, arm_r = arm_samples(P, side)
        radii = [r for r in arm_r]
        wr = [weights_arm(P, t, side) for t in arm_t]
        objs.append(tube(f"{cid}_arm_{side}", arm_path, radii,
                         [r * 0.94 for r in radii], 16, mats["skin"], wr,
                         cap_start=False, cap_end=True))
        build_hand(P, spec, mats, objs, side)
        leg_path, leg_t, leg_r = leg_samples(P, side)
        wrl = [weights_leg(P, t, side) for t in leg_t]
        objs.append(tube(f"{cid}_leg_{side}", leg_path, leg_r,
                         [r * 0.96 for r in leg_r], 16, mats["skin"], wrl,
                         cap_start=True, cap_end=True))


def arm_samples(P, side):
    sx = 1 if side == "L" else -1
    shoulder = Vector((sx * P["shoulder_joint"].x * 0.80, 0.0,
                       P["shoulder_joint"].z - 0.03))
    elbow = Vector((sx * P["elbow"].x, P["elbow"].y, P["elbow"].z))
    wrist = Vector((sx * P["wrist"].x, P["wrist"].y, P["wrist"].z))
    ctrl = [(0.0, shoulder.x, shoulder.y, shoulder.z),
            (0.53, elbow.x, elbow.y, elbow.z),
            (1.0, wrist.x, wrist.y, wrist.z)]
    dense = catmull(ctrl, 5)
    path, ts = [], []
    for row in dense:
        t, x, y, z = row
        path.append(Vector((x, y, z)))
        ts.append(t)
    base = P["H"] / 1.75
    ctrl = [(0.0, 0.050), (0.35, 0.041), (0.53, 0.036), (0.72, 0.032), (1.0, 0.025)]
    radii = [pchip(ctrl, t) * base for t in ts]
    if side == "R":
        radii = [r * 0.99 for r in radii]
    return path, ts, radii


def leg_samples(P, side):
    sx = 1 if side == "L" else -1
    hip = Vector((sx * P["hip_joint"].x, P["hip_joint"].y, P["hip_joint"].z))
    knee = Vector((sx * P["knee"].x, P["knee"].y, P["knee"].z))
    ankle = Vector((sx * P["ankle"].x, P["ankle"].y, P["ankle"].z))
    ctrl = [(0.0, hip.x, hip.y, hip.z), (0.55, knee.x, knee.y, knee.z),
            (1.0, ankle.x, ankle.y, ankle.z)]
    dense = catmull(ctrl, 5)
    path, ts = [], []
    for row in dense:
        t, x, y, z = row
        path.append(Vector((x, y, z)))
        ts.append(t)
    base = P["H"] / 1.75
    ctrl = [(0.0, 0.078 * P["build"]), (0.25, 0.064), (0.5, 0.050),
            (0.58, 0.048), (0.75, 0.043), (1.0, 0.031)]
    radii = [pchip(ctrl, t) * base for t in ts]
    return path, ts, radii


def build_hand(P, spec, mats, objs, side):
    cid = spec["id"]
    sx = 1 if side == "L" else -1
    wrist = Vector((sx * P["wrist"].x, P["wrist"].y, P["wrist"].z))
    direction = Vector((sx * 0.05, -0.04, -1.0)).normalized()
    side_axis = Vector((0, 1, 0))
    front = Vector((0, -1, 0))
    rr = P["H"] / 1.75
    palm_c = wrist + direction * (P["H"] * 0.032)
    palm_len = P["H"] * 0.058
    pts = [wrist + direction * 0.008, palm_c, palm_c + direction * palm_len * 0.55]
    objs.append(tube(f"{cid}_palm_{side}", pts,
                     [0.019 * rr, 0.023 * rr, 0.021 * rr],
                     [0.036 * rr, 0.041 * rr, 0.039 * rr], 12,
                     mats["skin"], [{"Hand_" + side: 1.0}] * 3, cap_start=False))
    finger_base = palm_c + direction * palm_len * 0.55
    for i in range(4):
        offset = (i - 1.5) * 0.023 * rr
        length = P["H"] * (0.036 if i in (0, 3) else 0.042)
        start_f = finger_base + side_axis * offset
        mid = start_f + direction * (length * 0.5) + front * 0.003
        end = mid + direction * (length * 0.26) + front * 0.020
        objs.append(tube(f"{cid}_finger_{side}_{i}", [start_f, mid, end],
                         [0.0100 * rr, 0.0094 * rr, 0.0072 * rr],
                         [0.0102 * rr, 0.0096 * rr, 0.0074 * rr], 6,
                         mats["skin"], [{"Hand_" + side: 1.0}] * 3))
    base = wrist + direction * (P["H"] * 0.045) + side_axis * (-sx * 0.024 * rr)
    thumb_mid = base + front * 0.024 + direction * 0.022
    thumb_end = thumb_mid + front * 0.010 + direction * 0.018
    objs.append(tube(f"{cid}_thumb_{side}", [base, thumb_mid, thumb_end],
                     [0.0115 * rr, 0.0105 * rr, 0.0075 * rr],
                     [0.0115 * rr, 0.0105 * rr, 0.0075 * rr], 6,
                     mats["skin"], [{"Hand_" + side: 1.0}] * 3))


# --------------------------------------------------------------------------- #
# clothing
# --------------------------------------------------------------------------- #
def surface_patch(name, P, z0, z1, ang0, ang1, offset, mat, weight_fn, rows=4, cols=10):
    verts, faces, weights = [], [], []
    for iz in range(rows + 1):
        z = lerp(z0, z1, iz / rows)
        rx, ry, yoff = sample_torso(P, z)
        for ia in range(cols + 1):
            a = lerp(ang0, ang1, ia / cols)
            verts.append(Vector(((rx + offset) * math.sin(a),
                                 yoff - (ry + offset) * math.cos(a), z)))
            weights.append(weight_fn(z))
    for iz in range(rows):
        for ia in range(cols):
            a = iz * (cols + 1) + ia
            faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    return add_mesh(name, verts, faces, mat, weights, smooth=True)


def build_top(P, spec, mats, objs):
    cid = spec["id"]
    top = spec["top"]
    kind = top["kind"]
    H = P["H"]
    hem_map = {"hoodie": 0.495, "jacket": 0.50, "tee": 0.52, "polo": 0.515,
               "sweater": 0.48, "shirt": 0.50, "blouse": 0.52, "cardigan": 0.49}
    hem_z = H * hem_map.get(kind, 0.51)
    neck_z = P["neck_base"] + 0.004
    rows = 14
    profile, wrings = [], []
    for i in range(rows + 1):
        z = lerp(hem_z, neck_z, i / rows)
        rx, ry, yoff = sample_torso(P, z)
        extra = 0.014 if kind in ("tee", "blouse") else 0.018
        profile.append((z, rx + extra, ry + extra, yoff))
        wrings.append(weights_torso(P, z))
    shell = loft_z(cid + "_top", profile, 28, mats["top"], wrings,
                   cap_start=False, cap_end=False)
    add_bust(shell, P, spec)
    apply_solidify(shell, 0.008)
    objs.append(shell)

    # sleeves
    sleeve_t = {"short": 0.30, "three_quarter": 0.72, "long": 0.96}[top.get("sleeve", "long")]
    for side, sx in (("L", 1), ("R", -1)):
        arm_path, arm_t, arm_r = arm_samples(P, side)
        path, radii, wr = [], [], []
        for i, (p, t, r) in enumerate(zip(arm_path, arm_t, arm_r)):
            if t > sleeve_t:
                break
            path.append(p)
            radii.append(r + 0.013)
            wr.append(weights_arm(P, t, side))
        if len(path) >= 2:
            objs.append(tube(f"{cid}_sleeve_{side}", path, radii,
                             [r * 0.92 for r in radii], 16, mats["top"], wr,
                             cap_start=False, cap_end=False))
            cuff = ellipsoid(f"{cid}_cuff_{side}", path[-1],
                             radii[-1] * 1.06, radii[-1] * 0.98, radii[-1] * 0.34,
                             mats["trim"], {"LowerArm_" + side: 1.0} if sleeve_t > 0.8
                             else {"UpperArm_" + side: 1.0},
                             segments=12, rings=6)
            objs.append(cuff)

    # collar
    neck_r = sample_torso(P, P["neck_base"])[0]
    collar_mat = mats["top"] if kind == "hoodie" else mats["trim"]
    objs.append(torus(f"{cid}_collar", Vector((0, 0.004, neck_z)),
                      neck_r * 0.92, 0.012 if kind == "hoodie" else 0.014,
                      collar_mat, {"Neck": 0.5, "Chest": 0.5},
                      axis="Z", major_seg=22, minor_seg=7, scale=(1.05, 1.0, 1.0)))

    # neckline / placket / details
    if kind in ("shirt", "polo", "blouse", "cardigan", "jacket", "sweater", "hoodie"):
        if kind != "hoodie":
            bw = sample_torso(P, P["chest_z"])[0] * 0.16
            h = P["chest_z"] - hem_z + 0.02
            placket = rounded_box(f"{cid}_placket",
                                  Vector((0, -sample_torso(P, (P["chest_z"] + hem_z) / 2)[1] - 0.012,
                                          (P["chest_z"] + hem_z) / 2)),
                                  (bw, 0.012, h / 2), mats["trim"], {"Chest": 0.35, "Spine": 0.35, "Hips": 0.3},
                                  radius=0.004)
            objs.append(placket)
            for k in range(4):
                bz = lerp(hem_z + 0.05, P["chest_z"], k / 3.0)
                rx, ry, yoff = sample_torso(P, bz)
                objs.append(ellipsoid(f"{cid}_btn_{k}", Vector((0, -ry - 0.024, bz)),
                                      0.006, 0.004, 0.006, mats["button"],
                                      {"Chest": 0.5, "Spine": 0.5}, segments=8, rings=5))
        if kind == "hoodie":
            hood_c = Vector((0, 0.085, P["neck_base"] + 0.005))
            objs.append(ellipsoid(f"{cid}_hood", hood_c,
                                  neck_r * 2.1, neck_r * 1.3, neck_r * 1.7,
                                  mats["top"], {"Chest": 0.45, "Neck": 0.55},
                                  segments=16, rings=10))
            for side, sx in (("L", 1), ("R", -1)):
                objs.append(tube(f"{cid}_string_{side}",
                                 [Vector((sx * 0.018, -neck_r * 1.5, P["neck_base"] + 0.01)),
                                  Vector((sx * 0.020, -neck_r * 1.7, P["chest_z"] - 0.03))],
                                 [0.004, 0.004], [0.004, 0.004], 5, mats["trim"],
                                 [{"Chest": 1.0}] * 2))
            pocket_z0, pocket_z1 = hem_z + 0.045, hem_z + 0.125
            pouch = surface_patch(f"{cid}_pocket", P, pocket_z0, pocket_z1,
                                  -0.5, 0.5, 0.021, mats["top_dark"],
                                  lambda z: weights_torso(P, z), rows=4, cols=10)
            for v in pouch.data.vertices:
                tz = (v.co.z - pocket_z0) / max(1e-5, pocket_z1 - pocket_z0)
                v.co.y -= 0.009 * math.sin(math.pi * max(0.0, min(1.0, tz)))
            pouch.data.update()
            apply_solidify(pouch, 0.006)
            objs.append(pouch)
            # ribbed hem
            objs.append(torus(f"{cid}_hemband", Vector((0, 0, hem_z + 0.02)),
                              sample_torso(P, hem_z + 0.02)[0] + 0.012, 0.012,
                              mats["top"], {"Hips": 1.0}, axis="Z",
                              major_seg=26, minor_seg=6, scale=(1.0, 0.8, 1.0)))
        if kind == "jacket":
            # zip line
            objs.append(rounded_box(f"{cid}_zip",
                                    Vector((0, -sample_torso(P, P["chest_z"])[1] - 0.026,
                                            (P["chest_z"] + hem_z) / 2)),
                                    (0.005, 0.005, (P["chest_z"] - hem_z) / 2), mats["metal"],
                                    {"Chest": 0.4, "Spine": 0.4, "Hips": 0.2}, radius=0.002))
            objs.append(torus(f"{cid}_hemband", Vector((0, 0, hem_z + 0.02)),
                              sample_torso(P, hem_z + 0.02)[0] + 0.012, 0.013,
                              mats["trim"], {"Hips": 1.0}, axis="Z",
                              major_seg=26, minor_seg=6, scale=(1.0, 0.82, 1.0)))
        if kind == "sweater" or kind == "blouse":
            objs.append(torus(f"{cid}_hemband", Vector((0, 0, hem_z + 0.015)),
                              sample_torso(P, hem_z + 0.015)[0] + 0.012, 0.012,
                              mats["trim"], {"Hips": 1.0}, axis="Z",
                              major_seg=26, minor_seg=6, scale=(1.0, 0.82, 1.0)))

    # shirt collar flaps
    if kind in ("shirt", "polo", "blouse"):
        for side, sx in (("L", 1), ("R", -1)):
            objs.append(rounded_box(
                f"{cid}_flap_{side}",
                Vector((sx * neck_r * 0.75, -neck_r * 0.9, P["neck_base"] - 0.01)),
                (neck_r * 0.45, 0.009, neck_r * 0.55), mats["trim"],
                {"Chest": 0.7, "Neck": 0.3}, radius=0.004))
    # cardigan open front hint
    if kind == "cardigan":
        for side, sx in (("L", 1), ("R", -1)):
            objs.append(rounded_box(
                f"{cid}_cardigan_edge_{side}",
                Vector((sx * 0.035, -sample_torso(P, P["chest_z"])[1] - 0.028,
                        (P["chest_z"] + hem_z) / 2)),
                (0.014, 0.008, (P["chest_z"] - hem_z) / 2), mats["trim"],
                {"Chest": 0.4, "Spine": 0.4, "Hips": 0.2}, radius=0.004))


def add_bust(ob, P, spec):
    if spec["sex"] != "F" or P["age"] <= 12:
        return
    hh = P["head_h"]
    cz = P["chest_z"] - 0.01
    amp = P["chest_x"] * 0.30
    for v in ob.data.vertices:
        if v.co.y >= 0:
            continue
        for sx in (-1, 1):
            cx = sx * P["chest_x"] * 0.38
            d = ((v.co.x - cx) / (P["chest_x"] * 0.42)) ** 2 + ((v.co.z - cz) / (hh * 0.30)) ** 2
            if d < 2.2:
                v.co.y -= amp * math.exp(-d)
    ob.data.update()


def build_bottom(P, spec, mats, objs):
    cid = spec["id"]
    kind = spec["bottom"]["kind"]
    H = P["H"]
    waist_z = P["waist_z"] + 0.012 * H
    if kind == "skirt":
        top_prof, wrings = [], []
        length = spec["bottom"].get("length", 0.7)
        end_z = lerp(P["waist_z"], P["knee_z"], length)
        rows = 12
        for i in range(rows + 1):
            t = i / rows
            z = lerp(waist_z, end_z, t)
            rx, ry, yoff = sample_torso(P, min(z, P["waist_z"]))
            flare = 1.0 + 0.55 * t ** 1.5
            top_prof.append((z, rx * flare + 0.008, ry * flare + 0.010, yoff))
            wrings.append(weights_torso(P, z))
        skirt = loft_z(cid + "_skirt", top_prof, 30, mats["bottom"], wrings,
                       cap_start=False, cap_end=False)
        # wavy hem
        for v in skirt.data.vertices:
            if abs(v.co.z - end_z) < 0.02:
                a = math.atan2(v.co.x, -v.co.y)
                v.co.z += math.sin(a * 5.0) * 0.012
        apply_solidify(skirt, 0.008)
        objs.append(skirt)
        # legs (tights)
        for side, sx in (("L", 1), ("R", -1)):
            leg_path, leg_t, leg_r = leg_samples(P, side)
            path = [p for p, t in zip(leg_path, leg_t) if t > 0.18]
            ts = [t for t in leg_t if t > 0.18]
            radii = [r * 0.92 + 0.006 for p, t, r in zip(leg_path, leg_t, leg_r) if t > 0.18]
            objs.append(tube(f"{cid}_tights_{side}", path, radii, radii, 14,
                             mats["bottom2"], [weights_leg(P, t, side) for t in ts],
                             cap_start=False))
        return

    # trousers / jeans / chinos / leggings / shorts
    extra = 0.018 if kind in ("jeans", "trousers") else 0.014
    hip_rows, wrings = [], []
    rows = 8
    for i in range(rows + 1):
        t = i / rows
        z = lerp(waist_z, P["crotch_z"] - 0.035 * H, t)
        rx, ry, yoff = sample_torso(P, max(z, P["crotch_z"] - 0.02 * H))
        taper = 1.0 - 0.42 * smoothstep(0.55, 1.0, t)
        hip_rows.append((z, rx * taper + extra, ry * taper + extra, yoff))
        wrings.append(weights_torso(P, z))
    objs.append(loft_z(cid + "_hips", hip_rows, 26, mats["bottom"], wrings,
                       cap_start=False, cap_end=True))
    shorts = kind == "shorts"
    for side, sx in (("L", 1), ("R", -1)):
        leg_path, leg_t, leg_r = leg_samples(P, side)
        end_t = 0.48 if shorts else 1.0
        path, radii, wr = [], [], []
        for p, t, r in zip(leg_path, leg_t, leg_r):
            if t > end_t:
                break
            baggy = 0.013 if kind in ("jeans", "chinos") else 0.011
            if kind == "leggings":
                baggy = 0.007
            radii.append(r + baggy)
            path.append(p)
            wr.append(weights_leg(P, t, side))
        objs.append(tube(f"{cid}_pant_{side}", path, radii, radii, 18,
                         mats["bottom"], wr, cap_start=False, cap_end=False))
        # cuff band
        cuff_r = radii[-1] + 0.005
        objs.append(torus(f"{cid}_cuff_b_{side}", path[-1],
                          cuff_r * 0.9, 0.012, mats["bottom2"],
                          {("Shin_" + side if end_t > 0.6 else "Thigh_" + side): 1.0},
                          axis="Z", major_seg=14, minor_seg=6, scale=(1, 1, 0.8)))
    # belts are skipped: the tops are untucked and would clip through them


def build_shoes(P, spec, mats, objs):
    cid = spec["id"]
    H = P["H"]
    foot_len = P["foot_len"]
    for side, sx in (("L", 1), ("R", -1)):
        x = sx * P["ankle"].x
        ankle_z = P["ankle_z"]
        sections = [
            (0.070 * foot_len / 0.25, 0.050, 0.0, ankle_z + 0.016),
            (0.035 * foot_len / 0.25, 0.056, 0.0, ankle_z + 0.030),
            (-0.020 * foot_len / 0.25, 0.059, 0.0, ankle_z + 0.020),
            (-0.075 * foot_len / 0.25, 0.057, 0.0, ankle_z + 0.002),
            (-0.135 * foot_len / 0.25, 0.052, 0.0, 0.048 * H / 1.75),
            (-0.185 * foot_len / 0.25, 0.040, 0.0, 0.036 * H / 1.75),
        ]
        # build from toe to heel for consistent winding
        verts, faces = [], []
        seg = 14
        for (yy, hw, zb, zt) in sections:
            zc = (zb + zt) / 2
            hz = max(0.008, (zt - zb) / 2)
            for j in range(seg):
                a = TAU * j / seg
                ca, sa = math.cos(a), math.sin(a)
                px = x + hw * math.copysign(abs(sa) ** 0.65, sa)
                pz = zc - hz * math.copysign(abs(ca) ** 0.65, ca)
                verts.append(Vector((px, P["ankle"].y + yy, pz)))
        for i in range(len(sections) - 1):
            base, nxt = i * seg, (i + 1) * seg
            for j in range(seg):
                j2 = (j + 1) % seg
                faces.append((base + j, base + j2, nxt + j2, nxt + j))
        c0 = len(verts)
        verts.append(Vector((x, P["ankle"].y + sections[0][0], (sections[0][2] + sections[0][3]) / 2)))
        c1 = len(verts)
        verts.append(Vector((x, P["ankle"].y + sections[-1][0], (sections[-1][2] + sections[-1][3]) / 2)))
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((c0, j2, j))
            base = (len(sections) - 1) * seg
            faces.append((c1, base + j, base + j2))
        objs.append(add_mesh(f"{cid}_shoe_{side}", verts, faces, mats["shoe"],
                             {"Foot_" + side: 1.0}))
        # sole
        sv, sf = [], []
        for (yy, hw, zb, zt) in sections:
            for j in range(seg):
                a = TAU * j / seg
                ca, sa = math.cos(a), math.sin(a)
                px = x + (hw + 0.004) * math.copysign(abs(sa) ** 0.7, sa)
                pz = 0.012 - 0.012 * math.copysign(abs(ca) ** 0.7, ca)
                sv.append(Vector((px, P["ankle"].y + yy, pz)))
        for i in range(len(sections) - 1):
            base, nxt = i * seg, (i + 1) * seg
            for j in range(seg):
                j2 = (j + 1) % seg
                sf.append((base + j, base + j2, nxt + j2, nxt + j))
        cs0 = len(sv)
        sv.append(Vector((x, P["ankle"].y + sections[0][0], 0.008)))
        cs1 = len(sv)
        sv.append(Vector((x, P["ankle"].y + sections[-1][0], 0.008)))
        for j in range(seg):
            j2 = (j + 1) % seg
            sf.append((cs0, j2, j))
            base = (len(sections) - 1) * seg
            sf.append((cs1, base + j, base + j2))
        objs.append(add_mesh(f"{cid}_sole_{side}", sv, sf, mats["sole"],
                             {"Foot_" + side: 1.0}))
        # laces
        for k in range(3):
            y = P["ankle"].y - foot_len * (0.10 + k * 0.09)
            z = ankle_z + 0.004 - k * 0.006
            objs.append(tube(f"{cid}_lace_{side}_{k}",
                             [Vector((x - 0.028, y, z)), Vector((x, y - 0.004, z + 0.006)),
                              Vector((x + 0.028, y, z))],
                             [0.0035] * 3, [0.0035] * 3, 5, mats["lace"],
                             [{"Foot_" + side: 1.0}] * 3))
        # toe cap
        objs.append(ellipsoid(f"{cid}_toecap_{side}",
                              Vector((x, P["ankle"].y - foot_len * 0.80, 0.022)),
                              0.042 * H / 1.75, foot_len * 0.18, 0.020 * H / 1.75,
                              mats["shoe"], {"Toe_" + side: 0.6, "Foot_" + side: 0.4},
                              segments=12, rings=6))
        # ankle sock
        objs.append(ellipsoid(f"{cid}_sock_{side}",
                              Vector((x, P["ankle"].y, ankle_z + 0.018)),
                              0.045 * H / 1.75, 0.045 * H / 1.75, 0.03 * H / 1.75,
                              mats["sock"], {"Foot_" + side: 1.0}, segments=12, rings=6))


# --------------------------------------------------------------------------- #
# accessories
# --------------------------------------------------------------------------- #
def build_accessories(P, spec, mats, objs, shape):
    cid = spec["id"]
    H = P["H"]
    hh = P["head_h"]
    acc = spec.get("accessories", [])
    eye_z = P["chin_z"] + hh * 0.565

    if "glasses" in acc:
        for side, sx in (("L", 1), ("R", -1)):
            ex = sx * shape.hw * 0.37 * spec["face"]["eyes"]
            yy = shape.surface_y(ex, shape.u_of_z(eye_z)) - 0.014
            objs.append(torus(f"{cid}_glass_{side}", Vector((ex, yy, eye_z)),
                              hh * 0.072, 0.0025, mats["metal"], {"Head": 1.0},
                              axis="Y", major_seg=18, minor_seg=5, scale=(1.05, 1.0, 0.72)))
            objs.append(tube(f"{cid}_glassarm_{side}",
                             [Vector((ex + sx * hh * 0.07, yy, eye_z)),
                              Vector((ex + sx * hh * 0.075, yy + hh * 0.06, eye_z + hh * 0.01)),
                              Vector((ex + sx * hh * 0.06, yy + hh * 0.19, eye_z + hh * 0.03))],
                             [0.0018] * 3, [0.0018] * 3, 5, mats["metal"],
                             [{"Head": 1.0}] * 3))
        objs.append(tube(f"{cid}_glassbridge",
                         [Vector((-hh * 0.03, shape.surface_y(-hh * 0.03, shape.u_of_z(eye_z)) - 0.014, eye_z)),
                          Vector((hh * 0.03, shape.surface_y(hh * 0.03, shape.u_of_z(eye_z)) - 0.014, eye_z))],
                         [0.0025] * 2, [0.0025] * 2, 5, mats["metal"],
                         [{"Head": 1.0}] * 2))

    if "backpack" in acc:
        back = Vector((0, P["chest_d"] * 0.6 + 0.11, P["chest_z"] - 0.04))
        objs.append(rounded_box(f"{cid}_pack", back,
                                (P["shoulder_x"] * 0.62, 0.075, P["H"] * 0.16),
                                mats["bag"], {"Chest": 1.0}, radius=0.028))
        objs.append(rounded_box(f"{cid}_packpocket",
                                back + Vector((0, 0.05, -0.04)),
                                (P["shoulder_x"] * 0.45, 0.02, P["H"] * 0.07),
                                mats["bag2"], {"Chest": 1.0}, radius=0.014))
    if "headphones" in acc:
        for side, sx in (("L", 1), ("R", -1)):
            c = Vector((sx * P["neck_r"] * 1.9, 0.02, P["neck_base"] + 0.045))
            objs.append(ellipsoid(f"{cid}_hp_{side}", c, 0.035, 0.028, 0.045,
                                  mats["accent"], {"Neck": 1.0}, segments=12, rings=8))
            objs.append(ellipsoid(f"{cid}_hppad_{side}", c + Vector((-sx * 0.014, 0, 0)),
                                  0.020, 0.025, 0.038, mats["trim"], {"Neck": 1.0},
                                  segments=10, rings=8))
        objs.append(torus(f"{cid}_hpband", Vector((0, 0.02, P["neck_base"] + 0.045)),
                          P["neck_r"] * 1.9, 0.011, mats["accent"], {"Neck": 1.0},
                          axis="Z", major_seg=18, minor_seg=6, scale=(1, 0.7, 1)))

    if "watch" in acc:
        wrist = Vector((P["wrist"].x, P["wrist"].y, P["wrist"].z))
        objs.append(torus(f"{cid}_watch", wrist, 0.036, 0.010, mats["accent"],
                          {"Hand_L": 1.0}, axis="Z", major_seg=14, minor_seg=5,
                          scale=(1, 1, 0.6)))
        objs.append(ellipsoid(f"{cid}_watchface", wrist + Vector((0.036, 0, 0)),
                              0.008, 0.016, 0.014, mats["metal"], {"Hand_L": 1.0},
                              segments=10, rings=6))

    if "shoulder_bag" in acc:
        bag_c = Vector((-P["hip_x"] * 1.05, -0.02, P["waist_z"] - 0.02))
        objs.append(rounded_box(f"{cid}_bag", bag_c,
                                (0.06, 0.035, 0.10), mats["bag"], {"Spine": 1.0},
                                radius=0.018))
        objs.append(tube(f"{cid}_bagstrap",
                         [Vector((0, P["chest_d"] * 0.55, P["shoulder_z"] - 0.01)),
                          Vector((P["hip_x"] * 0.8, 0.02, P["chest_z"])),
                          Vector((P["hip_x"] * 1.02, 0.0, P["waist_z"]))],
                         [0.012] * 3, [0.004] * 3, 5, mats["bag"],
                         [{"Chest": 0.6, "Spine": 0.4}] * 3))

    if "handbag" in acc:
        wrist = Vector((-P["wrist"].x, P["wrist"].y, P["wrist"].z))
        c = wrist + Vector((-0.02, -0.01, -0.10))
        objs.append(rounded_box(f"{cid}_handbag", c, (0.055, 0.032, 0.085),
                                mats["bag"], {"Hand_R": 1.0}, radius=0.014))
        objs.append(torus(f"{cid}_handbag_handle", c + Vector((0, 0, 0.085)),
                          0.045, 0.006, mats["bag2"], {"Hand_R": 1.0},
                          axis="Y", major_seg=14, minor_seg=5, scale=(1, 1, 0.9)))

    if "moustache" in acc:
        mz = P["chin_z"] + hh * 0.255 + hh * 0.018
        span = shape.hw * 0.20
        for side, sx in (("L", 1), ("R", -1)):
            pts = []
            for k in range(4):
                t = k / 3.0
                x = sx * span * t
                u = shape.u_of_z(mz)
                y = shape.surface_y(x, u) - hh * 0.0045
                pts.append(Vector((x, y, mz - hh * 0.006 * t)))
            objs.append(tube(f"{cid}_moustache_{side}", pts,
                             [hh * 0.0060, hh * 0.0066, hh * 0.0052, hh * 0.0022],
                             [hh * 0.0030] * 4, 6, mats["facial_hair"],
                             {"Head": 1.0}))

    if "necklace" in acc:
        objs.append(torus(f"{cid}_necklace", Vector((0, -0.005, P["neck_base"] - 0.005)),
                          P["neck_r"] * 1.35, 0.0035, mats["metal"], {"Neck": 1.0},
                          axis="Z", major_seg=18, minor_seg=5, scale=(1, 1, 0.7)))


# --------------------------------------------------------------------------- #
# skeleton
# --------------------------------------------------------------------------- #
def make_skeleton(P):
    sx = 1
    bones = [
        dict(name="Root", head=(0, 0, 0), tail=(0, 0, 0.10)),
        dict(name="Hips", head=(0, 0, P["hip_z"]), tail=(0, 0, P["waist_z"]), parent="Root"),
        dict(name="Spine", head=(0, 0, P["waist_z"]), tail=(0, 0, P["chest_z"]), parent="Hips", connect=True),
        dict(name="Chest", head=(0, 0, P["chest_z"]), tail=(0, 0, P["neck_base"]), parent="Spine", connect=True),
        dict(name="Neck", head=(0, 0, P["neck_base"]), tail=(0, 0, P["chin_z"] + 0.012), parent="Chest", connect=True),
        dict(name="Head", head=(0, 0, P["chin_z"] + 0.012), tail=(0, 0, P["crown_z"] + 0.02), parent="Neck", connect=True),
    ]
    for side, sign in (("L", 1), ("R", -1)):
        bones += [
            dict(name="Shoulder_" + side, head=(sign * 0.028, 0, P["neck_base"] - 0.035),
                 tail=(sign * P["shoulder_joint"].x, 0, P["shoulder_joint"].z), parent="Chest"),
            dict(name="UpperArm_" + side, head=(sign * P["shoulder_joint"].x, 0, P["shoulder_joint"].z),
                 tail=(sign * P["elbow"].x, P["elbow"].y, P["elbow"].z), parent="Shoulder_" + side, connect=True),
            dict(name="LowerArm_" + side, head=(sign * P["elbow"].x, P["elbow"].y, P["elbow"].z),
                 tail=(sign * P["wrist"].x, P["wrist"].y, P["wrist"].z), parent="UpperArm_" + side, connect=True),
            dict(name="Hand_" + side, head=(sign * P["wrist"].x, P["wrist"].y, P["wrist"].z),
                 tail=(sign * P["hand_end"].x, P["hand_end"].y, P["hand_end"].z), parent="LowerArm_" + side, connect=True),
            dict(name="Thigh_" + side, head=(sign * P["hip_joint"].x, 0, P["hip_joint"].z),
                 tail=(sign * P["knee"].x, P["knee"].y, P["knee"].z), parent="Hips"),
            dict(name="Shin_" + side, head=(sign * P["knee"].x, P["knee"].y, P["knee"].z),
                 tail=(sign * P["ankle"].x, P["ankle"].y, P["ankle"].z), parent="Thigh_" + side, connect=True),
            dict(name="Foot_" + side, head=(sign * P["ankle"].x, P["ankle"].y, P["ankle"].z),
                 tail=(sign * P["ankle"].x, -P["foot_len"] * 0.55, P["ankle_z"] * 0.35), parent="Shin_" + side, connect=True),
            dict(name="Toe_" + side, head=(sign * P["ankle"].x, -P["foot_len"] * 0.55, P["ankle_z"] * 0.35),
                 tail=(sign * P["ankle"].x, -P["foot_len"] * 0.95, 0.02), parent="Foot_" + side, connect=True),
        ]
    return bones


# --------------------------------------------------------------------------- #
# animation library
# --------------------------------------------------------------------------- #
def base_pose(style):
    stoop = style.get("stoop", 0.0)
    return {
        "Spine": (stoop * 0.35, 0, 0),
        "Chest": (stoop * 0.45, 0, 0),
        "Neck": (-stoop * 0.45, 0, 0),
        "Head": (-stoop * 0.25, 0, 0),
        "UpperArm_L": (2, 0, 5),
        "UpperArm_R": (2, 0, -5),
        "LowerArm_L": (-8, 0, 0),
        "LowerArm_R": (-8, 0, 0),
        "Hand_L": (0, 0, 0),
        "Hand_R": (0, 0, 0),
        "Shoulder_L": (0, 0, 0),
        "Shoulder_R": (0, 0, 0),
        "Thigh_L": (0, 0, 0),
        "Thigh_R": (0, 0, 0),
        "Shin_L": (-2, 0, 0),
        "Shin_R": (-2, 0, 0),
        "Foot_L": (1, 0, 0),
        "Foot_R": (1, 0, 0),
        "Toe_L": (0, 0, 0),
        "Toe_R": (0, 0, 0),
    }


def merge(*poses):
    out = {}
    for p in poses:
        out.update(p)
    return out


def contact_pose(style, s=1.0):
    st = style["stride"] * s
    ar = style["arm"] * s
    return {
        "Hips": (0, 0, 4 * s),
        "Spine": (style.get("stoop", 0) * 0.3 + 1.5, 0, -3 * s),
        "Chest": (style.get("stoop", 0) * 0.4, 0, -2 * s),
        "Neck": (-style.get("stoop", 0) * 0.3, 0, 3 * s),
        "Head": (0, 0, 2 * s),
        "Thigh_L": (26 * st, 0, 0),
        "Shin_L": (-6 * st, 0, 0),
        "Foot_L": (-9 * st, 0, 0),
        "Toe_L": (0, 0, 0),
        "Thigh_R": (-21 * st, 0, 0),
        "Shin_R": (-14 * st, 0, 0),
        "Foot_R": (16 * st, 0, 0),
        "Toe_R": (6 * st, 0, 0),
        "UpperArm_L": (-22 * ar, 0, 5),
        "LowerArm_L": (-14 * ar, 0, 0),
        "UpperArm_R": (24 * ar, 0, -5),
        "LowerArm_R": (-16 * ar, 0, 0),
    }


def passing_pose(style, s=1.0):
    st = style["stride"] * s
    return {
        "Hips": (0, 0, 0),
        "Spine": (style.get("stoop", 0) * 0.3 + 1.0, 0, 0),
        "Chest": (style.get("stoop", 0) * 0.4, 0, 0),
        "Neck": (-style.get("stoop", 0) * 0.3, 0, 0),
        "Thigh_L": (3 * st, 0, 0),
        "Shin_L": (-5 * st, 0, 0),
        "Foot_L": (2 * st, 0, 0),
        "Thigh_R": (10 * st, 0, 0),
        "Shin_R": (-48 * st, 0, 0),
        "Foot_R": (-8 * st, 0, 0),
        "Toe_R": (4 * st, 0, 0),
        "UpperArm_L": (-4 * style["arm"], 0, 5),
        "LowerArm_L": (-10, 0, 0),
        "UpperArm_R": (5 * style["arm"], 0, -5),
        "LowerArm_R": (-12, 0, 0),
    }


# The grip solver and the carry clips must agree on the torso lean, or the
# solved palms drift away from the prop.
CARRY_TORSO = {
    "basket": {"Spine": (4, 0, 0), "Chest": (2, 0, 0)},
    "cart": {"Spine": (5, 0, 0), "Chest": (2, 0, 0), "Neck": (-3, 0, 0)},
}
# Every character exports all 18 clips, but only carriers use these two walks.
# Non-carriers get a generic carry pose for the unused clips.
CARRY_ARMS = {
    "basket": {
        "UpperArm_L": (32, 8, 4), "LowerArm_L": (30, 0, 0),
        "UpperArm_R": (32, -8, -4), "LowerArm_R": (30, 0, 0),
        "Hand_L": (-6, 0, 0), "Hand_R": (-6, 0, 0),
    },
    "cart": {
        "UpperArm_L": (40, 6, 3), "LowerArm_L": (4, 0, 0),
        "UpperArm_R": (40, -6, -3), "LowerArm_R": (4, 0, 0),
        "Hand_L": (4, 0, 0), "Hand_R": (4, 0, 0),
    },
}


def walk_keys(style, variant="free", speed=1.0):
    """24-frame walk loop (1..25): two steps, contact/passing/contact/..."""
    b = base_pose(style)
    arm_override = {}
    torso = {}
    if variant in CARRY_TORSO:
        arm_override = style.get(f"{variant}_arms") or CARRY_ARMS[variant]
        torso = CARRY_TORSO[variant]
    c = merge(b, contact_pose(style), torso)
    p = merge(b, passing_pose(style), torso)
    cm = merge(b, mirror_pose(contact_pose(style)), torso)
    pm = merge(b, mirror_pose(passing_pose(style)), torso)
    c.update(arm_override)
    cm.update(arm_override)
    p.update(arm_override)
    pm.update(arm_override)
    # arms should not counter-swing when carrying
    if variant in CARRY_TORSO:
        for k in ("UpperArm_L", "LowerArm_L", "UpperArm_R", "LowerArm_R", "Hand_L", "Hand_R"):
            p[k] = arm_override.get(k, b.get(k, (0, 0, 0)))
            pm[k] = p[k]
    keys = [
        (1, c, (0, 0, -0.012)),
        (7, p, (0, 0, 0.014)),
        (13, cm, (0, 0, -0.012)),
        (19, pm, (0, 0, 0.014)),
        (25, c, (0, 0, -0.012)),
    ]
    return keys, 1, 25


def idle_keys(style):
    b = base_pose(style)
    breathe = dict(b)
    breathe["Chest"] = (b["Chest"][0] - 1.4, 0, 0)
    breathe["Neck"] = (b["Neck"][0] + 1.0, 0, 0)
    breathe["Shoulder_L"] = (0, 0, 2)
    breathe["Shoulder_R"] = (0, 0, -2)
    shift = dict(b)
    shift["Hips"] = (0, 1.4, 0)
    shift["Spine"] = (b["Spine"][0], -0.8, 1.2)
    shift["Head"] = (-1, 0, 4)
    shift["UpperArm_L"] = (b["UpperArm_L"][0], 0, 6.5)
    shift["UpperArm_R"] = (b["UpperArm_R"][0], 0, -6.5)
    keys = [
        (1, b, (0, 0, 0)),
        (25, breathe, (0.004, 0, 0.003)),
        (49, shift, (-0.004, 0, 0)),
        (73, breathe, (0, 0, 0.002)),
        (97, b, (0, 0, 0)),
    ]
    return keys, 1, 97


def idle_carry_keys(style, variant="basket"):
    """Stationary loop that keeps both hands on the basket or cart handle."""
    b = base_pose(style)
    arms = style.get(f"{variant}_arms") or CARRY_ARMS[variant]
    torso = CARRY_TORSO[variant]
    base = merge(b, arms, torso)
    breathe = dict(base)
    breathe["Chest"] = (base["Chest"][0] - 1.2, 0, 0)
    breathe["Neck"] = (base["Neck"][0] + 0.8, 0, 0)
    shift = dict(base)
    shift["Hips"] = (0, 1.4, 0)
    shift["Spine"] = (base["Spine"][0], -0.8, 1.2)
    shift["Head"] = (-1, 0, 4)
    keys = [
        (1, base, (0, 0, 0)),
        (25, breathe, (0.004, 0, 0.003)),
        (49, shift, (-0.004, 0, 0)),
        (73, breathe, (0, 0, 0.002)),
        (97, base, (0, 0, 0)),
    ]
    return keys, 1, 97


def wait_keys(style):
    b = base_pose(style)
    p1 = dict(b)
    p1.update({"Hips": (0, 2.5, 0), "Spine": (0, -1.5, 2), "Head": (2, 0, -3),
               "UpperArm_L": (4, 0, 7), "UpperArm_R": (0, 0, -4),
               "LowerArm_L": (-14, 0, 0), "LowerArm_R": (-6, 0, 0)})
    p2 = dict(b)
    p2.update({"Hips": (0, -1.5, 0), "Head": (-1, 0, 6), "UpperArm_L": (0, 0, 4),
               "UpperArm_R": (4, 0, -7), "LowerArm_L": (-6, 0, 0),
               "LowerArm_R": (-14, 0, 0), "Shin_L": (-4, 0, 0)})
    keys = [(1, b, (0, 0, 0)), (31, p1, (0.006, 0, 0)), (63, p2, (-0.006, 0, 0)), (97, b, (0, 0, 0))]
    return keys, 1, 97


def look_around_keys(style):
    b = base_pose(style)
    look_l = dict(b)
    look_l.update({"Neck": (0, 0, 18), "Head": (2, 0, 26), "Chest": (0, 0, 6),
                   "UpperArm_L": (2, 0, 8)})
    look_r = dict(b)
    look_r.update({"Neck": (0, 0, -18), "Head": (1, 0, -24), "Chest": (0, 0, -5)})
    look_up = dict(b)
    look_up.update({"Neck": (-6, 0, 0), "Head": (-8, 0, 0)})
    keys = [(1, b, (0, 0, 0)), (21, look_l, (0.004, 0, 0.003)),
            (49, look_r, (-0.004, 0, 0)), (69, look_up, (0, 0, 0.004)), (89, b, (0, 0, 0))]
    return keys, 1, 89


def turn_keys(style, direction=1):
    b = base_pose(style)
    mid = dict(b)
    sign = direction
    mid.update({
        "Hips": (0, 0, 12 * sign),
        "Spine": (0, 0, 8 * sign),
        "Chest": (0, 0, 6 * sign),
        "Neck": (0, 0, 6 * sign),
        "Head": (0, 0, 10 * sign),
        "Thigh_L": (6 * sign, 0, 0), "Thigh_R": (-4 * sign, 0, 0),
        "Foot_L": (0, 0, -6 * sign), "Foot_R": (0, 0, -4 * sign),
        "UpperArm_L": (4, 0, 5 + 4 * sign), "UpperArm_R": (4, 0, -5 + 4 * sign),
    })
    end = dict(b)
    end["Hips"] = (0, 0, 3 * sign)
    keys = [(1, b, (0, 0, 0)), (8, mid, (0, 0, -0.006)), (16, end, (0, 0, 0)), (24, b, (0, 0, 0))]
    return keys, 1, 24


def stop_keys(style):
    b = base_pose(style)
    decel = merge(b, contact_pose(style, 0.55))
    settle = dict(b)
    settle.update({"Hips": (0, 0, 0), "Spine": (2, 0, 0), "Shin_L": (-6, 0, 0),
                   "Shin_R": (-6, 0, 0), "Thigh_L": (4, 0, 0), "Thigh_R": (4, 0, 0),
                   "UpperArm_L": (0, 0, 6), "UpperArm_R": (0, 0, -6)})
    keys = [(1, decel, (0, 0, -0.008)), (9, settle, (0, 0, -0.018)), (18, b, (0, 0, 0))]
    return keys, 1, 18


def pick_keys(style):
    b = base_pose(style)
    lean = dict(b)
    lean.update({
        "Hips": (6, 0, 0), "Spine": (16, 0, -6), "Chest": (8, 0, -4),
        "Neck": (-12, 0, 4), "Head": (-6, 0, 4),
        "Thigh_L": (12, 0, 0), "Thigh_R": (10, 0, 0),
        "Shin_L": (-14, 0, 0), "Shin_R": (-14, 0, 0),
        "Foot_L": (6, 0, 0), "Foot_R": (6, 0, 0),
        "UpperArm_R": (64, 0, -12), "LowerArm_R": (24, 0, 0), "Hand_R": (-15, 0, 0),
        "UpperArm_L": (-8, 0, 6), "LowerArm_L": (-14, 0, 0),
    })
    grasp = dict(lean)
    grasp.update({"UpperArm_R": (52, 0, -16), "LowerArm_R": (46, 0, 0), "Hand_R": (-25, 0, 0)})
    keys = [(1, b, (0, 0, 0)), (14, lean, (0, 0, -0.02)), (24, grasp, (0, 0, -0.026)),
            (34, lean, (0, 0, -0.02)), (46, b, (0, 0, 0))]
    return keys, 1, 46


def place_keys(style):
    b = base_pose(style)
    reach = dict(b)
    reach.update({"Spine": (8, 0, 0), "Chest": (4, 0, 0),
                  "UpperArm_R": (48, 0, -10), "LowerArm_R": (48, 0, 0), "Hand_R": (12, 0, 0),
                  "UpperArm_L": (28, 8, 4), "LowerArm_L": (68, 0, 0)})
    out = dict(reach)
    out.update({"UpperArm_R": (62, 0, -14), "LowerArm_R": (22, 0, 0), "Hand_R": (22, 0, 0),
                "Chest": (8, 0, 0)})
    keys = [(1, b, (0, 0, 0)), (14, reach, (0, 0, -0.004)), (26, out, (0, 0, -0.01)),
            (38, reach, (0, 0, 0)), (48, b, (0, 0, 0))]
    return keys, 1, 48


def checkout_keys(style):
    b = base_pose(style)
    reach = dict(b)
    reach.update({"Spine": (4, 0, 2), "Chest": (2, 0, 2), "Neck": (-2, 0, 0),
                  "UpperArm_R": (62, 0, -14), "LowerArm_R": (26, 0, 0), "Hand_R": (10, 0, 0),
                  "UpperArm_L": (10, 0, 5)})
    tap = dict(reach)
    tap.update({"UpperArm_R": (70, 0, -10), "LowerArm_R": (14, 0, 0), "Hand_R": (-6, 0, 0),
                "Spine": (7, 0, 4)})
    pay = dict(b)
    pay.update({"UpperArm_R": (34, 0, -18), "LowerArm_R": (66, 0, 0), "Hand_R": (-10, 0, 0),
                "Neck": (-8, 0, 0), "Head": (-4, 0, 0)})
    keys = [(1, b, (0, 0, 0)), (14, reach, (0, 0, 0)), (22, tap, (0, 0, -0.004)),
            (34, pay, (0, 0, 0)), (48, b, (0, 0, 0))]
    return keys, 1, 48


def run_keys(style):
    b = base_pose(style)
    style2 = dict(style)
    style2["stride"] = style["stride"] * 1.55
    style2["arm"] = style["arm"] * 1.7
    c = merge(b, contact_pose(style2), {"Spine": (10, 0, 0), "Chest": (5, 0, 0),
                                        "Neck": (-8, 0, 0)})
    p = merge(b, passing_pose(style2), {"Spine": (10, 0, 0), "Chest": (5, 0, 0),
                                        "Neck": (-8, 0, 0)})
    cm = merge(b, mirror_pose(contact_pose(style2)), {"Spine": (10, 0, 0), "Chest": (5, 0, 0),
                                                      "Neck": (-8, 0, 0)})
    pm = merge(b, mirror_pose(passing_pose(style2)))
    keys = [(1, c, (0, 0, -0.02)), (5, p, (0, 0, 0.035)), (9, cm, (0, 0, -0.02)),
            (13, pm, (0, 0, 0.035)), (17, c, (0, 0, -0.02))]
    return keys, 1, 17


def greet_keys(style):
    b = base_pose(style)
    up = dict(b)
    up.update({"UpperArm_R": (20, 72, -8), "LowerArm_R": (0, 58, 0),
               "Hand_R": (0, 10, 0), "Head": (-2, 0, -6), "Neck": (0, 0, -4),
               "Chest": (0, 0, -3)})
    wave1 = dict(up)
    wave1.update({"LowerArm_R": (0, 42, 0), "Hand_R": (0, -18, 0)})
    wave2 = dict(up)
    wave2.update({"LowerArm_R": (0, 72, 0), "Hand_R": (0, 20, 0)})
    keys = [(1, b, (0, 0, 0)), (10, up, (0, 0, 0.004)), (18, wave1, (0, 0, 0.004)),
            (26, wave2, (0, 0, 0.004)), (34, wave1, (0, 0, 0.004)), (44, b, (0, 0, 0))]
    return keys, 1, 44


def inspect_keys(style):
    b = base_pose(style)
    hold = dict(b)
    hold.update({"UpperArm_R": (34, 0, -22), "LowerArm_R": (78, 0, 0), "Hand_R": (-16, 0, 0),
                 "Neck": (-10, 0, 0), "Head": (-8, 0, -4), "Spine": (2, 0, 0)})
    turn = dict(hold)
    turn.update({"Head": (-9, 0, 12), "Hand_R": (0, 0, 20)})
    keys = [(1, b, (0, 0, 0)), (12, hold, (0, 0, 0)), (30, turn, (0, 0, 0)),
            (48, hold, (0, 0, 0)), (60, b, (0, 0, 0))]
    return keys, 1, 60


def reach_high_keys(style):
    b = base_pose(style)
    up = dict(b)
    up.update({"UpperArm_R": (145, 0, -6), "LowerArm_R": (10, 0, 0), "Hand_R": (-10, 0, 0),
               "Neck": (-12, 0, 0), "Head": (-6, 0, 0), "Spine": (-4, 0, 0),
               "Chest": (-2, 0, 0), "Shin_L": (-4, 0, 0), "Shin_R": (-4, 0, 0)})
    keys = [(1, b, (0, 0, 0)), (14, up, (0, 0, 0.02)), (26, up, (0, 0, 0.02)), (40, b, (0, 0, 0))]
    return keys, 1, 40


# --------------------------------------------------------------------------- #
# carry grip solve
# --------------------------------------------------------------------------- #
# Props are authored in game space; glTF +Z maps to Blender -Y.
CARRY_GRIP_X = 0.17


def apply_pose(arm, pose, hips=(0, 0, 0)):
    for pb in arm.pose.bones:
        pb.rotation_quaternion = pose_quat(pb, pose.get(pb.name, (0.0, 0.0, 0.0)))
        pb.location = Vector((0.0, 0.0, 0.0))
        if pb.name == "Hips":
            m = pb.bone.matrix_local.to_3x3()
            pb.location = m.inverted() @ Vector(hips)
    bpy.context.view_layer.update()


def carry_target(kind, P):
    """Palm target for each prop, in Blender space and on the +X side."""
    if kind == "cart":
        return Vector((CARRY_GRIP_X, -0.38, 1.05))
    # Basket side rims: prop origin at half height, rim 0.21 m above it.
    return Vector((CARRY_GRIP_X, -0.36, P["H"] * 0.5 + 0.21))


def solve_carry_arms(style, arm, kind, target):
    """Two-link search that lands both palms on a prop's grip points.

    Poses are expressed as rotations about armature axes, so the same angles
    are valid for every rig once the arm length changes: the solver measures
    the actual Hand bone midpoint after each pose instead of guessing angles.
    """
    base = merge(base_pose(style), CARRY_TORSO[kind], {
        "Hand_L": (0, 0, 0), "Hand_R": (0, 0, 0),
    })
    # Hanging upper arms with flexed elbows are the natural carry pose. The
    # posture bias keeps the search off the mirror solution where the upper
    # arms point horizontally forward. Adduction stays small so the elbow does
    # not sink into the ribs; the forearm takes the rest of the inward reach.
    limits = [(-78.0, 12.0), (-6.0, 10.0), (-115.0, 55.0), (-8.0, 38.0)]
    posture = 0.00045

    def cost_of(candidate):
        ux, sy, lx, ly = candidate
        pose = dict(base)
        pose["UpperArm_L"] = (ux, sy, 0.0)
        pose["UpperArm_R"] = (ux, -sy, 0.0)
        pose["LowerArm_L"] = (lx, ly, 0.0)
        pose["LowerArm_R"] = (lx, -ly, 0.0)
        apply_pose(arm, pose)
        total = 0.0
        for side, sign in (("L", 1.0), ("R", -1.0)):
            pb = arm.pose.bones["Hand_" + side]
            mid = (pb.head + pb.tail) * 0.5
            goal = Vector((sign * target.x, target.y, target.z))
            total += (mid - goal).length_squared
        return total + posture * (ux / 100.0) ** 2

    # Coarse sweep first: the arm chain has more than one exact pose.
    best = None
    params = None
    for ux in range(-60, 11, 10):
        for sy in (0.0, 8.0):
            for lx in range(-110, 41, 15):
                for ly in (0.0, 12.0, 24.0):
                    candidate = [float(ux), sy, float(lx), ly]
                    cost = cost_of(candidate)
                    if best is None or cost < best:
                        best, params = cost, candidate

    step = 8.0
    for _ in range(10):
        moved = True
        guard = 0
        while moved and guard < 60:
            moved = False
            guard += 1
            for i in range(4):
                for direction in (-1.0, 1.0):
                    candidate = list(params)
                    lo, hi = limits[i]
                    candidate[i] = min(hi, max(lo, candidate[i] + direction * step))
                    if abs(candidate[i] - params[i]) < 1e-6:
                        continue
                    cost = cost_of(candidate)
                    if cost < best - 1e-9:
                        params, best = candidate, cost
                        moved = True
        step *= 0.5

    ux, sy, lx, ly = params
    arms = {
        "UpperArm_L": (round(ux, 2), round(sy, 2), 0.0),
        "UpperArm_R": (round(ux, 2), round(-sy, 2), 0.0),
        "LowerArm_L": (round(lx, 2), round(ly, 2), 0.0),
        "LowerArm_R": (round(lx, 2), round(-ly, 2), 0.0),
        "Hand_L": (0.0, 0.0, 0.0),
        "Hand_R": (0.0, 0.0, 0.0),
    }
    return arms, math.sqrt(best / 2.0)


def carry_grip_gap(arm, pose, target):
    """Worst palm-center distance to a solved prop grip."""
    apply_pose(arm, pose)
    worst = 0.0
    for side, sign in (("L", 1.0), ("R", -1.0)):
        pb = arm.pose.bones["Hand_" + side]
        mid = (pb.head + pb.tail) * 0.5
        goal = Vector((sign * target.x, target.y, target.z))
        worst = max(worst, (mid - goal).length)
    return worst


CLIP_BUILDERS = {
    "Idle": idle_keys,
    "Walk": lambda st: walk_keys(st, "free"),
    "WalkBasket": lambda st: walk_keys(st, "basket"),
    "WalkCart": lambda st: walk_keys(st, "cart"),
    "IdleBasket": lambda st: idle_carry_keys(st, "basket"),
    "IdleCart": lambda st: idle_carry_keys(st, "cart"),
    "Wait": wait_keys,
    "LookAround": look_around_keys,
    "TurnLeft": lambda st: turn_keys(st, 1),
    "TurnRight": lambda st: turn_keys(st, -1),
    "Stop": stop_keys,
    "PickItem": pick_keys,
    "PlaceItem": place_keys,
    "Checkout": checkout_keys,
    "Run": run_keys,
    "Greet": greet_keys,
    "Inspect": inspect_keys,
    "ReachHigh": reach_high_keys,
}


# --------------------------------------------------------------------------- #
# assemble one character
# --------------------------------------------------------------------------- #
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0


def add_preview_scene(P):
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    scene.collection.objects.link(cam)
    cam_data.lens = 70
    h = P["H"]
    cam.location = (1.15, -3.1, h * 0.62)
    look = Vector((0, 0, h * 0.52)) - cam.location
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    for name, loc, energy, size, color in (
        ("Key", (-2.2, -2.4, h + 1.2), 350, 2.0, (1.0, 0.95, 0.88)),
        ("Fill", (2.4, -1.9, h * 0.7), 140, 2.4, (0.82, 0.9, 1.0)),
        ("Rim", (0.6, 2.6, h + 0.8), 240, 1.6, (0.95, 0.98, 1.0)),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.size = size
        data.color = color
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = loc
        light.rotation_euler = (Vector((0, 0, h * 0.6)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.06, 0.07, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    scene.world = world


def make_materials(spec):
    cid = spec["id"]
    top = spec["top"]
    bottom = spec["bottom"]
    acc = spec.get("accessory_color") or spec.get("accent_color", 0x333333)
    mk = lambda key, color, rough=0.75, metal=0.0, alpha=1.0, ds=False: make_material(
        f"{cid}_{key}", color, rough, metal, alpha, ds)
    mats = {
        "skin": mk("skin", spec["skin"], 0.52),
        "skin_dark": mk("skin_dark", blend_hex(spec["skin"], 0x000000, 0.18), 0.6),
        "hair": mk("hair", spec["hair"], 0.38),
        "hair_grey": mk("hair_grey", spec.get("hair_grey", blend_hex(
            spec["hair"], 0xd8d4cc, 0.62)), 0.42),
        "facial_hair": mk("facial_hair", spec.get("facial_hair", blend_hex(
            spec["hair"], 0xd8d4cc, 0.45)), 0.6),
        "top": mk("top", top["color"], 0.82),
        "top2": mk("top2", top.get("accent", top["color"]), 0.8),
        "top_dark": mk("top_dark", blend_hex(top["color"], 0x000000, 0.16), 0.85),
        "trim": mk("trim", top.get("accent", 0xffffff), 0.85),
        "bottom": mk("bottom", bottom["color"], 0.86),
        "bottom2": mk("bottom2", blend_hex(bottom["color"], 0x000000, 0.18), 0.9),
        "shoe": mk("shoe", spec["shoes"]["color"], 0.62),
        "sole": mk("sole", spec["shoes"].get("accent", 0xffffff), 0.7),
        "lace": mk("lace", blend_hex(spec["shoes"]["color"], 0x000000, 0.25), 0.8),
        "sock": mk("sock", 0xf2efe8, 0.9),
        "bag": mk("bag", acc, 0.7),
        "bag2": mk("bag2", blend_hex(acc, 0x000000, 0.3), 0.75),
        "accent": mk("accent", acc, 0.6),
        "belt": mk("belt", blend_hex(bottom["color"], 0x000000, 0.35), 0.55),
        "metal": mk("metal", 0xb9bcc2, 0.32, 0.85),
        "button": mk("button", 0xf0ece2, 0.45),
        "eye_white": mk("eye_white", 0xf0e9df, 0.4),
        "irisL": mk("irisL", spec["iris"], 0.28),
        "irisR": mk("irisR", spec["iris"], 0.28),
        "pupil": mk("pupil", 0x0a0a0c, 0.22),
        "lash": mk("lash", 0x241c18, 0.5),
        "lips": mk("lips", lip_color(spec["skin"]), 0.45),
        "mouth": mk("mouth", 0x5a3230, 0.62),
        "brow": mk("brow", spec.get("brow_color", spec["hair"]), 0.45),
    }
    return mats


def lip_color(skin):
    r = (skin >> 16) & 255
    g = (skin >> 8) & 255
    b = skin & 255
    r = min(255, int(r * 0.78 + 55))
    g = min(255, int(g * 0.62 + 28))
    b = min(255, int(b * 0.66 + 32))
    return (r << 16) | (g << 8) | b


def blend_hex(c1, c2, t):
    r = int(lerp((c1 >> 16) & 255, (c2 >> 16) & 255, t))
    g = int(lerp((c1 >> 8) & 255, (c2 >> 8) & 255, t))
    b = int(lerp(c1 & 255, c2 & 255, t))
    return (r << 16) | (g << 8) | b


def build_character(spec):
    reset_scene()
    P = proportions(spec)
    P["torso_ctrl"] = torso_ctrl(P)
    mat_cache = make_materials(spec)
    objs = []
    shape = build_head(P, spec, mat_cache, objs)
    build_hair(P, spec, mat_cache, objs, shape)
    build_body(P, spec, mat_cache, objs)
    build_top(P, spec, mat_cache, objs)
    build_bottom(P, spec, mat_cache, objs)
    build_shoes(P, spec, mat_cache, objs)
    build_accessories(P, spec, mat_cache, objs, shape)

    arm = build_armature(spec["id"] + "_rig", make_skeleton(P))
    arm["fm_asset"] = spec["id"]

    # Carriers need their palms on the prop, not swinging at their sides. Solve
    # against the real bone lengths rather than hand-tuning per height.
    carry = spec.get("carry", "none")
    target = carry_target(carry, P) if carry in CARRY_TORSO else None
    if target is not None:
        carry_arms, solved_gap = solve_carry_arms(spec["walk"], arm, carry, target)
        spec["walk"][f"{carry}_arms"] = carry_arms
        elbow_x = abs(arm.pose.bones["LowerArm_L"].head.x)
        print(
            f"[grip] {spec['id']} solved {carry} arms {carry_arms['UpperArm_L']} / "
            f"{carry_arms['LowerArm_L']}, gap {solved_gap * 100:.1f} cm, "
            f"elbow x {elbow_x:.3f} m",
            flush=True,
        )

    # merge by material to minimise draw calls while keeping the skin weights
    groups = {}
    for ob in objs:
        if ob is None:
            continue
        key = ob.data.materials[0].name if ob.data.materials else "none"
        groups.setdefault(key, []).append(ob)
    merged = []
    for key, group in groups.items():
        joined = join_objects(group, f"{spec['id']}_{key.split('_', 1)[-1]}")
        joined["fm_asset"] = spec["id"]
        merged.append(joined)

    bind_meshes(arm, merged)

    actions = {}
    for name, builder in CLIP_BUILDERS.items():
        keys, start, end = builder(spec["walk"])
        action = make_action(arm, name, keys)
        actions[name] = (action, start, end)

    grip_gap = None
    if target is not None:
        grip_gap = carry_grip_gap(
            arm,
            merge(base_pose(spec["walk"]), CARRY_TORSO[carry], spec["walk"][f"{carry}_arms"]),
            target,
        )
        print(
            f"[grip] {spec['id']} verified Idle{carry.capitalize()} gap "
            f"{grip_gap * 100:.1f} cm",
            flush=True,
        )

    # Leave the rig in its rest pose so the .blend and GLB bind pose stay clean.
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = max(end for (_a, _s, end) in actions.values())
    add_preview_scene(P)
    bpy.context.view_layer.update()
    tri_count = sum(len(o.data.polygons) for o in merged)
    vert_count = sum(len(o.data.vertices) for o in merged)
    return dict(P=P, arm=arm, meshes=merged, actions=actions,
                tris=tri_count, verts=vert_count, materials=len(groups),
                grip_gap=grip_gap)


# --------------------------------------------------------------------------- #
# export
# --------------------------------------------------------------------------- #
def export_character(spec, character, do_render=False):
    cid = spec["id"]
    arm = character["arm"]
    meshes = character["meshes"]
    os.makedirs(OUT_BLEND, exist_ok=True)
    os.makedirs(OUT_GLB, exist_ok=True)
    os.makedirs(OUT_GAME, exist_ok=True)

    blend_path = os.path.join(OUT_BLEND, cid + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = arm

    glb_path = os.path.join(OUT_GLB, cid + ".glb")
    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format="GLB",
        use_selection=True,
        export_apply=False,
        export_yup=True,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_bake_animation=True,
        export_anim_single_armature=True,
        export_anim_slide_to_zero=True,
        export_cameras=False,
        export_lights=False,
        export_extras=True,
        export_materials="EXPORT",
    )
    import shutil
    shutil.copyfile(glb_path, os.path.join(OUT_GAME, cid + ".glb"))

    for m in meshes:
        m.data.calc_loop_triangles()
    character["tris"] = sum(len(m.data.loop_triangles) for m in meshes)
    meta = {
        "id": cid,
        "name": spec["name"],
        "gender": "male" if spec["sex"] == "M" else "female",
        "age_group": age_group(spec["age"]),
        "age": spec["age"],
        "height_m": round(character["P"]["H"], 3),
        "tris": character["tris"],
        "verts": character["verts"],
        "bones": len(arm.data.bones),
        "materials": character["materials"],
        "animations": sorted(character["actions"].keys()),
        "carry": spec.get("carry", "none"),
        "spawn_weight": spec.get("spawn_weight", 1.0),
        "walk": spec["walk"],
        "grip_gap": character.get("grip_gap"),
        "files": {
            "blend": f"assets/characters/blender_source/{cid}.blend",
            "glb": f"assets/characters/exports/glb/{cid}.glb",
            "game_glb": f"public/models/customers/{cid}.glb",
        },
    }
    with open(os.path.join(OUT_GLB, cid + ".json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    return meta, glb_path, blend_path


def age_group(age):
    if age <= 10:
        return "child"
    if age <= 17:
        return "teen"
    if age <= 30:
        return "young_adult"
    if age <= 45:
        return "adult"
    if age <= 64:
        return "middle_aged"
    return "senior"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = None
    if "--only" in argv:
        only = argv[argv.index("--only") + 1]
    specs = [s for s in SPECS if (only is None or s["id"] == only)]
    summary = []
    for spec in specs:
        t0 = time.time()
        character = build_character(spec)
        meta, glb, blend = export_character(spec, character)
        summary.append(meta)
        print(
            f"[build] {spec['id']}: {character['tris']} tris, {meta['bones']} bones, "
            f"{len(character['actions'])} clips, {time.time() - t0:.1f}s",
            flush=True,
        )
    if only is None:
        manifest = {
            "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "characters": summary,
        }
        with open(os.path.join(OUT_GLB, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
    print("DONE", json.dumps([s["id"] for s in summary]))


if __name__ == "__main__":
    main()
