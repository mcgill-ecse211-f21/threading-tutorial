"""
Module that handles all interaction with the BrickPi hardware, eg,
sensors and motors.

Authors: Ryan Au, Younes Boubekeur
"""

from __future__ import annotations  # not required in Python 3.10+
from brickpi3 import *
from typing import Literal, Type
import atexit
import os
import signal


PORTS: dict[str, int] = {
    '1': BrickPi3.PORT_1,
    '2': BrickPi3.PORT_2,
    '3': BrickPi3.PORT_3,
    '4': BrickPi3.PORT_4,
    'A': BrickPi3.PORT_A,
    'B': BrickPi3.PORT_B,
    'C': BrickPi3.PORT_C,
    'D': BrickPi3.PORT_D,
}


class RevEnumeration:
    """
    Take in a type object (class), finds every full-Uppercase attribute
    (constants) and creates a Reverse Enumeration, where the constant value
    is the key, and the constant's name is the value.
    """

    def __init__(self, enum):  # or *names, with no .split()
        "enum can be any type, but preferably a brickpi3.Enumeration object."
        for attr, val in enum.__dict__.items():
            if attr.isupper():
                setattr(self, str(val), attr)

    def __getitem__(self, key):
        "Allow performing get actions such as SENSOR_CODES[0]."
        return SENSOR_CODES.__dict__[str(key)]  # SENSOR_CODES -> self.enum?


SENSOR_CODES = RevEnumeration(BrickPi3.SENSOR_STATE)

BP = BrickPi3()  # The BrickPi3 instance


class ColorMapping:
    """
    Class that maps a color to a numeric code used by the color sensor.
    """

    def __init__(self, name: str, code: int):
        self.name = name
        self.code = code


class ColorMappings:
    """
    Color mappings based on the colors that can be detected by the color sensor.
    """
    UNKNOWN = ColorMapping("Unknown", 0)
    BLACK = ColorMapping("Black", 1)
    BLUE = ColorMapping("Blue", 2)
    GREEN = ColorMapping("Green", 3)
    YELLOW = ColorMapping("Yellow", 4)
    RED = ColorMapping("Red", 5)
    WHITE = ColorMapping("White", 6)
    ORANGE = ColorMapping("Orange", 7)

    _all_mappings = [UNKNOWN, BLACK, BLUE, GREEN, YELLOW, RED, WHITE, ORANGE]


class Color:
    """
    Namespace for color names, to reference them easily.
    """
    UNKNOWN = "Unknown"
    BLACK = "Black"
    BLUE = "Blue"
    GREEN = "Green"
    YELLOW = "Yellow"
    RED = "Red"
    WHITE = "White"
    ORANGE = "Orange"


_color_names_by_code = {c.code: c.name for c in ColorMappings._all_mappings}


