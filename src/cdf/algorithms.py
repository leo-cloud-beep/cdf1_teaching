import math
import random

HYPERBOLIC_MODEL_VERSION = "rosette-1"


# 1. INPUTS AND THE CROCHET GROWTH RULE
def _integer(value, name, minimum, maximum):
    number = float(value)
    if not math.isfinite(number) or number != int(number):
        raise ValueError(name + " must be a whole number.")
    value = int(number)
    if not minimum <= value <= maximum:
        raise ValueError("{} must be between {} and {}.".format(
            name, minimum, maximum))
    return value


def stitch_counts(base_chain_stitch_count, rows, increase):
    """Row zero is the base chain; rows counts additional crochet rows.

    Integer increase reproduces the screenshot's count exactly.
    Fractional increase is an average growth factor, rounded for display;
    the mesh uses the continuous, unrounded exponential growth law.
    """
    counts = []
    for row in range(rows + 1):
        count = base_chain_stitch_count * increase ** row
        counts.append(int(math.floor(count + 0.5)))
    return counts


def _rosette_start(base, rows, factor, resolution):
    """Sample a generalized Enneper seed with three broad lobes.

    This is only an initial guess, not the hyperbolic target metric.
    Its radial arc length is s(r) = r + r**5/5. Fit the base circumference
    and total radial width before relaxing to the exponential row lengths.
    """
    growth = math.log(factor) * rows
    outer = 0.45 + 1.15 * min(1.0, growth / 3.0)

    def arc(r):
        return r + r**5 / 5.0

    # The ratio is strictly increasing, so bisection also handles a wide
    # base with few rows without a fragile fixed-point iteration.
    target = base / (2.0 * math.pi * rows)
    low, high = 0.0, outer
    for _ in range(48):
        inner = (low + high) * 0.5
        ratio = inner * (1.0 + inner**4) / (arc(outer) - arc(inner))
        if ratio < target:
            low = inner
        else:
            high = inner
    inner = (low + high) * 0.5
    scale = rows / (arc(outer) - arc(inner))
    radii = []
    for j in range(rows * resolution + 1):
        target = arc(inner) + j / (resolution * scale)
        low, high = inner, outer
        for _ in range(40):
            r = (low + high) * 0.5
            if arc(r) < target:
                low = r
            else:
                high = r
        radii.append((low + high) * 0.5)
    return radii, scale, min(1.0, growth)


def _build_mesh(base, rows, factor, resolution, closed, seed):
    """Sample crochet rows, then stitch neighbouring rows with triangles."""
    points, coordinates, row_ids, faces = [], [], [], []
    sample_counts = []
    total = 0
    for j in range(rows * resolution + 1):
        t = float(j) / resolution
        n = int(math.floor(base * resolution * factor ** t + 0.5))
        total += n if closed else n + 1
        if total > 6500:
            raise ValueError("Mesh exceeds 6500 vertices. Reduce rows, "
                             "increase or resolution. Growth is exponential.")
        sample_counts.append(n)

    rng = random.Random(seed)
    phases = [rng.uniform(0.0, 2.0 * math.pi) for _ in range(3)]
    if closed and factor > 1.0:
        radii, rosette_scale, blend = _rosette_start(
            base, rows, factor, resolution)
    phase = (0.17 + (seed - 1) * 2.399963229728653) % (2.0 * math.pi)
    for j, n in enumerate(sample_counts):
        y = float(j) / resolution
        ids = []
        for i in range(n if closed else n + 1):
            u = float(i) / n
            angle = 2.0 * math.pi * u
            # A smooth initial disturbance chooses a folding direction.
            # Its amplitude is not a force or a constraint during relaxation.
            wave = (math.sin(3.0 * angle + phases[0] + 0.20 * y)
                    + 0.5 * math.sin(5.0 * angle + phases[1] - 0.17 * y)
                    + 0.25 * math.cos(7.0 * angle + phases[2]))
            z = 0.8 * min(1.0, (factor - 1.0) * 5.0) * (1.0 + 0.4*y) * wave
            if closed:
                radius = base / (2.0 * math.pi)
                # A periodic flat strip embeds naturally as a cylinder.
                p = [radius * math.cos(angle + phase),
                     radius * math.sin(angle + phase), y]
                if factor > 1.0:
                    r, t = radii[j], angle + phase
                    curled = [
                        rosette_scale * (r*math.cos(t) - r**5*math.cos(5*t)/5),
                        rosette_scale * (r*math.sin(t) + r**5*math.sin(5*t)/5),
                        rosette_scale * 2*r**3*math.cos(3*t)/3,
                    ]
                    p = [(1.0-blend)*p[k] + blend*curled[k] for k in range(3)]
            else:
                p = [(u - 0.5) * base, y, z]
            ids.append(len(points))
            points.append(p)
            coordinates.append((u, y))
        row_ids.append(ids)

    # A zipper triangulation joins rows with DIFFERENT numbers of points.
    # All faces share vertex indices, including the closed-mode seam.
    for j in range(len(row_ids) - 1):
        lower, upper = row_ids[j], row_ids[j + 1]
        n, m = sample_counts[j], sample_counts[j + 1]
        i = k = 0
        while i < n or k < m:
            a = lower[i % len(lower)]
            b = upper[k % len(upper)]
            if k == m or (i < n and (i + 1)*m <= (k + 1)*n):
                faces.append((a, lower[(i + 1) % len(lower)], b))
                i += 1
            else:
                faces.append((a, upper[(k + 1) % len(upper)], b))
                k += 1
    return points, coordinates, row_ids, faces


