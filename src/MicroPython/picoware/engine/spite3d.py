from micropython import const
from picoware.system.vector import Vector

MAX_TRIANGLES_PER_SPRITE = const(28)
SPRITE_HUMANOID = const(0)
SPRITE_TREE = const(1)
SPRITE_HOUSE = const(2)
SPRITE_PILLAR = const(3)
SPRITE_CUSTOM = const(4)


class Vertex3D:
    """3D vertex structure"""

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def rotate_y(self, angle):
        """Rotate vertex around Y axis (for sprite facing)"""
        from math import sin, cos

        cos_a = cos(angle)
        sin_a = sin(angle)
        return Vertex3D(
            self.x * cos_a - self.z * sin_a, self.y, self.x * sin_a + self.z * cos_a
        )

    def translate(self, dx, dy, dz):
        """Translate vertex"""
        return Vertex3D(self.x + dx, self.y + dy, self.z + dz)

    def scale(self, sx, sy, sz):
        """Scale vertex"""
        return Vertex3D(self.x * sx, self.y * sy, self.z * sz)

    def __sub__(self, other):
        """Subtraction operator for vector operations"""
        return Vertex3D(self.x - other.x, self.y - other.y, self.z - other.z)


class Triangle3D:
    """3D triangle structure"""

    def __init__(
        self, x1=0.0, y1=0.0, z1=0.0, x2=0.0, y2=0.0, z2=0.0, x3=0.0, y3=0.0, z3=0.0
    ) -> None:
        self.x1, self.y1, self.z1 = float(x1), float(y1), float(z1)
        self.x2, self.y2, self.z2 = float(x2), float(y2), float(z2)
        self.x3, self.y3, self.z3 = float(x3), float(y3), float(z3)
        self.visible = True
        self.distance = 0.0

    @property
    def center(self) -> Vertex3D:
        """Calculate triangle center for distance sorting"""
        return Vertex3D(
            (self.x1 + self.x2 + self.x3) / 3.0,
            (self.y1 + self.y2 + self.y3) / 3.0,
            (self.z1 + self.z2 + self.z3) / 3.0,
        )

    # we need this to access the scale, rotate, translate methods
    # and for easier parsing later on
    @property
    def vertices(self) -> list:
        """Get triangle vertices as a list"""
        return [
            Vertex3D(self.x1, self.y1, self.z1),
            Vertex3D(self.x2, self.y2, self.z2),
            Vertex3D(self.x3, self.y3, self.z3),
        ]

    @vertices.setter
    def vertices(self, verts: list[Vertex3D]):
        """Set triangle vertices from a list"""
        self.x1, self.y1, self.z1 = verts[0].x, verts[0].y, verts[0].z
        self.x2, self.y2, self.z2 = verts[1].x, verts[1].y, verts[1].z
        self.x3, self.y3, self.z3 = verts[2].x, verts[2].y, verts[2].z

    def is_facing_camera(self, camera_pos: Vector) -> bool:
        """Check if triangle is facing the camera (basic backface culling)"""
        # Calculate triangle normal using cross product
        vert_0 = Vertex3D(self.x1, self.y1, self.z1)
        vert_1 = Vertex3D(self.x2, self.y2, self.z2)
        vert_2 = Vertex3D(self.x3, self.y3, self.z3)
        v1 = vert_1 - vert_0
        v2 = vert_2 - vert_0

        # Cross product to get normal (right-hand rule)
        normal = Vertex3D(
            v1.y * v2.z - v1.z * v2.y,
            v1.z * v2.x - v1.x * v2.z,
            v1.x * v2.y - v1.y * v2.x,
        )

        # Vector from triangle center to camera
        center = self.center
        to_camera = Vertex3D(
            camera_pos.x - center.x,
            0.5 - center.y,  # Camera height
            camera_pos.y - center.z,  # camera_pos.y is Z in world space
        )

        # Dot product - if positive, triangle faces camera
        dot = normal.x * to_camera.x + normal.y * to_camera.y + normal.z * to_camera.z
        return dot > 0.0


