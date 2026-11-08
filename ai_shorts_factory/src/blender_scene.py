
import bpy
import sys
import os
import json
import math
import argparse
import subprocess
from mathutils import Vector

# ============================================================
# AI SHORTS FACTORY — PROCEDURAL 3D CARTOON
# Blender 5.x compatible
# ============================================================

def arguments():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--duration", type=float, default=35.0)
    return parser.parse_args(argv)


ARGS = arguments()
DURATION = max(8.0, min(44.5, ARGS.duration))
FPS = 24
WIDTH = 720
HEIGHT = 1280

OUTPUT_DIR = os.path.dirname(os.path.abspath(ARGS.output))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# RESET
# ============================================================

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

for block in list(bpy.data.materials):
    bpy.data.materials.remove(block)

# ============================================================
# SCENE
# ============================================================

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"

scene.render.resolution_x = WIDTH
scene.render.resolution_y = HEIGHT
scene.render.resolution_percentage = 100
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = int(DURATION * FPS)

scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.compression = 25
scene.render.film_transparent = False

scene.render.filepath = os.path.join(OUTPUT_DIR, "frame_")
scene.render.use_file_extension = True

try:
    scene.eevee.taa_render_samples = 32
except Exception:
    pass

try:
    scene.view_settings.view_transform = "AgX"
except Exception:
    pass

# ============================================================
# DATA
# ============================================================

with open(ARGS.data, "r", encoding="utf-8") as f:
    DATA = json.load(f)

TITLE = DATA.get("title", "Полезный совет")
HERO = DATA.get("hero", {})

if isinstance(HERO, str):
    HERO_ID = HERO
    HERO_NAME = HERO
else:
    HERO_ID = HERO.get("id", "banana")
    HERO_NAME = HERO.get("name", "Банан")

SCENES = DATA.get("scenes", [])

# ============================================================
# MATERIALS
# ============================================================

def material(name, color, roughness=0.55, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)

    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")

    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic

    return mat


MAT = {
    "yellow": material("Fruit Yellow", (1.0, 0.65, 0.04)),
    "yellow_light": material("Fruit Light", (1.0, 0.83, 0.25)),
    "green": material("Fresh Green", (0.08, 0.42, 0.12)),
    "green_light": material("Leaf Green", (0.24, 0.68, 0.17)),
    "red": material("Fresh Red", (0.78, 0.035, 0.07)),
    "red_light": material("Red Highlight", (1.0, 0.15, 0.19)),
    "pink": material("Pink", (1.0, 0.25, 0.43)),
    "orange": material("Orange", (1.0, 0.30, 0.025)),
    "brown": material("Brown", (0.34, 0.15, 0.055)),
    "purple": material("Purple", (0.29, 0.055, 0.48)),
    "white": material("White", (0.98, 0.98, 1.0)),
    "black": material("Black", (0.018, 0.018, 0.025)),
    "blue": material("Blue", (0.035, 0.26, 0.72)),
    "skin": material("Warm Skin", (0.95, 0.55, 0.31)),
    "floor": material("Warm Floor", (0.32, 0.19, 0.12)),
    "wall": material("Kitchen Wall", (0.76, 0.70, 0.58)),
    "wood": material("Wood", (0.38, 0.19, 0.075)),
}

# ============================================================
# OBJECT HELPERS
# ============================================================

def smooth(obj):
    if obj.type == "MESH":
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    return obj


def apply_material(obj, mat):
    if mat:
        obj.data.materials.append(mat)
    return obj


def uv_sphere(name, location, scale, mat, segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        location=location
    )

    obj = bpy.context.object
    obj.name = name
    obj.scale = scale

    apply_material(obj, mat)
    smooth(obj)

    return obj


def cube(name, location, scale, mat, bevel=0.08):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)

    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True
    )

    if bevel:
        modifier = obj.modifiers.new("Soft Edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
        obj.modifiers.new("Weighted Normals", "WEIGHTED_NORMAL")

    apply_material(obj, mat)
    return obj


def cylinder(name, location, radius, depth, mat):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=radius,
        depth=depth,
        location=location
    )

    obj = bpy.context.object
    obj.name = name

    apply_material(obj, mat)
    smooth(obj)
    return obj


