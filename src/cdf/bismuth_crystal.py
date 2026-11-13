
"""Bismut-Hopper: geometrische Wachstumsregeln, Python 3 / Rhino 8.

Schritte 1-3 laufen auch ohne Rhino. Schritt 4/5 brauchen RhinoCommon/.NET.
Die quadratischen Rahmen sind eine gestalterische Naeherung, keine
Simulation von Kristallgitter, Schmelze oder Oxidschicht. Verzweigungen
duerfen sich durchdringen; ausgegeben werden einzelne geschlossene Meshes.
"""

import math
import Rhino.Geometry as r  

import copy
import json
import math
import random


def pack(data):
    """Ein Text-Item fuer einen verlustfreien Grasshopper-Datentransport."""
    return json.dumps(data, separators=(",", ":"), allow_nan=False)


def unpack(text):
    return json.loads(str(text))


def _number(value, name, lower, upper=None, strict=False):
    value = float(value)
    if (not math.isfinite(value) or value < lower
            or (strict and value == lower)
            or (upper is not None and value > upper)):
        raise ValueError("Ungueltiger Wert fuer " + name)
    return value


def _integer(value, name, lower, upper):
    value = _number(value, name, lower, upper)
    if value != int(value):
        raise ValueError(name + " muss ganzzahlig sein.")
    return int(value)


def _cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0]]


def _point(branch, x=0.0, y=0.0, z=0.0):
    return [branch["o"][i] + x*branch["u"][i]
            + y*branch["v"][i] + z*branch["n"][i] for i in range(3)]


# 1. KEIM: sechs moegliche Wachstumsrichtungen auf einem kleinen Wuerfel.
def create_seed(origin=(0, 0, 0), size=4.0, directions=6, seed=11):
    size = _number(size, "size", 0, strict=True)
    directions = _integer(directions, "directions", 1, 6)
    seed = _integer(seed, "seed", 0, 2147483647)
    origin = [float(x) for x in origin]
    if len(origin) != 3 or not all(math.isfinite(x) for x in origin):
        raise ValueError("origin braucht drei endliche Koordinaten.")
    normals = [(0, 0, 1), (1, 0, 0), (0, 1, 0),
               (-1, 0, 0), (0, -1, 0), (0, 0, -1)]
    branches = []
    for index, normal in enumerate(normals[:directions]):
        u = [1, 0, 0] if normal[2] else [0, 0, 1]
        branches.append({
            "id": index, "o": [origin[i] + normal[i]*size/2 for i in range(3)],
            "u": u, "v": _cross(normal, u), "n": list(normal),
            "half": size/2, "scale": 1.0, "birth": 0, "depth": 0,
        })
    return {"origin": origin, "size": size, "seed": seed,
            "branches": branches, "rings": []}


def _grow_branch(branch, rules, seed):
    """Pro Zeitschritt waechst maximal ein neuer Rahmen nach aussen."""
    rng = random.Random(seed + 1009*branch["id"])
    speed = 1.0 - rules["variation"]*rng.random()
    available = max(0, rules["steps"] - branch["birth"])
    count = int(math.floor(available*speed + 1e-10))
    rings = []
    for k in range(count):
        h = branch["half"] + k*rules["spread"]*branch["scale"]
        wall = min(rules["wall"]*branch["scale"], h*0.8)
        rings.append({"branch": branch["id"], "layer": k,
                      "time": branch["birth"] + int(math.ceil((k+1)/speed - 1e-10)),
                      "half": h, "inner": h-wall,
                      "z": k*rules["rise"]*branch["scale"],
                      "height": rules["rise"]*branch["scale"]})
    return rings


# 2. HAUPTWACHSTUM: Rahmen werden hoeher UND breiter, die Mitte bleibt hohl.
def grow_hoppers(seed_data, steps=18, rise=0.8, spread=0.45,
                 wall=0.85, variation=0.5):
    steps = _integer(steps, "steps", 0, 120)
    rise = _number(rise, "rise", 0, strict=True)
    spread = _number(spread, "spread", 0)
    wall = _number(wall, "wall", 0, strict=True)
    variation = _number(variation, "variation", 0, 0.8)
    if wall <= spread:
        raise ValueError("wall muss groesser als spread sein: Rahmen muessen sich beruehren.")
    if wall >= seed_data["size"]/2:
        raise ValueError("wall muss kleiner als size/2 sein: Mitte soll offen bleiben.")
    if spread >= 4.0*seed_data["size"]/2:
        raise ValueError("spread ist fuer diesen Keim zu gross.")
    data = copy.deepcopy(seed_data)
    data["rules"] = {"steps": steps, "rise": rise, "spread": spread,
                     "wall": wall, "variation": variation}
    data["rings"] = []
    for branch in data["branches"]:
        data["rings"].extend(_grow_branch(branch, data["rules"], data["seed"]))
    return data


