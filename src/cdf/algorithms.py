

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


"------------------------------------------------------assignemnt 2.2----------------------------------------------------"




def generate_growth_rows(points, start_radius=3.0, spacing=2.0,
                         speed=1.0, time=10.0, boundary=None):
  
    import math
    import Rhino
    import Rhino.Geometry as rg

    r0, gap, v, t = map(float, (start_radius, spacing, speed, time))
    if any(math.isnan(x) or math.isinf(x) for x in (r0, gap, v, t)):
        raise ValueError("All numeric inputs must be finite.")
    if r0 <= 0 or gap <= 0 or v < 0 or t < 0:
        raise ValueError("Radius/spacing must be > 0; speed/time must be >= 0.")

    centres = [] if points is None else list(points)
    if not centres:
        return [], []
    if any(not isinstance(p, rg.Point3d) or not p.IsValid for p in centres):
        raise ValueError("Set points to List Access with the Point3d type hint.")

    base_plane = rg.Plane.WorldXY
    if boundary is not None:
        if not isinstance(boundary, rg.Curve) or not boundary.IsValid:
            raise ValueError("Connect the boundary with the Curve type hint.")
        if not boundary.IsClosed:
            raise ValueError("The boundary must be one closed curve.")
        doc = Rhino.RhinoDoc.ActiveDoc
        tol = doc.ModelAbsoluteTolerance if doc is not None else 0.001
        planar, base_plane = boundary.TryGetPlane(tol)
        if not planar:
            raise ValueError("The boundary must be planar, but can lie on any plane.")
        if any(abs(base_plane.DistanceTo(p)) > tol for p in centres):
            raise ValueError("Populate points must lie in the boundary's plane.")

    advance = v * t
    steps = advance / gap
    if math.isinf(steps) or math.isinf(r0 + advance):
        raise ValueError("Growth extent is too large.")
    row_count = int(math.floor(steps + 1e-9)) + 1
    if (row_count + 1) * len(centres) > 20000:
        raise ValueError("Too many circles: reduce time/speed or increase spacing.")

    row_groups = []
    fronts = []
    for centre in centres:
        row_plane = rg.Plane(base_plane)
        row_plane.Origin = centre
        group = []
        for k in range(row_count):
            radius = r0 + k * gap
            group.append(rg.Circle(row_plane, radius).ToNurbsCurve())
        row_groups.append(group)
        fronts.append(rg.Circle(row_plane, r0 + advance).ToNurbsCurve())

    return row_groups, fronts


