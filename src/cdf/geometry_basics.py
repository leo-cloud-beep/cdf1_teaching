"""
Geometry basics -- reusable Rhino.Geometry functions for Grasshopper.

Adding a new function with Copilot
-----------------------------------
1. Open this file and select this chat model, then ask Copilot something like:
   "Add a function here, all in Rhino geometry, that builds a <your shape/idea>.
   Follow the same style as create_cone / create_fractal_tree (defaults for
   optional inputs, a docstring listing params, return a Rhino.Geometry object)."
2. Once the function is added, ask Copilot:
   "Give me the Python code to use this function in a Grasshopper GHPython 3
   component, importing it from computational_design_and_fabrication."
3. Copy the snippet Copilot gives you into a GHPython component, wire up the
   inputs as sliders/panels, and set the output variable (e.g. `a`).
"""

import math
import Rhino.Geometry as rg

def create_cone(base_point=None, height=10.0, radius=5.0, cap_bottom=True):
   
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    plane = rg.Plane(base_point, rg.Vector3d.ZAxis)
    cone = rg.Cone(plane, height, radius)
    return cone.ToBrep(cap_bottom)

def create_sphere(center_point=None, radius=5.0):
    
    if center_point is None:
        center_point = rg.Point3d(0, 0, 0)

    if radius <= 0:
        raise ValueError("Radius must be a positive value.")

    sphere = rg.Sphere(center_point, radius)
    return sphere.ToBrep()

def boolean_difference(brep_a, brep_b):

    if brep_a is None or brep_b is None:
        raise ValueError("Both brep_a and brep_b must be provided.")    

    """
    Perform a boolean difference operation between two Breps.

    brep_a : Rhino.Geometry.Brep -- the first Brep
    brep_b : Rhino.Geometry.Brep -- the second Brep to subtract from the first

    Returns a list of Rhino.Geometry.Brep resulting from the difference.
    """
    result = rg.Brep.CreateBooleanDifference(brep_a, brep_b, 0.001)
    return result


def copy_brep_along_z(brep, distance, copy_count):
    """
    Create copies of a Brep, each offset in the +Z direction.

    brep : Rhino.Geometry.Brep -- the Brep to copy
    distance : float -- the Z spacing between consecutive copies
    copy_count : int -- the number of copies to create

    Returns a list of Rhino.Geometry.Brep copies; copy i is moved by distance * (i + 1).
    """
    if brep is None:
        raise ValueError("brep must be provided.")
    if copy_count < 0:
        raise ValueError("copy_count must not be negative.")

    copies = []
    for i in range(1, int(copy_count) + 1):
        copy = brep.DuplicateBrep()
        copy.Transform(rg.Transform.Translation(rg.Vector3d(0, 0, distance * i)))
        copies.append(copy)
    return copies




#-----------------------------------------------------------------------

def create_box(base_point=None, width=10.0, depth=10.0, height=10.0):
 
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    if width <= 0 or depth <= 0 or height <= 0:
        raise ValueError("Width, depth, and height must be positive values.")

    corner1 = base_point
    corner2 = rg.Point3d(base_point.X + width, base_point.Y + depth, base_point.Z + height)
    box = rg.Box(rg.BoundingBox(corner1, corner2))
    return box.ToBrep()

def create_cylinder(base_point=None, height=10.0, radius=5.0, axis=None, cap_bottom=True):
    
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    if radius <= 0 or height <= 0:
        raise ValueError("Radius and height must be positive values.")

    if axis is None:
        axis = rg.Vector3d.YAxis

    plane = rg.Plane(base_point, axis)
    base_circle = rg.Circle(plane, radius)
    cylinder = rg.Cylinder(base_circle, height)
    return cylinder.ToBrep(cap_bottom, True)

def boolean_difference1(brep_a, brep_b):

    if brep_a is None or brep_b is None:
        raise ValueError("Both brep_a and brep_b must be provided.")

    result = rg.Brep.CreateBooleanDifference(brep_a, brep_b, 0.001)
    return result