# 3. VERZWEIGUNG: Seitenarme beginnen an vorhandenen Aussenkanten.
def add_branches(primary_data, every=4, chance=0.6, branch_scale=0.8):
    """Eine Generation Seitenarme; keine rekursive Verzweigung.

    Jeder Seitenarm startet an einem bereits erzeugten Hauptrahmen.
    Beim Erhoehen von steps bleiben vorhandene Rahmen unveraendert.
    """
    every = _integer(every, "every", 1, 120)
    chance = _number(chance, "chance", 0, 1)
    branch_scale = _number(branch_scale, "branch_scale", 0.1, 1)
    if any(b["depth"] != 0 for b in primary_data["branches"]):
        raise ValueError("add_branches erwartet den Ausgang von grow_hoppers.")
    data = copy.deepcopy(primary_data)
    parents = {b["id"]: b for b in data["branches"]}
    rules = data["rules"]
    for ring in primary_data["rings"]:
        k = ring["layer"]
        if k == 0 or k % every:
            continue
        parent = parents[ring["branch"]]
        # ID und Zufallswert haengen nicht von der aktuellen Schrittzahl ab.
        child_id = 1000 + parent["id"]*1000 + k
        rng = random.Random(data["seed"] + 7919*child_id)
        if rng.random() >= chance:
            continue
        side = rng.randrange(4)
        sign = 1 if side % 2 == 0 else -1
        axis = parent["u"] if side < 2 else parent["v"]
        n = [sign*x for x in axis]
        u = parent["v"] if side < 2 else parent["u"]
        half = min(0.45*ring["height"], 0.4*ring["half"])
        # Ansatz nahe einer Ecke: dort werden Seitenarme besser sichtbar.
        offset = rng.choice((-1, 1))*0.9*(ring["half"]-half)
        x, y = ((sign*ring["half"], offset) if side < 2
                else (offset, sign*ring["half"]))
        # Der erste kleine Rahmen passt auf die Seitenflaeche des Elternrings.
        scale = parent["scale"]*branch_scale
        # Begrenzt die Ausweitung, damit auch die ersten kleinen Rahmen anliegen.
        if rules["spread"]*scale >= 4*half:
            raise ValueError("spread fuer Seitenarme zu gross: rise erhoehen oder spread senken.")
        child = {"id": child_id, "o": _point(parent, x, y, ring["z"]+ring["height"]/2),
                 "u": list(u), "v": _cross(n, u), "n": n,
                 "half": half, "scale": scale, "birth": ring["time"], "depth": 1,
                 "parent": parent["id"], "parent_layer": k}
        new_rings = _grow_branch(child, rules, data["seed"])
        if new_rings:
            data["branches"].append(child)
            data["rings"].extend(new_rings)
    return data


def mesh_data(data):
    """Reine Punkt-/Flaechenlisten, auch ausserhalb von Rhino pruefbar."""
    h = data["size"]/2
    core_branch = {"o": data["origin"], "u": [1, 0, 0],
                   "v": [0, 1, 0], "n": [0, 0, 1]}
    square = lambda a: [(-a, -a), (a, -a), (a, a), (-a, a)]
    vertices = [_point(core_branch, x, y, z) for z in (-h, h) for x, y in square(h)]
    faces = [(3, 2, 1, 0), (4, 5, 6, 7)]
    faces += [(i, (i+1)%4, (i+1)%4+4, i+4) for i in range(4)]
    result = [(vertices, faces, -1, -1)]
    branches = {b["id"]: b for b in data["branches"]}
    for ring in data["rings"]:
        b = branches[ring["branch"]]
        vertices = []
        for a in (ring["half"], ring["inner"]):
            for z in (ring["z"], ring["z"]+ring["height"]):
                vertices.extend(_point(b, x, y, z) for x, y in square(a))
        faces = []
        for i in range(4):
            j = (i+1) % 4
            faces.extend([(i, j, j+4, i+4),             # Aussenwand
                          (j+8, i+8, i+12, j+12),      # Innenwand
                          (i, i+8, j+8, j),            # Unterseite
                          (i+4, j+4, j+12, i+12)])     # Oberseite
        result.append((vertices, faces, ring["layer"], b["id"]))
    return result


# 4. GEOMETRIE: ein geschlossenes Rhino-Mesh pro Rahmen.
def make_meshes(data):
    import Rhino.Geometry as rg
    meshes, layers, branch_ids = [], [], []
    for vertices, faces, layer, branch_id in mesh_data(data):
        mesh = rg.Mesh()
        for x, y, z in vertices:
            mesh.Vertices.Add(x, y, z)
        for a, b, c, d in faces:
            mesh.Faces.AddFace(a, b, c, d)
        mesh.Normals.ComputeNormals()
        mesh.Unweld(0.0, False)
        mesh.Normals.ComputeNormals()
        mesh.Compact()
        meshes.append(mesh)
        layers.append(layer)
        branch_ids.append(branch_id)
    return meshes, layers, branch_ids


def rgb_colors(layers, branch_ids, phase=0.0):
    """Dekorative Farbfolge; keine optische Interferenzsimulation."""
    if len(layers) != len(branch_ids):
        raise ValueError("layers und branch_ids muessen gleich lang sein.")
    phase = _number(phase, "phase", -1000, 1000)
    palette = [(225, 181, 79), (210, 92, 134), (130, 82, 185),
               (57, 116, 189), (66, 181, 166), (225, 181, 79)]
    result = []
    for layer, branch_id in zip(layers, branch_ids):
        if int(layer) < 0:
            result.append((113, 100, 134))
            continue
        t = ((int(layer)*0.09 + (int(branch_id) % 13)*0.047 + phase) % 1)*5
        i = int(t)
        f = t-i
        result.append(tuple(int(round(a*(1-f)+b*f))
                            for a, b in zip(palette[i], palette[i+1])))
    return result


# 5. FARBEN: gleiche Listenlaenge und Reihenfolge wie bei den Meshes.
def make_colors(layers, branch_ids, phase=0.0):
    from System.Drawing import Color
    return [Color.FromArgb(r, g, b) for r, g, b in rgb_colors(layers, branch_ids, phase)]
