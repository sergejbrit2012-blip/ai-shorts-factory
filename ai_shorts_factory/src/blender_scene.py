
import bpy
import sys
import json
import math
import shutil
import subprocess
from pathlib import Path
from mathutils import Vector

# =====================================================
# AI SHORTS FACTORY - BLENDER 5.0.1
# =====================================================

def get_args():
    args = sys.argv
    args = args[args.index("--") + 1:] if "--" in args else []

    result = {
        "data": "data.json",
        "output": "video_silent.mp4",
        "duration": 15
    }

    i = 0
    while i < len(args):
        if args[i] == "--data" and i + 1 < len(args):
            result["data"] = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            result["output"] = args[i + 1]
            i += 2
        elif args[i] == "--duration" and i + 1 < len(args):
            result["duration"] = float(args[i + 1])
            i += 2
        else:
            i += 1

    return result


ARGS = get_args()
DATA_PATH = Path(ARGS["data"]).resolve()
OUTPUT_PATH = Path(ARGS["output"]).resolve()
DURATION = max(5, float(ARGS["duration"]))

FPS = 20
WIDTH = 540
HEIGHT = 960

FRAME_DIR = OUTPUT_PATH.parent / "blender_frames"


# =====================================================
# ЗАГРУЗКА СЦЕНАРИЯ
# =====================================================

def load_data():
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Не удалось прочитать сценарий:", e)
        return {}


DATA = load_data()


# =====================================================
# МАТЕРИАЛЫ
# =====================================================

def make_material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)

    nodes = mat.node_tree.nodes if mat.node_tree else None
    if nodes:
        bsdf = nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*color, 1)
            bsdf.inputs["Roughness"].default_value = 0.4

    return mat


RED = make_material("Клубника", (0.9, 0.025, 0.045))
YELLOW = make_material("Банан", (1.0, 0.65, 0.02))
GREEN = make_material("Огурец", (0.05, 0.55, 0.12))
WHITE = make_material("Глаза", (1, 1, 1))
BLACK = make_material("Зрачки", (0.005, 0.005, 0.005))
BLUE = make_material("Обувь", (0.025, 0.15, 0.7))
FLOOR = make_material("Пол", (0.025, 0.04, 0.1))


# =====================================================
# СОЗДАНИЕ ФИГУР
# =====================================================

def sphere(name, location, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=24,
        ring_count=16,
        location=location
    )

    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)

    bpy.ops.object.shade_smooth()
    return obj


def cylinder(name, location, radius, depth, material):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=24,
        radius=radius,
        depth=depth,
        location=location
    )

    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)

    bevel = obj.modifiers.new("Скругление", "BEVEL")
    bevel.width = 0.08
    bevel.segments = 3

    return obj


def cone(name, location, radius, depth, material):
    bpy.ops.mesh.primitive_cone_add(
        vertices=24,
        radius1=radius,
        radius2=0.04,
        depth=depth,
        location=location
    )

    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


# =====================================================
# ПЕРСОНАЖИ
# =====================================================

def create_character(name, x, material, kind):
    parts = []

    body = sphere(
        name + "_Тело",
        (x, 0, 2.1),
        (0.68, 0.5, 0.85),
        material
    )
    parts.append(body)

    # Глаза и зрачки
    for side in (-1, 1):
        eye = sphere(
            name + "_Глаз",
            (x + side * 0.22, -0.46, 2.4),
            (0.15, 0.08, 0.19),
            WHITE
        )
        parts.append(eye)

        pupil = sphere(
            name + "_Зрачок",
            (x + side * 0.22, -0.535, 2.39),
            (0.065, 0.035, 0.09),
            BLACK
        )
        parts.append(pupil)

    # Улыбка
    mouth = sphere(
        name + "_Рот",
        (x, -0.49, 2.0),
        (0.18, 0.045, 0.065),
        BLACK
    )
    parts.append(mouth)

    # Руки
    for side in (-1, 1):
        arm = sphere(
            name + "_Рука",
            (x + side * 0.78, 0, 2.0),
            (0.15, 0.15, 0.42),
            material
        )
        arm.rotation_euler[1] = side * -0.4
        parts.append(arm)

        hand = sphere(
            name + "_Кисть",
            (x + side * 0.9, -0.02, 1.65),
            (0.17, 0.17, 0.17),
            material
        )
        parts.append(hand)

    # Ноги и обувь
    for side in (-1, 1):
        leg = cylinder(
            name + "_Нога",
            (x + side * 0.27, 0, 1.2),
            0.12,
            0.5,
            BLUE
        )
        parts.append(leg)

        foot = sphere(
            name + "_Ступня",
            (x + side * 0.27, -0.1, 0.9),
            (0.22, 0.3, 0.12),
            BLACK
        )
        parts.append(foot)

    # Верхушки персонажей
    if kind == 0:
        top = sphere(
            name + "_Лист",
            (x, 0, 3.05),
            (0.16, 0.12, 0.28),
            GREEN
        )
        parts.append(top)

    elif kind == 1:
        top = cone(
            name + "_Верхушка",
            (x, 0, 3.1),
            0.25,
            0.5,
            GREEN
        )
        parts.append(top)

    else:
        top = sphere(
            name + "_Лист",
            (x, 0, 3.0),
            (0.25, 0.14, 0.12),
            GREEN
        )
        parts.append(top)

    # Родительский объект персонажа
    bpy.ops.object.empty_add(
        type="PLAIN_AXES",
        location=(x, 0, 0)
    )

    root = bpy.context.object
    root.name = name + "_Контроллер"

    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix

    return root


