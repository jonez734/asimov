# recursive expansion for aliases/compound commands
for sub_tok in _handle_command(tok, palette=palette, vars=vars):
	yield sub_tok

