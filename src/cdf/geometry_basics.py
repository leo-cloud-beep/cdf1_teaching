
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


def boolean_union(breps):
    """Perform a boolean union operation on multiple Breps.

    breps : iterable of Rhino.Geometry.Brep -- the Breps to join

    Returns a list of Rhino.Geometry.Brep objects resulting from the union.
    """
    if breps is None:
        raise ValueError("breps must contain at least two Breps.")

    try:
        breps = list(breps)
    except TypeError:
        raise TypeError("breps must be an iterable of Rhino.Geometry.Brep objects.")

    if len(breps) < 2:
        raise ValueError("At least two Breps are required for a boolean union.")
    if any(brep is None for brep in breps):
        raise ValueError("breps must not contain None.")

    return rg.Brep.CreateBooleanUnion(breps, 0.001)


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

def create_pyramid(point=None, number_of_corners=4, height=10.0, radius=5.0,
                   plane=None):
    """Create a closed pyramid with a regular polygon base.

    point : Rhino.Geometry.Point3d -- center of the base
    number_of_corners : int -- number of sides in the base polygon
    height : float -- distance from the base to the apex
    radius : float -- distance from the base center to each corner
    plane : Rhino.Geometry.Plane -- base orientation; the pyramid extends
            along its normal

    Returns a closed Rhino.Geometry.Brep.
    """
    if point is None:
        point = rg.Point3d(0, 0, 0)
    if plane is None:
        plane = rg.Plane.WorldXY

    number_of_corners = int(number_of_corners)
    if number_of_corners < 3:
        raise ValueError("number_of_corners must be at least 3.")
    if height <= 0 or radius <= 0:
        raise ValueError("Height and radius must be positive.")
    if not plane.IsValid:
        raise ValueError("plane must be a valid Rhino.Geometry.Plane.")

    base_points = []
    for i in range(number_of_corners):
        angle = 2.0 * math.pi * i / number_of_corners
        base_points.append(
            point
            + plane.Plane.XAxis * (radius * math.cos(angle))
            + plane.Plane.YAxis * (radius * math.sin(angle))
        )

    base_outline = rg.Polyline(base_points + [base_points[0]]).ToNurbsCurve()
    tolerance = 0.001
    base_faces = rg.Brep.CreatePlanarBreps(base_outline, tolerance)
    if not base_faces:
        raise ValueError("Could not create the pyramid base.")

    apex = point + plane.Plane.Normal * height
    faces = [base_faces[0]]
    for i in range(number_of_corners):
        next_i = (i + 1) % number_of_corners
        side_face = rg.Brep.CreateFromCornerPoints(
            base_points[i], base_points[next_i], apex, tolerance
        )
        if side_face is None:
            raise ValueError("Could not create a pyramid side.")
        faces.append(side_face)

    pyramid = rg.Brep.JoinBreps(faces, tolerance)
    if pyramid is None or len(pyramid) != 1 or not pyramid[0].IsSolid:
        raise ValueError("Could not join the pyramid into a closed Brep.")

    return pyramid[0]

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


def attach_module(module, ports, target_port, source_port_index=0):
    """
    Attach one copy of `module` to an existing `target_port`.

    module: geometry of the module
    ports: list of the module's outward-facing port planes
    target_port: port plane on the existing assembly
    source_port_index: which port on the new copy to connect
    """

    if module is None:
        raise ValueError("Module geometry is missing.")

    ports = list(ports)

    if not ports:
        raise ValueError("No port planes were provided.")

    if source_port_index < 0 or source_port_index >= len(ports):
        raise IndexError("source_port_index is outside the ports list.")

    source_port = ports[source_port_index]

    # Reverse the target plane so the two connected port normals oppose each other.
    target_flipped = rg.Plane(
        target_port.Origin,
        target_port.XAxis,
        -target_port.YAxis
    )

    # Move the chosen source port onto the reversed target port.
    transform = rg.Transform.PlaneToPlane(source_port, target_flipped)

    attached_geometry = module.Duplicate()
    if not attached_geometry.Transform(transform):
        raise RuntimeError("Could not transform the module geometry.")

    # Return the new positions of all ports, for later growth.
    attached_ports = []
    for port in ports:
        moved_port = rg.Plane(port.Origin, port.XAxis, port.YAxis)
        moved_port.Transform(transform)
        attached_ports.append(moved_port)

    return attached_geometry, attached_ports

