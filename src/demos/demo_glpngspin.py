import ctypes

import glfw
import numpy as np
import pyrr
from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_ELEMENT_ARRAY_BUFFER,
    GL_FALSE,
    GL_FLOAT,
    GL_FRAGMENT_SHADER,
    GL_LINEAR,
    GL_RGBA,
    GL_STATIC_DRAW,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_REPEAT,
    GL_TRIANGLES,
    GL_UNSIGNED_BYTE,
    GL_UNSIGNED_INT,
    GL_VERTEX_SHADER,
    glBindBuffer,
    glBindTexture,
    glBindVertexArray,
    glBufferData,
    glClear,
    glDrawElements,
    glEnable,
    glEnableVertexAttribArray,
    glGenerateMipmap,
    glGenBuffers,
    glGenTextures,
    glGenVertexArrays,
    glGetUniformLocation,
    glTexImage2D,
    glTexParameteri,
    glUniformMatrix4fv,
    glUseProgram,
    glVertexAttribPointer,
)
import OpenGL.GL.shaders
from PIL import Image

def load_texture(image_path):
    image = Image.open(image_path)
    image = image.transpose(Image.FLIP_TOP_BOTTOM)
    img_data = np.array(image, dtype=np.uint8)
    
    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.width, image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    glGenerateMipmap(GL_TEXTURE_2D)
    
    return texture

def create_shader():
    vertex_shader = """
    #version 330 core
    layout (location = 0) in vec3 position;
    layout (location = 1) in vec2 texCoord;
    
    uniform mat4 model;
    uniform mat4 projection;
    
    out vec2 TexCoord;
    
    void main()
    {
        gl_Position = projection * model * vec4(position, 1.0);
        TexCoord = texCoord;
    }
    """
    
    fragment_shader = """
    #version 330 core
    in vec2 TexCoord;
    out vec4 color;
    
    uniform sampler2D texture1;
    
    void main()
    {
        color = texture(texture1, TexCoord);
    }
    """
    
    shader = OpenGL.GL.shaders.compileProgram(
        OpenGL.GL.shaders.compileShader(vertex_shader, GL_VERTEX_SHADER),
        OpenGL.GL.shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER)
    )
    
    return shader

def create_cube():
    vertices = [
        # Positions         # Texture Coords
        -0.5, -0.5, -0.5,  0.0, 0.0,
         0.5, -0.5, -0.5,  1.0, 0.0,
         0.5,  0.5, -0.5,  1.0, 1.0,
        -0.5,  0.5, -0.5,  0.0, 1.0,
    ]
    vertices = np.array(vertices, dtype=np.float32)
    
    indices = [0, 1, 2, 2, 3, 0]
    indices = np.array(indices, dtype=np.uint32)
    
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)
    
    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
    
    ebo = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
    
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * vertices.itemsize, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * vertices.itemsize, ctypes.c_void_p(3 * vertices.itemsize))
    glEnableVertexAttribArray(1)
    
    return vao, len(indices)

def main(image_path):
    if not glfw.init():
        return
    
    window = glfw.create_window(800, 600, "Textured Cube", None, None)
    if not window:
        glfw.terminate()
        return
    
    glfw.make_context_current(window)
    glEnable(GL_DEPTH_TEST)
    
    vao, count = create_cube()
    texture = load_texture(image_path)
    shader = create_shader()
    
    projection = pyrr.matrix44.create_perspective_projection_matrix(45, 800/600, 0.1, 10.0)
    model = pyrr.matrix44.create_identity()
    
    angle = 0.0
    rotation_speed = 1.5
    
    glUseProgram(shader)
    proj_loc = glGetUniformLocation(shader, "projection")
    model_loc = glGetUniformLocation(shader, "model")
    glUniformMatrix4fv(proj_loc, 1, GL_FALSE, projection)
    
    while not glfw.window_should_close(window):
        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            break
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        model = pyrr.matrix44.create_from_eulers([angle, angle, angle])
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, model)
        
        glBindTexture(GL_TEXTURE_2D, texture)
        glBindVertexArray(vao)
        glDrawElements(GL_TRIANGLES, count, GL_UNSIGNED_INT, None)
        
        angle += rotation_speed * 0.01
        
        glfw.swap_buffers(window)
        glfw.poll_events()
    
    glfw.terminate()

if __name__ == "__main__":
    main("/home/jam/projects/playingcarddata/sets/bicycle/3_of_clubs.png")