class Brick(BrickPi3):
    """
    Wrapper class for the BrickPi3 class. Comes with additional methods such get_sensor_status.
    """

    def __init__(self):
        self.bp = BP
        child = self.__dict__
        parent = BP.__dict__
        for key in parent.keys():
            setattr(self, str(key), child.get(key, parent.get(key)))

    def get_sensor_status(self, port: Literal[1, 2, 4, 8]):
        """
        Read a sensor status.

        Keyword arguments:
        port - The sensor port (one at a time). PORT_1, PORT_2, PORT_3, or PORT_4.

        Return a code from 0 to 4 with the following meanings:

        0: VALID_DATA
        1: NOT_CONFIGURED
        2: CONFIGURING
        3: NO_DATA
        4: I2C_ERROR
        """
        if port == self.PORT_1:
            message_type = self.BPSPI_MESSAGE_TYPE.GET_SENSOR_1
            port_index = 0
        elif port == self.PORT_2:
            message_type = self.BPSPI_MESSAGE_TYPE.GET_SENSOR_2
            port_index = 1
        elif port == self.PORT_3:
            message_type = self.BPSPI_MESSAGE_TYPE.GET_SENSOR_3
            port_index = 2
        elif port == self.PORT_4:
            message_type = self.BPSPI_MESSAGE_TYPE.GET_SENSOR_4
            port_index = 3
        else:
            raise IOError("get_sensor error. Must be one sensor port at a time. PORT_1, PORT_2, PORT_3, or PORT_4.")

        if self.SensorType[port_index] == self.SENSOR_TYPE.CUSTOM:
            outArray = [self.SPI_Address, message_type, 0, 0, 0, 0, 0, 0, 0, 0]
            reply = self.spi_transfer_array(outArray)
            if reply[3] == 0xA5:
                if reply[4] == self.SensorType[port_index]:
                    return reply[5]
                else:
                    raise SensorError("get_sensor error: Invalid sensor data")
            else:
                raise IOError("get_sensor error: No SPI response")

        elif self.SensorType[port_index] == self.SENSOR_TYPE.I2C:
            outArray = [self.SPI_Address, message_type, 0, 0, 0, 0]
            for b in range(self.I2CInBytes[port_index]):
                outArray.append(0)
            reply = self.spi_transfer_array(outArray)
            if reply[3] == 0xA5:
                if reply[4] == self.SensorType[port_index]:
                    return reply[5]
                else:
                    raise SensorError("get_sensor error: Invalid sensor data")
            else:
                raise IOError("get_sensor error: No SPI response")

        elif (self.SensorType[port_index] == self.SENSOR_TYPE.TOUCH
              or self.SensorType[port_index] == self.SENSOR_TYPE.NXT_TOUCH
              or self.SensorType[port_index] == self.SENSOR_TYPE.EV3_TOUCH
              or self.SensorType[port_index] == self.SENSOR_TYPE.NXT_ULTRASONIC
              or self.SensorType[port_index] == self.SENSOR_TYPE.EV3_COLOR_REFLECTED
              or self.SensorType[port_index] == self.SENSOR_TYPE.EV3_COLOR_AMBIENT
              or self.SensorType[port_index] == self.SENSOR_TYPE.EV3_COLOR_COLOR
              or self.SensorType[port_index] == self.SENSOR_TYPE.EV3_ULTRASONIC_LISTEN
              or self.SensorType[port_index] == self.SENSOR_TYPE.EV3_INFRARED_PROXIMITY):
            outArray = [self.SPI_Address, message_type, 0, 0, 0, 0, 0]
            reply = self.spi_transfer_array(outArray)
            if (reply[3] == 0xA5):
                if ((reply[4] == self.SensorType[port_index] or (self.SensorType[port_index] == self.SENSOR_TYPE.TOUCH
                                                                 and (reply[4] == self.SENSOR_TYPE.NXT_TOUCH or reply[4] == self.SENSOR_TYPE.EV3_TOUCH)))):
                    return reply[5]
                else:
                    raise SensorError("get_sensor error: Invalid sensor data")
            else:
                raise IOError("get_sensor error: No SPI response")

        elif self.SensorType[port_index] == self.SENSOR_TYPE.NXT_COLOR_FULL:
            outArray = [self.SPI_Address, message_type, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            reply = self.spi_transfer_array(outArray)
            if reply[3] == 0xA5:
                if reply[4] == self.SensorType[port_index]:
                    return reply[5]
                else:
                    raise SensorError("get_sensor error: Invalid sensor data")
            else:
                raise IOError("get_sensor error: No SPI response")

        elif (self.SensorType[port_index] == self.SENSOR_TYPE.NXT_LIGHT_ON
              or self.SensorType[port_index] == self.SENSOR_TYPE.NXT_LIGHT_OFF
              or self.SensorType[port_index] == self.SENSOR_TYPE.NXT_COLOR_RED
              or self.SensorType[port_index] == self.SENSOR_TYPE.NXT_COLOR_GREEN
              or self.SensorType[port_index] == self.SENSOR_TYPE.NXT_COLOR_BLUE
              or self.SensorType[port_index] == self.SENSOR_TYPE.NXT_COLOR_OFF
              or self.SensorType[port_index] == self.SENSOR_TYPE.EV3_GYRO_ABS
              or self.SensorType[port_index] == self.SENSOR_TYPE.EV3_GYRO_DPS
              or self.SensorType[port_index] == self.SENSOR_TYPE.EV3_ULTRASONIC_CM
              or self.SensorType[port_index] == self.SENSOR_TYPE.EV3_ULTRASONIC_INCHES):
            outArray = [self.SPI_Address, message_type, 0, 0, 0, 0, 0, 0]
            reply = self.spi_transfer_array(outArray)
            if reply[3] == 0xA5:
                if reply[4] == self.SensorType[port_index]:
                    return reply[5]
                else:
                    raise SensorError("get_sensor error: Invalid sensor data")
            else:
                raise IOError("get_sensor error: No SPI response")

        elif (self.SensorType[port_index] == self.SENSOR_TYPE.EV3_COLOR_RAW_REFLECTED
              or self.SensorType[port_index] == self.SENSOR_TYPE.EV3_GYRO_ABS_DPS):
            outArray = [self.SPI_Address, message_type, 0, 0, 0, 0, 0, 0, 0, 0]
            reply = self.spi_transfer_array(outArray)
            if reply[3] == 0xA5:
                if reply[4] == self.SensorType[port_index]:
                    return reply[5]
                else:
                    raise SensorError("get_sensor error: Invalid sensor data")
            else:
                raise IOError("get_sensor error: No SPI response")

        elif self.SensorType[port_index] == self.SENSOR_TYPE.EV3_COLOR_COLOR_COMPONENTS:
            outArray = [self.SPI_Address, message_type, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            reply = self.spi_transfer_array(outArray)
            if reply[3] == 0xA5:
                if reply[4] == self.SensorType[port_index]:
                    return reply[5]
                else:
                    raise SensorError("get_sensor error: Invalid sensor data")
            else:
                raise IOError("get_sensor error: No SPI response")

        elif self.SensorType[port_index] == self.SENSOR_TYPE.EV3_INFRARED_SEEK:
            outArray = [self.SPI_Address, message_type, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            reply = self.spi_transfer_array(outArray)
            if reply[3] == 0xA5:
                if reply[4] == self.SensorType[port_index]:
                    return reply[5]
                else:
                    raise SensorError("get_sensor error: Invalid sensor data")
            else:
                raise IOError("get_sensor error: No SPI response")

        elif self.SensorType[port_index] == self.SENSOR_TYPE.EV3_INFRARED_REMOTE:
            outArray = [self.SPI_Address, message_type, 0, 0, 0, 0, 0, 0, 0, 0]
            reply = self.spi_transfer_array(outArray)
            if reply[3] == 0xA5:
                if reply[4] == self.SensorType[port_index]:
                    return reply[5]
                else:
                    raise SensorError("get_sensor error: Invalid sensor data")
            else:
                raise IOError("get_sensor error: No SPI response")

        raise IOError("get_sensor error: Sensor not configured or not supported.")


class Sensor:
    """
    Template Sensor class. Must implement set_mode(mode) to function.
    """
    class Status:
        VALID_DATA = "VALID_DATA"
        NOT_CONFIGURED = "NOT_CONFIGURED"
        CONFIGURING = "CONFIGURING"
        NO_DATA = "NO_DATA"
        I2C_ERROR = "I2C_ERROR"

    def __init__(self, port: Literal[1, 2, 3, 4]):
        "Initialize sensor with a given port (1, 2, 3, or 4)."
        self.brick = Brick()
        self.port = PORTS[str(port).upper()]

    def get_status(self):
        """
        Get the sensor status of this sensor.

        Return one of the following status messages:
        VALID_DATA
        NOT_CONFIGURED
        CONFIGURING
        NO_DATA
        I2C_ERROR
        """
        return SENSOR_CODES[self.brick.get_sensor_status(self.port)]

    def set_port(self, port: Literal[1, 2, 3, 4]):
        "Change sensor port number. Does not unassign previous port."
        try:
            self.port = PORTS[str(port).upper()]
            self.set_mode(self.mode)
        except SensorError as error:
            return error

    def get_value(self):
        "Get the sensor value. May return a float, int, list or None if error."
        try:
            return self.brick.get_sensor(self.port)
        except SensorError:
            return None

    def wait_ready(self):
        "Wait (pause program) until the sensor is initialized."
        while self.get_status() != Sensor.Status.VALID_DATA:
            pass


class TouchSensor(Sensor):
    """
    Basic touch sensor class. There is only one mode.
    Gives values 0 to 1, with 1 meaning the button is being pressed.
    """

    def __init__(self, port: Literal[1, 2, 3, 4], mode="touch"):
        """
        Initialize touch sensor with a given port number.
        mode does not need to be set and actually does nothing here.
        """
        super(TouchSensor, self).__init__(port)
        self.set_mode(mode)

    def set_mode(self, mode="touch"):
        """
        Touch sensor only has one mode, and does not require an input.
        This method is useless unless you wish to re-initialize the sensor.
        """
        try:
            self.mode = mode
            self.brick.set_sensor_type(self.port, BrickPi3.SENSOR_TYPE.TOUCH)
            return True
        except SensorError as error:
            return error

    def is_pressed(self) -> bool:
        "Return True if pressed, False otherwise."
        return self.brick.get_sensor(self.port) > 0


class EV3UltrasonicSensor(Sensor):
    """
    EV3 Ultrasonic Sensor. Default mode returns distance in centimeters (cm).

    Values given by modes:
    cm - centimeter measure (0 to 255)
    in - inches measure
    listen - 0 or 1, 1 means another ultrasonic sensor is detected
    """
    class Mode:
        "Mode for the EV3 Ultrasonic Sensor."
        CM = "cm"
        IN = "in"
        LISTEN = "listen"

    def __init__(self, port: Literal[1, 2, 3, 4], mode="cm"):
        super(EV3UltrasonicSensor, self).__init__(port)
        self.set_mode(mode)

    def set_mode(self, mode):
        """
        Set ultrasonic sensor mode. Return True if mode change successful.
        cm - centimeter measure (0 to 255)
        in - inches measure
        listen - 0 or 1, 1 means another ultrasonic sensor is detected
        """
        try:
            self.mode = mode
            if mode.lower() == self.Mode.CM:
                self.brick.set_sensor_type(self.port, BrickPi3.SENSOR_TYPE.EV3_ULTRASONIC_CM)
            elif mode.lower() == self.Mode.IN:
                self.brick.set_sensor_type(self.port, BrickPi3.SENSOR_TYPE.EV3_ULTRASONIC_INCHES)
            elif mode.lower() == self.Mode.LISTEN:
                self.brick.set_sensor_type(self.port, BrickPi3.SENSOR_TYPE.EV3_ULTRASONIC_LISTEN)
            else:
                return False
            return True
        except SensorError as error:
            return error


class EV3ColorSensor(Sensor):
    """
    EV3 Color Sensor. Default mode is "component".

    Values given by modes:
    component - give list of values [Red, Green, Blue, Unknown?]
    ambient - light off, detect any light
    red - red light on, detect red value only
    rawred - give list of values [Red, Unknown?]
    id - provide a single integer value based on the sensor's guess of detected color
    """
    class Mode:
        "Mode for the EV3 Color Sensor."
        COMPONENT = "component"
        AMBIENT = "ambient"
        RED = "red"
        RAW_RED = "rawred"
        ID = "id"

    def __init__(self, port, mode="component"):
        super(EV3ColorSensor, self).__init__(port)
        self.set_mode(mode)

    def set_mode(self, mode):
        """
        Sets color sensor mode. Return True if mode change successful.

        component - give list of values [Red, Green, Blue, Unknown?]
        ambient - light off, detect any light
        red - red light on, detect red value only
        rawred - give list of values [Red, Unknown?]
        id - provide a single integer value based on the sensor's guess of detected color
        """
        try:
            self.mode = mode
            if mode.lower() == self.Mode.COMPONENT:
                self.brick.set_sensor_type(self.port, BrickPi3.SENSOR_TYPE.EV3_COLOR_COLOR_COMPONENTS)
            elif mode.lower() == self.Mode.AMBIENT:
                self.brick.set_sensor_type(self.port, BrickPi3.SENSOR_TYPE.EV3_COLOR_AMBIENT)
            elif mode.lower() == self.Mode.RED:
                self.brick.set_sensor_type(self.port, BrickPi3.SENSOR_TYPE.EV3_COLOR_REFLECTED)
            elif mode.lower() == self.Mode.RAW_RED:
                self.brick.set_sensor_type(self.port, BrickPi3.SENSOR_TYPE.EV3_COLOR_RAW_REFLECTED)
            elif mode.lower() == self.Mode.ID:
                self.brick.set_sensor_type(self.port, BrickPi3.SENSOR_TYPE.EV3_COLOR_COLOR)
            else:
                return False
            return True
        except SensorError as error:
            return error

    def get_rgb(self) -> list[float]:
        "Return the RGB values from the sensor. This will switch the sensor to component mode."
        if self.mode != self.Mode.COMPONENT:
            self.set_mode(self.Mode.COMPONENT)
            self.wait_ready()
        return self.get_value()[:-1]

    def get_color(self) -> str:
        "Return the closest detected color by name. This will switch the sensor to id mode."
        if self.mode != self.Mode.ID:
            self.set_mode(self.Mode.ID)
            self.wait_ready()
        return _color_names_by_code.get(self.get_value(), Color.UNKNOWN)


class EV3GyroSensor(Sensor):
    """
    EV3 Gyro sensor. Default mode is "both".

    Values given by modes:
    abs - Absolute degrees rotated since start
    dps - Degrees per second of rotation
    both - list of [abs, dps] values
    """
    class Mode:
        "Mode for the EV3 Gyro Sensor."
        ABS = "abs"
        DPS = "dps"
        BOTH = "both"

    def __init__(self, port: Literal[1, 2, 3, 4], mode="both"):
        super(EV3GyroSensor, self).__init__(port)
        self.set_mode(mode)

    def set_mode(self, mode):
        """
        Change gyro sensor mode.

        abs - Absolute degrees rotated since start
        dps - Degrees per second of rotation
        both - list of [abs, dps] values
        """
        try:
            self.mode = mode
            if mode == self.Mode.ABS:
                self.brick.set_sensor_type(self.port, BrickPi3.SENSOR_TYPE.EV3_GYRO_ABS)
            elif mode == self.Mode.DPS:
                self.brick.set_sensor_type(self.port, BrickPi3.SENSOR_TYPE.EV3_GYRO_DPS)
            elif mode == self.Mode.BOTH:
                self.brick.set_sensor_type(self.port, BrickPi3.SENSOR_TYPE.EV3_GYRO_ABS_DPS)
            else:
                return True
        except SensorError as error:
            return error


class Motor:
    "Motor class for any motor."

    def __init__(self, port: Literal["A", "B", "C", "D"] | list[str]):
        """
        Initialize this Motor object with the ports "A", "B", "C", or "D".
        You may also provide a list of these ports such as ["A", "C"] to run
        both motors at the exact same time (exact combined behavior unknown).
        """
        self.brick = BP
        self.set_port(port)

    def set_port(self, port):
        """
        Port can be "A", "B", "C", or "D".
        You may also provide a list of these ports such as ["A", "C"] to run
        both motors at the exact same time (exact combined behavior unknown).
        """
        if isinstance(port, list):
            self.port = sum([PORTS[i] for i in port])
        elif isinstance(port, int) or isinstance(port, str):
            self.port = PORTS[str(port).upper()]

    def set_power(self, power):
        """
        Set the motor power in percent.

        Keyword arguments:
        power - The power from -100 to 100, or -128 for float
        """
        self.brick.set_motor_power(self.port, power)

    def float_motor(self):
        "Float the motor, which means let it rotate freely while measuring rotations."
        self.brick.set_motor_power(self.port, -128)

    def set_position(self, position):
        "Set the motor target position in degrees."
        self.brick.set_motor_position(self.port, position)

    def set_position_relative(self, degrees):
        "Set the relative motor target position in degrees, current position plus the specified degrees."
        self.brick.set_motor_position_relative(self.port, degrees)

    def set_position_kp(self, kp=25):
        """
        Set the motor target position KP constant.

        If you set kp higher, the motor will be more responsive to errors in position, at the cost of perhaps overshooting and oscillating.
        kd slows down the motor as it approaches the target, and helps to prevent overshoot.
        In general, if you increase kp, you should also increase kd to keep the motor from overshooting and oscillating.

        Keyword arguments:
        port - The motor port(s). PORT_A, PORT_B, PORT_C, and/or PORT_D.
        kp - The KP constant (default 25)
        """
        self.brick.set_motor_position_kp(self.port, kp)

    def set_position_kd(self, kd=70):
        """
        Set the motor target position KD constant.

        If you set kp higher, the motor will be more responsive to errors in position, at the cost of perhaps overshooting and oscillating.
        kd slows down the motor as it approaches the target, and helps to prevent overshoot.
        In general, if you increase kp, you should also increase kd to keep the motor from overshooting and oscillating.

        Keyword arguments:
        port - The motor port(s). PORT_A, PORT_B, PORT_C, and/or PORT_D.
        kd - The KD constant (default 70)
        """
        self.brick.set_motor_position_kd(self.port, kd)

    def set_dps(self, dps):
        """
        Set the motor target speed in degrees per second.

        Keyword arguments:
        port - The motor port(s). PORT_A, PORT_B, PORT_C, and/or PORT_D.
        dps - The target speed in degrees per second
        """
        self.brick.set_motor_dps(self.port, dps)

    def set_limits(self, power=0, dps=0):
        """
        Set the motor speed limit.

        Keyword arguments:
        port - The motor port(s). PORT_A, PORT_B, PORT_C, and/or PORT_D.
        power - The power limit in percent (0 to 100), with 0 being no limit (100)
        dps - The speed limit in degrees per second, with 0 being no limit
        """
        self.brick.set_motor_limits(self.port, power, dps)

    def get_status(self):
        """
        Read a motor status.

        Keyword arguments:
        port - The motor port (one at a time). PORT_A, PORT_B, PORT_C, or PORT_D.

        Returns a list:
            flags - 8-bits of bit-flags that indicate motor status:
                bit 0 - LOW_VOLTAGE_FLOAT - The motors are automatically disabled because the battery voltage is too low
                bit 1 - OVERLOADED - The motors aren't close to the target (applies to position control and dps speed control).
            power - the raw PWM power in percent (-100 to 100)
            encoder - The encoder position
            dps - The current speed in Degrees Per Second
        """
        self.brick.get_motor_status(self.port)

    def get_encoder(self):
        """
        Read a motor encoder in degrees.

        Keyword arguments:
        port - The motor port (one at a time). PORT_A, PORT_B, PORT_C, or PORT_D.

        Returns the encoder position in degrees
        """
        self.brick.get_motor_encoder(self.port)

    def offset_encoder(self, position):
        """
        Offset a motor encoder.

        Keyword arguments:
        port - The motor port(s). PORT_A, PORT_B, PORT_C, and/or PORT_D.
        offset - The encoder offset

        You can zero the encoder by offsetting it by the current position
        """
        self.brick.offset_motor_encoder(self.port, position)

    def reset_encoder(self):
        """
        Reset motor encoder(s) to 0.

        Keyword arguments:
        port - The motor port(s). PORT_A, PORT_B, PORT_C, and/or PORT_D.
        """
        self.brick.reset_motor_encoder(self.port)


def configure_ports(*,
                    PORT_1: Type[Sensor] = None,
                    PORT_2: Type[Sensor] = None,
                    PORT_3: Type[Sensor] = None,
                    PORT_4: Type[Sensor] = None,
                    PORT_A: Type[Motor] = None,
                    PORT_B: Type[Motor] = None,
                    PORT_C: Type[Motor] = None,
                    PORT_D: Type[Motor] = None,
                    wait: bool = True,
                    print_status: bool = True) -> Sensor | Motor | list[Sensor | Motor]:
    """
    Configure the ports to use the specified sensor or motor and return objects for each item,
    ordered by sensor ports followed by motor ports.

    When wait is True (the default), the function will wait for the sensors to be ready before returning.
    When print_status is True (the default), the function will print two messages, the first to let the user
    know to wait until the ports are configured, and the second to indicate the port configuration is complete.

    Example:

    TOUCH_SENSOR, COLOR_SENSOR, MOTOR = configure_ports(PORT_1=TouchSensor, PORT_3=EV3ColorSensor, PORT_A=Motor)
    """
    sensor_ports = [PORT_1, PORT_2, PORT_3, PORT_4]
    motor_ports = [PORT_A, PORT_B, PORT_C, PORT_D]
    is_single_device = False
    if (sensor_ports + motor_ports).count(None) == 7:  # if only one device configured
        is_single_device = True
    if print_status:
        print(f"Configuring port{'' if is_single_device else 's'}, please wait...")
    sensors: list[Sensor] = []
    motors: list[Motor] = []
    for n, sensor_type in enumerate(sensor_ports, 1):
        if sensor_type:
            sensor = sensor_type(n)
            if wait:
                if isinstance(sensor, (EV3UltrasonicSensor, EV3ColorSensor)):
                    sensor.wait_ready()
            if is_single_device:
                return sensor
            sensors.append(sensor)
    for letter, motor_type in zip("ABCD", motor_ports):
        if motor_type:
            if is_single_device:
                return motor_type(letter)
            motors.append(motor_type(letter))
    if print_status:
        print("Port configuration complete!")
    return sensors + motors


# Save process ID of this program so we can force stop it later if needed
os.system(f"echo {os.getpid()} > ~/brickpi3_pid")


def reset_brick(*args):
    "Reset BrickPi devices when program exits ('at exit')."
    BP.reset_all()


# Reset brick when the program exits
atexit.register(reset_brick)
signal.signal(signal.SIGTERM, reset_brick)
signal.signal(signal.SIGINT, reset_brick)  # Ctrl-C
