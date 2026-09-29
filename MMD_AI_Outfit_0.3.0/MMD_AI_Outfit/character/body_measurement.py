"""Body measurements for standard and extended MMD armatures."""


BONE_NAMES = {
    "head": ("頭", "head"),
    "neck": ("首", "neck"),
    "left_arm": (
        "左腕", "左上腕", "左腕上", "左腕1", "upperarm.l", "upper_arm.l",
        "arm_upper.l", "upperarm_l", "upper_arm_l", "arm_l", "arm.l", "left_upper_arm", "left_arm",
    ),
    "right_arm": (
        "右腕", "右上腕", "右腕上", "右腕1", "upperarm.r", "upper_arm.r",
        "arm_upper.r", "upperarm_r", "upper_arm_r", "arm_r", "arm.r", "right_upper_arm", "right_arm",
    ),
    "left_elbow": (
        "左ひじ", "左肘", "左前腕", "forearm.l", "lowerarm.l", "lower_arm.l",
        "elbow.l", "forearm_l", "lowerarm_l", "lower_arm_l", "elbow_l", "left_forearm", "left_elbow",
    ),
    "right_elbow": (
        "右ひじ", "右肘", "右前腕", "forearm.r", "lowerarm.r", "lower_arm.r",
        "elbow.r", "forearm_r", "lowerarm_r", "lower_arm_r", "elbow_r", "right_forearm", "right_elbow",
    ),
    "left_wrist": ("左手首", "手首.l", "wrist.l", "hand.l", "wrist_l", "left_wrist"),
    "right_wrist": ("右手首", "手首.r", "wrist.r", "hand.r", "wrist_r", "right_wrist"),
    "left_leg": ("左足", "左脚", "左股", "thigh.l", "upper_leg.l", "thigh_l", "upper_leg_l", "left_leg"),
    "right_leg": ("右足", "右脚", "右股", "thigh.r", "upper_leg.r", "thigh_r", "upper_leg_r", "right_leg"),
    "left_knee": ("左ひざ", "左膝", "左すね", "knee.l", "shin.l", "lower_leg.l", "knee_l", "left_knee"),
    "right_knee": ("右ひざ", "右膝", "右すね", "knee.r", "shin.r", "lower_leg.r", "knee_r", "right_knee"),
    "left_ankle": ("左足首", "ankle.l", "foot.l", "ankle_l", "left_ankle"),
    "right_ankle": ("右足首", "ankle.r", "foot.r", "ankle_r", "right_ankle"),
    "left_toe": ("左つま先", "左爪先", "toe.l", "toe_l", "left_toe"),
    "right_toe": ("右つま先", "右爪先", "toe.r", "toe_r", "right_toe"),
    "waist": ("腰", "センター", "センタ", "waist", "hips", "pelvis"),
}


def _normalize(name):
    """Normalize common Blender side suffixes and punctuation for comparison."""
    return "".join(char.lower() for char in name if char.isalnum() or ord(char) > 127)


def _bone_names(armature, bone):
    names = [bone.name]
    # MMD Tools can retain original PMX names on either the data or pose bone.
    pose_bone = armature.pose.bones.get(bone.name)
    for owner in (bone, pose_bone):
        mmd_data = getattr(owner, "mmd_bone", None) if owner is not None else None
        if mmd_data is not None:
            for attr in ("name_j", "name_e"):
                value = getattr(mmd_data, attr, "")
                if value:
                    names.append(value)
    return names


def _is_auxiliary(armature, bone):
    markers = ("捩", "twist", "helper", "補助", "ik", "キャンセル")
    return any(
        _normalize(marker) in _normalize(name)
        for name in _bone_names(armature, bone)
        for marker in markers
    )

def _bone(armature, key):
    bones = list(armature.data.bones)
    aliases = BONE_NAMES[key]
    normalized_aliases = [_normalize(name) for name in aliases]

    # Prefer a literal base-bone name before normalized aliases, which may
    # ignore suffix punctuation such as '+' and could otherwise pick a helper.
    for alias in aliases:
        for bone in bones:
            if alias in _bone_names(armature, bone):
                return bone

    exact = []
    for alias in normalized_aliases:
        for bone in bones:
            if any(_normalize(name) == alias for name in _bone_names(armature, bone)):
                exact.append(bone)
    if exact:
        return min(exact, key=lambda item: (_is_auxiliary(armature, item), len(_normalize(item.name))))

    # MMD models commonly add suffixes such as '+' or digits. Match Japanese
    # prefixes and Blender-style side suffixes, while excluding helper/twist
    # bones so a split arm does not resolve to a twist segment by accident.
    for alias in normalized_aliases:
        candidates = []
        for bone in bones:
            if _is_auxiliary(armature, bone):
                continue
            for name in _bone_names(armature, bone):
                normalized = _normalize(name)
                if normalized.startswith(alias) or normalized.endswith(alias):
                    candidates.append(bone)
                    break
        if candidates:
            return min(candidates, key=lambda item: len(_normalize(item.name)))
    return None


def _point(armature, bone, end=False):
    return armature.matrix_world @ (bone.tail_local if end else bone.head_local)


def _distance(a, b):
    return (a - b).length


def _required(armature, key):
    bone = _bone(armature, key)
    if bone is None:
        choices = ", ".join(BONE_NAMES[key][:4])
        raise ValueError(f"必須ボーンが見つかりません: {choices} など")
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



