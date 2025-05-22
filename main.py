from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
import os
import io
import numpy as np
import sounddevice as sd
import soundfile as sf
import keyboard
from openai import OpenAI
from libs.starttypes import text, number
from sudoku_context import get_context

from daisys import DaisysAPI
from daisys.v1.speak import SimpleProsody
from pydub import AudioSegment
from pydub.playback import play

LLMClient = False
sample_rate = 22050
channels = 1
dtype = 'int16'
audio_buffer = []


def _getOpenAiClient():
    if "OPENAI_API_KEY" not in os.environ:
        raise RuntimeError("Set OPENAI_API_KEY in your environment.")
    global LLMClient
    if not LLMClient:
        LLMClient = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return LLMClient


def callback(indata, frames, time, status):
    if status:
        print(f"Status: {status}")
    audio_buffer.append(indata.copy())


def _listen(lenArg):
    global audio_buffer
    audio_buffer = []
    max_rec_time = lenArg.value

    print("Press space to start recording...")
    while not keyboard.is_pressed('space'):
        pass
    while keyboard.is_pressed('space'):
        pass
    print("Recording...")

    with sd.InputStream(samplerate=sample_rate, channels=channels, dtype=dtype, callback=callback):
        while not keyboard.is_pressed('space'):
            pass

    audio_data = np.concatenate(audio_buffer, axis=0)
    sf.write("temp.wav", audio_data, sample_rate, format="wav")

    client = _getOpenAiClient()
    transcript = client.audio.translations.create(
        model="whisper-1",
        file=open("temp.wav", "rb")
    )
    return text(transcript.text)


def _prompt(s1):
    client = _getOpenAiClient()
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a robot that assists players with solving sudoku's. "
                    "You cannot help with anything else. Always speak in plain English, no more than 100 words per response. "
                    "Avoid lists, code, or technical formatting. "
                    "Speak naturally as if talking to a human and always stay on the topic of sudoku's."
                )
            },
            {
                "role": "user",
                "content": s1.value
            }
        ]
    )
    return text(value=completion.choices[0].message.content)


def speak_with_daisys(text_to_speak):
    try:
        email = os.environ["DAISYS_EMAIL"]
        password = os.environ["DAISYS_PASSWORD"]

        with DaisysAPI('speak', email=email, password=password) as speak:
            voices = speak.get_voices()
            if not voices:
                raise RuntimeError("No voices available in Daisys account.")

            voice = voices[0]  # Use the first voice found
            take = speak.generate_take(
                voice_id=voice.voice_id,
                text=text_to_speak,
                prosody=SimpleProsody(pace=0, pitch=0, expression=5)
            )
            speak.get_take_audio(take_id=take.take_id, file="daisys_reply.mp3", format="mp3")

        audio = AudioSegment.from_file("daisys_reply.mp3", format="mp3")
        play(audio)

    except Exception as e:
        print(f"Daisys TTS error: {e}")
        print("Falling back to terminal printout.")
        print(">>", text_to_speak)


@inlineCallbacks
def main(session, details):
    print("Press 'q' at any time to quit.")
    yield session.call("rom.optional.behavior.play", name="BlocklyStand")

    while not keyboard.is_pressed('q'):
        try:
            user_input = _listen(number(5))
            print("User said:", user_input.value)

            sudoku_context = get_context()
            combined_prompt = sudoku_context + "\nUser said:\n" + user_input.value

            reply = _prompt(text(combined_prompt))
            print("GPT-4o mini reply:", reply.value)

            # Use Daisys API for TTS instead of NAO
            speak_with_daisys(reply.value)

        except Exception as e:
            print("Error during interaction:", e)

    yield session.call("rom.optional.behavior.play", name="BlocklyCrouch")
    print("Quitting interaction loop...")
    session.leave()


wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"],
        "max_retries": 0
    }],
    realm="rie.682eede91f2d588ceb27ab09",
)

wamp.on_join(main)

if __name__ == "__main__":
    run([wamp])