def create_half_cylinder(base_point=None, height=10.0, radius=5.0, axis=None):
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    if axis is None:
        axis = rg.Vector3d.YAxis

    if height <= 0 or radius <= 0:
        raise ValueError("Height and radius must be positive.")

    plane = rg.Plane(
    base_point,
    rg.Vector3d.XAxis,  # flache Kante liegt waagerecht am Boden
    rg.Vector3d.ZAxis   # Halbkreis wölbt sich nach oben
    )
    circle = rg.Circle(plane, radius)

    # Half-circle arc, plus the straight diameter, makes a closed profile
    arc = rg.Arc(circle, rg.Interval(0.0, math.pi))
    arc_curve = arc.ToNurbsCurve()
    diameter = rg.LineCurve(arc.EndPoint, arc.StartPoint)

    profile_parts = rg.Curve.JoinCurves([arc_curve, diameter], 0.001)
    if not profile_parts:
        raise ValueError("Could not join the half-circle profile.")

    extrusion = rg.Extrusion.Create(profile_parts[0], height, True)
    if extrusion is None:
        raise ValueError("Could not create the half-cylinder.")

    return extrusion.ToBrep(False)


#Kreissegment mit einstellbaren Winkeln und Radius, das entlang der Z-Achse extrudiert wird

def create_segment_cylinder(center_point=None, height=10.0, radius=5.0,
                            start_angle_degrees=0.0,
                            end_angle_degrees=180.0):

    if center_point is None:
        center_point = rg.Point3d(0, 0, 0)

    if height <= 0 or radius <= 0:
        raise ValueError("Height and radius must be positive.")

    if not -360 <= start_angle_degrees < end_angle_degrees <= 360:
        raise ValueError("Angles must satisfy -360 <= start < end <= 360.")

    # Kreis liegt in der X-Z-Ebene; die Extrusion geht in -Y
    plane = rg.Plane(
        center_point,
        rg.Vector3d.XAxis,
        rg.Vector3d.ZAxis
    )
    circle = rg.Circle(plane, radius)

    start_angle = math.radians(start_angle_degrees)
    end_angle = math.radians(end_angle_degrees)

    arc = rg.Arc(
        circle,
        rg.Interval(start_angle, end_angle)
    )
    arc_curve = arc.ToNurbsCurve()

    # Die beiden geraden Kanten laufen vom Kreisbogen zum Mittelpunkt.
    edge_1 = rg.LineCurve(arc.EndPoint, center_point)
    edge_2 = rg.LineCurve(center_point, arc.StartPoint)

    profiles = rg.Curve.JoinCurves(
        [arc_curve, edge_1, edge_2],
        0.001
    )

    if not profiles:
        raise ValueError("Could not create the sector profile.")

    extrusion = rg.Extrusion.Create(profiles[0], height, True)

    if extrusion is None:
        raise ValueError("Could not create the extrusion.")

    return extrusion.ToBrep(False)

#moves the geometry by input (dont know if I should becaouse there is already a componant for that in there)
import Rhino.Geometry as rg

def move_geometry(geometry, x, y, z):
    if geometry is None:
        raise ValueError("geometry muss angegeben werden.")

    vector = rg.Vector3d(float(x), float(y), float(z))

    # Einen Punkt direkt um den Vektor verschieben
    if isinstance(geometry, rg.Point3d):
        return geometry + vector

    # Andere Geometrien kopieren und verschieben
    moved_geometry = geometry.Duplicate()
    moved_geometry.Transform(rg.Transform.Translation(vector))
    return moved_geometry

def scale_geometry(geometry, scale_factor=None, origin_point=None):

    if geometry is None:
        raise ValueError("geometry must be provided.")

    if scale_factor is None:
        raise ValueError("scale_factor must be provided.")
  
    if origin_point is None:
        origin_point = rg.Point3d(0, 0, 0)

    scaled_geometry = geometry.Duplicate()
    scaled_geometry.Transform(rg.Transform.Scale(origin_point, scale_factor))
    return scaled_geometry