# 2. TARGET LENGTHS: EXTRA ROW LENGTH CREATES NEGATIVE TARGET CURVATURE
def _target_distance(a, b, coordinates, base, factor, closed):
    ua, ya = coordinates[a]
    ub, yb = coordinates[b]
    du = abs(ua - ub)
    if closed:
        du = min(du, 1.0 - du)
    dx, dy = base * du, ya - yb
    k = math.log(factor)
    if k < 1.e-10:
        return math.sqrt(dx*dx + dy*dy)
    # Exact intrinsic distance for ds^2 = dy^2 + exp(2*k*y) dx^2.
    # This numerically stable expression is equivalent to the hyperbolic
    # upper-half-plane distance formula. See the guide's math appendix.
    value = (math.sinh(0.5*k*dy)**2
             + (0.5*k*dx)**2 * math.exp(k*(ya + yb)))
    return 2.0 * math.asinh(math.sqrt(value)) / k


def _constraints(faces, coordinates, base, factor, closed, seed):
    edges = {}
    for a, b, c in faces:
        for i, j, opposite in ((a, b, c), (b, c, a), (c, a, b)):
            key = (min(i, j), max(i, j))
            edges.setdefault(key, []).append(opposite)
    springs, hinges = [], []
    for (a, b), opposite in sorted(edges.items()):
        target = _target_distance(a, b, coordinates, base, factor, closed)
        springs.append((a, b, target))
        if len(opposite) == 2:
            hinges.append((a, b, opposite[0], opposite[1]))
    rng = random.Random(seed + 137)
    rng.shuffle(springs)
    rng.shuffle(hinges)
    return springs, hinges


# 3. RELAX THE SHEET IN THREE DIMENSIONS
def _fit_lengths(points, springs, strength=0.9):
    for a, b, target in springs:
        p, q = points[a], points[b]
        dx, dy, dz = q[0]-p[0], q[1]-p[1], q[2]-p[2]
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length < 1.e-12:
            continue
        amount = 0.5 * strength * (length - target) / length
        dx, dy, dz = dx*amount, dy*amount, dz*amount
        p[0] += dx; p[1] += dy; p[2] += dz
        q[0] -= dx; q[1] -= dy; q[2] -= dz