import random
import Rhino.Geometry as rg


def grow_modules(module, ports, count=10, seed=1):
    ports = list(ports)

    if module is None:
        raise ValueError("Module geometry is missing.")
    if not ports:
        raise ValueError("No port planes were provided.")

    count = max(1, int(count))
    tolerance = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
    rng = random.Random(seed)

    shapes = [module.Duplicate()]
    open_ports = [(plane, 0, i) for i, plane in enumerate(ports)]

    for _ in range(count - 1):
        placed = False

        # Try different open ports and module ports until one fits.
        options = [
            (target_i, source_i)
            for target_i in range(len(open_ports))
            for source_i in range(len(ports))
        ]
        rng.shuffle(options)

        for target_i, source_i in options:
            target_plane = open_ports[target_i][0]
            new_shape, new_ports = attach_module(
                module, ports, target_plane, source_i
            )

            collides = any(
                _has_volume_overlap(new_shape, existing, tolerance)
                for existing in shapes
            )

            if not collides:
                del open_ports[target_i]
                shapes.append(new_shape)

                for i, plane in enumerate(new_ports):
                    if i != source_i:
                        open_ports.append((plane, len(shapes) - 1, i))

                placed = True
                break

        # Stop if no port pairing can place another copy without overlap.
        if not placed:
            break

    free_ports = [item[0] for item in open_ports]
    return shapes, free_ports

#picks colurs dependant on their placement in time 
def generation_values(shapes):
    shapes = list(shapes)
    total = len(shapes)

    if total == 0:
        return []
    if total == 1:
        return [0.0]

    return [i / float(total - 1) for i in range(total)]

from System.Drawing import Color

def color_by_generation(shapes):
    shapes = list(shapes)
    total = len(shapes)

    if total == 0:
        return []
    if total == 1:
        return [0.0]

    return [i / float(total - 1) for i in range(total)]

GROW_ALONG_VERSION = "curve-guide-2026-11-08"


def _bbox_has_interior_overlap(a, b, tolerance):
    """A contact within the document's length tolerance is not penetration."""
    return all(
        min(getattr(a.Max, axis), getattr(b.Max, axis))
        - max(getattr(a.Min, axis), getattr(b.Min, axis)) > tolerance
        for axis in ("X", "Y", "Z")
    )


def _volume_overlap_state(a, b, tolerance, box_a=None, box_b=None):
    """Return 'clear', 'overlap', or 'unknown'; never accept a failed Boolean."""
    if not isinstance(a, rg.Brep) or not isinstance(b, rg.Brep):
        raise TypeError("Collision checking needs Brep geometry.")
    if not a.IsSolid or not b.IsSolid:
        raise ValueError("Collision checking needs closed solids. Cap the module first.")
    box_a = box_a if box_a is not None else a.GetBoundingBox(True)
    box_b = box_b if box_b is not None else b.GetBoundingBox(True)
    if not _bbox_has_interior_overlap(box_a, box_b, tolerance):
        return "clear"
    try:
        intersection = rg.Brep.CreateBooleanIntersection(a, b, tolerance)
    except Exception:
        return "unknown"
    if intersection is None:
        return "unknown"
    state = "clear"
    try:
        for part in intersection:
            if part is None or not part.IsValid or not part.IsSolid:
                if state != "overlap":
                    state = "unknown"
                continue
            try:
                mass = rg.VolumeMassProperties.Compute(part)
            except Exception:
                mass = None
            if mass is None:
                if state != "overlap":
                    state = "unknown"
                continue
            try:
                if abs(mass.Volume) > tolerance ** 3:
                    state = "overlap"
            finally:
                mass.Dispose()
    finally:
        for part in intersection:
            if part is not None:
                part.Dispose()
    return state


