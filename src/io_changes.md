# Key Updates / Integrations (including new DECSTBM feature)

1. **ACS Characters**
   - Full single and double-line box-drawing characters.
   - Optional repeat.
   - Tokenized and handled in `echo()`.

2. **Commands**
   - `{cls}` now expands to `{erasedisplay:2}{home}`.
   - `{home}` = `{curpos:1,1}`.
   - `CURPOS` supports kwargs or positional args.
   - `{f6}` = hard newline (for word wrap).
   - `{var:<name>}` and `{<name>}` = runtime variables.
   - `{rgb}` supports `#RRGGBB`, `R,G,B` triplets, optional `fg/bg`.
   - **New:** `{decstbm:top,bottom}` = DECSTBM, sets the top and bottom margin, 1-based.
   - **CUP (Cursor Position)** — `ESC [ row ; col H` or `ESC [ row ; col f`  
	Sets the cursor to the absolute position (row, col).  
	Uses 1-based indexing.  
   - **CUU (Cursor Up)** — `ESC [ n A`  
	Moves the cursor *up* by *n* rows (relative).  

   - **CUD (Cursor Down)** — `ESC [ n B`  
	Moves the cursor *down* by *n* rows (relative).  

   - **CUF (Cursor Forward)** — `ESC [ n C`  
        Moves the cursor *right* by *n* columns (relative).  

   - **CUB (Cursor Backward)** — `ESC [ n D`  
        Moves the cursor *left* by *n* columns (relative).  

   - **DECSTBM (Set Top and Bottom Margins)** — `ESC [ top ; bottom r`  
	Sets the vertical scrolling region (top and bottom margins).  
	Uses 1-based indexing.  

   - **ED (Erase in Display)** — `ESC [ n J`  
	Clears part or all of the screen depending on `n`.  

   - **EL (Erase in Line)** — `ESC [ n K`  
	Clears part or all of the current line depending on `n`.  

   - **DSR (Device Status Report)** — `ESC [ 6 n`  
	Reports the current cursor position as `ESC [ row ; col R`.  

3. **Colors**
   - Two palettes: ANSI and C64.
   - Background colors `{bgred}`, `{bgyellow}`, etc.
   - Aliases map cleanly to commands.
   - `set_palette()` allows runtime switching.

4. **Word Wrap**
   - Maintains cursor position across lines.
   - Hard newline `{f6}` respected.
   - Markdown-style attributes (`**bold**`, `*italic*`, `__underline__`).

5. **Tokenizer**
   - `Token = namedtuple("Token", ["kind","value","args","kwargs","raw"])`
   - `kind` includes `WORD`, `WHITESPACE`, `F6`, `CURSOR`, `COLOR`, `DECSTBM`, etc.
   - `args` is always a sequence; `kwargs` added for optional named parameters.
   - Recursive command expansion supported.

6. **echo() / echo_file()**
   - Preserves cursor position and attributes across calls.
   - Word wrap logic integrated with `{f6}`.
   - Supports raw mode and runtime variables.
   - `echo_file()` supports custom more prompts and paging with command tokens.

7. **Palette Switching**
   - Runtime selection between ANSI and C64 palettes.
   - RGB commands evaluated according to selected palette.
   - Light colors mapped explicitly in C64 palette.

8. **Integration Notes**
   - Commands are case-insensitive.
   - `{cls}` yields `{erasedisplay:2}{home}`.
   - `{decstbm:top,bottom}` emits `\033[<top>;<bottom>r`.
   - Markdown attributes (`**bold**`, `*italic*`, `__underline__`) converted to ANSI sequences.
