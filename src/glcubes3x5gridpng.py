import argparse
import glfw
from itertools import cycle
from OpenGL.GL import *
import numpy as np
import pyrr
import sys
sys.path.insert(0, '/home/jam/projects/asimov/src')
from asimov import render


def main(image_paths, side_image, n_cubes=15, spacing=1.2):
    if not glfw.init():
        return

    window = glfw.create_window(800, 600, "Textured Cube Stack", None, None)
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
    cols = 3
    for i in range(n_cubes):
        row, col = divmod(i, cols)
        vao, count = render.create_cube()
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
        nargs="+",
        default=[
            "../cards/10_of_clubs.png", "../cards/10_of_hearts.png", "../cards/10_of_spades.png",
            "../cards/2_of_clubs.png", "../cards/3_of_clubs.png", "../cards/4_of_clubs.png",
            "../cards/5_of_clubs.png", "../cards/6_of_clubs.png", "../cards/7_of_clubs.png",
            "../cards/8_of_clubs.png", "../cards/9_of_clubs.png", "../cards/ace_of_clubs.png",
            "../cards/jack_of_clubs.png", "../cards/king_of_clubs.png", "../cards/queen_of_clubs.png",
        ],
        help="Path to card image(s). Can be a single file or multiple files. "
             "If fewer than --cubes, cycles through the list.",
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
    args = parser.parse_args()

    if args.image:
        image_paths = [args.image] * args.cubes
    else:
        image_paths = args.cardpath

    main(image_paths, args.side, n_cubes=args.cubes, spacing=args.spacing)
