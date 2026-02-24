# asimov/main_udp.py

import warnings
warnings.warn(
    "asimov.main_udp is deprecated and unused. It will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

import time
import threading
from multiprocessing import Event, Process

import cv2

from . import lib as libasimov, conf, net

from bbsengine6 import io

MODULES = {
    "cap": { "upstreamaddr": None, "upstream": None, "downstreamaddr": None, "downstream": None },
#    "render_imshow": {"senderaddr": (127.0.0.1, 4300), "receiveraddr": ("127.0.0.1", 4200)},
}

def main(args, **kwargs):
    stop_e = Event()

    try:
        io.echo("Starting main application...")

        # Create processes
        for name, data in MODULES.items():
            print(f"{name=}")
            if data["downstreamaddr"] is not None:
                data["downstream"] = net.UDPSender(data["downstreamaddr"][0], data["downstreamaddr"][1])

            if data["upstreamaddr"] is not None:
                 data["upstream"] = net.UDPReceiver(data["upstreamaddr"][0], data["upstreamaddr"][1], blocking=False)

            m = libasimov.loadmodule(args, name,)
            p = Process(target=m.main,  args=(args, data["downstream"], data["upstream"], stop_e), kwargs=kwargs, name=name)
            # print(f"{p=}")
            data["proc"] = p
            p.start()

        io.echo("All processes started. Close the OpenGL window or press 'q' to quit.")
#        for name, data in MODULES.items():
#            data["proc"].join()
        
    finally:
        # cap.release()
        # cv2.destroyAllWindows()
        MODULES["cap"]["downstream"].send_eos()
        for name, data in MODULES.items():
            p = data.get("proc", None)
            if p is None:
                continue

            if p.is_alive(): # Only join if it's still running
                io.echo(f"Waiting for {p.name} to terminate...")
                p.join(timeout=5) # Give it a timeout in case it's truly stuck
                if p.is_alive():
                    io.echo(f"Warning: {p.name} did not terminate cleanly. Terminating forcefully.")
                    p.terminate() # Forceful termination as a last resort
                    p.join() # Wait for termination
                    exit_code = 1 # Indicate an error in shutdown
        
#            if data["downstream"] is not None:
#                data["downstram"].send_eos()
#                data["downstream"].close()
            if data["upstream"] is not None:
                data["upstream"].close()
        
def init(args=None, **kwargs):
    """
    Initializes any necessary components for the module.
    :param args: Placeholder for command-line arguments.
    :param kwargs: Additional keyword arguments.
    :return: True if initialization is successful, False otherwise.
    """
    io.echo("Module init() called.")
    # No specific initialization needed here for this example,
    # as multiprocessing components are set up in main().
    return True

def access(args=None, op=None, **kwargs):
    """
    Provides a generic access point for operations.
    :param args: Placeholder for command-line arguments or other data.
    :param op: The operation to perform (e.g., 'start', 'stop').
    :param kwargs: Additional keyword arguments.
    :return: True if operation is successful, False otherwise.
    """
    return True

def buildargs(args=None, **kwargs):
    """
    Builds and returns arguments, typically for a command-line parser.
    :param args: Placeholder for initial arguments.
    :param kwargs: Additional keyword arguments.
    :return: An object containing arguments, or None if not applicable.
    """
    io.echo("Module buildargs() called.")
    # In a real scenario, this might return an argparse.ArgumentParser instance
    # or parse default arguments.
    return None
