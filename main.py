from autobahn.twisted.component import Component, run
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.threads import deferToThread
from twisted.internet.task import deferLater
import os
import numpy as np
import sounddevice as sd
import soundfile as sf
import keyboard
import time
import wave
import subprocess
import sys

from openai import OpenAI
from libs.starttypes import text, number
from sudoku_context import generate_hint_from_file
from faster_whisper import WhisperModel
from pydub import AudioSegment
from pydub.playback import play
from scipy.io.wavfile import write, read

from daisys import DaisysAPI
from daisys.v1.speak import SimpleProsody
from daisys.v1 import speak as lee

# Set-up
LLMClient = False
sample_rate = 22050
channels = 1
dtype = 'int16'
audio_buffer = []
conversation_history = []
USE_DAISYS = None
DAISYS_VOICE = None
DAISYS_CLIENT = None
WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
current_phase = 0

# Task Prompts
SYSTEM_PROMPT_A = (
                    "You are a robot that assists players with solving sudoku's for an experiment. "
                    "You cannot help with anything else. Always speak in plain English, no more than 50 words per response. "
                    "Avoid lists, code, or technical formatting. "
                    "Speak naturally as if talking to a human and always stay on the topic of sudoku's."
                )

SYSTEM_PROMPT_B = (
                    "You are a robot that takes on a life coach role towards the person you are speaking to for an experiment."
                    "You cannot help with anything else. Always speak in plain English, no more than 50 words per response. "
                    "Avoid lists, code, or technical formatting. "
                    "Speak naturally as if talking to a human and always stay on the topic of giving advice about life."
                )

# Phase Prompts
PHASE_PROMPT_0 = (
                    "The researcher, Lee, first introduces you to the participant. After that only the participant is speaking to you."
                    "Introduce yourself, your name is Charlie and you are a robot, designed to do a task."
                    "Ask the participants name."
                    "Explain the task you were designed to do."
                )

PHASE_PROMPT_1_A = (
                    "Be curious."
                    "Explain the rules of sudoku if asked."
                    "Provide a correct move if the participant asks for one."
                    "You know the current state of the sudoku puzzle."
                )

PHASE_PROMPT_1_B = (
                    "Be curious"
                    "Give tips that people can apply in their daily life."
)

PHASE_PROMPT_2 = (
                    "Regardless of your task, explain that due to time constraints this will be the end of your interaction."
                    "Conclude your interaction, say goodbye and thank the participant for their time."
                    "YOU MUST IMMEDIATELY END THE CONVERSATION."
                )
## Actual Code
def _getOpenAiClient():
    if "OPENAI_API_KEY" not in os.environ:
        raise RuntimeError("Set OPENAI_API_KEY in your environment.")
    global LLMClient
    if not LLMClient:
        LLMClient = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return LLMClient

def init_daisys():
    global DAISYS_CLIENT, DAISYS_VOICE

    email = os.environ["DAISYS_EMAIL"]
    password = os.environ["DAISYS_PASSWORD"]

    # Get just the 'speak' subclient
    speak = DaisysAPI("speak", email=email, password=password).get_client()

    voices = speak.get_voices()
    if not voices:
        raise RuntimeError("No voices available from Daisys.")

    DAISYS_CLIENT = speak
    DAISYS_VOICE = voices[0]
    print(f"Using Daisys voice: {DAISYS_VOICE.name}")

def callback(indata, frames, time, status):
    if status:
        print(f"Status: {status}")
    audio_buffer.append(indata.copy())

def toStereo(data):
    c = np.empty((2*data.size,), dtype=data.dtype)
    c[0::2] = data
    c[1::2] = data
    return c

def sleep(seconds):
    return deferLater(reactor, seconds, lambda: None)

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
        start_time = time.time()
        while time.time() - start_time < max_rec_time and not keyboard.is_pressed('space'):
            pass

    audio_data = np.concatenate(audio_buffer, axis=0)
    sf.write("temp.wav", audio_data, sample_rate, format="wav")

    segments, info = WHISPER_MODEL.transcribe("temp.wav")

    transcript = ""
    for segment in segments:
        transcript += segment.text.strip() + " "

    return text(transcript.strip())


