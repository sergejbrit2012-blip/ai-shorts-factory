
import bpy
import sys
import json
import math
import shutil
import subprocess
from pathlib import Path
from mathutils import Vector

# ============================================================
# AI SHORTS FACTORY — BLENDER 5.0.1
# Простая процедурная 3D-анимация для YouTube Shorts
# ============================================================

def get_arguments():
    args = sys.argv
    if "--" in args:
        args = args[args.index("--") + 1:]
    else:
        args = []

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


ARGS = get_arguments()
DATA_PATH = Path(ARGS["data"]).resolve()
OUTPUT_PATH = Path(ARGS["output"]).resolve()
DURATION = max(5, float(ARGS["duration"]))

FPS = 20
WIDTH = 540
HEIGHT = 960

FRAME_DIR = OUTPUT_PATH.parent / "blender_frames"


# ============================================================
# ЧТЕНИЕ СЦЕНАРИЯ
# ============================================================

def load_data():
    if not DATA_PATH.exists():
        print("Файл сценария не найден:", DATA_PATH)
        return {}

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as error:
        print("Ошибка чтения сценария:", error)
        return {}


DATA = load_data()


def get_scene_texts():
    scenes = DATA.get("scenes", [])

    result = []

    if isinstance(scenes, list):
        for scene in scenes:
            if isinstance(scene, dict):
                text = (
                    scene.get("text")
                    or scene.get("description")
                    or scene.get("visual")
                    or scene.get("action")
                    or ""
                )
                result.append(str(text))
            else:
                result.append(str(scene))

    while len(result) < 3:
        result.append("Весёлые персонажи встречаются и разговаривают")

    return result[:3]


SCENE_TEXTS = get_scene_texts()


# ============================================================
# МАТЕРИАЛЫ
# ============================================================

def create_material(name, color, metallic=0.0, roughness=0.45):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1)
    material.use_nodes = True

    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness

    return material


MAT_RED = create_material("Красный", (0.9, 0.035, 0.055))
MAT_YELLOW = create_material("Жёлтый", (1.0, 0.65, 0.02))
MAT_GREEN = create_material("Зелёный", (0.08, 0.65, 0.18))
MAT_ORANGE = create_material("Оранжевый", (1.0, 0.25, 0.015))
MAT_WHITE = create_material("Белый", (1, 1, 1))
MAT_BLACK = create_material("Чёрный", (0.008, 0.008, 0.012))
MAT_BLUE = create_material("Голубой", (0.025, 0.35, 0.9))
MAT_FLOOR = create_material("Пол", (0.035, 0.055, 0.12))


# ============================================================
# ОБЪЕКТЫ
# ============================================================

def add_uv_sphere(name, location, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=20,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)

    bpy.ops.object.shade_smooth()
    return obj


def add_cylinder(name, location, radius, depth, material):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=radius,
        depth=depth,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)

    bevel = obj.modifiers.new("Скругление", "BEVEL")
    bevel.width = 0.12
    bevel.segments = 3

    obj.modifiers.new("Нормали", "WEIGHTED_NORMAL")
    return obj


def add_cone(name, location, radius, depth, material):
    bpy.ops.mesh.primitive_cone_add(
        vertices=32,
        radius1=radius,
        radius2=0.05,
        depth=depth,
        location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def add_text(body, location, size, material):
    curve = bpy.data.curves.new("Текст", "FONT")
    curve.body = str(body)
    curve.size = size
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.extrude = 0.015

    obj = bpy.data.objects.new("Надпись", curve)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.data.materials.append(material)

    return obj


# ============================================================
# ПЕРСОНАЖИ
# ============================================================

def create_character(name, x, material, character_type=0):
    parts = []

    body = add_uv_sphere(
        name + "_Тело",
        (x, 0, 2.2),
        (0.72, 0.55, 0.85),
        material
    )
    parts.append(body)

    # Глаза
    for eye_x in (-0.24, 0.24):
        eye = add_uv_sphere(
            name + "_Глаз",
            (x + eye_x, -0.49, 2.48),
            (0.16, 0.09, 0.2),
            MAT_WHITE
        )
        parts.append(eye)

        pupil = add_uv_sphere(
            name + "_Зрачок",
            (x + eye_x, -0.575, 2.46),
            (0.07, 0.045, 0.1),
            MAT_BLACK
        )
        parts.append(pupil)

    # Улыбка
    mouth = add_uv_sphere(
        name + "_Улыбка",
        (x, -0.54, 2.05),
        (0.19, 0.055, 0.07),
        MAT_BLACK
    )
    parts.append(mouth)

    # Руки
    for side in (-1, 1):
        arm = add_uv_sphere(
            name + "_Рука",
            (x + side * 0.83, 0, 2.05),
            (0.17, 0.17, 0.48),
            material
        )
        arm.rotation_euler[1] = side * -0.45
        parts.append(arm)

        hand = add_uv_sphere(
            name + "_Кисть",
            (x + side * 0.98, -0.02, 1.68),
            (0.19, 0.19, 0.19),
            material
        )
        parts.append(hand)

    # Ноги
    for side in (-1, 1):
        leg = add_cylinder(
            name + "_Нога",
            (x + side * 0.3, 0, 1.18),
            0.13,
            0.55,
            MAT_BLUE
        )
        parts.append(leg)

        foot = add_uv_sphere(
            name + "_Ступня",
            (x + side * 0.3, -0.12, 0.88),
            (0.24, 0.32, 0.13),
            MAT_BLACK
        )
        parts.append(foot)

    # Верхушка для разных персонажей
    if character_type == 0:
        top = add_uv_sphere(
            name + "_Лист",
            (x, 0, 3.08),
            (0.15, 0.12, 0.32),
            MAT_GREEN
        )
        top.rotation_euler[1] = -0.4
        parts.append(top)

    elif character_type == 1:
        top = add_cone(
            name + "_Верхушка",
            (x, 0, 3.13),
            0.3,
            0.55,
            MAT_GREEN
        )
        parts.append(top)

    elif character_type == 2:
        top = add_uv_sphere(
            name + "_Лист",
            (x, 0, 3.0),
            (0.25, 0.16, 0.12),
            MAT_GREEN
        )
        parts.append(top)

    # Объединяем части персонажа в один родительский объект
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(x, 0, 0))
    root = bpy.context.object
    root.name = name + "_Контроллер"

    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix

    return root


