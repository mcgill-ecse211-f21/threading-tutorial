#!/usr/bin/env python3

"""
Simple examples of using threads and sampling rates in the context of the BrickPi3.
"""

from collections import deque
from statistics import mean
from time import time, sleep
from threading import Thread
from types import FunctionType

from utils.brick import EV3ColorSensor, EV3UltrasonicSensor, Sensor, configure_ports


US_SENSOR, COLOR_SENSOR = configure_ports(PORT_1=EV3UltrasonicSensor, PORT_2=EV3ColorSensor)

print_red = lambda text: print(f"\033[91m{text}\033[0m")
print_green = lambda text: print(f"\033[92m{text}\033[0m")


def determine_max_sensor_sample_rate(sensor: Sensor):
    """
    Determine the maximum sample rate of the given sensor in Hz. Do this by sampling the sensor at
    a known rate of 1 Hz (1 sample per second) and then continuously increasing the sample rate,
    by halving the sleep time, until the number of reads no longer increases.
    """
    DEQUE_LEN = 10
    sensor_name = sensor.__class__.__name__
    log: FunctionType = print_red if sensor_name == EV3UltrasonicSensor.__name__ else print_green
    all_num_reads = deque(maxlen=DEQUE_LEN)  # double-ended queue, FIFO (first-in-first-out)
    num_reads = 0
    sleep_time = sr_timeout = 1  # second
    sr_start = time()
    
    while True:
        log(f"{sensor_name}: Using {sleep_time = }")
        log(f"{sensor_name}: Number of readings: {num_reads}")
        num_reads = 0
        while time() - sr_start < sr_timeout:
            sensor.get_value()
            num_reads += 1
            sleep(sleep_time)
        sleep_time /= 2
        sr_start = time()
        all_num_reads.append(num_reads)
        avg_num_reads = mean(all_num_reads)
        if num_reads < avg_num_reads:
            text = f"{sensor_name} max sample rate: {avg_num_reads}"
            log(f"\n{(eqs := len(text) * '=')}\n{text}\n{eqs}\n\n")
            break


def determine_max_sensor_sample_rate_multithreaded():
    """
    Determine the maximum sample rate of both sensors in Hz. Do this by sampling the sensors,
    each in their own thread, at a known rate of 1 Hz (1 sample per second) and then continuously
    increasing the sample rate, by halving the sleep time, until the number of reads no longer increases.
    """
    for sensor in (US_SENSOR, COLOR_SENSOR):
        # the lambda here means that the entire function invocation is first passed to run_in_background() and then run
        run_in_background(lambda: determine_max_sensor_sample_rate(sensor))


def run_in_background(action: FunctionType):
    "Use to run an action (a function) in the background."
    return Thread(target=action).start()


if __name__ == "__main__":
    print("Determining max sensor sample rates using a single thread")
    for sensor in (US_SENSOR, COLOR_SENSOR):
        determine_max_sensor_sample_rate(sensor)
    sleep(2)
    print("Determining max sensor sample rates using multiple threads")
    determine_max_sensor_sample_rate_multithreaded()
