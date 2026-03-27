import os
import tempfile

from gtts import gTTS

from bbsengine6 import io


def speak(text: str) -> bool:
    munged = text.replace(" ", "-")
    filename = f"{munged}.mp3"
    fn, ext = os.path.splitext(filename)
    tts = gTTS(text=text, lang="en", slow=True)
    tts.save(f"{fn}.mp3")
    f = tempfile.TemporaryFile()
    tts.write_to_fp(f)
    f.close()
    os.system(f"ffmpeg -y -i {fn}.mp3 {fn}.ogg")
    os.system(f"ffplay -autoexit -nodisp {fn}.ogg")


if __name__ == "__main__":
    text = io.inputstring("text: ", "greetings")
    speak(text)