def _soften_folds(points, hinges, strength):
    """Gently align adjacent triangles around their common edge.

    This is a geometric bending regularizer, not a calibrated yarn law.
    Length constraints are reapplied after this step.
    """
    for a, b, c, d in hinges:
        p, q, r, s = points[a], points[b], points[c], points[d]
        ex, ey, ez = q[0]-p[0], q[1]-p[1], q[2]-p[2]
        length = math.sqrt(ex*ex + ey*ey + ez*ez)
        if length < 1.e-12:
            continue
        ex, ey, ez = ex/length, ey/length, ez/length
        rx, ry, rz = r[0]-p[0], r[1]-p[1], r[2]-p[2]
        sx, sy, sz = s[0]-p[0], s[1]-p[1], s[2]-p[2]
        rt = ex*rx + ey*ry + ez*rz
        st = ex*sx + ey*sy + ez*sz
        rx, ry, rz = rx-rt*ex, ry-rt*ey, rz-rt*ez
        sx, sy, sz = sx-st*ex, sy-st*ey, sz-st*ez
        hr = math.sqrt(rx*rx + ry*ry + rz*rz)
        hs = math.sqrt(sx*sx + sy*sy + sz*sz)
        if min(hr, hs) < 1.e-12:
            continue
        vx, vy, vz = rx/hr-sx/hs, ry/hr-sy/hs, rz/hr-sz/hs
        length = math.sqrt(vx*vx + vy*vy + vz*vz)
        if length < 1.e-12:
            continue
        vx, vy, vz = vx/length, vy/length, vz/length
        r[0] += strength * (hr*vx-rx)
        r[1] += strength * (hr*vy-ry)
        r[2] += strength * (hr*vz-rz)
        s[0] += strength * (-hs*vx-sx)
        s[1] += strength * (-hs*vy-sy)
        s[2] += strength * (-hs*vz-sz)


def _relax(points, springs, hinges, iterations, progressive=False):
    if iterations * (2*len(springs) + len(hinges)) > 35000000:
        raise ValueError("This solve is too large. Reduce iterations, rows, "
                         "increase or resolution.")
    starting_lengths = None
    if progressive and iterations:
        starting_lengths = [math.sqrt(sum(
            (points[a][i]-points[b][i])**2 for i in range(3)))
            for a, b, _ in springs]
    working = springs
    for step in range(iterations):
        progress = float(step) / max(1, iterations - 1)
        if starting_lengths is not None and step % 5 == 0:
            weight = min(1.0, step / max(1.0, iterations * 0.65))
            working = [(a, b, (1.0-weight)*start + weight*target)
                       for start, (a, b, target) in zip(starting_lengths, springs)]
        # First find broad folds; then prioritize accurate edge lengths.
        bend = 0.12 * (1.0 - 0.85 * max(0.0, (progress-0.7)/0.3))
        _soften_folds(points, hinges, bend)
        _fit_lengths(points, working)
        _fit_lengths(points, working)
    if iterations:
        for _ in range(32):
            _fit_lengths(points, springs)


def generate(base_chain_stitch_count=8, rows=16, increase=1.25,
             stitch_size=1.0, resolution=2, iterations=600,
             closed=True, seed=1):
    """Return plain Python geometry; safe to import outside Rhino.

    Units follow the Rhino document: stitch_size controls width AND height.
    closed joins the base chain into a ring; it does not make a solid.
    """
    base = _integer(base_chain_stitch_count, "base_chain_stitch_count", 2, 200)
    rows = _integer(rows, "rows", 1, 40)
    resolution = _integer(resolution, "resolution", 1, 4)
    iterations = _integer(iterations, "iterations", 0, 1500)
    seed = _integer(seed, "seed", 0, 2147483000)
    factor, size = float(increase), float(stitch_size)
    if not math.isfinite(factor) or not 1.0 <= factor <= 2.0:
        raise ValueError("increase must be between 1.0 and 2.0.")
    if not math.isfinite(size) or size <= 0.0:
        raise ValueError("stitch_size must be positive and finite.")
    if not isinstance(closed, bool):
        raise ValueError("closed needs a Boolean Toggle, with bool Type Hint.")
    if closed and base < 8:
        raise ValueError("Use at least 8 base stitches for a circular model.")

    points, uv, row_ids, faces = _build_mesh(
        base, rows, factor, resolution, closed, seed)
    springs, hinges = _constraints(faces, uv, base, factor, closed, seed)
    _relax(points, springs, hinges, iterations,
           progressive=closed and factor > 1.0)

    errors = []
    for a, b, target in springs:
        p, q = points[a], points[b]
        length = math.sqrt(sum((p[i]-q[i])**2 for i in range(3)))
        errors.append(abs(length/target - 1.0))
    # Solve in stitch units, then scale; size does not change the folding.
    center = [sum(p[i] for p in points)/len(points) for i in range(3)]
    points = [[(p[i]-center[i])*size for i in range(3)] for p in points]
    stats = {
        "vertices": len(points), "faces": len(faces),
        "mean_edge_error": sum(errors)/len(errors),
        "max_edge_error": max(errors),
        "target_gaussian_curvature": -(math.log(factor)/size)**2,
        "iterations": iterations,
        "initialization": ("rosette" if factor > 1.0 else "cylinder")
                          if closed else "open strip",
    }
    return {"points": points, "faces": faces,
            "row_ids": row_ids[::resolution],
            "all_row_ids": row_ids,
            "counts": stitch_counts(base, rows, factor),
            "closed": closed, "stats": stats}