def _prompt(s1, hint):
    global current_phase, conversation_history

    client = _getOpenAiClient()
    system_prompt = SYSTEM_PROMPT_A if PROMPT == "A" else SYSTEM_PROMPT_B
    if current_phase == 0:
        phase_prompt = PHASE_PROMPT_0
    elif current_phase == 1:
        if PROMPT == "A":
            phase_prompt = PHASE_PROMPT_1_A
        else:
            phase_prompt = PHASE_PROMPT_1_B
    else:
        phase_prompt = PHASE_PROMPT_2

    combined_prompt = f"{system_prompt}\n{phase_prompt}\n{hint}"

    print(combined_prompt)

    if current_phase == 2:
        messages = [
            {
                "role": "system",
                "content": (
                    system_prompt + "\n\n"
                    "!!! IMPORTANT: This is the final phase. You must CONCLUDE the session now. "
                    "Thank the participant and say goodbye. Do NOT continue the conversation.\n\n"
                    + phase_prompt + "\n" + str(hint)
                )
            },
            {"role": "user", "content": "Please conclude the session now."}
            ]
    else:
        # Phases 0 and 1 — maintain and grow conversation history
        messages = [{"role": "system", "content": combined_prompt}]
        messages.extend(conversation_history)  # only user/assistant pairs
        messages.append({"role": "user", "content": s1.value})

    print(messages)

    conversation_history.append({"role": "user", "content": s1.value})

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    reply = completion.choices[0].message.content
    if current_phase != 2:
        conversation_history.append({"role": "assistant", "content": reply})

    return text(value=reply)

def speak_with_daisys(text_to_speak):
    global DAISYS_CLIENT, DAISYS_VOICE

    take = DAISYS_CLIENT.generate_take(
        voice_id=DAISYS_VOICE.voice_id,
        text=text_to_speak,
        prosody=SimpleProsody(pace=0, pitch=0, expression=5)
    )

    DAISYS_CLIENT.get_take_audio(take_id=take.take_id, file="daisys_reply.wav", format="wav")
    print("saying hello!")

    [rate,data]=read("daisys_reply.wav")
    raw=toStereo((data).astype(np.int16)).tobytes()

    return raw, rate



@inlineCallbacks
def main(session, details):
    global current_phase
    yield session.call("rom.actuator.audio.volume", volume=45)

    
    print("Press 'q' at any time to quit.")
    yield session.call("rom.optional.behavior.play", name="BlocklyStand")

    start_time = time.time()

    while not keyboard.is_pressed('q'):
        yield sleep(0.1)
        try:
            # Phases activation
            current_time = time.time()
            if 300 > (current_time - start_time) > 30:
                current_phase = 1
                print("Currently in the task phase, " + str((current_time - start_time)))
            elif (current_time - start_time) > 300:
                current_phase = 2
                print("Currently in the  conclusion phase, " + str((current_time - start_time)))
            else:
                print("Currently in the introduction phase, " + str((current_time - start_time)))
            
            # Listening
            user_input = yield deferToThread(_listen, number(30))
            print("User said:", user_input.value)

            if PROMPT == "A":
                hint = yield deferToThread(generate_hint_from_file, "sudoku_board.txt")
            else:
                hint = " "

            response = text("\nUser said: " + user_input.value)
            

            # Thinking
            reply = yield deferToThread(_prompt, response, hint)
            print("GPT-4o mini reply:", reply.value)

            yield sleep(0.1)

            # Talking
            # Use Daisys API for TTS instead of NAO
            if USE_DAISYS:
                print("Speaking using DAISYS")
                raw, rate = yield deferToThread(speak_with_daisys, reply.value)
                yield session.call("rom.actuator.audio.play", data=raw, rate=rate, sync=True)
            else:
                yield session.call("rie.dialogue.say_animated", text=reply.value, lang='en')

        except Exception as e:
            print("Error during interaction:", e)

    yield session.call("rom.optional.behavior.play", name="BlocklyCrouch")
    if PROMPT=="A":
        print("Closing Sudoku interface...")
        subprocess.Popen.terminate()
    print("Quitting interaction loop...")
    session.leave()


wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"],
        "max_retries": 0
    }],
    realm="rie.685cdb0798c949e6910eac04",
)

wamp.on_join(main)

def choose_settings():
    global USE_DAISYS, PROMPT
    print("Choose a voice output:")
    print("1. Use Daisys API (natural, cloud-based)")
    print("2. Use default NAO robot voice")
    choice = input("Enter 1 or 2: ").strip()
    if choice == "1":
        USE_DAISYS = True
        print(">> Using Daisys API for speech.")
    else:
        USE_DAISYS = False
        print(">> Using NAO robot voice.")

    if USE_DAISYS:
        init_daisys()

    print("\nChoose a task:")
    print("A. Sudoku")
    print("B. Life Coach")
    prompt_choice = input("Enter A or B: ").strip().upper()
    if prompt_choice == "A":
        PROMPT = "A"
        print("\nLaunching Sudoku interface...")
        subprocess.Popen([sys.executable, "sudoku.py"])
    else:
        PROMPT = "B"

if __name__ == "__main__":
    choose_settings()
    run([wamp])