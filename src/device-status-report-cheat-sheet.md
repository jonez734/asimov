# Device Status Report (DSR) Cheat-Sheet

## Standard DSR

| Query       | Response              | Official Name                              | Notes                  |
|-------------|-----------------------|--------------------------------------------|------------------------|
| `CSI 5 n`   | `CSI 0 n`             | Device Status Report — Status              | Reports "OK"           |
| `CSI 6 n`   | `CSI <row>;<col> R`   | Device Status Report — Cursor Position     | Also called **CPR**    |

## DEC Private DSR

| Query        | Response                  | Official Name                                  | Notes                                     |
|--------------|---------------------------|-----------------------------------------------|-------------------------------------------|
| `CSI ? 6 n`  | `CSI <row>;<col> R`       | DECXCPR — Extended Cursor Position Report      | VT100/VT220 extension                     |
| `CSI ? 15 n` | `CSI ? 10 n` / `? 11 n`   | Device Status Report — Printer Status          | `?10n` = not connected, `?11n` = ready    |
| `CSI ? 25 n` | `CSI ? 20 n` / `? 21 n`   | Device Status Report — UDK (User Defined Keys) | `?20n` = locked, `?21n` = unlocked        |
| `CSI ? 26 n` | `CSI ? 27;<id> n`         | Device Status Report — Keyboard Status         | `<id>` varies by terminal                 |
| `CSI ? 55 n` | `CSI ? 53 n` / `? 54 n`   | Device Status Report — Macro Space             | `?53n` = no memory, `?54n` = enough memory|
| `CSI ? 56 n` | Implementation dependent  | Device Status Report — Locator Device Status   | DEC locator/mouse extensions               |
