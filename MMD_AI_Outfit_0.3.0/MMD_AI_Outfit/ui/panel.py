import bpy
from bpy.props import PointerProperty, StringProperty
from bpy.types import Operator, Panel

from ..character import (
    find_body_mesh,
    load_profile,
    measure_body,
    measure_body_shape,
    record_body_shape,
    record_skeleton,
    serialize_profile,
)


def find_armature(obj):
    """Return the armature that represents *obj*, if one can be found."""
    if obj is None:
        return None
    if obj.type == "ARMATURE":
        return obj
    armature = obj.find_armature()
    if armature is not None:
        return armature
    parent = obj.parent
    while parent is not None:
        if parent.type == "ARMATURE":
            return parent
        parent = parent.parent
    return None


def _mesh_poll(_self, obj):
    return obj is not None and obj.type == "MESH"


def _profile_for_scene(scene, armature):
    return load_profile(
        scene.mmd_ai_outfit_character_profile_json,
        armature.name,
        scene.mmd_ai_outfit_measurement_json,
    )


def _measure_skeleton_into_profile(scene, armature):
    values = measure_body(armature)
    profile = _profile_for_scene(scene, armature)
    record_skeleton(profile, values)
    scene.mmd_ai_outfit_character_profile_json = serialize_profile(profile)
    # Keep the former property synchronized so existing scenes/UI data remain usable.
    import json
    scene.mmd_ai_outfit_measurement_json = json.dumps(values, ensure_ascii=False)
    return profile, values


class MMD_AI_OUTFIT_OT_register_target(Operator):
    """Register the selected MMD model armature as the outfit target"""
    bl_idname = "mmd_ai_outfit.register_target"
    bl_label = "対象モデルとして登録"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return find_armature(context.active_object) is not None

    def execute(self, context):
        armature = find_armature(context.active_object)
        if armature is None:
            self.report({"ERROR"}, "アーマチュアまたはその配下メッシュを選択してください")
            return {"CANCELLED"}
        scene = context.scene
        scene.mmd_ai_outfit_target = armature
        scene.mmd_ai_outfit_measurement_json = ""
        scene.mmd_ai_outfit_character_profile_json = ""
        scene.mmd_ai_outfit_body_mesh = find_body_mesh(armature, scene.objects)
        if scene.mmd_ai_outfit_body_mesh:
            self.report({"INFO"}, f"対象モデルと身体メッシュを登録しました: {scene.mmd_ai_outfit_body_mesh.name}")
        else:
            self.report({"INFO"}, f"対象モデルに登録しました: {armature.name}。身体メッシュを選択してください")
        return {"FINISHED"}


class MMD_AI_OUTFIT_OT_clear_target(Operator):
    """Clear the currently registered outfit target"""
    bl_idname = "mmd_ai_outfit.clear_target"
    bl_label = "登録を解除"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        scene.mmd_ai_outfit_target = None
        scene.mmd_ai_outfit_body_mesh = None
        scene.mmd_ai_outfit_measurement_json = ""
        scene.mmd_ai_outfit_character_profile_json = ""
        self.report({"INFO"}, "対象モデルの登録を解除しました")
        return {"FINISHED"}


class MMD_AI_OUTFIT_OT_detect_body_mesh(Operator):
    """Automatically detect the body mesh attached to the target armature"""
    bl_idname = "mmd_ai_outfit.detect_body_mesh"
    bl_label = "身体メッシュを自動検出"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene.mmd_ai_outfit_target is not None

    def execute(self, context):
        scene = context.scene
        mesh = find_body_mesh(scene.mmd_ai_outfit_target, scene.objects)
        if mesh is None:
            self.report({"WARNING"}, "身体メッシュを検出できません。下の欄から手動で選択してください")
            return {"CANCELLED"}
        scene.mmd_ai_outfit_body_mesh = mesh
        self.report({"INFO"}, f"身体メッシュを検出しました: {mesh.name}")
        return {"FINISHED"}


class MMD_AI_OUTFIT_OT_measure_body(Operator):
    """Measure skeleton dimensions and write the Skeleton section of the Profile"""
    bl_idname = "mmd_ai_outfit.measure_body"
    bl_label = "Skeletonを測定"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene.mmd_ai_outfit_target is not None

    def execute(self, context):
        try:
            _measure_skeleton_into_profile(context.scene, context.scene.mmd_ai_outfit_target)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "Skeletonを測定し、Character Profileを更新しました")
        return {"FINISHED"}


class MMD_AI_OUTFIT_OT_measure_body_shape(Operator):
    """Always measure Skeleton first, then measure mesh cross-sections."""
    bl_idname = "mmd_ai_outfit.measure_body_shape"
    bl_label = "Body Shapeを測定"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene.mmd_ai_outfit_target is not None

    def execute(self, context):
        scene = context.scene
        armature = scene.mmd_ai_outfit_target
        try:
            # Skeleton is unconditionally refreshed before any Body Shape work.
            profile, _skeleton_values = _measure_skeleton_into_profile(scene, armature)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, f"先にSkeleton測定が必要です: {exc}")
            return {"CANCELLED"}

        body_mesh = scene.mmd_ai_outfit_body_mesh
        if body_mesh is None or body_mesh.type != "MESH":
            body_mesh = find_body_mesh(armature, scene.objects)
            scene.mmd_ai_outfit_body_mesh = body_mesh
        if body_mesh is None:
            self.report({"WARNING"}, "SkeletonをProfileに保存しました。身体メッシュを選択してBody Shapeを再測定してください")
            return {"CANCELLED"}

        try:
            measurements = measure_body_shape(armature, body_mesh, context)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, f"Skeletonは保存済みです。Body Shape測定: {exc}")
            return {"CANCELLED"}

        record_body_shape(profile, body_mesh.name, measurements)
        scene.mmd_ai_outfit_character_profile_json = serialize_profile(profile)
        self.report({"INFO"}, "SkeletonとBody ShapeをCharacter Profileに保存しました")
        return {"FINISHED"}