def _has_volume_overlap(a, b, tolerance):
    # Keep the existing helper's public behaviour: True rejects the placement.
    return _volume_overlap_state(a, b, tolerance) != "clear"


def _cg_point(point, transform):
    result = rg.Point3d(point)
    result.Transform(transform)
    return result


def _cg_plane(plane, transform=None):
    result = rg.Plane(plane.Origin, plane.XAxis, plane.YAxis)
    if transform is not None and not result.Transform(transform):
        raise RuntimeError("Could not transform a port plane.")
    return result


def _cg_front(mask, station_count):
    """Index of the first uncovered station, or station_count if complete."""
    missing = ((1 << station_count) - 1) ^ mask
    return station_count if not missing else (missing & -missing).bit_length() - 1


def _cg_bit_count(mask):
    # Rhino 8 Python 3.9 does not have int.bit_count().
    return bin(mask).count("1")


class _CGPart:
    def __init__(self, uid, geometry, ports, center):
        self.uid = uid
        self.geometry = geometry
        self.ports = ports
        self.center = center
        self.box = geometry.GetBoundingBox(True)


class _CGPose:
    def __init__(self, parent, target, source, transform, center, mask, tie,
                 future, curve_distance):
        self.parent = parent
        self.target = target
        self.source = source
        self.transform = transform
        self.center = center
        self.mask = mask
        self.tie = tie
        self.future = future
        self.curve_distance = curve_distance
        self.part = None
        self.blocked = False


