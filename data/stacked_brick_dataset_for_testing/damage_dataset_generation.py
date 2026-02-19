import json
import random
import os

# ------------------------------------------------------------
# Brick size regulation
# Set your target brick size here (meters)
# ------------------------------------------------------------
BRICK_SIZE_X = 0.24
BRICK_SIZE_Y = 0.12
BRICK_SIZE_Z = 0.045

# ------------------------------------------------------------
# Dataset settings
# ------------------------------------------------------------
TOTAL_BRICKS = 100                 # will be forced to even
STACK_COUNT = 2                    # fixed to 2 as requested
BRICK_ID_TEMPLATE = "stack{stack}_brick{idx}"  # naming convention

# ------------------------------------------------------------
# Derived constants (do not edit)
# Brick is centered at origin
# ------------------------------------------------------------
HALF_X = BRICK_SIZE_X / 2.0
HALF_Y = BRICK_SIZE_Y / 2.0
HALF_Z = BRICK_SIZE_Z / 2.0
Z_TOP = HALF_Z
Z_BOT = -HALF_Z

FACES = {
    0: {"name": "top", "u_dir": "right", "v_dir": "front"},
    1: {"name": "front", "u_dir": "right", "v_dir": "top"},
    2: {"name": "right", "u_dir": "front", "v_dir": "top"},
    3: {"name": "back", "u_dir": "right", "v_dir": "top"},
    4: {"name": "left", "u_dir": "front", "v_dir": "top"},
    5: {"name": "bottom", "u_dir": "right", "v_dir": "front"}
}

# Vertices derived from brick size
VERTS = {
    0: {"pos": [-HALF_X,  HALF_Y,  HALF_Z], "desc": "top-front-left corner"},
    1: {"pos": [-HALF_X, -HALF_Y,  HALF_Z], "desc": "top-back-left corner"},
    2: {"pos": [ HALF_X, -HALF_Y,  HALF_Z], "desc": "top-back-right corner"},
    3: {"pos": [ HALF_X,  HALF_Y,  HALF_Z], "desc": "top-front-right corner"},
    4: {"pos": [-HALF_X,  HALF_Y, -HALF_Z], "desc": "bottom-front-left corner"},
    5: {"pos": [ HALF_X,  HALF_Y, -HALF_Z], "desc": "bottom-front-right corner"},
    6: {"pos": [ HALF_X, -HALF_Y, -HALF_Z], "desc": "bottom-back-right corner"},
    7: {"pos": [-HALF_X, -HALF_Y, -HALF_Z], "desc": "bottom-back-left corner"}
}

EDGES = [
    ([0, 3], "top-front edge"),
    ([1, 2], "top-back edge"),
    ([0, 1], "top-left edge"),
    ([3, 2], "top-right edge"),
    ([4, 5], "bottom-front edge"),
    ([7, 6], "bottom-back edge"),
    ([0, 4], "front-left vertical edge"),
    ([3, 5], "front-right vertical edge")
]


