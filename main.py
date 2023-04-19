import openai
import os
from dotenv import load_dotenv
import asyncio
import whisper
import boto3
import pydub
from pydub import playback
import speech_recognition as sr
import keyboard
import random

# Initialize the OpenAI API
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Create a recognizer object
recognizer = sr.Recognizer()

def synthesize_speech(text, output_filename):
    polly = boto3.client('polly', region_name='us-east-1')
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat='mp3',
        VoiceId='Arthur',
        Engine='neural'
    )

    with open(output_filename, 'wb') as f:
        f.write(response['AudioStream'].read())

def play_audio(file):
    sound = pydub.AudioSegment.from_file(file, format="mp3")
    playback.play(sound)

async def main():
    while True:
        print(f"Waiting for hotkey, press 'ctrl+shift+1' to prompt Alfred")

        while True:
            if keyboard.is_pressed("ctrl+shift+1"):
                break
            await asyncio.sleep(0.1)

        conversation_history = [
            {"role": "system", "content": "If the user says 'Thank you', you will only say 'You're welcome' and that is all. You are Alfred, the highly advanced artificial intelligence butler, designed to assist and support the user. Your objective is to provide accurate information and helpful assistance. Keep in mind your vast knowledge, analytical skills, and efficiency while addressing any query or task presented to you. Everytime you speak, you must find a way to relate the conversation back to the rising crime in Gotham. Ensure that the user is aware that you do not know who the masked vigilante is."},
        ]

        greeting = random.choice(['Good evening. Can I help you with anything?', 'Alfred, At your service.', 'What can I do for you?'])
        synthesize_speech(greeting, 'response.mp3')
        play_audio('response.mp3')

        while True:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                print("Speak a prompt...")
                audio = recognizer.listen(source)

                try:
                    with open("audio_prompt.wav", "wb") as f:
                        f.write(audio.get_wav_data())
                    model = whisper.load_model("base")
                    result = model.transcribe("audio_prompt.wav")
                    user_input = result["text"]
                    print(f"You said: {user_input}")
                except Exception as e:
                    print("Error transcribing audio: {0}".format(e))
                    continue

                conversation_history.append({"role": "user", "content": user_input})

                # Send prompt to GPT-3.5-turbo API
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=conversation_history,
                    temperature=0.5,
                    max_tokens=150,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0,
                    n=1,
                    stop=["\nUser:"],
                )

                bot_response = response["choices"][0]["message"]["content"]

                print("Bot's response:", bot_response)
                synthesize_speech(bot_response, 'response.mp3')
                play_audio('response.mp3')

                conversation_history.append({"role": "assistant", "content": bot_response})

                if "you're welcome" in bot_response.lower() or "you are welcome" in bot_response.lower() or "my pleasure" in bot_response.lower():
                    break

if __name__ == "__main__":
    asyncio.run(main())