class _CurveGrower:
    """Curve-guided port search with no distance boundary, then free aggregation."""

    def __init__(self, module, ports, curve, count, seed, tolerance,
                 rotation_steps, lookahead, beam_width,
                 start_at_curve, max_attempts):
        if not isinstance(module, rg.Brep):
            raise TypeError("G: connect ONE Brep; set Type Hint = Brep, Item Access.")
        if not module.IsValid or not module.IsSolid:
            raise ValueError("G must be one valid CLOSED solid Brep (Cap / Solid Union).")
        if not isinstance(curve, rg.Curve) or not curve.IsValid:
            raise TypeError("C: connect a curve; set Type Hint = Curve, Item Access.")
        if ports is None:
            raise ValueError("P is missing. Connect the module's port planes.")
        try:
            ports = list(ports)
        except TypeError:
            raise TypeError("P needs List Access, Type Hint = Plane, and Flatten.")
        if len(ports) < 2:
            raise ValueError("P needs at least two port planes for continuing growth.")
        if any(not isinstance(p, rg.Plane) or not p.IsValid for p in ports):
            raise TypeError("P must contain planes, not vectors, points or Panel text.")

        self.count = int(count)
        self.tol = float(tolerance)
        if self.count < 1:
            raise ValueError("count must be >= 1.")
        if not math.isfinite(self.tol) or self.tol <= 0:
            raise ValueError("collision_tolerance must be a positive length.")
        self.rotation_steps = int(rotation_steps)
        self.lookahead = int(lookahead)
        self.beam_width = int(beam_width)
        self.max_attempts = int(max_attempts)
        if not 1 <= self.rotation_steps <= 72:
            raise ValueError("rotation_steps must be between 1 and 72.")
        if not 1 <= self.lookahead <= 6 or not 1 <= self.beam_width <= 12:
            raise ValueError("lookahead: 1..6; beam_width: 1..12.")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive.")

        self.rng = random.Random(int(seed))
        self.module = module.DuplicateBrep()
        if self.module.SolidOrientation == rg.BrepSolidOrientation.Inward:
            self.module.Flip()
        mass = rg.VolumeMassProperties.Compute(self.module)
        if mass is None:
            raise ValueError("G: could not calculate the solid's volume and centroid.")
        try:
            self.reference = rg.Point3d(mass.Centroid)
        finally:
            mass.Dispose()

        # Check each connector against the actual solid. A supporting port plane
        # has the ENTIRE solid on one side. This lets us prove that a correctly
        # attached parent and child only touch, without a coplanar Boolean.
        self.ports, self.supported = [], []
        self.flipped_ports = 0
        for i, original in enumerate(ports):
            port = _cg_plane(original)
            closest = self.module.ClosestPoint(port.Origin)
            if not closest.IsValid or closest.DistanceTo(port.Origin) > 5.0 * self.tol:
                raise ValueError(
                    "P[{0}] is not on the module surface. Use the centre of the "
                    "OUTER end face, in the same coordinates as G.".format(i)
                )
            local = self.module.DuplicateBrep()
            try:
                local.Transform(rg.Transform.PlaneToPlane(port, rg.Plane.WorldXY))
                box = local.GetBoundingBox(True)
            finally:
                local.Dispose()
            support_epsilon = self.tol * 0.001
            negative = box.Max.Z <= support_epsilon and box.Min.Z < -self.tol
            positive = box.Min.Z >= -support_epsilon and box.Max.Z > self.tol
            if positive:
                port = rg.Plane(port.Origin, port.XAxis, -port.YAxis)
                self.flipped_ports += 1
            self.ports.append(port)
            self.supported.append(negative or positive)

        radii = sorted(self.reference.DistanceTo(p.Origin) for p in self.ports)
        self.step = 2.0 * radii[len(radii) // 2]
        if self.step <= 10 * self.tol:
            raise ValueError("Port origins are too close to the module centroid.")
        # A cheap direction hint breaks ties between twists with the same
        # centre. Real lookahead below still validates actual attachments.
        self.exit_hints = [rg.Point3d(
            p.Origin.X + p.ZAxis.X * self.step * 0.5,
            p.Origin.Y + p.ZAxis.Y * self.step * 0.5,
            p.Origin.Z + p.ZAxis.Z * self.step * 0.5
        ) for p in self.ports]
        # Used ONLY to decide which curve samples have been reached. This is
        # derived from the module, and is NOT an admissible-distance boundary:
        # candidates farther away remain available for multi-step detours.
        self.cover_distance = 0.75 * self.step

        self.curve = curve.DuplicateCurve()
        if not self.curve.IsClosed:
            if (self.reference.DistanceTo(curve.PointAtEnd)
                    < self.reference.DistanceTo(curve.PointAtStart)):
                self.curve.Reverse()
        length = self.curve.GetLength()
        if length <= self.tol:
            raise ValueError("C has zero length or is too short.")
        divisions = max(2, int(math.ceil(length / (self.cover_distance * 0.4))))
        if divisions > 2000:
            raise ValueError(
                "C is very long relative to G. Check the units/scale of the curve and module."
            )
        self.stations = [self.curve.PointAtNormalizedLength(i / float(divisions))
                         for i in range(divisions + 1)]
        if any(not p.IsValid for p in self.stations):
            raise ValueError("Could not sample C by arc length.")
        self.full_mask = (1 << len(self.stations)) - 1
        self.stats = dict(poses=0, projection_failed=0, checked=0, overlap=0,
                          boolean_failed=0, parent_contact=0)
        self.cache = {}
        self.next_uid = 0
        self.parts, self.open_ports = [], []
        self.mask = 0
        self.reason = None

        seed_transform = rg.Transform.Identity
        if start_at_curve:
            tangent = rg.Vector3d(self.curve.TangentAtStart)
            if not tangent.Unitize():
                raise ValueError("C has no valid tangent at its start.")
            # Rotate the complete module and all planes together. Subsequent
            # attachments NEVER substitute a curve-tangent plane for a real port.
            # Align a route THROUGH two ports, not one arm with the tangent.
            # A tetrahedral module has no straight-through pair: aligning one
            # arm exactly with the curve forces the following step far sideways.
            # The port-to-port direction shares this zigzag between both sides.
            entry, exit_port = max(
                ((a, b) for a in self.ports for b in self.ports if a is not b),
                key=lambda pair: pair[0].Origin.DistanceTo(pair[1].Origin)
            )
            forward = exit_port.Origin - entry.Origin
            if forward * tangent < 0:
                forward = -forward
            if not forward.Unitize():
                raise ValueError("P needs distinct connector origins.")
            turn = rg.Transform.Rotation(forward, tangent, self.reference)
            move = rg.Transform.Translation(self.curve.PointAtStart - self.reference)
            seed_transform = move * turn
        seed_part = self._make_part(seed_transform)
        distance = self._distance(seed_part.center)
        if distance is None:
            raise ValueError("Could not evaluate the guide curve near the start module.")
        self.parts.append(seed_part)
        self.open_ports = [(seed_part, i) for i in range(len(self.ports))]
        self.mask = self._coverage(seed_part.center)
        self.guided_count = 1

    def _make_part(self, transform):
        geometry = self.module.DuplicateBrep()
        if not geometry.Transform(transform):
            geometry.Dispose()
            raise RuntimeError("Could not transform the module Brep.")
        ports = [_cg_plane(p, transform) for p in self.ports]
        result = _CGPart(self.next_uid, geometry, ports,
                         _cg_point(self.reference, transform))
        self.next_uid += 1
        return result

    def _distance(self, point):
        success, parameter = self.curve.ClosestPoint(point)
        if not success:
            return None
        return point.DistanceTo(self.curve.PointAt(parameter))

    def _coverage(self, center):
        mask = 0
        for i, station in enumerate(self.stations):
            if center.DistanceTo(station) <= self.cover_distance:
                mask |= 1 << i
        return mask

    def _poses(self, entry, guided):
        parent, target_index = entry
        key = (parent.uid, target_index, guided)
        if key in self.cache:
            return self.cache[key]
        target = parent.ports[target_index]
        flipped = rg.Plane(target.Origin, target.XAxis, -target.YAxis)
        poses = []
        for source_index, source in enumerate(self.ports):
            mate = rg.Transform.PlaneToPlane(source, flipped)
            for angle_index in range(self.rotation_steps):
                angle = 2.0 * math.pi * angle_index / self.rotation_steps
                roll = rg.Transform.Rotation(angle, target.ZAxis, target.Origin)
                transform = roll * mate
                center = _cg_point(self.reference, transform)
                self.stats["poses"] += 1
                distance = 0.0
                if guided:
                    distance = self._distance(center)
                    if distance is None:
                        self.stats["projection_failed"] += 1
                        continue
                mask = self._coverage(center) if guided else 0
                future = [_cg_point(p, transform) for i, p in enumerate(self.exit_hints)
                          if i != source_index] if guided else []
                poses.append(_CGPose(parent, target_index, source_index,
                                     transform, center, mask, self.rng.random(),
                                     future, distance))
        self.cache[key] = poses
        return poses

    def _valid(self, pose, path):
        if pose.blocked:
            return False
        if self.stats["checked"] >= self.max_attempts:
            self.reason = "search_budget"
            return False
        self.stats["checked"] += 1
        if pose.part is None:
            pose.part = self._make_part(pose.transform)
        candidate = pose.part
        for existing in self.parts + [p.part for p in path]:
            if (existing is pose.parent and self.supported[pose.target]
                    and self.supported[pose.source]):
                # Both solids are proven to lie behind their outward port
                # planes. Mating reverses those normals: opposite half-spaces.
                self.stats["parent_contact"] += 1
                continue
            state = _volume_overlap_state(candidate.geometry, existing.geometry,
                                          self.tol, candidate.box, existing.box)
            if state != "clear":
                counter = "overlap" if state == "overlap" else "boolean_failed"
                self.stats[counter] += 1
                # A rejection against committed geometry remains a rejection.
                # A speculative-path collision must NOT poison other paths.
                if existing in self.parts:
                    pose.blocked = True
                return False
        return True

    def _rank(self, mask, pose):
        front = _cg_front(mask, len(self.stations))
        goal = self.stations[min(front, len(self.stations) - 1)]
        # Attraction, not containment: distance is a soft cost with no cut-off.
        # First reward newly reached curve sections, then prefer a short route
        # back to the next missing section. The lookahead can accept a lateral
        # first step when its continuation is more useful.
        distance = round((pose.center.DistanceTo(goal)
                          + 0.25 * pose.curve_distance) / self.step, 6)
        future = min(p.DistanceTo(goal) for p in getattr(pose, "future", [pose.center]))
        return (-front, -_cg_bit_count(mask), distance,
                round(future / self.step, 6), pose.tie)

    def _configuration_key(self, pose):
        # Symmetric modules can yield the same physical connector layout from
        # several source/roll combinations. Do not fill the beam with copies.
        scale = max(self.tol, self.step * 1e-6)
        return tuple(sorted(
            tuple(int(round(value / scale)) for value in
                  (p.Origin.X, p.Origin.Y, p.Origin.Z))
            for i, p in enumerate(pose.part.ports) if i != pose.source
        ))

    def _guided_path(self):
        front = _cg_front(self.mask, len(self.stations))
        goal = self.stations[front]
        baseline_distance = min(part.center.DistanceTo(goal) for part in self.parts)
        beam = [([], self.mask)]
        best_bridge = None
        best_gain = None
        for depth in range(min(self.lookahead, self.count - len(self.parts))):
            choices = []
            for path, mask in beam:
                entries = self.open_ports if not path else [
                    (path[-1].part, i) for i in range(len(self.ports))
                    if i != path[-1].source
                ]
                for entry in entries:
                    for pose in self._poses(entry, True):
                        if not pose.blocked:
                            next_mask = mask | pose.mask
                            key = self._rank(next_mask, pose)
                            choices.append((key, path, next_mask, pose))
            choices.sort(key=lambda item: item[0])
            next_beam = []
            seen = set()
            for key, path, next_mask, pose in choices:
                if self._valid(pose, path):
                    new_path = path + [pose]
                    # Sideways steps are permitted. A path can earn coverage
                    # on its second or third step, rather than on every step.
                    if next_mask == self.full_mask:
                        return new_path[:1]
                    if next_mask != self.mask:
                        if best_gain is None or key < best_gain[0]:
                            best_gain = (key, new_path)
                    configuration = self._configuration_key(pose)
                    if configuration in seen:
                        continue
                    seen.add(configuration)
                    next_beam.append((new_path, next_mask))
                    if pose.center.DistanceTo(goal) < baseline_distance - self.tol:
                        if best_bridge is None or key < best_bridge[0]:
                            best_bridge = (key, new_path)
                    if len(next_beam) >= self.beam_width:
                        break
                if self.reason == "search_budget":
                    return None
            beam = next_beam
            if not beam:
                break
        # Commit only the first step of the best route, then re-plan. The
        # selected twist has a checked continuation instead of a random future.
        best = best_gain if best_gain is not None else best_bridge
        return None if best is None else best[1][:1]

    def _commit(self, pose, guided):
        self.open_ports.remove((pose.parent, pose.target))
        self.parts.append(pose.part)
        self.open_ports.extend((pose.part, i) for i in range(len(self.ports))
                               if i != pose.source)
        if guided:
            self.mask |= pose.mask
            self.guided_count += 1

    def run(self):
        while self.mask != self.full_mask and len(self.parts) < self.count:
            path = self._guided_path()
            if path is None:
                self.reason = self.reason or "blocked_along_curve"
                break
            for pose in path:
                self._commit(pose, True)

        if self.mask == self.full_mask:
            # Free spreading starts only after measured curve coverage.
            while len(self.parts) < self.count:
                entries = list(self.open_ports)
                self.rng.shuffle(entries)
                placed = False
                for entry in entries:
                    options = list(self._poses(entry, False))
                    self.rng.shuffle(options)
                    for pose in options:
                        if self._valid(pose, []):
                            self._commit(pose, False)
                            placed = True
                            break
                        if self.reason == "search_budget":
                            break
                    if placed or self.reason == "search_budget":
                        break
                if not placed:
                    self.reason = self.reason or "blocked_spread"
                    break
        self.reason = self.reason or (
            "complete" if self.mask == self.full_mask else "count_limit_before_coverage"
        )
        fraction = _cg_bit_count(self.mask) / float(len(self.stations))
        explanations = {
            "complete": "Kurve abgedeckt; Gesamtzahl erreicht.",
            "count_limit_before_coverage":
                "count erreicht, bevor die Kurve abgedeckt ist. count erhoehen.",
            "blocked_along_curve":
                "Keine passende Fortsetzung in der begrenzten Suche gefunden. "
                "Ports und Meldungen unten pruefen; ggf. lookahead oder rotation_steps erhoehen.",
            "blocked_spread": "Kurve abgedeckt; keine weitere kollisionsfreie Verbindung gefunden.",
            "search_budget": "Suchbudget erreicht. Ergebnisse sind teilweise; max_attempts erhoehen.",
        }
        message = (
            "{version}\n{count}/{requested} Module; davon {guided} in der Kurvenphase.\n"
            "Kurvenabdeckung: {coverage:.1f}% ({covered}/{stations} Messpunkte).\n"
            "{explanation}\n"
            "Fehlgeschlagene Kurvenprojektionen: {projection_failed}; "
            "Ueberschneidungen: {overlap}; "
            "unklare Boolean-Pruefungen: {failed}; geprueft: {checked}.\n"
            "Nach aussen korrigierte Ports: {flipped}."
        ).format(version=GROW_ALONG_VERSION, count=len(self.parts), requested=self.count,
                 guided=self.guided_count, coverage=100 * fraction,
                 covered=_cg_bit_count(self.mask), stations=len(self.stations),
                 explanation=explanations[self.reason],
                 projection_failed=self.stats["projection_failed"],
                 overlap=self.stats["overlap"], failed=self.stats["boolean_failed"],
                 checked=self.stats["checked"], flipped=self.flipped_ports)
        info = dict(version=GROW_ALONG_VERSION, reason=self.reason, message=message,
                    coverage=fraction, count=len(self.parts), guided_count=self.guided_count,
                    guide_mode="curve_attraction", coverage_distance=self.cover_distance,
                    stations=self.stations,
                    uncovered_points=[p for i, p in enumerate(self.stations)
                                      if not self.mask & (1 << i)],
                    stats=dict(self.stats), flipped_ports=self.flipped_ports)
        shapes = [part.geometry for part in self.parts]
        free_ports = [part.ports[i] for part, i in self.open_ports]
        return shapes, free_ports, self.guided_count, info


def grow_along_curve(module, ports, curve, count=50, seed=1, *,
                     collision_tolerance=None, rotation_steps=12,
                     lookahead=3, beam_width=5, start_at_curve=True,
                     return_info=False, max_attempts=20000):
    """Grow connected copies along a guide curve, then spread freely.

    G/module: one valid closed Brep. P/ports: list of planes on the outer
    connection faces, with outward Z axes. Circular faces can twist about Z;
    the algorithm never tilts a mating face away from its actual counterpart.
    C/curve: guide curve. The seed is moved to the nearest end by default.

    count: maximum TOTAL number of modules, including the seed.
    The curve is an attractor and has no hard distance boundary. Candidate
        routes are ranked by curve coverage, distance to the next uncovered
        section, and distance to the curve. Lateral detours are allowed.
    Curve coverage is sampled at a spacing derived automatically from the
        module size. A sample is reached within 1.5 times the median
        centre-to-port distance. This recognition distance does NOT reject
        candidate modules; it only controls progress and the phase switch.
    rotation_steps: tested twists around each real connection (12 = 30 deg).
    lookahead / beam_width: bounded search for useful sideways detours.
    collision_tolerance: Rhino document LENGTH tolerance for overlap checks.
    max_attempts: cap on expensive candidate checks, with a diagnostic on stop.

    Grasshopper inputs: G, P, C, count, seed. Remove the old radius,
        curve_tolerance and along_count inputs and arguments.
    Returns (shapes, free_ports, guided_count). With return_info=True also
    returns a dict with coverage, message, reason and uncovered_points.
    A blocked search returns its partial result; it never silently claims that
    the entire curve is covered. Re-evaluation with the same inputs is stable.
    """
    if collision_tolerance is None:
        doc = Rhino.RhinoDoc.ActiveDoc
        collision_tolerance = doc.ModelAbsoluteTolerance if doc is not None else 0.01
    engine = _CurveGrower(module, ports, curve, count, seed,
                         collision_tolerance, rotation_steps, lookahead, beam_width,
                         start_at_curve, max_attempts)
    result = engine.run()
    return result if return_info else result[:3]
