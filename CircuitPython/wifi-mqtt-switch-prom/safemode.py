# Sometimes a PicoW will get itself into a weird state saying
# "You pressed the reset button during boot." which is a button
# the PicoW doesn't have. This code resets it when it happens.

import microcontroller
import time

print("SAFEMODE: Waiting 10 seconds before restart.")
microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)
time.sleep(10)
microcontroller.reset()
