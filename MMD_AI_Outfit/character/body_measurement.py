"""Body measurements for standard MMD armatures."""


BONE_NAMES = {
    "head": ("頭", "head"),
    "neck": ("首", "neck"),
    "left_shoulder": ("左肩", "shoulder_l", "shoulder.l", "left_shoulder"),
    "right_shoulder": ("右肩", "shoulder_r", "shoulder.r", "right_shoulder"),
    "left_arm": ("左腕", "arm_l", "arm.l", "left_arm"),
    "right_arm": ("右腕", "arm_r", "arm.r", "right_arm"),
    "left_elbow": ("左ひじ", "左肘", "elbow_l", "elbow.l", "left_elbow"),
    "right_elbow": ("右ひじ", "右肘", "elbow_r", "elbow.r", "right_elbow"),
    "left_wrist": ("左手首", "wrist_l", "wrist.l", "left_wrist"),
    "right_wrist": ("右手首", "wrist_r", "wrist.r", "right_wrist"),
    "left_leg": ("左足", "thigh_l", "thigh.l", "upper_leg_l", "left_leg"),
    "right_leg": ("右足", "thigh_r", "thigh.r", "upper_leg_r", "right_leg"),
    "left_knee": ("左ひざ", "左膝", "knee_l", "knee.l", "left_knee"),
    "right_knee": ("右ひざ", "右膝", "knee_r", "knee.r", "right_knee"),
    "left_ankle": ("左足首", "ankle_l", "ankle.l", "left_ankle"),
    "right_ankle": ("右足首", "ankle_r", "ankle.r", "right_ankle"),
    "left_toe": ("左つま先", "左爪先", "toe_l", "toe.l", "left_toe"),
    "right_toe": ("右つま先", "右爪先", "toe_r", "toe.r", "right_toe"),
    "waist": ("腰", "センター", "センタ", "waist", "hips", "pelvis"),
}


def _bone(armature, key):
    for name in BONE_NAMES[key]:
        bone = armature.data.bones.get(name)
        if bone is not None:
            return bone
    # PMX imports sometimes append suffixes to Japanese bone names.
    for name in BONE_NAMES[key]:
        if any(ord(char) > 127 for char in name):
            for bone in armature.data.bones:
                if bone.name.startswith(name):
                    return bone
    return None


def _point(armature, bone, end=False):
    return armature.matrix_world @ (bone.tail_local if end else bone.head_local)


def _distance(a, b):
    return (a - b).length


def _required(armature, key):
    bone = _bone(armature, key)
    if bone is None:
        raise ValueError("必須ボーンが見つかりません: " + ", ".join(BONE_NAMES[key][:2]))
    return bone


def measure_body(armature):
    """Return measurements in Blender units using the armature's rest bones."""
    if armature is None or armature.type != "ARMATURE":
        raise ValueError("対象モデルとしてアーマチュアを登録してください")

    head = _required(armature, "head")
    neck = _required(armature, "neck")
    l_arm, r_arm = _required(armature, "left_arm"), _required(armature, "right_arm")
    l_elbow, r_elbow = _required(armature, "left_elbow"), _required(armature, "right_elbow")
    l_wrist, r_wrist = _required(armature, "left_wrist"), _required(armature, "right_wrist")
    l_leg, r_leg = _required(armature, "left_leg"), _required(armature, "right_leg")
    l_knee, r_knee = _required(armature, "left_knee"), _required(armature, "right_knee")
    l_ankle, r_ankle = _required(armature, "left_ankle"), _required(armature, "right_ankle")
    waist = _required(armature, "waist")

    head_top = _point(armature, head, end=True)
    l_toe, r_toe = _bone(armature, "left_toe"), _bone(armature, "right_toe")
    foot_l = _point(armature, l_toe) if l_toe else _point(armature, l_ankle)
    foot_r = _point(armature, r_toe) if r_toe else _point(armature, r_ankle)
    floor_z = min(foot_l.z, foot_r.z)

    l_sh, r_sh = _point(armature, l_arm), _point(armature, r_arm)
    l_el, r_el = _point(armature, l_elbow), _point(armature, r_elbow)
    l_wr, r_wr = _point(armature, l_wrist), _point(armature, r_wrist)
    l_hip, r_hip = _point(armature, l_leg), _point(armature, r_leg)
    l_kn, r_kn = _point(armature, l_knee), _point(armature, r_knee)
    l_an, r_an = _point(armature, l_ankle), _point(armature, r_ankle)
    waist_center = _point(armature, waist)

    values = {
        "身長": head_top.z - floor_z,
        "肩幅": _distance(l_sh, r_sh),
        "左腕長": _distance(l_sh, l_el) + _distance(l_el, l_wr),
        "右腕長": _distance(r_sh, r_el) + _distance(r_el, r_wr),
        "左脚長": _distance(l_hip, l_kn) + _distance(l_kn, l_an),
        "右脚長": _distance(r_hip, r_kn) + _distance(r_kn, r_an),
        "腰幅": _distance(l_hip, r_hip),
        "上半身長": abs(waist_center.z - _point(armature, neck).z),
    }
    if any(value <= 0 or value == float("inf") or value != value for value in values.values()):
        raise ValueError("ボーン位置から有効な測定値を計算できません。ボーン配置を確認してください")
    return values