import random

import random

def assign_colors(geometries, palette, seed=None):
    geometries = geometries or []
    palette = palette or []

    if not geometries:
        return []

    if not palette:
        raise ValueError("Die Farbpalette darf nicht leer sein.")

    if len(geometries) < len(palette):
        raise ValueError(
            "Es gibt weniger Geometrien ({}) als Farben ({}). "
            "Damit jede Farbe vorkommt, braucht es mindestens so viele Geometrien wie Farben."
            .format(len(geometries or []), len(palette or []))
        )

    rng = random.Random(seed)

    # Zuerst jede Farbe mindestens einmal verwenden
    colors = list(palette)

    # Übrige Geometrien zufällig einfärben
    while len(colors) < len(geometries):
        colors.append(rng.choice(palette))

    # Reihenfolge zufällig mischen
    rng.shuffle(colors)

    return colors

def extrude_brep_from_plane(brep, plane, distance):
    if brep is None or plane is None:
        raise ValueError("Brep und Plane müssen vorhanden sein.")

    if distance == 0:
        raise ValueError("Distance darf nicht 0 sein.")

    # Eingabe in ein Brep umwandeln
    if isinstance(brep, rg.BrepFace):
        face_brep = brep.DuplicateFace(False)
    elif isinstance(brep, rg.Surface):
        face_brep = rg.Brep.CreateFromSurface(brep)
    elif isinstance(brep, rg.Brep):
        face_brep = brep
    else:
        raise TypeError("Am Eingang muss eine Fläche oder ein Brep anliegen.")

    # Geschlossene Außenkante der Fläche als Extrusionsprofil verwenden
    face = face_brep.Faces[0]
    profile = face.OuterLoop.To3dCurve()

    if profile is None or not profile.IsClosed:
        raise ValueError("Die Fläche hat keine geschlossene Außenkante.")

    # Geschlossene Extrusion erzeugen
    extrusion = rg.Extrusion.Create(profile, plane, distance, True)

    if extrusion is None:
        raise ValueError("Extrusion konnte nicht erstellt werden.")

    result = extrusion.ToBrep()

    return result

import Rhino
import Rhino.Geometry as rg