def text_object(body, location, size, mat, align="CENTER"):
    curve = bpy.data.curves.new("Text", "FONT")
    curve.body = str(body)
    curve.size = size
    curve.align_x = align
    curve.extrude = 0.003

    obj = bpy.data.objects.new("Text", curve)
    bpy.context.collection.objects.link(obj)

    obj.location = location
    obj.rotation_euler = (math.radians(90), 0, 0)

    apply_material(obj, mat)
    return obj


def parent_to(obj, parent):
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world


# ============================================================
# LIGHTS
# ============================================================

def area_light(name, location, energy, size, target):
    bpy.ops.object.light_add(type="AREA", location=location)

    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size

    direction = Vector(target) - light.location
    light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_lighting():
    area_light("Large Softbox", (1, -6, 9), 1200, 7, (0, 0, 2))
    area_light("Front Fill", (-5, -4, 4), 700, 5, (0, 0, 2))
    area_light("Rim Light", (2, 4, 6), 1500, 4, (0, 0, 2))


# ============================================================
# ENVIRONMENT
# ============================================================

def create_kitchen():
    cube("Floor", (0, 0, -0.25), (12, 12, 0.5), MAT["wood"])

    cube("Back Wall", (0, 3.0, 4), (12, 0.3, 8), MAT["wall"])

    cube("Kitchen Counter", (0, 0.6, 1.1), (9, 1.4, 0.25), MAT["white"])

    cube("Cabinet", (0, 1.25, 0.45), (8, 0.9, 0.9), MAT["blue"])

    for x in [-3, -1.5, 0, 1.5, 3]:
        cube(
            "Cabinet Door",
            (x, 0.77, 0.45),
            (1.35, 0.06, 0.72),
            MAT["white"],
            0.04
        )

    cube("Window Frame", (-3.5, 2.78, 4.6), (2.5, 0.12, 2.2), MAT["white"])
    cube("Window Glass", (-3.5, 2.70, 4.6), (2.25, 0.05, 1.95), MAT["blue"], 0.01)

    cube("Window Divider", (-3.5, 2.62, 4.6), (0.07, 0.05, 2.0), MAT["white"], 0.01)
    cube("Window Divider", (-3.5, 2.62, 4.6), (2.3, 0.05, 0.07), MAT["white"], 0.01)

    cube("Shelf", (3.1, 2.5, 4.2), (2.2, 0.55, 0.12), MAT["wood"])

    for x, color in [(2.4, "red"), (3.1, "green"), (3.8, "yellow")]:
        cylinder("Kitchen Jar", (x, 2.4, 4.55), 0.18, 0.55, MAT[color])


# ============================================================
# CHARACTER BODY
# ============================================================