# ============================================================
# АНИМАЦИЯ
# ============================================================

def animate_character(obj, start_frame, end_frame, offset=0):
    obj.location.z = 0
    obj.keyframe_insert(data_path="location", frame=start_frame)

    middle = (start_frame + end_frame) // 2

    obj.location.z = 0.35
    obj.keyframe_insert(data_path="location", frame=middle)

    obj.location.z = 0
    obj.keyframe_insert(data_path="location", frame=end_frame)

    obj.rotation_euler[1] = -0.12
    obj.keyframe_insert(data_path="rotation_euler", frame=start_frame)

    obj.rotation_euler[1] = 0.12
    obj.keyframe_insert(data_path="rotation_euler", frame=middle)

    obj.rotation_euler[1] = -0.12
    obj.keyframe_insert(data_path="rotation_euler", frame=end_frame)

    if obj.animation_data and obj.animation_data.action:
        try:
            for fcurve in obj.animation_data.action.fcurves:
                for key in fcurve.keyframe_points:
                    key.interpolation = "BEZIER"
        except Exception:
            pass


# ============================================================
# СЦЕНА
# ============================================================

def setup_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    scene = bpy.context.scene

    available_engines = scene.render.bl_rna.properties["engine"].enum_items.keys()

if "BLENDER_EEVEE_NEXT" in available_engines:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
elif "BLENDER_EEVEE" in available_engines:
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

    scene.render.film_transparent = False

    scene.world.color = (0.025, 0.025, 0.04)

    # Цвет фона
    world = scene.world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.025, 0.035, 0.09, 1)
        background.inputs["Strength"].default_value = 0.6

    # Пол
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "Пол"
    floor.data.materials.append(MAT_FLOOR)

    # Камера
    bpy.ops.object.camera_add(location=(0, -12, 4.2))
    camera = bpy.context.object
    camera.name = "Камера"

    target = Vector((0, 0, 1.9))
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 8.5

    scene.camera = camera

    # Свет
    bpy.ops.object.light_add(
        type="AREA",
        location=(0, -5, 8)
    )
    light = bpy.context.object
    light.data.energy = 1500
    light.data.shape = "DISK"
    light.data.size = 7

    # Дополнительный свет
    bpy.ops.object.light_add(
        type="AREA",
        location=(5, 2, 5)
    )
    light2 = bpy.context.object
    light2.data.energy = 900
    light2.data.color = (0.3, 0.5, 1.0)
    light2.data.size = 5

    # Персонажи
    characters = [
        create_character("Клубника", -2.0, MAT_RED, 0),
        create_character("Банан", 0, MAT_YELLOW, 1),
        create_character("Огурец", 2.0, MAT_GREEN, 2)
    ]

    # Заголовок
    title = str(DATA.get("title", "Весёлые приключения"))
    title = title[:45]

    title_obj = add_text(
        title,
        (0, -0.7, 4.3),
        0.42,
        MAT_WHITE
    )

    title_obj.rotation_euler[0] = math.radians(90)

    # Анимация
    total_frames = scene.frame_end
    third = max(1, total_frames // 3)

    for index, character in enumerate(characters):
        animate_character(
            character,
            1,
            total_frames,
            index
        )

    # Персонажи немного перемещаются
    for index, character in enumerate(characters):
        original_x = [-2.0, 0, 2.0][index]

        character.location.x = original_x - 0.25
        character.keyframe_insert(data_path="location", frame=1)

        character.location.x = original_x + 0.25
        character.keyframe_insert(data_path="location", frame=total_frames // 2)

        character.location.x = original_x - 0.25
        character.keyframe_insert(data_path="location", frame=total_frames)

    # Настройки качества
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "Standard"

    return scene


# ============================================================
# РЕНДЕР КАДРОВ И СБОРКА ВИДЕО
# ============================================================

def render_video(scene):
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Удаляем старые кадры
    for old_file in FRAME_DIR.glob("frame_*.png"):
        old_file.unlink()

    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(FRAME_DIR / "frame_")

    print("Начинаем рендеринг кадров...")
    bpy.ops.render.render(animation=True)

    frames = list(FRAME_DIR.glob("frame_*.png"))

    if not frames:
        raise RuntimeError("Blender не создал PNG-кадры.")

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
        raise RuntimeError("FFmpeg не создал готовое видео.")

    print("Видео успешно создано:", OUTPUT_PATH)


# ============================================================
# ЗАПУСК
# ============================================================

def main():
    print("================================")
    print("AI SHORTS FACTORY — BLENDER 5")
    print("================================")

    scene = setup_scene()
    render_video(scene)

    print("================================")
    print("3D-ВИДЕО ГОТОВО!")
    print("================================")


if __name__ == "__main__":
    main()