def limit_growth_rows(points, row_groups, boundary, tolerance=None):

    import math
    import Rhino
    import Rhino.Geometry as rg

    if tolerance is None:
        doc = Rhino.RhinoDoc.ActiveDoc
        tolerance = doc.ModelAbsoluteTolerance if doc is not None else 0.001
    tol = float(tolerance)
    if math.isnan(tol) or math.isinf(tol) or tol <= 0:
        raise ValueError("Tolerance must be a positive finite number.")

    allowed = (rg.PointContainment.Inside, rg.PointContainment.Coincident)
    if not isinstance(boundary, rg.Curve) or not boundary.IsValid:
        raise ValueError("Connect your outer boundary with the Curve type hint.")
    if not boundary.IsClosed:
        raise ValueError("The boundary must be one closed curve.")
    planar, plane = boundary.TryGetPlane(tol)
    if not planar:
        raise ValueError("The boundary must be planar, but can lie on any plane.")

    def local_vector(point, origin):
        dx, dy, dz = point.X - origin.X, point.Y - origin.Y, point.Z - origin.Z
        x, y = plane.XAxis, plane.YAxis
        return (dx * x.X + dy * x.Y + dz * x.Z,
                dx * y.X + dy * y.Y + dz * y.Z)
    self_events = rg.Intersect.Intersection.CurveSelf(boundary, tol)
    if self_events is not None and self_events.Count > 0:
        raise ValueError("The boundary must not cross or overlap itself.")

    centres = [] if points is None else list(points)
    groups = [] if row_groups is None else list(row_groups)
    if len(groups) != len(centres):
        raise ValueError("Keep rows as a tree: one input branch per Populate point.")
    for i, centre in enumerate(centres):
        if not isinstance(centre, rg.Point3d) or not centre.IsValid:
            raise ValueError("Set points to List Access and the Point3d type hint.")
        if abs(plane.DistanceTo(centre)) > tol:
            raise ValueError("Populate points must lie in the boundary's plane.")
        if boundary.Contains(centre, plane, tol) not in allowed:
            raise ValueError("Populate point {0} is outside the boundary.".format(i))

    # Each neighbour defines a half-plane in the boundary's local coordinates:
    # dot(point - centre, unit_direction_to_neighbour) <= distance / 2.
    neighbours = []
    for i, centre in enumerate(centres):
        limits = []
        for j, other in enumerate(centres):
            if i == j:
                continue
            dx, dy = local_vector(other, centre)
            distance = math.hypot(dx, dy)
            if distance <= tol:
                raise ValueError("Populate points {0} and {1} coincide.".format(i, j))
            limits.append((dx / distance, dy / distance,
                           distance / 2.0, math.atan2(dy, dx)))
        neighbours.append(limits)

    tau = 2.0 * math.pi
    angle_eps = 1e-10
    result = []
    for i, centre in enumerate(centres):
        seed_rows = []
        for row_index, row in enumerate(groups[i]):
            if (not isinstance(row, rg.Curve) or not row.IsValid or
                    not row.IsClosed or not row.IsInPlane(plane, tol)):
                raise ValueError("Rows must lie in the boundary plane. Update Generate Growth Rows and connect the same boundary to it.")
            is_circle, fitted = row.TryGetCircle(tol)
            if not is_circle or fitted.Center.DistanceTo(centre) > tol:
                raise ValueError("Rows and points do not match. Use the same Populate output and order.")
            radius = fitted.Radius
            cuts = []

            # Actual boundary intersections; these support curved boundaries.
            events = rg.Intersect.Intersection.CurveCurve(row, boundary, tol, tol)
            if events is None:
                raise RuntimeError("Rhino could not evaluate a row/boundary intersection.")
            for event in events:
                hits = [event.PointA]
                if event.IsOverlap:
                    hits.append(event.PointA2)
                for hit in hits:
                    hx, hy = local_vector(hit, centre)
                    cuts.append(math.atan2(hy, hx) % tau)

            # Exact circle/bisector intersections, computed as angles.
            active = [n for n in neighbours[i] if n[2] <= radius + tol]
            for ux, uy, half_distance, direction in active:
                if half_distance <= radius:
                    delta = math.acos(min(1.0, half_distance / radius))
                    cuts.extend(((direction - delta) % tau,
                                 (direction + delta) % tau))

            angles = [0.0]
            for angle in sorted(cuts):
                if angle_eps < angle < tau - angle_eps:
                    if angle - angles[-1] > angle_eps:
                        angles.append(angle)
            angles.append(tau)

            # All crossings are now cuts: membership is constant between cuts.
            kept = []
            for a, b in zip(angles[:-1], angles[1:]):
                mid = (a + b) / 2.0
                lx, ly = radius * math.cos(mid), radius * math.sin(mid)
                x, y = plane.XAxis, plane.YAxis
                probe = rg.Point3d(centre.X + lx * x.X + ly * y.X,
                                   centre.Y + lx * x.Y + ly * y.Y,
                                   centre.Z + lx * x.Z + ly * y.Z)
                inside = boundary.Contains(probe, plane, tol) in allowed
                numeric_eps = 1e-12 * max(1.0, radius)
                owned = all(lx * ux + ly * uy <= half + numeric_eps
                            for ux, uy, half, direction in active)
                if inside and owned:
                    if kept and abs(kept[-1][1] - a) <= angle_eps:
                        kept[-1] = (kept[-1][0], b)
                    else:
                        kept.append((a, b))

            # Join continuity across the circle's 0/2*pi seam.
            if (len(kept) > 1 and kept[0][0] <= angle_eps and
                    kept[-1][1] >= tau - angle_eps):
                wrapped = (kept[-1][0], kept[0][1] + tau)
                kept = kept[1:-1] + [wrapped]

            pieces = []
            row_plane = rg.Plane(plane)
            row_plane.Origin = centre
            circle = rg.Circle(row_plane, radius)
            for a, b in kept:
                if (b - a) * radius <= tol:
                    continue
                if b - a >= tau - angle_eps:
                    pieces.append(row.DuplicateCurve())
                else:
                    arc = rg.Arc(circle, rg.Interval(a, b))
                    if not arc.IsValid:
                        raise RuntimeError("Rhino could not construct a clipped circular arc.")
                    piece = arc.ToNurbsCurve()
                    if piece is None or not piece.IsValid:
                        raise RuntimeError("Rhino could not convert a clipped arc to a curve.")
                    pieces.append(piece)
            seed_rows.append(pieces)
        result.append(seed_rows)

    return result