def create_body():
    root = bpy.data.objects.new("CHARACTER_ROOT", None)
    bpy.context.collection.objects.link(root)

    if HERO_ID == "banana":
        body = uv_sphere("Banana Body", (0, 0, 2.4), (0.65, 0.48, 1.45), MAT["yellow"])
        body.rotation_euler[1] = math.radians(-12)

        tip1 = uv_sphere("Banana Tip", (0.16, 0, 3.78), (0.15, 0.16, 0.23), MAT["brown"])
        tip2 = uv_sphere("Banana Stem", (-0.12, 0, 0.99), (0.14, 0.14, 0.20), MAT["brown"])

        parent_to(body, root)
        parent_to(tip1, root)
        parent_to(tip2, root)

    elif HERO_ID == "watermelon":
        body = uv_sphere("Watermelon Body", (0, 0, 2.3), (0.95, 0.75, 1.0), MAT["green"])

        for x in [-0.65, -0.3, 0, 0.3, 0.65]:
            stripe = uv_sphere(
                "Watermelon Stripe",
                (x, -0.65, 2.3),
                (0.045, 0.035, 0.82),
                MAT["green_light"]
            )
            parent_to(stripe, root)

        parent_to(body, root)

    elif HERO_ID == "strawberry":
        body = uv_sphere("Strawberry Body", (0, 0, 2.35), (0.78, 0.62, 1.0), MAT["red"])
        body.scale.z = 1.3

        for x in [-0.4, 0, 0.4]:
            leaf = uv_sphere("Strawberry Leaf", (x, 0, 3.42), (0.35, 0.12, 0.13), MAT["green_light"])
            parent_to(leaf, root)

        parent_to(body, root)

    elif HERO_ID == "carrot":
        body = uv_sphere("Carrot Body", (0, 0, 2.3), (0.62, 0.56, 1.15), MAT["orange"])
        body.scale.x = 0.82
        body.scale.z = 1.25
        parent_to(body, root)

        for x in [-0.3, 0, 0.3]:
            leaf = uv_sphere("Carrot Leaf", (x, 0, 3.65), (0.14, 0.12, 0.65), MAT["green"])
            leaf.rotation_euler[1] = math.radians(x * 60)
            parent_to(leaf, root)

    elif HERO_ID == "cucumber":
        body = uv_sphere("Cucumber Body", (0, 0, 2.35), (0.55, 0.55, 1.3), MAT["green"])
        parent_to(body, root)

        for x in [-0.35, 0, 0.35]:
            for z in [1.8, 2.2, 2.6, 3.0]:
                dot = uv_sphere("Cucumber Texture", (x, -0.52, z), (0.045, 0.035, 0.045), MAT["green_light"])
                parent_to(dot, root)

    elif HERO_ID == "apple":
        body = uv_sphere("Apple Body", (0, 0, 2.3), (0.82, 0.72, 0.95), MAT["red"])
        parent_to(body, root)

        stem = cylinder("Apple Stem", (0, 0, 3.28), 0.06, 0.4, MAT["brown"])
        parent_to(stem, root)

        leaf = uv_sphere("Apple Leaf", (0.24, 0, 3.38), (0.35, 0.12, 0.12), MAT["green"])
        parent_to(leaf, root)

    elif HERO_ID in ("orange", "lemon"):
        body = uv_sphere(
            "Citrus Body",
            (0, 0, 2.35),
            (0.82, 0.72, 0.9),
            MAT["orange"] if HERO_ID == "orange" else MAT["yellow"]
        )
        parent_to(body, root)

        leaf = uv_sphere("Citrus Leaf", (0.25, 0, 3.2), (0.35, 0.12, 0.13), MAT["green"])
        parent_to(leaf, root)

    else:
        body = uv_sphere("Generic Fruit Body", (0, 0, 2.3), (0.8, 0.7, 1.0), MAT["yellow"])
        parent_to(body, root)

    return root


# ============================================================
# FACE
# ============================================================

def create_face(root):
    eye_positions = [-0.25, 0.25]

    for x in eye_positions:
        eye = uv_sphere("Eye White", (x, -0.44, 2.78), (0.18, 0.10, 0.23), MAT["white"])
        parent_to(eye, root)

        pupil = uv_sphere("Eye Pupil", (x, -0.535, 2.76), (0.085, 0.055, 0.13), MAT["black"])
        parent_to(pupil, root)

        shine = uv_sphere("Eye Shine", (x - 0.025, -0.585, 2.82), (0.035, 0.025, 0.045), MAT["white"])
        parent_to(shine, root)

    for x in eye_positions:
        brow = uv_sphere("Eyebrow", (x, -0.47, 3.08), (0.19, 0.055, 0.055), MAT["brown"])
        parent_to(brow, root)

    smile = uv_sphere("Smile", (0, -0.49, 2.34), (0.19, 0.06, 0.065), MAT["black"])
    parent_to(smile, root)

    for x in [-0.48, 0.48]:
        cheek = uv_sphere("Cheek", (x, -0.43, 2.45), (0.12, 0.045, 0.075), MAT["pink"])
        parent_to(cheek, root)


# ============================================================
# CLOTHING
# ============================================================

def create_clothes(root):
    shirt = uv_sphere("Cartoon Shirt", (0, 0, 1.65), (0.57, 0.5, 0.36), MAT["blue"])
    parent_to(shirt, root)

    badge = uv_sphere("Shirt Badge", (0.22, -0.49, 1.72), (0.11, 0.04, 0.11), MAT["yellow_light"])
    parent_to(badge, root)


# ============================================================
# ARMS AND HANDS
# ============================================================

def create_arm(root, side):
    direction = -1 if side == "L" else 1

    arm = uv_sphere(
        "Arm " + side,
        (direction * 0.78, 0, 2.0),
        (0.14, 0.14, 0.48),
        MAT["skin"]
    )

    arm.rotation_euler[1] = math.radians(direction * -22)
    parent_to(arm, root)

    hand = uv_sphere(
        "Hand " + side,
        (direction * 0.92, -0.03, 1.58),
        (0.18, 0.16, 0.17),
        MAT["skin"]
    )
    parent_to(hand, root)

    for finger in range(3):
        offset = (finger - 1) * 0.09

        obj = uv_sphere(
            "Finger",
            (direction * 1.02 + offset, -0.03, 1.47),
            (0.055, 0.07, 0.12),
            MAT["skin"]
        )
        parent_to(obj, root)


