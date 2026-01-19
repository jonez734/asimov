# io_demo.md

{reset}Welcome, {var:player}! Your score is {var:score}.{f6}

## C64 Palette Colors

{red}Red{reset} {green}Green{reset} {blue}Blue{reset} {yellow}Yellow{reset} {lightcyan}Light Cyan{reset}{f6}

## ANSI Palette Colors (via {{rgb}} command)

{rgb:fg:#FF00FF}Magenta text{reset} {rgb:bg:#00FFFF}on cyan background{reset}{f6}

## ACS Characters (box drawing)

{acs:ulcorner}{acs:hline:5}{acs:urcorner}{f6}
{acs:vline} Hello {acs:vline}{f6}
{acs:llcorner}{acs:hline:5}{acs:lrcorner}{f6}

## Cursor and Screen Control

{cls}Screen cleared, cursor at home.{f6}

{curpos:10,5}This is at row 10, column 5.{f6}
{cup:3}Move up 3 rows{f6}
{cud:2}Move down 2 rows{f6}
{cuf:4}Move forward 4 columns{f6}
{cub:4}Move back 4 columns{f6}

{erasedisplay:2}Erase entire display{f6}
{el:0}Erase to start of line{f6}
{el:1}Erase to end of line{f6}
{el:2}Erase entire line{f6}
{decstbm:5,20}Set top/bottom margin (rows 5-20){f6}

## Hard Newlines

This is the first line.{f6}
This is the second line using {f6}.{f6}

## Runtime Variables

Hello, {var:player}! Your score is {var:score}.{f6}

## Raw Mode / Literal Braces

{{This is literal braces, not a command}}{f6}

## Word Wrap Demo

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.{f6}
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.{f6}
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.{f6}
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.{f6}
