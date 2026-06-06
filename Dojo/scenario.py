import math

from pydantic import GetCoreSchemaHandler, BaseModel, Field
from pydantic_core import core_schema
from rlbot.flat import Vector3, DesiredGameState, DesiredBallState, DesiredCarState, DesiredPhysics, Vector3Partial, \
    RotatorPartial


class Vec3(Vector3):
    @classmethod
    def from_rlbot(cls, vec):
        return Vec3(x=vec.x, y=vec.y, z=vec.z)

    def to_rlbot_partial(self) -> Vector3Partial:
        return Vector3Partial(self.x, self.y, self.z)

    def __neg__(self) -> 'Vec3':
        return Vec3(x=-self.x, y=-self.y, z=-self.z)

    def __add__(self, other) -> 'Vec3':
        return Vec3(x=self.x + other.x, y=self.y + other.y, z=self.z + other.z)

    def __sub__(self, other) -> 'Vec3':
        return Vec3(x=self.x - other.x, y=self.y - other.y, z=self.z - other.z)

    @classmethod
    def __get_pydantic_core_schema__(
            cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls._serialize,
                info_arg=False,
            ),
        )

    @classmethod
    def _validate(cls, value) -> 'Vec3':
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(x=value['x'], y=value['y'], z=value['z'])
        # Handle the base Vector3 type
        if isinstance(value, Vector3):
            return cls.from_rlbot(value)
        raise ValueError(f"Cannot convert {type(value)} to Vec3")

    def _serialize(self) -> dict:
        return {'x': self.x, 'y': self.y, 'z': self.z}


class RotatorModel(BaseModel):
    pitch: float = 0
    yaw: float = 0
    roll: float = 0

    @classmethod
    def from_rlbot(cls, rotator):
        return cls(pitch=rotator.pitch, yaw=rotator.yaw, roll=rotator.roll)

    def to_rlbot_partial(self) -> RotatorPartial:
        return RotatorPartial(self.pitch, self.yaw, self.roll)


class PhysicsModel(BaseModel):
    location: Vec3 = Field(default_factory=Vec3)
    velocity: Vec3 = Field(default_factory=Vec3)
    rotation: RotatorModel = Field(default_factory=RotatorModel)
    angular_velocity: Vec3 = Field(default_factory=Vec3)

    @classmethod
    def from_rlbot(cls, phys):
        return cls(
            location=Vec3.from_rlbot(phys.location),
            velocity=Vec3.from_rlbot(phys.velocity),
            rotation=RotatorModel.from_rlbot(phys.rotation),
            angular_velocity=Vec3.from_rlbot(phys.angular_velocity)
        )

    def to_rlbot_desired(self) -> DesiredPhysics:
        return DesiredPhysics(
            location=self.location.to_rlbot_partial(),
            velocity=self.velocity.to_rlbot_partial(),
            rotation=self.rotation.to_rlbot_partial(),
            angular_velocity=self.angular_velocity.to_rlbot_partial(),
        )


class CarStateModel(BaseModel):
    physics: PhysicsModel = Field(default_factory=PhysicsModel)
    boost_amount: float = 0

    @classmethod
    def from_rlbot(cls, car):
        return cls(
            physics=PhysicsModel.from_rlbot(car.physics),
            boost_amount=car.boost
        )

    def to_rlbot_desired(self) -> DesiredCarState:
        return DesiredCarState(
            physics=self.physics.to_rlbot_desired(),
            boost_amount=self.boost_amount
        )


class BallStateModel(BaseModel):
    physics: PhysicsModel = Field(default_factory=PhysicsModel)

    @classmethod
    def from_rlbot(cls, car):
        return cls(physics=PhysicsModel.from_rlbot(car.physics))

    def to_rlbot_desired(self) -> DesiredBallState:
        return DesiredBallState(physics=self.physics.to_rlbot_desired())


