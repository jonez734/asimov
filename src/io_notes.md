- echo uses "yield from ..." (python 3.3+)
- if a command does snot exist, the raw input is displayed (ray)
- small atomic functions which do things like read and write from a stream
  * read_current_input_stream() calls _read_current_input_stream after acquiring the _current_stream_lock
  * write_current_output_stream() calls _write_current_input_stream
- {/bgcolor} command, applies only to ansi palette
- multple named color palettes
- runtime variables
- skin - promptcolor, valuecolor, inputcolor, etc implemented as echo runtime variables
- echo commands have positional and keyword args: {foo bing,1,2,3 baz=True}
- Token dataclass
- echo raw mode
- inputstring uses raw mode when displaying the buffer
- {reset}
  * color (default)
  * stbm
- {savecursor}
  * cur_x
  * cur_y
  * color_fg
  * color_bg
  