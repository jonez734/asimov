        elif token.kind == "COMMAND":
            # handle F6 separately
            print(f"echo_iter.100: {tok.value=}")
            if token.value.lower().startswith("{f6"):
                yield Token(kind="F6", value="{f6}", args=[repeat], raw=token.raw, text="\n"*int(repeat), repeat=repeat)
                x = 0
            else:
                # all other commands yield as-is
                # recursive expansion for aliases/compound commands
                for sub_token in _handle_command(tok, palette=palette, vars=vars):
                    yield sub_token
                # update x if command affects cursor horizontally
                if token.value.lower().startswith("{cha") or token.value.lower().startswith("{curpos"):
                    # simple heuristic: reset x if absolute positioning
                    x = 0
