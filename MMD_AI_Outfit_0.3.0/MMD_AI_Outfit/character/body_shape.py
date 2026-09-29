"""Body mesh discovery and cross-section measurements for a Character Profile."""

from math import hypot

from .body_measurement import _bone, _bone_names, _normalize


_BODY_TERMS = ("body", "skin", "nude", "素体", "身体", "体", "ボディ", "肌")


def _is_linked_to_armature(obj, armature):
    parent = obj.parent
    while parent is not None:
        if parent == armature:
            return True
        parent = parent.parent
    return any(mod.type == "ARMATURE" and mod.object == armature for mod in obj.modifiers)


def find_body_mesh(armature, objects):
    """Find the most likely mesh belonging to the registered MMD model."""
    if armature is None:
        return None
    armature_names = {
        _normalize(name)
        for bone in armature.data.bones
        for name in _bone_names(armature, bone)
    }
    candidates = []
    for obj in objects:
        if obj.type != "MESH" or not _is_linked_to_armature(obj, armature):
            continue
        normalized_name = _normalize(obj.name)
        score = sum(24 for term in _BODY_TERMS if _normalize(term) in normalized_name)
        group_names = {_normalize(group.name) for group in obj.vertex_groups}
        coverage = len(group_names & armature_names)
        score += min(coverage, 20) * 2
        score += min(len(obj.data.vertices), 100000) / 100000
        candidates.append((score, len(obj.data.vertices), obj.name, obj))
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[0], item[1], item[2]))[3]


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _inside(point, polygon):
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i, current in enumerate(polygon):
        previous = polygon[j]
        if ((current[1] > y) != (previous[1] > y)) and x < (
            (previous[0] - current[0]) * (y - current[1]) / (previous[1] - current[1]) + current[0]
        ):
            inside = not inside
        j = i
    return inside


def _section_segments(vertices, triangles, plane_z, epsilon):
    points = {}
    segments = set()

    def point_key(point):
        return (round(point[0] / epsilon), round(point[1] / epsilon))

    for tri in triangles:
        intersections = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            a, b = vertices[tri[i]], vertices[tri[j]]
            da, db = a[2] - plane_z, b[2] - plane_z
            if da < -epsilon and db > epsilon or db < -epsilon and da > epsilon:
                t = da / (da - db)
                intersections.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
            elif abs(da) <= epsilon and abs(db) > epsilon:
                intersections.append((a[0], a[1]))
        unique = {}
        for point in intersections:
            key = point_key(point)
            unique[key] = point
        if len(unique) != 2:
            continue
        keys = list(unique)
        for key, point in unique.items():
            points[key] = point
        edge = tuple(sorted(keys))
        if edge[0] != edge[1]:
            segments.add(edge)

    adjacency = {}
    for a, b in segments:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)

    loops = []
    unused = set(segments)
    while unused:
        edge = next(iter(unused))
        start, current = edge
        path = [start, current]
        unused.remove(edge)
        previous = start
        for _ in range(len(segments) + 1):
            if current == start:
                break
            options = [other for other in adjacency.get(current, ()) if tuple(sorted((current, other))) in unused]
            if not options:
                break
            following = options[0]
            unused.remove(tuple(sorted((current, following))))
            previous, current = current, following
            path.append(current)
        if len(path) >= 4 and path[-1] == start:
            polygon = [points[key] for key in path[:-1]]
            perimeter = sum(hypot(polygon[(i + 1) % len(polygon)][0] - p[0], polygon[(i + 1) % len(polygon)][1] - p[1]) for i, p in enumerate(polygon))
            loops.append((polygon, perimeter))
    return loops


def _measure_section(vertices, triangles, plane_z, center_xy):
    z_values = [point[2] for point in vertices]
    epsilon = max((max(z_values) - min(z_values)) * 1e-7, 1e-8)
    loops = _section_segments(vertices, triangles, plane_z, epsilon)
    if not loops:
        raise ValueError("指定した高さで閉じた身体断面を取得できませんでした")
    containing = [(poly, perimeter) for poly, perimeter in loops if _inside(center_xy, poly)]
    if containing:
        return max(perimeter for _, perimeter in containing)
    return min(loops, key=lambda item: hypot(
        sum(point[0] for point in item[0]) / len(item[0]) - center_xy[0],
        sum(point[1] for point in item[0]) / len(item[0]) - center_xy[1],
    ))[1]


def measure_body_shape(armature, body_mesh, context):
    """Measure chest, waist, and hip circumferences from horizontal mesh slices."""
    if body_mesh is None or body_mesh.type != "MESH":
        raise ValueError("身体メッシュを選択または自動検出してください")

    waist_bone = _bone(armature, "waist")
    neck_bone = _bone(armature, "neck")
    left_arm = _bone(armature, "left_arm")
    right_arm = _bone(armature, "right_arm")
    left_leg = _bone(armature, "left_leg")
    right_leg = _bone(armature, "right_leg")
    if not all((waist_bone, neck_bone, left_arm, right_arm, left_leg, right_leg)):
        raise ValueError("断面の高さを決める腰・首・腕・脚ボーンを取得できません")

    waist_z = waist_bone.head_local.z
    neck_z = neck_bone.head_local.z
    if neck_z <= waist_z:
        raise ValueError("腰から首への高さを決定できません。モデルの向きを確認してください")
    chest_z = waist_z + (neck_z - waist_z) * 0.72
    hip_z = (left_leg.head_local.z + right_leg.head_local.z) * 0.5
    center_xy = (waist_bone.head_local.x, waist_bone.head_local.y)

    depsgraph = context.evaluated_depsgraph_get()
    evaluated = body_mesh.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        to_rig = armature.matrix_world.inverted() @ evaluated.matrix_world
        vertices = [tuple(to_rig @ vertex.co) for vertex in mesh.vertices]
        triangles = [tuple(tri.vertices) for tri in mesh.loop_triangles]
        return {
            "胸囲": _measure_section(vertices, triangles, chest_z, center_xy),
            "ウエスト": _measure_section(vertices, triangles, waist_z, center_xy),
            "ヒップ": _measure_section(vertices, triangles, hip_z, center_xy),
        }
    finally:
        evaluated.to_mesh_clear()