class Sprite3D:
    """3D sprite class for rendering 3D objects"""

    def __init__(self):
        self.triangles = [Triangle3D() for _ in range(MAX_TRIANGLES_PER_SPRITE)]
        self.triangle_count = 0
        self.pos = Vector(0, 0)
        self.rotation_y = 0.0
        self.scale_factor = 1.0
        self.type = SPRITE_CUSTOM
        self.active = False
        self.color = 0x0000  # Default black

    def __del__(self):
        for tri in self.triangles:
            del tri
        self.triangles = None
        del self.pos
        self.pos = None
        self.color = None
        self.active = False

    @property
    def position(self) -> Vector:
        """Get sprite position"""
        return self.pos

    @position.setter
    def position(self, pos: Vector):
        """Set sprite position"""
        self.pos = pos

    @property
    def rotation(self):
        """Get sprite rotation"""
        return self.rotation_y

    @rotation.setter
    def rotation(self, rot):
        """Set sprite rotation around Y axis"""
        self.rotation_y = rot

    @property
    def scale(self):
        """Get sprite scale factor"""
        return self.scale_factor

    @scale.setter
    def scale(self, scale):
        """Set sprite scale factor"""
        self.scale_factor = scale

    @property
    def is_active(self):
        """Check if sprite is active"""
        return self.active

    @is_active.setter
    def is_active(self, state):
        """Set sprite active state"""
        self.active = state

    @property
    def sprite_type(self):
        """Get sprite type"""
        return self.type

    def add_triangle(self, triangle: Triangle3D):
        """Add triangle to sprite"""
        if self.triangle_count < MAX_TRIANGLES_PER_SPRITE:
            self.triangles[self.triangle_count] = triangle
            self.triangle_count += 1

    def clear_triangles(self):
        """Clear all triangles"""
        self.triangle_count = 0

    # Initialize sprite with specific parameters (for Entity class)
    def initialize_as_humanoid(self, pos, height, rot, color=0x000000):
        """Initialize sprite as humanoid"""
        self.position = pos
        self.rotation_y = rot
        self.clear_triangles()
        self.type = SPRITE_HUMANOID
        self.color = color
        self.active = True
        self._create_humanoid(height)

    def initialize_as_tree(self, pos, height, color=0x000000):
        """Initialize sprite as tree"""
        self.position = pos
        self.rotation_y = 0
        self.clear_triangles()
        self.type = SPRITE_TREE
        self.color = color
        self.active = True
        self._create_tree(height)

    def initialize_as_house(self, pos, width, height, rot, color=0x000000):
        """Initialize sprite as house"""
        self.position = pos
        self.rotation_y = rot
        self.clear_triangles()
        self.type = SPRITE_HOUSE
        self.color = color
        self.active = True
        self._create_house(width, height)

    def initialize_as_pillar(self, pos, height, radius, color=0x000000):
        """Initialize sprite as pillar"""
        self.position = pos
        self.rotation_y = 0
        self.clear_triangles()
        self.type = SPRITE_PILLAR
        self.color = color
        self.active = True
        self._create_pillar(height, radius)

    def get_transformed_triangles(self, camera_pos) -> list:
        """Get transformed triangles (with position, rotation, scale applied)"""
        from math import sqrt

        output_triangles = []

        if not self.active:
            return output_triangles

        for i in range(self.triangle_count):
            transformed = Triangle3D(
                self.triangles[i].x1,
                self.triangles[i].y1,
                self.triangles[i].z1,
                self.triangles[i].x2,
                self.triangles[i].y2,
                self.triangles[i].z2,
                self.triangles[i].x3,
                self.triangles[i].y3,
                self.triangles[i].z3,
            )

            # Apply transformations to each vertex
            for v in range(3):
                # Scale
                transformed.vertices[v] = transformed.vertices[v].scale(
                    self.scale_factor, self.scale_factor, self.scale_factor
                )

                # Rotate around Y axis
                transformed.vertices[v] = transformed.vertices[v].rotate_y(
                    self.rotation_y
                )

                # Translate to world position
                transformed.vertices[v] = transformed.vertices[v].translate(
                    self.position.x, 0, self.position.y
                )

            # Check if triangle should be rendered
            if transformed.is_facing_camera(camera_pos):
                # Calculate distance for sorting
                center = transformed.center
                dx = center.x - camera_pos.x
                dz = center.z - camera_pos.y
                transformed.distance = sqrt(dx * dx + dz * dz)

                output_triangles.append(transformed)

        return output_triangles

    # Create different sprite types
    def _create_humanoid(self, height=1.8):
        """Create a humanoid character"""
        self.clear_triangles()
        self.type = SPRITE_HUMANOID

        head_radius = height * 0.12
        torso_width = height * 0.20
        torso_height = height * 0.35
        leg_height = height * 0.45
        arm_length = height * 0.25

        # Head (simplified as a cube) - positioned at top, wider
        self._create_cube(
            0,
            height - head_radius,
            0,
            head_radius * 2,
            head_radius * 2,
            head_radius * 1.5,
        )

        # Torso - positioned in middle, wider and deeper
        self._create_cube(
            0,
            leg_height + torso_height / 2,
            0,
            torso_width,
            torso_height,
            torso_width * 0.8,
        )

        # Arms - positioned at shoulder level
        arm_width = torso_width * 0.35
        arm_y = leg_height + torso_height - arm_length / 2
        self._create_cube(
            -torso_width * 0.8, arm_y, 0, arm_width, arm_length, arm_width
        )
        self._create_cube(torso_width * 0.8, arm_y, 0, arm_width, arm_length, arm_width)

        # Legs - positioned so their bottoms touch ground (y=0)
        leg_width = torso_width * 0.45
        self._create_cube(
            -leg_width * 0.7, leg_height / 2, 0, leg_width, leg_height, leg_width
        )
        self._create_cube(
            leg_width * 0.7, leg_height / 2, 0, leg_width, leg_height, leg_width
        )

    def _create_tree(self, height=2.0):
        """Create a simple tree"""
        self.clear_triangles()
        self.type = SPRITE_TREE

        trunk_width = height * 0.18
        trunk_height = height * 0.4
        crown_width = height * 0.65
        crown_height = height * 0.6

        # Trunk (simple cube) - positioned so bottom touches ground (y=0)
        self._create_cube(
            0, trunk_height / 2, 0, trunk_width, trunk_height, trunk_width
        )

        # Crown (simple cube representing foliage) - positioned on top of trunk
        self._create_cube(
            0,
            trunk_height + crown_height / 2,
            0,
            crown_width,
            crown_height,
            crown_width,
        )

    def _create_house(self, width=2.0, height=2.5):
        """Create a simple house"""
        self.clear_triangles()
        self.type = SPRITE_HOUSE

        wall_height = height * 0.7
        roof_height = height * 0.3
        house_width = width * 1.3
        house_depth = width * 1.1

        # House base (cube)
        self._create_cube(0, wall_height / 2, 0, house_width, wall_height, house_depth)

        # Roof (triangular prism)
        self._create_triangular_prism(
            0, wall_height + roof_height / 2, 0, house_width, roof_height, house_depth
        )

    def _create_pillar(self, height=3.0, radius=0.3):
        """Create a pillar"""
        self.clear_triangles()
        self.type = SPRITE_PILLAR
        pillar_radius = radius * 1.5

        # Main cylinder - 6 segments = 12 triangles
        self._create_cylinder(0, height / 2, 0, pillar_radius, height, 6)

        # Base - 4 segments = 8 triangles
        self._create_cylinder(
            0, pillar_radius * 0.4, 0, pillar_radius * 1.4, pillar_radius * 0.8, 4
        )

        # Top - 4 segments = 8 triangles
        self._create_cylinder(
            0,
            height - pillar_radius * 0.4,
            0,
            pillar_radius * 1.4,
            pillar_radius * 0.8,
            4,
        )

    def _create_cube(self, x, y, z, width, height, depth):
        """Create a cube with 8 triangles (4 side faces only)"""
        hw = width * 0.5
        hh = height * 0.5
        hd = depth * 0.5

        # Render 4 most important faces (skip top and bottom to save triangles)
        # This gives 8 triangles per cube instead of 12

        # Front face (2 triangles)
        self.add_triangle(
            Triangle3D(
                x - hw,
                y - hh,
                z + hd,
                x + hw,
                y - hh,
                z + hd,
                x + hw,
                y + hh,
                z + hd,
            )
        )
        self.add_triangle(
            Triangle3D(
                x - hw,
                y - hh,
                z + hd,
                x + hw,
                y + hh,
                z + hd,
                x - hw,
                y + hh,
                z + hd,
            )
        )

        # Back face (2 triangles)
        self.add_triangle(
            Triangle3D(
                x + hw,
                y - hh,
                z - hd,
                x - hw,
                y - hh,
                z - hd,
                x - hw,
                y + hh,
                z - hd,
            )
        )
        self.add_triangle(
            Triangle3D(
                x + hw,
                y - hh,
                z - hd,
                x - hw,
                y + hh,
                z - hd,
                x + hw,
                y + hh,
                z - hd,
            )
        )

        # Right face (2 triangles)
        self.add_triangle(
            Triangle3D(
                x + hw,
                y - hh,
                z + hd,
                x + hw,
                y - hh,
                z - hd,
                x + hw,
                y + hh,
                z - hd,
            )
        )
        self.add_triangle(
            Triangle3D(
                x + hw,
                y - hh,
                z + hd,
                x + hw,
                y + hh,
                z - hd,
                x + hw,
                y + hh,
                z + hd,
            )
        )

        # Left face (2 triangles)
        self.add_triangle(
            Triangle3D(
                x - hw,
                y - hh,
                z - hd,
                x - hw,
                y - hh,
                z + hd,
                x - hw,
                y + hh,
                z + hd,
            )
        )
        self.add_triangle(
            Triangle3D(
                x - hw,
                y - hh,
                z - hd,
                x - hw,
                y + hh,
                z + hd,
                x - hw,
                y + hh,
                z - hd,
            )
        )

    def _create_cylinder(self, x, y, z, radius, height, segments):
        """Create a cylinder with side faces only (no caps to save triangles)"""
        from math import cos, pi, sin

        hh = height * 0.5

        # Limit segments to prevent too many triangles
        segments = min(segments, 6)

        # Only side faces - no caps to save triangles
        for i in range(segments):
            angle1 = float(i) * 2.0 * pi / segments
            angle2 = float(i + 1) * 2.0 * pi / segments

            x1 = x + radius * cos(angle1)
            z1 = z + radius * sin(angle1)
            x2 = x + radius * cos(angle2)
            z2 = z + radius * sin(angle2)

            # Side face triangles only
            self.add_triangle(
                Triangle3D(
                    x1,
                    y - hh,
                    z1,
                    x2,
                    y - hh,
                    z2,
                    x2,
                    y + hh,
                    z2,
                )
            )
            self.add_triangle(
                Triangle3D(
                    x1,
                    y - hh,
                    z1,
                    x2,
                    y + hh,
                    z2,
                    x1,
                    y + hh,
                    z1,
                )
            )

    def _create_sphere(self, x, y, z, radius, segments):
        """Create a sphere (limited segments to prevent triangle explosion)"""
        from math import cos, pi, sin

        # Limit segments for sphere to prevent triangle explosion
        segments = min(segments, 4)

        for lat in range(segments // 2):
            theta1 = float(lat) * pi / (segments // 2)
            theta2 = float(lat + 1) * pi / (segments // 2)

            for lon in range(segments):
                phi1 = float(lon) * 2.0 * pi / segments
                phi2 = float(lon + 1) * 2.0 * pi / segments

                # Calculate vertices
                x1 = x + radius * sin(theta1) * cos(phi1)
                y1 = y + radius * cos(theta1)
                z1 = z + radius * sin(theta1) * sin(phi1)
                #
                x2 = x + radius * sin(theta1) * cos(phi2)
                y2 = y + radius * cos(theta1)
                z2 = z + radius * sin(theta1) * sin(phi2)
                #
                x3 = x + radius * sin(theta2) * cos(phi1)
                y3 = y + radius * cos(theta2)
                z3 = z + radius * sin(theta2) * sin(phi1)
                #
                x4 = x + radius * sin(theta2) * cos(phi2)
                y4 = y + radius * cos(theta2)
                z4 = z + radius * sin(theta2) * sin(phi2)

                # Add triangles
                if lat > 0:
                    self.add_triangle(
                        Triangle3D(
                            x1,
                            y1,
                            z1,
                            x2,
                            y2,
                            z2,
                            x3,
                            y3,
                            z3,
                        )
                    )
                if lat < segments // 2 - 1:
                    self.add_triangle(
                        Triangle3D(
                            x2,
                            y2,
                            z2,
                            x4,
                            y4,
                            z4,
                            x3,
                            y3,
                            z3,
                        )
                    )

    def _create_triangular_prism(self, x, y, z, width, height, depth):
        """Create a triangular prism (for roofs)"""
        hw = width * 0.5
        hh = height * 0.5
        hd = depth * 0.5

        # Front triangle
        self.add_triangle(
            Triangle3D(
                x - hw,
                y - hh,
                z + hd,
                x + hw,
                y - hh,
                z + hd,
                x,
                y + hh,
                z + hd,
            )
        )

        # Back triangle
        self.add_triangle(
            Triangle3D(
                x + hw,
                y - hh,
                z - hd,
                x - hw,
                y - hh,
                z - hd,
                x,
                y + hh,
                z - hd,
            )
        )

        # Bottom face
        self.add_triangle(
            Triangle3D(
                x - hw,
                y - hh,
                z - hd,
                x + hw,
                y - hh,
                z - hd,
                x + hw,
                y - hh,
                z + hd,
            )
        )
        self.add_triangle(
            Triangle3D(
                x - hw,
                y - hh,
                z - hd,
                x + hw,
                y - hh,
                z + hd,
                x - hw,
                y - hh,
                z + hd,
            )
        )

        # Side faces
        self.add_triangle(
            Triangle3D(
                x - hw,
                y - hh,
                z + hd,
                x,
                y + hh,
                z + hd,
                x,
                y + hh,
                z - hd,
            )
        )
        self.add_triangle(
            Triangle3D(
                x - hw,
                y - hh,
                z + hd,
                x,
                y + hh,
                z - hd,
                x - hw,
                y - hh,
                z - hd,
            )
        )

        self.add_triangle(
            Triangle3D(
                x,
                y + hh,
                z + hd,
                x + hw,
                y - hh,
                z + hd,
                x + hw,
                y - hh,
                z - hd,
            )
        )
        self.add_triangle(
            Triangle3D(
                x,
                y + hh,
                z + hd,
                x + hw,
                y - hh,
                z - hd,
                x,
                y + hh,
                z - hd,
            )
        )
