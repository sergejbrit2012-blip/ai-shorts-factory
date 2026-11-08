import bpy
import sys
import json
import math
from pathlib import Path
from mathutils import Vector

def arg_value(name, default=None):
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return default

DATA_PATH = Path(arg_value("--data"))
OUTPUT_PATH = Path(arg_value("--output"))
DURATION = float(arg_value("--duration", "40"))
DATA = json.loads(DATA_PATH.read_text(encoding="utf-8"))

def mat(name, color, roughness=0.55, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, 1)
    bs.inputs["Roughness"].default_value = roughness
    bs.inputs["Metallic"].default_value = metallic
    return m

RED = mat("Ярко-красная клубника", (0.88, 0.035, 0.07), 0.3)
YELLOW = mat("Бананово-жёлтый", (1.0, 0.68, 0.035), 0.32)
GREEN = mat("Огуречный зелёный", (0.08, 0.48, 0.16), 0.4)
ORANGE = mat("Морковный оранжевый", (1.0, 0.24, 0.025), 0.4)
BROWN = mat("Картофельный", (0.55, 0.29, 0.12), 0.65)
WHITE = mat("Белки глаз", (1, 1, 1), 0.25)
BLACK = mat("Зрачки и рот", (0.012, 0.009, 0.018), 0.25)
LEAF = mat("Листья", (0.04, 0.32, 0.08), 0.5)
FLOOR = mat("Пол сцены", (0.12, 0.17, 0.29), 0.65)
WALL = mat("Фон", (0.035, 0.075, 0.16), 0.8)
CYAN = mat("Бирюзовый декор", (0.04, 0.62, 0.72), 0.35, 0.15)

def smooth(obj):
    if obj.type == "MESH":
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj

def uv_sphere(name, loc, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    return smooth(o)

def cylinder_between(name, a, b, radius, material):
    a, b = Vector(a), Vector(b)
    delta = b - a
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12, radius=radius, depth=delta.length,
        location=(a + b) / 2
    )
    o = bpy.context.object
    o.name = name
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = delta.to_track_quat("Z", "Y")
    o.data.materials.append(material)
    bevel = o.modifiers.new("Мягкие края", "BEVEL")
    bevel.width = radius * 0.35
    bevel.segments = 2
    return smooth(o)

def add_text(body, loc, size, material, align="CENTER"):
    curve = bpy.data.curves.new("Текст мультфильма", "FONT")
    curve.body = str(body)[:95]
    curve.size = size
    curve.align_x = align
    curve.extrude = 0.006
    obj = bpy.data.objects.new("Надпись: " + str(body)[:25], curve)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.data.materials.append(material)
    return obj

def key_bob(obj, base_z, end_frame):
    for frame, offset in [(1, 0), (10, 0.13), (20, 0), (30, 0.08), (40, 0)]:
        f = min(frame, end_frame)
        obj.location.z = base_z + offset
        obj.keyframe_insert(data_path="location", frame=f)
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "SINE"

def character(kind, x, name, body_material, scale=1.0, end_frame=900):
    # Character root is an empty parent so the whole character can bounce.
    root = bpy.data.objects.new(name + " — движение", None)
    bpy.context.collection.objects.link(root)
    root.location = (x, 0, 0)

    def parent(obj):
        obj.parent = root
        return obj

    body = parent(uv_sphere(name + " тело", (x, 0, 1.55*scale), (0.72*scale, 0.48*scale, 0.92*scale), body_material))
    head_z = 2.05 * scale

    # Strawberry leaves / fruit crown.
    if kind == "strawberry":
        for j in range(5):
            ang = j * math.tau / 5
            leaf_obj = parent(uv_sphere(
                name + " листик",
                (x + math.cos(ang)*0.18*scale, -0.01, 2.42*scale),
                (0.12*scale, 0.09*scale, 0.28*scale), LEAF
            ))
            leaf_obj.rotation_euler[1] = math.cos(ang) * 0.55
            leaf_obj.rotation_euler[0] = math.sin(ang) * 0.55
    elif kind == "banana":
        # A small curved stem and a rounded banana tip.
        parent(cylinder_between(name + " хвостик", (x, 0, 2.35*scale), (x+0.13*scale, 0, 2.65*scale), 0.09*scale, GREEN))
    elif kind == "carrot":
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.12*scale, radius2=0.48*scale, depth=0.9*scale, location=(x, 0, 2.45*scale))
        cone = parent(bpy.context.object)
        cone.name = name + " ботва"
        cone.data.materials.append(LEAF)

    # Eyes on the front (camera looks from negative Y).
    for ex in [-0.24, 0.24]:
        parent(uv_sphere(name + " глаз", (x+ex*scale, -0.425*scale, head_z), (0.17*scale, 0.075*scale, 0.22*scale), WHITE))
        parent(uv_sphere(name + " зрачок", (x+ex*scale, -0.50*scale, head_z-0.015*scale), (0.075*scale, 0.04*scale, 0.11*scale), BLACK))

    mouth = parent(uv_sphere(name + " рот", (x, -0.49*scale, 1.72*scale), (0.13*scale, 0.055*scale, 0.055*scale), BLACK))
    for frame, height in [(1, 0.04), (8, 0.15), (15, 0.04), (22, 0.13), (29, 0.04), (36, 0.11), (43, 0.04)]:
        f = min(frame, end_frame)
        mouth.scale.z = height * scale
        mouth.keyframe_insert(data_path="scale", frame=f)

    # Arms and legs.
    for side in [-1, 1]:
        arm = parent(cylinder_between(
            name + " рука",
            (x+side*0.52*scale, 0, 1.75*scale),
            (x+side*0.95*scale, -0.02, 1.35*scale),
            0.095*scale, body_material
        ))
        hand = parent(uv_sphere(name + " ладонь", (x+side*0.95*scale, -0.02, 1.34*scale), (0.14*scale, 0.13*scale, 0.14*scale), body_material))
        for frame, angle in [(1, -0.12*side), (12, 0.5*side), (24, -0.25*side), (36, 0.35*side), (48, -0.12*side)]:
            f = min(frame, end_frame)
            arm.rotation_euler[1] = angle
            arm.keyframe_insert(data_path="rotation_euler", frame=f)
            hand.rotation_euler[1] = angle
            hand.keyframe_insert(data_path="rotation_euler", frame=f)
        leg = parent(cylinder_between(
            name + " нога",
            (x+side*0.25*scale, 0, 0.78*scale),
            (x+side*0.32*scale, -0.02, 0.28*scale),
            0.11*scale, body_material
        ))
        parent(uv_sphere(name + " ботинок", (x+side*0.34*scale, -0.08, 0.19*scale), (0.22*scale, 0.28*scale, 0.13*scale), BLACK))

    key_bob(root, 0, end_frame)
    return root

