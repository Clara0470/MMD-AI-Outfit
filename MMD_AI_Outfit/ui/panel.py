import bpy
from bpy.props import PointerProperty, StringProperty
from bpy.types import Operator, Panel

from ..character import measure_body


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
        context.scene.mmd_ai_outfit_target = armature
        context.scene.mmd_ai_outfit_measurement_json = ""
        self.report({"INFO"}, f"対象モデルに登録しました: {armature.name}")
        return {"FINISHED"}


class MMD_AI_OUTFIT_OT_clear_target(Operator):
    """Clear the currently registered outfit target"""
    bl_idname = "mmd_ai_outfit.clear_target"
    bl_label = "登録を解除"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        context.scene.mmd_ai_outfit_target = None
        context.scene.mmd_ai_outfit_measurement_json = ""
        self.report({"INFO"}, "対象モデルの登録を解除しました")
        return {"FINISHED"}


class MMD_AI_OUTFIT_OT_measure_body(Operator):
    """Measure body proportions from the registered armature"""
    bl_idname = "mmd_ai_outfit.measure_body"
    bl_label = "体格情報を取得"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene.mmd_ai_outfit_target is not None

    def execute(self, context):
        import json
        try:
            values = measure_body(context.scene.mmd_ai_outfit_target)
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        context.scene.mmd_ai_outfit_measurement_json = json.dumps(values, ensure_ascii=False)
        self.report({"INFO"}, "体格情報を取得しました")
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
        target = scene.mmd_ai_outfit_target
        box = layout.box()
        box.label(text="対象キャラクター", icon="ARMATURE_DATA")
        if target is None:
            box.label(text="未登録", icon="INFO")
            box.label(text="アーマチュアまたはモデルのメッシュを選択")
        else:
            row = box.row(align=True)
            row.label(text=target.name, icon="OUTLINER_OB_ARMATURE")
            row.operator("mmd_ai_outfit.clear_target", text="", icon="X")
        box.operator("mmd_ai_outfit.register_target", icon="PLUS")

        layout.separator()
        measure_box = layout.box()
        measure_box.label(text="体格情報", icon="MOD_ARMATURE")
        measure_box.operator("mmd_ai_outfit.measure_body", icon="FILE_REFRESH")
        if scene.mmd_ai_outfit_measurement_json:
            try:
                values = json.loads(scene.mmd_ai_outfit_measurement_json)
            except (TypeError, ValueError):
                measure_box.label(text="測定結果を読み込めません", icon="ERROR")
            else:
                for label, value in values.items():
                    measure_box.label(text=f"{label}: {value:.3f} BU")
        elif target is not None:
            measure_box.label(text="ボタンを押して測定してください")

        layout.separator()
        coming_soon = layout.box()
        coming_soon.label(text="次の実装予定", icon="TOOL_SETTINGS")
        coming_soon.label(text="衣装の読み込み・フィッティング")


classes = (
    MMD_AI_OUTFIT_OT_register_target,
    MMD_AI_OUTFIT_OT_clear_target,
    MMD_AI_OUTFIT_OT_measure_body,
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
        description="Last body measurement result",
        default="",
        options={"HIDDEN"},
    )


def unregister():
    if hasattr(bpy.types.Scene, "mmd_ai_outfit_measurement_json"):
        del bpy.types.Scene.mmd_ai_outfit_measurement_json
    if hasattr(bpy.types.Scene, "mmd_ai_outfit_target"):
        del bpy.types.Scene.mmd_ai_outfit_target
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
