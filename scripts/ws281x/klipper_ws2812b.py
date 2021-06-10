#!/usr/bin/env python3

from rpi_ws281x import PixelStrip, Color
import argparse

# LED strip configuration:
LED_COUNT = 7        # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-r", "--red",
        metavar="r", nargs="+",
        help= """Red Color 0-255"""
    )

    parser.add_argument(
        "-g", "--green",
        metavar="g", nargs="+",
        help= """Green Color 0-255"""
    )

    parser.add_argument(
        "-b", "--blue",
        metavar="b", nargs="+",
        help= """Blue Color 0-255"""
    )

    parser.add_argument(
        "-v", "--value",
        metavar="v", nargs="+",
        help= """Value for brightness 0-255"""
    )

    args = parser.parse_args()

    if args.red is not None:
        red = int(args.red[0])
    else:
        red = 0

    if args.green is not None:
        green = int(args.green[0])
    else:
        green = 0

    if args.blue is not None:
        blue = int(args.blue[0])
    else:
        blue = 0

    if args.value is not None:
        brightness = int(args.value[0])
    else:
        brightness = 255

    print("Red: {} Green: {} Blue: {} Brightness: {}".format(red, green, blue, brightness))

    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, brightness, LED_CHANNEL)
    strip.begin()

    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(red, green, blue))
        strip.show()