def create_stair_cut(body, N):
    # Eingaben prüfen
    if body is None:
        raise ValueError("Am Eingang body liegt keine Geometrie an.")

    if not body.IsSolid:
        raise ValueError("body muss ein geschlossener Brep-Körper sein.")

    N = int(N)

    if N < 1:
        raise ValueError("N muss mindestens 1 sein.")

    # Maße und Lage des Körpers bestimmen
    bbox = body.GetBoundingBox(True)

    body_width = bbox.Max.Y - bbox.Min.Y  # Treppenlauf: Y-Richtung
    body_depth = bbox.Max.X - bbox.Min.X  # Extrusion: X-Richtung
    body_height = bbox.Max.Z - bbox.Min.Z

    if body_width <= 0 or body_depth <= 0 or body_height <= 0:
        raise ValueError("Der Körper hat in X, Y oder Z keine Ausdehnung.")

    # Auftritt und Steigung aus Körpermaßen und Stufenzahl berechnen
    tread = body_width / N
    rise = body_height / N

    # Kleine Überstände helfen bei der Boolean Difference
    tol = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
    eps = tol * 2

    x_min = bbox.Min.X
    x_max = bbox.Max.X
    y_min = bbox.Min.Y
    y_max = bbox.Max.Y
    z_min = bbox.Min.Z
    z_max = bbox.Max.Z

    # Profil liegt knapp vor dem Körper und steigt links unten nach rechts oben
    profile_x = bbox.Min.X - eps
    points = []

    points.append(rg.Point3d(profile_x, y_min - eps, z_min - eps))
    points.append(rg.Point3d(profile_x, y_min - eps, z_min + rise))

    for i in range(N):
        next_y = y_min + (i + 1) * tread
        next_z = z_min + (i + 1) * rise

        # Waagerechter Auftritt
        points.append(rg.Point3d(profile_x, next_y, next_z))

        # Senkrechte Setzstufe
        if i < N - 1:
            higher_z = z_min + (i + 2) * rise
            points.append(rg.Point3d(profile_x, next_y, higher_z))

    points.append(rg.Point3d(profile_x, y_max + eps, z_max))
    points.append(rg.Point3d(profile_x, y_max + eps, z_min - eps))
    points.append(points[0])

    profile = rg.Polyline(points).ToNurbsCurve()

    # Extrusionsebene so ausrichten, dass der Körper in Y-Richtung entsteht
    extrusion_plane = rg.Plane(
        rg.Point3d(profile_x, 0, 0),
        rg.Vector3d.YAxis,
        rg.Vector3d.ZAxis
    )

    extrusion_depth = body_depth + 2 * eps
    # Schneidkörper über die gesamte Tiefe des Körpers extrudieren
    extrusion_depth = body_depth + 2 * eps

    extrusion = rg.Extrusion.Create(
        profile,
        extrusion_plane,
        extrusion_depth,
        True
    )

    if extrusion is None:
        raise ValueError("Der Stufenkörper konnte nicht erzeugt werden.")

    cutter = extrusion.ToBrep()

    if cutter is None or not cutter.IsSolid:
        raise ValueError("Der Stufenkörper ist nicht geschlossen.")

    # Schneidkörper vom ursprünglichen Körper abziehen
    cut_body = rg.Brep.CreateBooleanDifference(body, cutter, tol)

    if cut_body is None or len(cut_body) == 0:
        raise ValueError("Boolean Difference ist fehlgeschlagen.")

    return cutter, cut_body, tread, rise

'--------------------------------------------------------------------------------'

import Rhino.Geometry as rg

def create_curve(t_values, y_values, z_values):
    t_values = list(t_values)
    y_values = list(y_values)
    z_values = list(z_values)

    if not (len(t_values) == len(y_values) == len(z_values)):
        raise ValueError("t, y und z müssen gleich viele Werte enthalten.")

    if len(t_values) < 2:
        raise ValueError("Es werden mindestens zwei Werte benötigt.")

    points = []

    for t, y, z in zip(t_values, y_values, z_values):
        point = rg.Point3d(
            float(t),  # x
            float(y),  # y aus Graph Mapper 1
            float(z)   # z aus Graph Mapper 2
        )
        points.append(point)

    degree = min(3, len(points) - 1)

    return rg.Curve.CreateInterpolatedCurve(points, degree)

import math
import random
import Rhino.Geometry as rg


def populate(curve, count, cube_size, radius, falloff=4.0, seed=1):
    """Ermittelt Würfelmittelpunkte um die Kurve.
    Nahe an der Kurve liegende Positionen werden bevorzugt.
    """

    cube_size = float(cube_size)
    radius = float(radius)
    count = int(count)

    if curve is None:
        raise ValueError("Es wurde keine Kurve übergeben.")
    if cube_size <= 0 or radius <= 0 or count < 1:
        raise ValueError("Würfelgröße, Radius und Anzahl müssen positiv sein.")

    bounds = curve.GetBoundingBox(True)

    ix0 = int(math.floor((bounds.Min.X - radius) / cube_size))
    ix1 = int(math.ceil((bounds.Max.X + radius) / cube_size))
    iy0 = int(math.floor((bounds.Min.Y - radius) / cube_size))
    iy1 = int(math.ceil((bounds.Max.Y + radius) / cube_size))
    iz0 = int(math.floor((bounds.Min.Z - radius) / cube_size))
    iz1 = int(math.ceil((bounds.Max.Z + radius) / cube_size))

    rng = random.Random(seed)
    candidates = []

    for ix in range(ix0, ix1):
        for iy in range(iy0, iy1):
            for iz in range(iz0, iz1):
                center = rg.Point3d(
                    (ix + 0.5) * cube_size,
                    (iy + 0.5) * cube_size,
                    (iz + 0.5) * cube_size
                )

                success, parameter = curve.ClosestPoint(center)
                if not success:
                    continue

                nearest_point = curve.PointAt(parameter)
                distance = center.DistanceTo(nearest_point)

                if distance <= radius:
                    weight = math.exp(
                        -falloff * (distance / radius) ** 2
                    )
                    random_value = max(rng.random(), 1e-12)
                    rank = -math.log(random_value) / weight
                    candidates.append((rank, center))

    if len(candidates) < count:
        raise ValueError(
            "Es gibt nicht genug mögliche Positionen. "
            "Vergrößere den Radius oder verkleinere die Würfel."
        )

    candidates.sort(key=lambda item: item[0])
    return [center for rank, center in candidates[:count]]