# ============================================================
# LEGS AND SHOES
# ============================================================

def create_legs(root):
    for side in [-1, 1]:
        leg = uv_sphere("Leg", (side * 0.3, 0, 0.76), (0.13, 0.15, 0.48), MAT["blue"])
        parent_to(leg, root)

        shoe = uv_sphere("Cartoon Shoe", (side * 0.3, -0.08, 0.3), (0.27, 0.38, 0.17), MAT["black"])
        parent_to(shoe, root)

        sole = uv_sphere("Shoe Sole", (side * 0.3, -0.09, 0.19), (0.28, 0.38, 0.06), MAT["white"])
        parent_to(sole, root)


# ============================================================
# TABLE PROPS
# ============================================================

def create_props():
    cube("Cutting Board", (0, -0.3, 1.34), (2.4, 1.0, 0.08), MAT["wood"])

    for x, mat in [
        (-2.7, MAT["red"]),
        (-2.0, MAT["green"]),
        (2.5, MAT["yellow"])
    ]:
        uv_sphere("Food Prop", (x, 0.2, 1.65), (0.3, 0.3, 0.3), mat)


# ============================================================
# CAMERA
# ============================================================

def setup_camera():
    bpy.ops.object.camera_add(location=(4.6, -11.5, 4.5))
    camera = bpy.context.object
    camera.name = "Main Camera"

    target = Vector((0, 0, 2.0))
    direction = target - camera.location

    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    camera.data.lens = 45
    camera.data.dof.use_dof = False

    scene.camera = camera
    return camera


# ============================================================
# ANIMATION — BLENDER 5 COMPATIBLE
# ============================================================

def animate_character(root):
    for frame in range(1, scene.frame_end + 1, 6):
        time = frame / FPS

        root.location.z = 0.12 * abs(math.sin(time * 4.0))
        root.rotation_euler.y = math.radians(4.0 * math.sin(time * 2.2))

        root.keyframe_insert(data_path="location", frame=frame)
        root.keyframe_insert(data_path="rotation_euler", frame=frame)

    # Blender 5.x: do not access action.fcurves.
    # Keyframes use Blender's default smooth interpolation.


def animate_camera(camera):
    for frame in range(1, scene.frame_end + 1, 12):
        t = frame / FPS

        camera.location.x = 4.6 + math.sin(t * 0.5) * 0.25
        camera.location.z = 4.5 + math.sin(t * 0.7) * 0.12

        camera.keyframe_insert(data_path="location", frame=frame)

    # Blender 5.x compatible: no direct action.fcurves access.


# ============================================================
# SCENE TEXT
# ============================================================

def create_title():
    title = text_object(
        TITLE[:48],
        (0, -2.5, 6.3),
        0.42,
        MAT["white"]
    )

    title.name = "Video Title"


# ============================================================
# BUILD
# ============================================================

def build():
    print("Building 3D cartoon...")
    print("Hero:", HERO_NAME)

    scene.world.color = (0.12, 0.12, 0.12)

    create_kitchen()
    create_props()

    root = create_body()
    create_face(root)
    create_clothes(root)

    create_arm(root, "L")
    create_arm(root, "R")
    create_legs(root)

    create_title()

    setup_lighting()

    camera = setup_camera()
    animate_character(root)
    animate_camera(camera)

    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 100
    scene.render.filepath = os.path.join(OUTPUT_DIR, "frame_")

    scene.frame_set(1)

    print("Rendering frames...")

    bpy.ops.render.render(animation=True)

    print("Frames rendered.")

    frame_pattern = os.path.join(OUTPUT_DIR, "frame_%04d.png")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loglevel", "error",
            "-framerate", str(FPS),
            "-i", frame_pattern,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            ARGS.output
        ],
        check=True
    )

    if not os.path.exists(ARGS.output) or os.path.getsize(ARGS.output) < 10000:
        raise RuntimeError("FFmpeg не создал полноценный видеофайл.")

    print("Video created:", ARGS.output)


if __name__ == "__main__":
    build()