# =====================================================
# АНИМАЦИЯ
# =====================================================

def animate_character(obj, end_frame, phase=0):
    start = 1
    middle = max(2, end_frame // 2)

    obj.location.z = 0
    obj.keyframe_insert(data_path="location", frame=start)

    obj.location.z = 0.3
    obj.keyframe_insert(data_path="location", frame=middle)

    obj.location.z = 0
    obj.keyframe_insert(data_path="location", frame=end_frame)

    obj.rotation_euler[1] = -0.1
    obj.keyframe_insert(data_path="rotation_euler", frame=start)

    obj.rotation_euler[1] = 0.1
    obj.keyframe_insert(data_path="rotation_euler", frame=middle)

    obj.rotation_euler[1] = -0.1
    obj.keyframe_insert(data_path="rotation_euler", frame=end_frame)

    if obj.animation_data and obj.animation_data.action:
        try:
            for curve in obj.animation_data.action.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = "BEZIER"
        except Exception:
            pass


# =====================================================
# ТЕКСТ
# =====================================================

def add_title():
    title = str(DATA.get("title", "Весёлые приключения"))
    title = title[:45]

    font = bpy.data.curves.new("Заголовок", "FONT")
    font.body = title
    font.size = 0.35
    font.align_x = "CENTER"
    font.extrude = 0.01

    obj = bpy.data.objects.new("Заголовок", font)
    bpy.context.collection.objects.link(obj)

    obj.location = (0, -0.7, 4.2)
    obj.rotation_euler[0] = math.radians(90)
    obj.data.materials.append(WHITE)


# =====================================================
# НАСТРОЙКА СЦЕНЫ
# =====================================================

def setup_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    scene = bpy.context.scene

    # Выбираем реально доступный движок
    engines = scene.render.bl_rna.properties["engine"].enum_items.keys()

    if "BLENDER_EEVEE_NEXT" in engines:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in engines:
        scene.render.engine = "BLENDER_EEVEE"
    else:
        scene.render.engine = "CYCLES"

    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = max(1, int(DURATION * FPS))

    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    scene.view_settings.view_transform = "Standard"

    # Фон
    world = scene.world
    world.use_nodes = True

    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.015, 0.025, 0.08, 1)
        bg.inputs["Strength"].default_value = 0.7

    # Пол
    bpy.ops.mesh.primitive_plane_add(
        size=200,
        location=(0, 0, 0)
    )
    bpy.context.object.data.materials.append(FLOOR)

    # Камера
    bpy.ops.object.camera_add(location=(0, -12, 4.0))
    camera = bpy.context.object

    direction = Vector((0, 0, 2.0)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 8.5

    scene.camera = camera

    # Основной свет
    bpy.ops.object.light_add(
        type="AREA",
        location=(0, -5, 8)
    )
    light = bpy.context.object
    light.data.energy = 1300
    light.data.shape = "DISK"
    light.data.size = 7

    # Дополнительный свет
    bpy.ops.object.light_add(
        type="AREA",
        location=(5, 2, 5)
    )
    light2 = bpy.context.object
    light2.data.energy = 700
    light2.data.color = (0.3, 0.5, 1.0)
    light2.data.size = 5

    # Персонажи
    characters = [
        create_character("Клубника", -2, RED, 0),
        create_character("Банан", 0, YELLOW, 1),
        create_character("Огурец", 2, GREEN, 2)
    ]

    add_title()

    for index, character in enumerate(characters):
        animate_character(character, scene.frame_end, index)

    return scene


# =====================================================
# РЕНДЕР И СБОРКА MP4
# =====================================================

def render_video(scene):
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    for old in FRAME_DIR.glob("frame_*.png"):
        old.unlink()

    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(FRAME_DIR / "frame_")

    print("Начинаем рендеринг...")
    bpy.ops.render.render(animation=True)

    frames = list(FRAME_DIR.glob("frame_*.png"))

    if not frames:
        raise RuntimeError("Blender не создал кадры PNG.")

    print("Создано кадров:", len(frames))

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg не найден.")

    command = [
        ffmpeg,
        "-y",
        "-framerate", str(FPS),
        "-i", str(FRAME_DIR / "frame_%04d.png"),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(OUTPUT_PATH)
    ]

    print("Собираем MP4...")
    subprocess.run(command, check=True)

    if not OUTPUT_PATH.exists() or OUTPUT_PATH.stat().st_size == 0:
        raise RuntimeError("Не удалось создать MP4.")

    print("Готовое видео:", OUTPUT_PATH)


# =====================================================
# ЗАПУСК
# =====================================================

def main():
    print("================================")
    print("AI SHORTS FACTORY")
    print("BLENDER 3D RENDER")
    print("================================")

    scene = setup_scene()
    render_video(scene)

    print("3D-ВИДЕО УСПЕШНО СОЗДАНО!")


if __name__ == "__main__":
    main()
