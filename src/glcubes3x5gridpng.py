import argparse
import glfw
from itertools import cycle, product
from OpenGL.GL import *
import numpy as np
import pyrr
import sys
sys.path.insert(0, '/home/jam/projects/asimov/src')
from asimov import render
from asimov.playingcard.cards import RANKS, SUITS, get_card_path


def get_default_card_paths(n=15, basedir="../cards"):
    """Generate paths for n unique cards from a standard deck."""
    deck = list(product(RANKS, SUITS))
    return [get_card_path(rank, suit, basedir=basedir) for rank, suit in deck[:n]]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render textured cube grid")
    parser.add_argument(
        "--cubes",
        type=int,
        default=15,
        help="Number of cubes to render (default: 15)",
    )
    parser.add_argument(
        "--image",
        default=None,
        help="Single image file to apply to all faces. Overrides --cardpath.",
    )
    parser.add_argument(
        "--cardpath",
        nargs="*",
        default=None,
        help="Path to card image(s). Can be a single file or multiple files. "
             "If fewer than --cubes, cycles through the list. "
             "Default: 15 unique cards from a standard deck.",
    )
    parser.add_argument(
        "--side",
        default="../640x480-solidwhite.png",
        help="Path to side texture image",
    )
    parser.add_argument(
        "--spacing",
        type=float,
        default=1.2,
        help="Spacing between cubes",
    )
    parser.add_argument(
        "--carddir",
        default="../cards",
        help="Base directory for card images (default: ../cards)",
    )
    args = parser.parse_args()

    if args.image:
        image_paths = [args.image] * args.cubes
    elif args.cardpath:
        image_paths = args.cardpath
    else:
        image_paths = get_default_card_paths(args.cubes, basedir=args.carddir)

    main(image_paths, args.side, n_cubes=args.cubes, spacing=args.spacing)
