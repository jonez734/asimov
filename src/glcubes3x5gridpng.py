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
from PIL import Image


def get_default_card_paths(n=15, basedir="../cards"):
    """Generate paths for n unique cards from a standard deck."""
    deck = list(product(RANKS, SUITS))
    return [get_card_path(rank, suit, basedir=basedir) for rank, suit in deck[:n]]


def main(image_paths, side_image, n_cubes=15, spacing=1.2, width=800, height=600):
    if not glfw.init():
        return

    window = glfw.create_window(width, height, "Textured Cube Stack", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)
    glEnable(GL_DEPTH_TEST)

    shader = render.create_shader(render.VERTEX_SHADER, render.FRAGMENT_SHADER)
    projection = pyrr.matrix44.create_orthogonal_projection_matrix(-2, 2, -2, 2, 0.1, 10)
    glUseProgram(shader)
    proj_loc = glGetUniformLocation(shader, "projection")
    model_loc = glGetUniformLocation(shader, "model")
    glUniformMatrix4fv(proj_loc, 1, GL_FALSE, projection)

    cubes = []
    image_cycle = cycle(image_paths)

    first_image = Image.open(image_paths[0])
    aspect_ratio = first_image.width / first_image.height

    cols = 3
    for i in range(n_cubes):
        row, col = divmod(i, cols)
        vao, count = render.create_cube(aspect_ratio=aspect_ratio)
        cubes.append((vao, count, render.load_texture(next(image_cycle))))

    side_texture = render.load_texture(side_image)

    while not glfw.window_should_close(window):
        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            break

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        for index, (vao, count, texture) in enumerate(cubes):
            row, col = divmod(index, cols)
            model = pyrr.matrix44.create_from_translation(
                [(col - 1) * spacing, (2 - row) * spacing, -5]
            )
            glUniformMatrix4fv(model_loc, 1, GL_FALSE, model)

            glBindTexture(GL_TEXTURE_2D, texture)
            glBindVertexArray(vao)
            glDrawElements(GL_TRIANGLES, count, GL_UNSIGNED_INT, None)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()


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
    parser.add_argument(
        "--width",
        type=int,
        default=1200,
        help="Window width (default: 1200)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=900,
        help="Window height (default: 900)",
    )
    args = parser.parse_args()

    if args.image:
        image_paths = [args.image] * args.cubes
    elif args.cardpath:
        image_paths = args.cardpath
    else:
        image_paths = get_default_card_paths(args.cubes, basedir=args.carddir)

    main(image_paths, args.side, n_cubes=args.cubes, spacing=args.spacing,
         width=args.width, height=args.height)
