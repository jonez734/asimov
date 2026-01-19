from asimov.io import echo, rendered_length

prompt = f"{{yellow}}prompt here> {{green}}"
echo(f"{rendered_length(prompt)=}")
