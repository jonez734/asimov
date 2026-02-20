#!/usr/bin/env python3
# io_demo.py - demo for io.py features

from asimov import io  # assuming io.py is in asimov/ package

def main():
    # Set some runtime variables
#    io.set_var("player", "Alice Cooper Is Amazing")
#    io.set_var("score", "42")
#    io.set_var("testvar", "73")

    # Set palette to C64 for demo (you can switch to ANSI)
    io.set_palette("c64")

    # Sample markdown file path
    sample_path = "io_demo_invalidcommandbug.md"

#    print(io.get_cursor_position())
    # Print demo: interpreted
#    io.echo("\n--- Raw Output ---\n")
#    io.echo_file(sample_path, raw=True)
    io.echo("{f6:2}-- interpreted output --{f6:2}")
    io.echo_file(sample_path, raw=False, wordwrap=True, end="")
#    # Print demo: raw
#    print("\n--- Raw Output ---\n")
#    io.echo_file(sample_path, raw=True)

if __name__ == "__main__":
    main()