def setup_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x = 540
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.fps = 20
    scene.frame_start = 1
    scene.frame_end = max(160, int(DURATION * scene.render.fps))
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.filepath = str(OUTPUT_PATH)
    scene.render.use_file_extension = True
    scene.render.film_transparent = False
    scene.world.color = (0.025, 0.035, 0.07)

    # Stage and wall.
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "Большой пол"
    floor.data.materials.append(FLOOR)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 4, 8), rotation=(math.pi/2, 0, 0))
    wall = bpy.context.object
    wall.name = "Фон студии"
    wall.data.materials.append(WALL)

    # Decorative glowing rings and spheres.
    for i in range(7):
        uv_sphere("Декоративный шар", (-4.2 + i*1.4, 1.2, 4.5 + (i%2)*1.2), (0.12, 0.12, 0.12), CYAN)

    # Lighting.
    bpy.ops.object.light_add(type="AREA", location=(0, -7, 9))
    key = bpy.context.object
    key.data.energy = 1500
    key.data.shape = "DISK"
    key.data.size = 8
    key.rotation_euler = (math.radians(25), 0, 0)
    bpy.ops.object.light_add(type="AREA", location=(-6, -2, 4))
    fill = bpy.context.object
    fill.data.energy = 700
    fill.data.size = 6
    fill.rotation_euler = (math.radians(45), 0, math.radians(-35))
    bpy.ops.object.light_add(type="AREA", location=(5, 2, 6))
    rim = bpy.context.object
    rim.data.energy = 1100
    rim.data.size = 5
    rim.rotation_euler = (math.radians(35), 0, math.radians(145))

    # Camera: vertical portrait framing.
    bpy.ops.object.camera_add(location=(0, -13.5, 5.2))
    camera = bpy.context.object
    camera.rotation_euler = (Vector((0, 0, 2.4)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 8.4
    scene.camera = camera

    category = DATA.get("category", "SERIES")
    if category == "SERIES":
        character("strawberry", -1.35, "Клубника", RED, 0.9, scene.frame_end)
        character("banana", 1.25, "Банан", YELLOW, 0.92, scene.frame_end)
    elif category == "HOME":
        character("potato", -1.2, "Картошка", BROWN, 0.95, scene.frame_end)
        character("carrot", 1.2, "Морковка", ORANGE, 0.95, scene.frame_end)
    else:
        # Friendly 3D robot mascot, built from rounded primitives.
        character("cucumber", -1.2, "Зелёный помощник", GREEN, 0.95, scene.frame_end)
        character("banana", 1.2, "Жёлтый помощник", YELLOW, 0.95, scene.frame_end)

    # Header and scene cards.
    title = add_text(DATA.get("title", "Мультфильм"), (0, -0.35, 5.15), 0.38, WHITE)
    title.rotation_euler[0] = math.radians(90)
    title.location.y = -0.7

    # Three scene captions are staged in 3D and switched on/off by scale.
    captions = []
    scenes = DATA.get("scenes", [])
    for i, item in enumerate(scenes[:3]):
        obj = add_text(item.get("title", ""), (0, -0.65, 4.35), 0.28, CYAN)
        obj.rotation_euler[0] = math.radians(90)
        captions.append(obj)
        for frame, scale in [(1, 0.001), (int((i+1)*scene.frame_end/4), 0.001),
                             (int((i+1)*scene.frame_end/4)+2, 1),
                             (int((i+2)*scene.frame_end/4), 1),
                             (int((i+2)*scene.frame_end/4)+2, 0.001)]:
            frame = max(1, min(scene.frame_end, frame))
            obj.scale = (scale, scale, scale)
            obj.keyframe_insert(data_path="scale", frame=frame)

    # Slow camera push-in with a gentle side-to-side move.
    camera.data.lens = 50
    for frame, x, z in [(1, 0, 5.2), (scene.frame_end//2, 0.25, 5.0), (scene.frame_end, 0, 5.2)]:
        camera.location.x = x
        camera.location.z = z
        camera.keyframe_insert(data_path="location", frame=frame)

    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.render.filepath = str(OUTPUT_PATH)

setup_scene()
bpy.ops.render.render(animation=True)
print("3D_RENDER_COMPLETE", OUTPUT_PATH)
