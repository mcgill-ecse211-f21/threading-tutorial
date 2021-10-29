# ECSE211 Threading and Sampling Rates Tutorial

In this tutorial, we will cover the concepts of threading and sampling rates
in the context of the BrickPi.

## ⏲️ Sampling rate

Sampling is the selection of discrete data points, known as samples,
from a continuous signal at regular intervals.
The **sampling rate**, also known as the **sampling frequency**,
is the **number of samples per second**,
measured in Hertz (Hz), which is equal to 1/s.
The higher this number, the smaller the interval (period) between two
consecutive samples.

To set the sampling rate for a sensor, we `sleep()` for the interval
before requesting another sample.
This is done like this:

```python
while True:
    sensor_reading = sensor.get_value()
    # do something with sensor_reading
    sleep(sleep_time)
```

In practice, every sensor has a maximum sampling rate it cannot exceed.
After a certain threshold, decreasing the sleep time will no longer
yield more values per interval.
In this tutorial, we calculate this threshold for the ultrasonic and
color sensors.

## 🧵 Threads

A **thread** allows an action (ie, a piece of code like a function)
to run in the background.
This allows more than one action to happen at the same time.

**Example 1:**

A 2-wheeled robot uses threads to collect ultrasonic and color data
in the background and run the main application code in the foreground,
also known as the main thread.
The latter uses the data gathered from the background threads in its own
operations, eg, to avoid obstacles.

**Example 2:**

The [`deploy_to_robot`](deploy_to_robot.py#L119) module has a simple
user interface (UI) that uses threads to perform actions in the background.
When a button (eg, "Reset Robot") is pressed, a new thread is started
and the action associated with the button takes place in the background.
If it happened in the foreground (main thread), the UI would be unresponsive
until the action completes, which could take a long time!

In both cases, the `run_in_background()` function is used to specify the action
that should take place. Alternatively, we can write

```python
Thread(target=action).start()
```

where `action` is a `FunctionType` that has already been defined or a
lambda (anonymous) function.

## ❓ Questions

1. What is the sampling rate corresponding to a sleep time of 1ms?
2. How many threads can we run at once on the BrickPi?
3. What happens if there are too many threads?
4. How do we stop a thread once we no longer need it to run in the background?