def _midpoint(p1, p2):
    return [(p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0, (p1[2] + p2[2]) / 2.0]


def _round_point(p, nd=4):
    return [round(float(p[0]), nd), round(float(p[1]), nd), round(float(p[2]), nd)]


def _face_point_from_uv(face_idx, u, v):
    """
    u and v are always in [0..1]
    Coordinates are in the brick local frame centered at origin.
    """
    # top and bottom: u maps along x, v maps along y
    if face_idx == 0:  # top
        x = -HALF_X + u * BRICK_SIZE_X
        y = -HALF_Y + v * BRICK_SIZE_Y
        z = Z_TOP
        return [x, y, z]

    if face_idx == 5:  # bottom
        x = -HALF_X + u * BRICK_SIZE_X
        y = -HALF_Y + v * BRICK_SIZE_Y
        z = Z_BOT
        return [x, y, z]

    # front and back: u maps along x, v maps along z
    if face_idx == 1:  # front (+y)
        x = -HALF_X + u * BRICK_SIZE_X
        y = HALF_Y
        z = -HALF_Z + v * BRICK_SIZE_Z
        return [x, y, z]

    if face_idx == 3:  # back (-y)
        x = -HALF_X + u * BRICK_SIZE_X
        y = -HALF_Y
        z = -HALF_Z + v * BRICK_SIZE_Z
        return [x, y, z]

    # right and left: u maps along y, v maps along z
    if face_idx == 2:  # right (+x)
        x = HALF_X
        y = -HALF_Y + u * BRICK_SIZE_Y
        z = -HALF_Z + v * BRICK_SIZE_Z
        return [x, y, z]

    if face_idx == 4:  # left (-x)
        x = -HALF_X
        y = -HALF_Y + u * BRICK_SIZE_Y
        z = -HALF_Z + v * BRICK_SIZE_Z
        return [x, y, z]

    return [0.0, 0.0, 0.0]


def generate_damage(stack, idx_in_stack):
    """
    Generates one brick json object.
    Naming is handled by the caller. This function only builds the content.
    """
    # Determine brick condition: 10% perfect, 20% heavy, 70% mixed
    r = random.random()
    if r < 0.10:
        num_items = 0
    elif r > 0.80:
        num_items = random.randint(6, 10)
    else:
        num_items = random.randint(1, 5)

    damages = []
    for _ in range(num_items):
        dtype = random.choice(["face", "edge", "vertex"])
        status = random.choice(["Chipping", "Spalling", "Staining", "Material Loss", "Crack"])
        val = random.randint(1, 5)

        if dtype == "face":
            f_idx = random.choice(list(FACES.keys()))
            u = round(random.random(), 2)
            v = round(random.random(), 2)

            pt = _face_point_from_uv(f_idx, u, v)

            damages.append({
                "type": "face",
                "vertices": [f_idx],
                "status": status,
                "value": val,
                "uv": [u, v],
                "description": f"Extensive {status.lower()} visible on the {FACES[f_idx]['name']} surface.",
                "coordinates": {
                    "point": _round_point(pt, 4),
                    "xaxis": [1, 0, 0],
                    "yaxis": [0, 1, 0]
                }
            })

        elif dtype == "vertex":
            v_idx = random.choice(list(VERTS.keys()))
            damages.append({
                "type": "vertex",
                "vertices": [v_idx],
                "status": status,
                "value": val,
                "description": f"{status} located at the {VERTS[v_idx]['desc']}.",
                "coordinates": {
                    "point": _round_point(VERTS[v_idx]["pos"], 4),
                    "xaxis": [1, 0, 0],
                    "yaxis": [0, 1, 0]
                }
            })

        elif dtype == "edge":
            e_verts, e_name = random.choice(EDGES)
            p1 = VERTS[e_verts[0]]["pos"]
            p2 = VERTS[e_verts[1]]["pos"]
            mid = _midpoint(p1, p2)

            damages.append({
                "type": "edge",
                "vertices": sorted(e_verts),
                "status": status,
                "value": val,
                "description": f"Noticable {status.lower()} along the {e_name}.",
                "coordinates": {
                    "point": _round_point(mid, 4),
                    "xaxis": [1, 0, 0],
                    "yaxis": [0, 1, 0]
                }
            })

    return {
        "nodeKey": "0",
        "brickId": BRICK_ID_TEMPLATE.format(stack=stack, idx=idx_in_stack),
        "brickSize": {"x": BRICK_SIZE_X, "y": BRICK_SIZE_Y, "z": BRICK_SIZE_Z},
        "appendDamages": damages
    }


def main():
    # Resolve output folder next to script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "brick_dataset")
    os.makedirs(output_dir, exist_ok=True)

    # Force even and split into 2 stacks evenly
    total = int(TOTAL_BRICKS)
    if total <= 0:
        raise ValueError("TOTAL_BRICKS must be > 0")
    if total % 2 == 1:
        total -= 1

    per_stack = total // 2

    # Write files
    for stack in range(1, STACK_COUNT + 1):
        for idx in range(1, per_stack + 1):
            brick_name = BRICK_ID_TEMPLATE.format(stack=stack, idx=idx)
            file_path = os.path.join(output_dir, f"{brick_name}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(generate_damage(stack, idx), f, indent=2)

    print(f"Finished! {total} files created in: {output_dir}")
    print(f"Stack 1: {per_stack} bricks, Stack 2: {per_stack} bricks")
    print(f"Brick size used: x={BRICK_SIZE_X}, y={BRICK_SIZE_Y}, z={BRICK_SIZE_Z}")


if __name__ == "__main__":
    main()