class ScenarioModel(BaseModel):
    offensive_team: int = 0
    offensive_car_state: CarStateModel = Field(default_factory=CarStateModel)
    defensive_car_state: CarStateModel = Field(default_factory=CarStateModel)
    ball_state: BallStateModel = Field(default_factory=BallStateModel)

    def to_rlbot_desired(self, human_offense: bool) -> DesiredGameState:
        """Convert GameStateModel to RLBot DesiredGameState"""
        human = self.offensive_car_state if human_offense else self.defensive_car_state
        bot = self.defensive_car_state if human_offense else self.offensive_car_state

        car_states = [bot.to_rlbot_desired(), human.to_rlbot_desired()]
        ball_states = [self.ball_state.to_rlbot_desired()]

        return DesiredGameState(car_states=car_states, ball_states=ball_states)

    def mirror(self):
        '''
        Mirror the scenario across the Y axis, turning defensive scenarios into offensive scenarios
        Involves flipping the Y aspects of the car + ball locations, velocity, and yaw
        '''
        self.offensive_car_state.physics.location.y = -self.offensive_car_state.physics.location.y
        self.defensive_car_state.physics.location.y = -self.defensive_car_state.physics.location.y
        self.ball_state.physics.location.y = -self.ball_state.physics.location.y

        self.offensive_car_state.physics.rotation.yaw = -self.offensive_car_state.physics.rotation.yaw
        self.defensive_car_state.physics.rotation.yaw = -self.defensive_car_state.physics.rotation.yaw

        self.offensive_car_state.physics.velocity.y = -self.offensive_car_state.physics.velocity.y
        self.defensive_car_state.physics.velocity.y = -self.defensive_car_state.physics.velocity.y
        self.ball_state.physics.velocity.y = -self.ball_state.physics.velocity.y

        self.offensive_team = 1 - self.offensive_team

    def draw(self):
        '''
        Plot the scenario against a simulated field, for debugging purposes
        '''
        import matplotlib.pyplot as plt

        plt.figure()
        # Rocket League uses a coordinate system (X, Y, Z), where Z is upwards. Note also that negative Y is towards Blue's goal (team 0).

        # Floor: 0
        # Center field: (0, 0)
        # Side wall: x=±4096
        # Side wall length: 7936
        # Back wall: y=±5120
        # Back wall length: 5888
        # Ceiling: z=2044
        # Goal height: z=642.775
        # Goal center-to-post: 892.755
        # Goal depth: 880
        # Corner wall length: 1629.174
        # The corner planes intersect the axes at ±8064 at a 45 degrees angle

        # Draw the field

        # Add vertical lines from at X=-4096 and X=4096, each from Y=-5120 to Y=5120
        # Stop 1152 units short from each wall to leave room for the corners
        corner_start = 5120 - 1152
        plt.plot([-4096, -4096], [-corner_start, corner_start], 'k-')
        plt.plot([4096, 4096], [-corner_start, corner_start], 'k-')

        # Add horizontal lines from at Y=-5120 and Y=5120, each from X=-4096 to X=4096
        corner_start = 4096 - 1152
        plt.plot([-corner_start, corner_start], [-5120, -5120], 'k-')
        plt.plot([-corner_start, corner_start], [5120, 5120], 'k-')

        # Draw lines representing the corners
        # Top left goes from X=-4096, Y=(5120-1152) to X=(-4096+1152), Y=-5120
        plt.plot([-4096, -4096 + 1152], [5120 - 1152, 5120], 'k-')
        # Top right goes from X=4096, Y=(5120-1152) to X=(4096-1152), Y=-5120
        plt.plot([4096, 4096 - 1152], [5120 - 1152, 5120], 'k-')
        # Bottom left goes from X=-4096, Y=-5120 to X=(-4096+1152), Y=(-5120+1152)
        plt.plot([-4096, -4096 + 1152], [-5120 + 1152, -5120], 'k-')
        # Bottom right goes from X=4096, Y=-5120 to X=(4096-1152), Y=(-5120+1152)
        plt.plot([4096, 4096 - 1152], [-5120 + 1152, -5120], 'k-')

        # Goal extends from -893 to +893 in X, and 880 past the goal line in Y, which is at Y=+-5120
        plt.plot([-893, -893], [-5120 - 880, -5120], 'k-')
        plt.plot([893, 893], [-5120 - 880, -5120], 'k-')
        plt.plot([-893, 893], [-5120 - 880, -5120 - 880], 'k-')

        plt.plot([-893, -893], [5120, 5120 + 880], 'k-')
        plt.plot([893, 893], [5120, 5120 + 880], 'k-')
        plt.plot([-893, 893], [5120 + 880, 5120 + 880], 'k-')

        # Draw a dotted line across the center of the field at Y=0, make it opaque
        plt.plot([-4096, 4096], [0, 0], 'k--', alpha=0.5)

        # Draw the offensive car as a blue triangle
        # Car is 200 units long, 100 units wide
        # Draw an arrow from center -100 to center +100 units in the direction of the car's yaw
        car_length = 200
        car_width = 100
        offensive_x_component = car_length * math.cos(self.offensive_car_state.physics.rotation.yaw)
        offensive_y_component = car_width * math.sin(self.offensive_car_state.physics.rotation.yaw)
        offensive_arrow_x_start = self.offensive_car_state.physics.location.x
        offensive_arrow_y_start = self.offensive_car_state.physics.location.y

        plt.arrow(offensive_arrow_x_start,
                  offensive_arrow_y_start,
                  offensive_x_component,
                  offensive_y_component,
                  head_width=200, head_length=400, fc='b', ec='b', length_includes_head=True)

        defensive_x_component = car_length * math.cos(self.defensive_car_state.physics.rotation.yaw)
        defensive_y_component = car_width * math.sin(self.defensive_car_state.physics.rotation.yaw)
        defensive_arrow_x_start = self.defensive_car_state.physics.location.x
        defensive_arrow_y_start = self.defensive_car_state.physics.location.y
        plt.arrow(defensive_arrow_x_start,
                  defensive_arrow_y_start,
                  defensive_x_component,
                  defensive_y_component,
                  head_width=200, head_length=400, fc='r', ec='r', length_includes_head=True)

        # plt.plot(self.offensive_car_state.physics.location.x, self.offensive_car_state.physics.location.y, 'bo', markersize=10)
        # Draw the defensive car as a red triangle
        # plt.plot(self.defensive_car_state.physics.location.x, self.defensive_car_state.physics.location.y, 'ro', markersize=10)

        # Draw the ball as a gray circle
        plt.plot(self.ball_state.physics.location.x, self.ball_state.physics.location.y, 'ko', markersize=10)

        # Draw the offensive car's velocity vector
        plt.arrow(self.offensive_car_state.physics.location.x, self.offensive_car_state.physics.location.y,
                  self.offensive_car_state.physics.velocity.x, self.offensive_car_state.physics.velocity.y,
                  head_width=50, head_length=50, fc='b', ec='b')

        # Draw the defensive car's velocity vector
        plt.arrow(self.defensive_car_state.physics.location.x, self.defensive_car_state.physics.location.y,
                  self.defensive_car_state.physics.velocity.x, self.defensive_car_state.physics.velocity.y,
                  head_width=50, head_length=50, fc='r', ec='r')

        # Draw the ball's velocity vector
        plt.arrow(self.ball_state.physics.location.x, self.ball_state.physics.location.y,
                  self.ball_state.physics.velocity.x, self.ball_state.physics.velocity.y,
                  head_width=50, head_length=50, fc='k', ec='k')

        # Enforce same scale on both axes
        ax = plt.gca()
        ax.get_xaxis().get_major_formatter().set_scientific(False)
        ax.get_yaxis().get_major_formatter().set_scientific(False)
        plt.axis('equal')

        plt.show()