import math
import random
import Rhino.Geometry as rg


def populate(curve, count, x_size, y_size, z_size, radius,
             falloff=4.0, seed=1):
    """Berechnet Mittelpunkte für Quader nahe der Kurve."""

    x_size = float(x_size)
    y_size = float(y_size)
    z_size = float(z_size)
    radius = float(radius)
    count = int(count)

    if curve is None:
        raise ValueError("Es wurde keine Kurve übergeben.")
    if min(x_size, y_size, z_size, radius) <= 0 or count < 1:
        raise ValueError("Maße, Radius und Anzahl müssen positiv sein.")

    bounds = curve.GetBoundingBox(True)

    ix0 = int(math.floor((bounds.Min.X - radius) / x_size))
    ix1 = int(math.ceil((bounds.Max.X + radius) / x_size))
    iy0 = int(math.floor((bounds.Min.Y - radius) / y_size))
    iy1 = int(math.ceil((bounds.Max.Y + radius) / y_size))
    iz0 = int(math.floor((bounds.Min.Z - radius) / z_size))
    iz1 = int(math.ceil((bounds.Max.Z + radius) / z_size))

    rng = random.Random(seed)
    candidates = []

    for ix in range(ix0, ix1):
        for iy in range(iy0, iy1):
            for iz in range(iz0, iz1):
                center = rg.Point3d(
                    (ix + 0.5) * x_size,
                    (iy + 0.5) * y_size,
                    (iz + 0.5) * z_size
                )

                success, parameter = curve.ClosestPoint(center)
                if not success:
                    continue

                nearest_point = curve.PointAt(parameter)
                distance = center.DistanceTo(nearest_point)

                if distance <= radius:
                    weight = math.exp(
                        -falloff * (distance / radius) ** 2
                    )
                    random_value = max(rng.random(), 1e-12)
                    rank = -math.log(random_value) / weight
                    candidates.append((rank, center))

    if len(candidates) < count:
        raise ValueError(
            "Es gibt nicht genug Positionen. "
            "Vergrößere den Radius oder verkleinere die Quader."
        )

    candidates.sort(key=lambda item: item[0])
    return [center for rank, center in candidates[:count]]


def create_cubes(centers, x_size, y_size, z_size):
    """Erzeugt Quader mit unabhängig einstellbaren X-, Y- und Z-Maßen."""

    x_size = float(x_size)
    y_size = float(y_size)
    z_size = float(z_size)

    if min(x_size, y_size, z_size) <= 0:
        raise ValueError("Alle drei Maße müssen größer als 0 sein.")

    cubes = []

    for center in centers:
        box = rg.Box(
            rg.Plane.WorldXY,
            rg.Interval(center.X - x_size / 2.0, center.X + x_size / 2.0),
            rg.Interval(center.Y - y_size / 2.0, center.Y + y_size / 2.0),
            rg.Interval(center.Z - z_size / 2.0, center.Z + z_size / 2.0)
        )
        cubes.append(box.ToBrep())

    return cubes