class MMD_AI_OUTFIT_PT_main(Panel):
    bl_idname = "MMD_AI_OUTFIT_PT_main"
    bl_label = "MMD AI Outfit"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MMD AI Outfit"

    def draw(self, context):
        import json
        layout = self.layout
        scene = context.scene
        armature = scene.mmd_ai_outfit_target

        target_box = layout.box()
        target_box.label(text="対象キャラクター", icon="ARMATURE_DATA")
        if armature is None:
            target_box.label(text="未登録", icon="INFO")
            target_box.label(text="アーマチュアまたはモデルのメッシュを選択")
        else:
            row = target_box.row(align=True)
            row.label(text=armature.name, icon="OUTLINER_OB_ARMATURE")
            row.operator("mmd_ai_outfit.clear_target", text="", icon="X")
        target_box.operator("mmd_ai_outfit.register_target", icon="PLUS")

        layout.separator()
        profile_box = layout.box()
        profile_box.label(text="Character Profile", icon="ARMATURE_DATA")
        profile_box.label(text="Skeleton", icon="BONE_DATA")
        profile_box.operator("mmd_ai_outfit.measure_body", text="Skeletonを測定", icon="FILE_REFRESH")
        profile = None
        raw_profile = scene.mmd_ai_outfit_character_profile_json
        if raw_profile:
            try:
                profile = json.loads(raw_profile)
            except (TypeError, ValueError):
                profile_box.label(text="Profileを読み込めません", icon="ERROR")
        elif scene.mmd_ai_outfit_measurement_json:
            # Show pre-profile Skeleton results from an existing .blend scene.
            try:
                legacy = json.loads(scene.mmd_ai_outfit_measurement_json)
            except (TypeError, ValueError):
                legacy = {}
            if legacy:
                profile_box.label(text="旧Skeleton測定値（再測定でProfileに移行）")
                for label, value in legacy.items():
                    profile_box.label(text=f"{label}: {value:.3f} BU")
        if profile and profile.get("skeleton", {}).get("measurements"):
            for label, value in profile["skeleton"]["measurements"].items():
                profile_box.label(text=f"{label}: {value:.3f} BU")

        layout.separator()
        body_box = layout.box()
        body_box.label(text="Body Shape", icon="MESH_DATA")
        body_box.label(text="身体メッシュ")
        body_box.prop(scene, "mmd_ai_outfit_body_mesh", text="")
        row = body_box.row(align=True)
        row.operator("mmd_ai_outfit.detect_body_mesh", text="自動検出", icon="VIEWZOOM")
        row.operator("mmd_ai_outfit.measure_body_shape", text="Body Shapeを測定", icon="DRIVER_DISTANCE")
        if profile and profile.get("body_shape", {}).get("measurements"):
            for label, value in profile["body_shape"]["measurements"].items():
                body_box.label(text=f"{label}: {value:.3f} BU")
            mesh_name = profile.get("body_shape", {}).get("mesh")
            if mesh_name:
                body_box.label(text=f"測定メッシュ: {mesh_name}")
        else:
            body_box.label(text="胸囲・ウエスト・ヒップの断面を測定")

        layout.separator()
        coming_soon = layout.box()
        coming_soon.label(text="次の実装予定", icon="TOOL_SETTINGS")
        coming_soon.label(text="衣装の読み込み・自動フィッティング")


classes = (
    MMD_AI_OUTFIT_OT_register_target,
    MMD_AI_OUTFIT_OT_clear_target,
    MMD_AI_OUTFIT_OT_detect_body_mesh,
    MMD_AI_OUTFIT_OT_measure_body,
    MMD_AI_OUTFIT_OT_measure_body_shape,
    MMD_AI_OUTFIT_PT_main,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mmd_ai_outfit_target = PointerProperty(
        name="MMD AI Outfit Target",
        description="Armature registered as the target character",
        type=bpy.types.Object,
    )
    bpy.types.Scene.mmd_ai_outfit_measurement_json = StringProperty(
        name="MMD AI Outfit Measurements",
        description="Legacy Skeleton measurement result",
        default="",
        options={"HIDDEN"},
    )
    bpy.types.Scene.mmd_ai_outfit_character_profile_json = StringProperty(
        name="MMD AI Outfit Character Profile",
        description="Persistent Skeleton and Body Shape measurements",
        default="",
        options={"HIDDEN"},
    )
    bpy.types.Scene.mmd_ai_outfit_body_mesh = PointerProperty(
        name="Body Mesh",
        description="Mesh used for Body Shape cross-section measurements",
        type=bpy.types.Object,
        poll=_mesh_poll,
    )


def unregister():
    for name in (
        "mmd_ai_outfit_body_mesh",
        "mmd_ai_outfit_character_profile_json",
        "mmd_ai_outfit_measurement_json",
        "mmd_ai_outfit_target",
    ):
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
