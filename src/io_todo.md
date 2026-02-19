# future
- better {reset} comand (color, decstbm, attr, all)

- header() broken
  * cosmetic only
  * there is a hack in echo such that if there is an {f6} followed by a
    space, the space is eaten. 
  * this makes the header offset by a space for the 2nd and third lines
  * "fixed" by removing the {f6} and replacing it with end="\n"

