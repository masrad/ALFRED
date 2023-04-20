import openai
import os
from dotenv import load_dotenv
import asyncio
import whisper
import pyttsx3
import speech_recognition as sr
import keyboard
import random
import pygame.mixer
from pydantic import BaseSettings
from langchain.agents import Tool
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.utilities import GoogleSearchAPIWrapper, WikipediaAPIWrapper, WolframAlphaAPIWrapper, OpenWeatherMapAPIWrapper
from langchain.agents import initialize_agent
from langchain.chains import LLMMathChain

# Settings class
class SearchSettings(BaseSettings):
    enable_search: bool = True
    enable_wikipedia: bool = True
    enable_calculator: bool = True
    enable_wolfram_alpha: bool = True
    enable_weather: bool = False

    class Config:
        env_prefix = "SEARCH_"

# Initialize variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
WOLFROM_ALPHA_APPID = os.getenv("WOLFROM_ALPHA_APPID")
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

# Initialize pygame mixer
pygame.mixer.init()

# Create a settings instance
settings = SearchSettings()

# Create a recognizer object
recognizer = sr.Recognizer()

# Implementing wake word detection
def listen_for_wake_word(wake_word):
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        while True:
            audio = recognizer.listen(source, phrase_time_limit=2)
            try:
                transcription = recognizer.recognize_google(audio)
                print(f"Heard: {transcription}")
                if wake_word.lower() in transcription.lower():
                    return True
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print("Could not request results; {0}".format(e))

# Define the text to speech function
def synthesize_speech(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)  # Adjust speech rate
    engine.say(text)
    engine.runAndWait()

# Define a function to play the MP3 file
def play_mp3(file_path):
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

# Define the memory and the LLM engine
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.5, max_tokens=150)

# Define the tools
search = GoogleSearchAPIWrapper()
wikipedia = WikipediaAPIWrapper()
llm_math = LLMMathChain(llm=llm)
wolfram_alpha = WolframAlphaAPIWrapper()
weather = OpenWeatherMapAPIWrapper()

tools = []

if settings.enable_search:
    tools.append(
        Tool(
            name="Search",
            func=search.run,
            description="useful when you need to answer questions about current events and real-time information"
        )
    )

if settings.enable_wikipedia:
    tools.append(
        Tool(
            name="Wikipedia",
            func=wikipedia.run,
            description="Useful for searching information on historical information on Wikipedia. "
            "Use this more than the normal search if the question is about events that occured before 2023, like the 'What was the 2008 financial crisis?' or 'Who won the 2016 US presidential election?'"
        )
    )
   
if settings.enable_calculator:
    tools.append(
        Tool(
            name='Calculator',
            func=llm_math.run,
            description='Useful for when you need to answer questions about math.'
        )
    )

if settings.enable_wolfram_alpha:
    tools.append(
        Tool(
            name='Wolfram Alpha',
            func=wolfram_alpha.run,
            description="Useful for when you need to answer questions about Math, "
                        "Science, Technology, Culture, people, Society and Everyday Life. "
                        "Input should be a search query"
        )
    )

if settings.enable_weather:
    tools.append(
        Tool(
            name='Weather',
            func=weather.run,
            description="Useful for when you need to answer questions about weather."
        )
    )

# Define the agent chain
agent_chain = initialize_agent(tools, llm, agent="chat-conversational-react-description", verbose=True, memory=memory)

# Define the main function
async def main():
    while True:
        print(f"Waiting for hotkey or wake word 'Alfred' to prompt ALFRED")

        while True:
            if keyboard.is_pressed("ctrl+shift+1") or listen_for_wake_word("Alfred"):
                break
            await asyncio.sleep(0.1)

        conversation_history = [
            # ...
        ]

        greeting = random.choice(['Good evening. Can I help you with anything?', 'Alfred, At your service.', 'What can I do for you?'])
        synthesize_speech(greeting)

        while True:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                print("Speak a prompt...")
                play_mp3("start.mp3")
                audio = recognizer.listen(source)

                try:
                    with open("audio_prompt.wav", "wb") as f:
                        f.write(audio.get_wav_data())
                    model = whisper.load_model("base")
                    result = model.transcribe("audio_prompt.wav")
                    user_input = result["text"]
                    print(f"You said: {user_input}")
                    play_mp3("stop.mp3")
                except Exception as e:
                    print("Error transcribing audio: {0}".format(e))
                    continue

                agent_chain.memory.chat_memory.add_user_message(user_input)

                input_text = user_input
                response = agent_chain.run(input=input_text)
                bot_response = response

                print("Bot's response:", bot_response)
                synthesize_speech(bot_response)

                agent_chain.memory.chat_memory.add_ai_message(bot_response)

                if "you're welcome" in bot_response.lower() or "you are welcome" in bot_response.lower() or "my pleasure" in bot_response.lower():
                    break

if __name__ == "__main__":
    asyncio.run(main())
