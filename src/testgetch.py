import sys
import termios
import tty

ESC = '\x1B'

fd = sys.stdin.fileno()
old = termios.tcgetattr(fd)
tty.setraw(fd)
try:
    while True:
        b = sys.stdin.read(1)
        print(repr(b))
        if b == '\x03':
            raise KeyboardInterrupt
        elif b == '\x04':
            raise EOFError
finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old)
