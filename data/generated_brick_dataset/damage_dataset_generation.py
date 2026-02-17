import json
import random
import os

# Brick Constants
X_SIZE = 0.25
Y_SIZE = 0.12
Z_TOP = 0.0325
Z_BOT = -0.0325

FACES = {
    0: {"name": "top", "u_dir": "right", "v_dir": "front"},
    1: {"name": "front", "u_dir": "right", "v_dir": "top"},
    2: {"name": "right", "u_dir": "front", "v_dir": "top"},
    3: {"name": "back", "u_dir": "right", "v_dir": "top"},
    4: {"name": "left", "u_dir": "front", "v_dir": "top"},
    5: {"name": "bottom", "u_dir": "right", "v_dir": "front"}
}

VERTS = {
    0: {"pos": [-0.125, 0.06, 0.0325], "desc": "top-front-left corner"},
    1: {"pos": [-0.125, -0.06, 0.0325], "desc": "top-back-left corner"},
    2: {"pos": [0.125, -0.06, 0.0325], "desc": "top-back-right corner"},
    3: {"pos": [0.125, 0.06, 0.0325], "desc": "top-front-right corner"},
    4: {"pos": [-0.125, 0.06, -0.0325], "desc": "bottom-front-left corner"},
    5: {"pos": [0.125, 0.06, -0.0325], "desc": "bottom-front-right corner"},
    6: {"pos": [0.125, -0.06, -0.0325], "desc": "bottom-back-right corner"},
    7: {"pos": [-0.125, -0.06, -0.0325], "desc": "bottom-back-left corner"}
}

EDGES = [
    ([0, 3], "top-front edge"), ([1, 2], "top-back edge"), ([0, 1], "top-left edge"),
    ([3, 2], "top-right edge"), ([4, 5], "bottom-front edge"), ([7, 6], "bottom-back edge"),
    ([0, 4], "front-left vertical edge"), ([3, 5], "front-right vertical edge")
]

def generate_damage(id_num):
    # Determine brick condition: 10% perfect, 20% heavy, 70% mixed
    rand = random.random()
    if rand < 0.10: num_items = 0
    elif rand > 0.80: num_items = random.randint(6, 10)
    else: num_items = random.randint(1, 5)

    damages = []
    for _ in range(num_items):
        dtype = random.choice(["face", "edge", "vertex"])
        status = random.choice(["Chipping", "Spalling", "Staining", "Material Loss", "Crack"])
        val = random.randint(1, 5)

        if dtype == "face":
            f_idx = random.choice(list(FACES.keys()))
            u, v = round(random.random(), 2), round(random.random(), 2)
            # Calculate coordinates based on face
            x = -0.125 + (u * 0.25) if f_idx in [0, 1, 3, 5] else (0.125 if f_idx == 2 else -0.125)
            y = -0.06 + (v * 0.12) if f_idx in [0, 2, 4, 5] else (0.06 if f_idx == 1 else -0.06)
            z = Z_TOP if f_idx == 0 else (Z_BOT if f_idx == 5 else -0.0325 + (v * 0.065))
            
            damages.append({
                "type": "face", "vertices": [f_idx], "status": status, "value": val, "uv": [u, v],
                "description": f"Extensive {status.lower()} visible on the {FACES[f_idx]['name']} surface.",
                "coordinates": {"point": [round(x, 4), round(y, 4), round(z, 4)], "xaxis": [1, 0, 0], "yaxis": [0, 1, 0]}
            })

        elif dtype == "vertex":
            v_idx = random.choice(list(VERTS.keys()))
            damages.append({
                "type": "vertex", "vertices": [v_idx], "status": status, "value": val,
                "description": f"{status} located at the {VERTS[v_idx]['desc']}.",
                "coordinates": {"point": VERTS[v_idx]['pos'], "xaxis": [1, 0, 0], "yaxis": [0, 1, 0]}
            })

        elif dtype == "edge":
            e_verts, e_name = random.choice(EDGES)
            p1, p2 = VERTS[e_verts[0]]['pos'], VERTS[e_verts[1]]['pos']
            mid = [(p1[0]+p2[0])/2, (p1[1]+p2[1])/2, (p1[2]+p2[2])/2]
            damages.append({
                "type": "edge", "vertices": sorted(e_verts), "status": status, "value": val,
                "description": f"Noticable {status.lower()} along the {e_name}.",
                "coordinates": {"point": mid, "xaxis": [1, 0, 0], "yaxis": [0, 1, 0]}
            })

    return {"nodeKey": "0", "appendDamages": damages}

# This gets the directory where the script itself is saved
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "brick_dataset")

# Create the folder using the absolute path
os.makedirs(output_dir, exist_ok=True)

for i in range(100):
    file_path = os.path.join(output_dir, f"brick_{i:03d}.json")
    with open(file_path, "w") as f:
        json.dump(generate_damage(i), f, indent=2)

print(f"Finished! 100 files are in: {output_dir}")