def create_tapered_tiles(points, row_curves, boundary, width=0.06, depth=0.08,
                         gap=0.01, rotation=0.0, tolerance=None,
                         sizes=None, seed=1):

    import math
    import random
    import Rhino
    import Rhino.Geometry as rg

    doc = Rhino.RhinoDoc.ActiveDoc
    tol = float(tolerance if tolerance is not None else
                (doc.ModelAbsoluteTolerance if doc is not None else 0.001))
    width, depth, gap, rotation = map(float, (width, depth, gap, rotation))
    if any(math.isnan(v) or math.isinf(v) for v in (tol, width, depth, gap, rotation)):
        raise ValueError("All numeric inputs must be finite.")
    if tol <= 0 or width <= tol or depth <= tol or gap < 0:
        raise ValueError("Width/depth must exceed model tolerance; gap must be >= 0.")
    if not isinstance(boundary, rg.Curve) or not boundary.IsValid or not boundary.IsClosed:
        raise ValueError("Connect the same closed Curve boundary as Limit Growth.")
    planar, plane = boundary.TryGetPlane(tol)
    if not planar:
        raise ValueError("The boundary must be planar.")
    crossings = rg.Intersect.Intersection.CurveSelf(boundary, tol)
    if crossings is not None and crossings.Count:
        raise ValueError("The boundary must not cross or overlap itself.")

    def uv(point):
        d = (point.X - plane.Origin.X, point.Y - plane.Origin.Y,
             point.Z - plane.Origin.Z)
        x, y = plane.XAxis, plane.YAxis
        return (d[0]*x.X + d[1]*x.Y + d[2]*x.Z,
                d[0]*y.X + d[1]*y.Y + d[2]*y.Z)

    centres = [] if points is None else list(points)
    allowed = (rg.PointContainment.Inside, rg.PointContainment.Coincident)
    for p in centres:
        if not isinstance(p, rg.Point3d) or not p.IsValid:
            raise ValueError("Set points to List Access, Point3d and Flatten.")
        if abs(plane.DistanceTo(p)) > tol or boundary.Contains(p, plane, tol) not in allowed:
            raise ValueError("Use the filtered Populate points inside the boundary, in its plane.")
    seed_uv = [uv(p) for p in centres]
    for i, (sx, sy) in enumerate(seed_uv):
        for qx, qy in seed_uv[:i]:
            if math.hypot(qx-sx, qy-sy) <= tol:
                raise ValueError("Populate points must be distinct.")

    seed_value = float(seed if seed is not None else 1)
    if math.isnan(seed_value) or math.isinf(seed_value) or seed_value != int(seed_value):
        raise ValueError("seed must be a whole number.")
    if sizes is None:
        factors = []
    else:
        try:
            factors = list(sizes)
        except TypeError:
            factors = [sizes]
    if not factors:
        rng = random.Random(int(seed_value))
        factors = [rng.uniform(0.65, 1.0) for _ in centres]
    elif len(factors) == 1:
        factors = factors * len(centres)
    if len(factors) != len(centres):
        raise ValueError("sizes needs one value per filtered point, one shared value, or no values for automatic sizes.")
    factors = list(map(float, factors))
    if any(math.isnan(v) or math.isinf(v) or v <= 0 or v > 1 for v in factors):
        raise ValueError("Each size must be greater than 0 and at most 1. Increase growth time for larger available radii.")

    tau = 2.0 * math.pi
    records = [[] for _ in centres]
    for curve in ([] if row_curves is None else row_curves):
        if (not isinstance(curve, rg.Curve) or not curve.IsValid or
                not curve.IsClosed or not curve.IsInPlane(plane, tol)):
            raise ValueError("Connect the ORIGINAL rows output from Generate Growth Rows (full circles), not clipped_rows.")
        ok, fitted = curve.TryGetCircle(tol)
        if not ok:
            raise ValueError("Use the original full-circle rows from Generate Growth Rows.")
        centre, radius = fitted.Center, fitted.Radius
        matches = [i for i, p in enumerate(centres) if p.DistanceTo(centre) <= tol]
        if len(matches) != 1:
            raise ValueError("A row does not match one centre. Use the SAME filtered Cull Pattern points as the growth components.")
        index = matches[0]
        record = next((r for r in records[index] if abs(r['radius']-radius) <= tol), None)
        if record is None:
            record = {'radius': radius}
            records[index].append(record)

    stats = {'centres': len(centres), 'candidates': 0, 'tiles': 0,
             'cut_tiles': 0, 'outside_limits': 0, 'too_close': 0,
             'small_rows': 0, 'tiny_pieces': 0, 'sizes': factors,
             'hidden_centres': [], 'radii': [], 'order': [],
             'fragment_rejections': 0}
    for seed_records in records:
        seed_records.sort(key=lambda record: record['radius'])
        for a, b in zip(seed_records[:-1], seed_records[1:]):
            if depth + gap > b['radius'] - a['radius'] + tol:
                raise ValueError("depth + gap exceeds row spacing. Reduce depth/gap or increase spacing in Generate Growth Rows.")

    patch_radii = [(rows[-1]['radius'] + depth/2.0) * factors[i] if rows else 0.0
                   for i, rows in enumerate(records)]
    for i, rows in enumerate(records):
        if rows and patch_radii[i] <= max(tol, rows[0]['radius']-depth/2.0) + tol:
            raise ValueError("Size for centre {0} is too small to reach its first tile row. Increase its size or growth time.".format(i))
    order = sorted((i for i, rows in enumerate(records) if rows),
                   key=lambda i: (-patch_radii[i], i))
    stats['radii'], stats['order'] = patch_radii, order

    def circle_at(index, radius):
        p = rg.Plane(plane)
        p.Origin = centres[index]
        return rg.Circle(p, radius).ToNurbsCurve()

    def clip_region(a, b, subtract=False):
        relation = rg.Curve.PlanarClosedCurveRelationship(a, b, plane, tol)
        if subtract:
            if relation == rg.RegionContainment.Disjoint:
                return [a]
            if relation == rg.RegionContainment.AInsideB:
                return []
            # Every subtractor is a disk at least as large as the original
            # patch. It cannot form a contained hole inside a patch fragment.
            if relation == rg.RegionContainment.BInsideA:
                raise RuntimeError("Unexpected circular containment. Check the model tolerance relative to the patch sizes.")
            result = rg.Curve.CreateBooleanDifference(a, b, tol)
        else:
            if relation == rg.RegionContainment.Disjoint:
                return []
            if relation == rg.RegionContainment.AInsideB:
                return [a]
            if relation == rg.RegionContainment.BInsideA:
                return [b.DuplicateCurve()]
            result = rg.Curve.CreateBooleanIntersection(a, b, tol)
        if result is None:
            raise RuntimeError("Rhino could not calculate a circular trim. Check the boundary and model tolerance.")
        result = list(result)
        if any(not curve.IsValid or not curve.IsClosed for curve in result):
            raise RuntimeError("Rhino returned an invalid circular trim.")
        return result

    # Reserve the WHOLE disk, including its centre opening and tile joints.
    # This prevents weaker tiles from showing through a dominant pattern.
    # Increasing the cutting radius by gap leaves a circular joint.
    patches = [circle_at(i, r) if r > 0 else None for i, r in enumerate(patch_radii)]
    cutters = [circle_at(i, r+gap) if r > 0 else None for i, r in enumerate(patch_radii)]
    regions = [[] for _ in centres]
    for rank, i in enumerate(order):
        parts = clip_region(patches[i], boundary)
        for j in order[:rank]:
            distance = math.hypot(seed_uv[i][0]-seed_uv[j][0], seed_uv[i][1]-seed_uv[j][1])
            if distance >= patch_radii[i]+patch_radii[j]+gap+tol:
                continue
            parts = [piece for part in parts for piece in clip_region(part, cutters[j], True)]
            if not parts:
                break
        regions[i] = parts
        if not parts:
            stats['hidden_centres'].append(i)

    # Use all angular positions, including those whose centreline is outside
    # a limit but whose finite footprint still extends inside it.
    # Alternate rows shift half a pitch to stagger joints.
    for i, seed_records in enumerate(records):
        for row_index, record in enumerate(seed_records):
            r = record['radius']
            inner = r - depth/2.0
            record['ids'] = []
            if not regions[i]:
                continue
            if inner <= tol or gap >= 2.0*inner:
                stats['small_rows'] += 1
                continue
            count = max(6, int(math.floor(tau*r/(width+gap) + 0.5)))
            if count > 100000:
                raise ValueError("Tile width is too small for these row radii.")
            pitch = tau/count
            gap_angle = 2.0*math.asin(min(1.0, gap/(2.0*inner)))
            half = (pitch-gap_angle)/2.0
            if half <= 0 or 2.0*inner*math.sin(half) <= tol:
                stats['small_rows'] += 1
                continue
            phase = (0.5 + 0.5*(row_index % 2))*pitch
            record.update({'ids': range(count), 'pitch': pitch,
                           'phase': phase, 'half': half})
            stats['candidates'] += count
            if stats['candidates'] > 100000:
                raise ValueError("More than 100,000 candidate tiles. Increase width or reduce the number of centres/rows.")

    def edges(poly):
        return list(zip(poly, poly[1:] + poly[:1]))

    def area(curve):
        properties = rg.AreaMassProperties.Compute(curve, tol)
        if properties is None:
            raise RuntimeError("Rhino could not measure a cut tile. Check boundary validity and model tolerance.")
        value = abs(properties.Area)
        properties.Dispose()
        return value

    def polygons_overlap(a, b):
        # Separating-axis test for convex polygons; edge contact is allowed.
        for p, q in edges(a) + edges(b):
            nx, ny = -(q[1]-p[1]), q[0]-p[0]
            length = math.hypot(nx, ny)
            if length <= 1e-15:
                continue
            nx, ny = nx/length, ny/length
            aa = [x*nx+y*ny for x, y in a]
            bb = [x*nx+y*ny for x, y in b]
            if min(max(aa), max(bb)) - max(min(aa), min(bb)) <= 1e-12:
                return False
        return True

    def point_segment_distance_sq(p, a, b):
        dx, dy = b[0]-a[0], b[1]-a[1]
        denom = dx*dx + dy*dy
        t = 0.0 if denom == 0 else max(0.0, min(1.0,
            ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/denom))
        return (p[0]-a[0]-t*dx)**2 + (p[1]-a[1]-t*dy)**2

    min_gap_sq = max(0.0, gap-tol)**2

    def too_close(a, b):
        if polygons_overlap(a, b):
            return True
        if min_gap_sq == 0:
            return False
        for p in a:
            for c, d in edges(b):
                if point_segment_distance_sq(p, c, d) < min_gap_sq:
                    return True
        for p in b:
            for c, d in edges(a):
                if point_segment_distance_sq(p, c, d) < min_gap_sq:
                    return True
        return False

    # Broad-phase spatial grid, followed by actual polygon overlap/distance.
    cell_size = max(width+gap, depth+gap, 10.0*tol)

    def cells(poly, padding=0.0):
        x0 = int(math.floor((min(p[0] for p in poly)-padding)/cell_size))
        x1 = int(math.floor((max(p[0] for p in poly)+padding)/cell_size))
        y0 = int(math.floor((min(p[1] for p in poly)-padding)/cell_size))
        y1 = int(math.floor((max(p[1] for p in poly)+padding)/cell_size))
        return [(x, y) for x in range(x0, x1+1) for y in range(y0, y1+1)]

    angle = math.radians(rotation % 360.0)
    ca, sa = math.cos(angle), math.sin(angle)
    output = []
    for seed_index, seed_records in enumerate(records):
        sx, sy = seed_uv[seed_index]
        # Other seeds are already separated by their circular region masks.
        # Use footprint collision tests only within this seed's own rows.
        grid, accepted = {}, []
        seed_output = []
        for record in seed_records:
            row_output = []
            r = record['radius']
            for k in record['ids']:
                theta = record['phase'] + k*record['pitch']
                h = record['half']
                inner, outer = r-depth/2.0, r+depth/2.0
                poly = [(sx+radius*math.cos(a), sy+radius*math.sin(a))
                        for radius, a in ((inner, theta-h), (outer, theta-h),
                                          (outer, theta+h), (inner, theta+h))]
                mx, my = sx+r*math.cos(theta), sy+r*math.sin(theta)
                if abs(angle) > 1e-12:
                    poly = [(mx+ca*(x-mx)-sa*(y-my), my+sa*(x-mx)+ca*(y-my))
                            for x, y in poly]

                world = [plane.PointAt(x, y) for x, y in poly]
                outline = rg.Polyline(world+[world[0]]).ToNurbsCurve()
                pieces = [piece for region in regions[seed_index]
                          for piece in clip_region(outline, region)]
                if not pieces:
                    stats['outside_limits'] += 1
                    continue
                cut = not (len(pieces) == 1 and pieces[0] is outline)

                nearby = set()
                for key in cells(poly, gap):
                    nearby.update(grid.get(key, []))
                if any(too_close(poly, accepted[index]) for index in sorted(nearby)):
                    stats['too_close'] += 1
                    continue

                kept = []
                measured = sorted(((area(piece), piece) for piece in pieces),
                                  key=lambda pair: -pair[0])
                for piece_area, piece in measured:
                    if not piece.IsValid or not piece.IsClosed:
                        raise RuntimeError("Rhino returned an invalid boundary cut.")
                    if piece_area <= tol*tol:
                        stats['tiny_pieces'] += 1
                        continue
                    fragment_too_close = False
                    if gap > tol:
                        for previous in kept:
                            success, pa, pb = piece.ClosestPoints(previous)
                            if not success:
                                raise RuntimeError("Rhino could not check the spacing between cut fragments.")
                            if pa.DistanceTo(pb) < gap-tol:
                                fragment_too_close = True
                                break
                    if fragment_too_close:
                        stats['fragment_rejections'] += 1
                        continue
                    surfaces = rg.Brep.CreatePlanarBreps(piece, tol)
                    if surfaces is None or len(surfaces) != 1 or not surfaces[0].IsValid:
                        raise RuntimeError("Rhino could not create a cut tile surface. Check boundary validity and model tolerance.")
                    row_output.append((piece, surfaces[0]))
                    stats['tiles'] += 1
                    if cut:
                        stats['cut_tiles'] += 1
                    kept.append(piece)
                if not kept:
                    continue
                index = len(accepted)
                accepted.append(poly)
                for key in cells(poly):
                    grid.setdefault(key, []).append(index)
            seed_output.append(row_output)
        output.append(seed_output)
    return output, stats