# 4. FINISH: CONVERT TO RHINO GEOMETRY AND EXPLAIN THE OUTPUT
def to_rhino(result):
    import Rhino.Geometry as rg
    points = [rg.Point3d(*p) for p in result["points"]]
    mesh = rg.Mesh()
    for p in points:
        mesh.Vertices.Add(p)
    for a, b, c in result["faces"]:
        mesh.Faces.AddFace(a, b, c)
    mesh.Normals.ComputeNormals()
    mesh.Compact()

    def curve(ids, close=False):
        polyline = rg.Polyline()
        for index in ids:
            polyline.Add(points[index])
        if close:
            polyline.Add(points[ids[0]])
        return polyline.ToPolylineCurve()

    rows_out = [curve(ids, result["closed"]) for ids in result["row_ids"]]
    all_rows = result["all_row_ids"]
    if result["closed"]:
        boundaries = [rows_out[0], rows_out[-1]]
    else:
        outline = (all_rows[0] + [r[-1] for r in all_rows[1:]]
                   + all_rows[-1][-2::-1]
                   + [r[0] for r in all_rows[-2:0:-1]])
        boundaries = [curve(outline, True)]
    stats = result["stats"]
    info = ("Model: {} | Start: {}\n"
            "Stitches per row (base first): {}\n"
            "Vertices: {} | Triangles: {}\n"
            "Mean edge error: {:.2%} | Max: {:.2%}\n"
            "Target K: {:.6g} per document-unit squared\n"
            "Approximate sheet; no thickness or self-collision.").format(
                HYPERBOLIC_MODEL_VERSION, stats["initialization"],
                ", ".join(str(c) for c in result["counts"]),
                stats["vertices"], stats["faces"],
                stats["mean_edge_error"], stats["max_edge_error"],
                stats["target_gaussian_curvature"])
    if stats["iterations"] == 0:
        info += "\nUNRELAXED: iterations is zero."
    if stats["mean_edge_error"] > 0.05:
        info += "\nPoor length fit: try more iterations or less growth."
    return mesh, rows_out, boundaries, result["counts"], info


def grasshopper_outputs(inputs):
    defaults = dict(base_chain_stitch_count=8, rows=16, increase=1.25,
                    stitch_size=1.0, resolution=2, iterations=600,
                    closed=True, seed=1)
    if inputs.get("run", True) is False:
        return None, [], [], [], "Paused. Set run to True."
    values = {name: defaults[name] if inputs.get(name) is None else inputs[name]
              for name in defaults}
    return to_rhino(generate(**values))


def create_hyperbolic_surface(base_chain_stitch_count=8, rows=16,
                              increase=1.25, stitch_size=1.0,
                              resolution=2, iterations=600,
                              closed=True, seed=1, run=True):
    """Public entry point; export this from cdf.__init__ for package use."""
    return grasshopper_outputs({
        "base_chain_stitch_count": base_chain_stitch_count,
        "rows": rows,
        "increase": increase,
        "stitch_size": stitch_size,
        "resolution": resolution,
        "iterations": iterations,
        "closed": closed,
        "seed": seed,
        "run": run,
    })


# Executed when pasted into Grasshopper, but not on normal module import.
if "ghenv" in globals():
    M, R, B, C, Info = grasshopper_outputs(globals())
