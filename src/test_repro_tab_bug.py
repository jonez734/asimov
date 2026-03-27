import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock dependencies
sys.modules["asimov.io.terminal"] = MagicMock()
sys.modules["asimov.io.echo"] = MagicMock()
sys.modules["asimov.io.getch"] = MagicMock()
sys.modules["asimov.io.common"] = MagicMock()
sys.modules["asimov.io.util"] = MagicMock()

# Configure mocks
sys.modules["asimov.io.terminal"].columns.return_value = 80
sys.modules["asimov.io.echo"].echo = MagicMock()
sys.modules["asimov.io.echo"].rendered_length = lambda x: len(x)
sys.modules["asimov.io.common"].get_cursor_position.return_value = (0, 0)
sys.modules["asimov.io.common"]._current_stream_lock = MagicMock()
sys.modules["asimov.io.common"]._current_stream_lock.__enter__ = MagicMock()
sys.modules["asimov.io.common"]._current_stream_lock.__exit__ = MagicMock()
sys.modules["asimov.io.common"]._terminal_state = MagicMock()

from asimov.io.inputstring import inputstring


class TestInputString(unittest.TestCase):
    def test_tab_ctrl_u_tab(self):
        # Setup completer
        COMPLETIONS = ["apple", "banana", "cherry"]

        def my_completer(prefix, **kwargs):
            if not prefix:
                return COMPLETIONS
            return [c for c in COMPLETIONS if c.startswith(prefix)]

        # Mock getch sequence:
        # 1. 'a'
        # 2. TAB (complete to 'apple' or show list?) -> 'a' matches 'apple'. Single match? No, 'apple'
        #    Wait, 'a' matches 'apple'. 'banana' doesn't. 'cherry' doesn't.
        #    So 'a' -> ['apple']. Autocomplete to 'apple'.
        # 3. KEY_CUTTOBOL (Ctrl+U)
        # 4. TAB (should show all matches)
        # 5. ENTER (finish)

        # NOTE: KEY_CUTTOBOL is mapped in inputstring.KEY_ACTIONS.
        # We need to make sure we use the key string that is in KEY_ACTIONS.
        # We assume KEY_CUTTOBOL string is "KEY_CUTTOBOL" or whatever getch returns.
        # In inputstring.py: add_key_mapping("KEY_CUTTOBOL", handle_cuttobol)

        keys = iter(["a", "KEY_TAB", "KEY_CUTTOBOL", "KEY_TAB", "KEY_ENTER"])

        def mock_getch(timeout=None):
            try:
                return next(keys)
            except StopIteration:
                return "KEY_ENTER"  # Safety

        with patch("asimov.io.inputstring.getch", side_effect=mock_getch):
            # We also need to mock print_matches to verify it was called
            with patch("asimov.io.inputstring.print_matches") as mock_print:
                # We also need to mock redraw_line because print_matches calls echo which is mocked, but redraw_line
                # calls echo too.
                with patch("asimov.io.inputstring.redraw_line"):
                    result = inputstring("Prompt: ", completer=my_completer)

                # Check calls
                # First TAB: 'a' -> 'apple'. Auto-complete. No print_matches.
                # Ctrl+U: Buffer cleared.
                # Second TAB: Buffer empty. Matches all. Should print_matches.

                print("\nCalls to print_matches:", mock_print.call_count)
                if mock_print.call_count > 0:
                    print("print_matches called with:", mock_print.call_args)

                # Verify result is empty string (since we Ctrl+U then Tab (show matches) then Enter)
                self.assertEqual(result, "")

                # Verify print_matches was called once (for the second tab)
                # If bug exists, this might fail or check might fail
                # Actually, the user says "I do not get the complete list of items".
                # This suggests print_matches is NOT called, or called with subset?
                # If buffer is cleared, prefix is empty. Completer returns all.
                # If print_matches is not called, maybe tab logic thinks nothing changed?

                # The issue is likely `last_matches` state.
                # When TAB happens, `last_matches` is updated.
                # When Ctrl+U happens, `last_matches` is NOT cleared?
                # Wait, KEY_CUTTOBOL handler returns (buffer, 0, 0).
                # In inputstring loop:
                # elif ch in KEY_ACTIONS:
                #    result = KEY_ACTIONS[ch](...)
                #    buffer, curpos, scroll_offset = result
                #    last_matches = []  <-- THIS CLEARS last_matches!
                #    tab_count = 0

                # So last_matches IS cleared.

                # Let's run the test to see.

                if mock_print.call_count == 0:
                    print("FAIL: print_matches not called")
                else:
                    args, _ = mock_print.call_args
                    print("Matches printed:", args[0])
                    if args[0] != COMPLETIONS:
                        print("FAIL: printed matches != COMPLETIONS")


if __name__ == "__main__":
    unittest.main()
