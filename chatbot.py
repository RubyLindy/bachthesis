import numpy as np
from openai import OpenAI
import pyaudio
import io
import keyboard
import time
import os
import sounddevice as sd
import soundfile as sf
from libs.starttypes import *

LLMClient = False
sample_rate = 22050  # Samples per second
channels = 1  # Stereo
dtype = 'int16'  # Data type for audio
audio_buffer = []


def _getOpenAiClient():
    global LLMClient

    if "OPENAI_API_KEY" in os.environ:
        key=os.environ["OPENAI_API_KEY"]
    else:
        raise StartError("Start runtime error: to use OpenAI LLM you must set the api key\nWindows: setx OPENAI_API_KEY \"your_api_key_here\" (in your terminal, then restart the terminal) \nLinux: export OPENAI_API_KEY=\"your_api_key_here\"")

    if (LLMClient == False):
        LLMClient= OpenAI(api_key = key)
        
    return LLMClient

    
def _prompt(s1):
    completion = _getOpenAiClient().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": ""},
            {
                "role": "user",
                "content": s1.value
            }
        ]
    )
    return text(value=completion.choices[0].message.content)

def _say(s1):
    # Initialize PyAudio
    p = pyaudio.PyAudio()

    response = _getOpenAiClient().audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=s1.value,
        response_format="pcm"
    )

    # Convert response data to audio and play
    
    audio_stream = io.BytesIO(response.content)

    stream = p.open(format=p.get_format_from_width(2),  # Assuming 16-bit audio
                    channels=1,  # Mono audio
                    rate=24000,  # Typical OpenAI-generated audio sample rate
                    output=True,)
    # Play audio
    stream.write(audio_stream.read())
    stream.stop_stream()
    stream.close()
    
    # Terminate PyAudio
    p.terminate()


def callback(indata, frames, time, status):
    """Callback function to handle audio chunks."""
    if status:
        print(f"Status: {status}")
    audio_buffer.append(indata.copy())
    
def _listen(lenArg):
    global audio_buffer
    audio_buffer=[]
    
    max_rec_time=lenArg.value

    while not keyboard.is_pressed('space'):
        pass
        
    while keyboard.is_pressed('space'):
        pass
    
    start_time = time.time()
    
    # Create the input stream
    with sd.InputStream(samplerate=sample_rate, channels=channels, dtype=dtype, callback=callback):
        while time.time()-start_time<max_rec_time and not keyboard.is_pressed('space'):
            pass
            
    # Combine the recorded chunks into a single NumPy array
    audio_data = np.concatenate(audio_buffer, axis=0)

    sf.write("temp.wav", audio_data, sample_rate, format="wav")
     
    client = _getOpenAiClient()

    transcript = client.audio.translations.create(
      model="whisper-1",
      file=open("temp.wav", "rb")
    )
    return text(transcript.text)
