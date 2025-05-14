from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
import os
import io
import time
import socket
import numpy as np
import pyaudio
import sounddevice as sd
import soundfile as sf
import keyboard
from openai import OpenAI
from libs.starttypes import text, number

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
	import keyboard
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
						"You are a robot that assists players with solving sudoku's."
						"Always speak in plain English, no more than a 100 words per response."
						"Avoid lists, code, or technical formatting."
						"Speak naturally as if talking to a human."
					)
				},
					
			{
                "role": "user",
                "content": s1.value
            }
        ]
	)
	return text(value=completion.choices[0].message.content)

# ---- WAMP Component Setup ----

@inlineCallbacks
def main(session, details):
	print("Press 'q' at any time to quit.")

	while not keyboard.is_pressed('q'):
		try:
			user_input = _listen(number(5))
			print("User said:", user_input.value)

			reply = _prompt(user_input)
			print("GPT-4o mini reply:", reply.value)

			yield session.call("rie.dialogue.say", text=reply.value)
			yield session.call("rom.optional.behavior.play", name="BlocklyWaveRightArm")

		except Exception as e:
			print("Error during interaction:", e)
	
	print("Quitting interaction loop...")
	session.leave()

wamp = Component(
	transports=[{
		"url": "ws://wamp.robotsindeklas.nl",
		"serializers": ["msgpack"],
		"max_retries": 0
	}],
	realm="rie.681b0af3bab2120e3ffc563f",
)

wamp.on_join(main)

if __name__ == "__main__":
	run([wamp])
