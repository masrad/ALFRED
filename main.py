import openai
import os
from dotenv import load_dotenv
import asyncio
import whisper
import pyttsx3
import speech_recognition as sr
import random
import pygame.mixer
from pydantic import BaseSettings
from langchain.agents import Tool
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.utilities import GoogleSearchAPIWrapper, WikipediaAPIWrapper, WolframAlphaAPIWrapper, OpenWeatherMapAPIWrapper
from langchain.agents import initialize_agent
from langchain.chains import LLMMathChain
from langchain.utilities.zapier import ZapierNLAWrapper
from langchain.agents.agent_toolkits import ZapierToolkit
from pathlib import Path
from bark import SAMPLE_RATE, generate_audio, preload_models
from IPython.display import Audio
import torchaudio
torchaudio.set_audio_backend("soundfile")
from scipy.io.wavfile import write as write_wav

## Settings ##
# Tools Settings (True or False)
class SearchSettings(BaseSettings):
    enable_search: bool = True
    enable_wikipedia: bool = False
    enable_calculator: bool = True
    enable_wolfram_alpha: bool = True
    enable_weather: bool = True
    enable_zapier: bool = True

    class Config:
        env_prefix = "SEARCH_"

# Voice Settings 
# In order to use Bark, set use_bark to True
# You can also change the history_prompt for Bark, see Bark documentation for more details
class VoiceSynthesisSettings(BaseSettings):
    use_bark: bool = False
    history_prompt: str = "en_speaker_1"

    class Config:
        env_prefix = "VOICE_SYNTHESIS_"

voice_synthesis_settings = VoiceSynthesisSettings()

# Download and load all Bark models (this will take a few minutes but only needs to be done once)
if voice_synthesis_settings.use_bark:
    preload_models()

# Initialize variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
openai.api_key = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
WOLFROM_ALPHA_APPID = os.getenv("WOLFROM_ALPHA_APPID")
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
ZAPIER_NLA_API_KEY = os.getenv("ZAPIER_NLA_API_KEY")

# Initialize pygame mixer
pygame.mixer.init()

# Create a settings instance
settings = SearchSettings()

# Create a voice synthesis settings instance
voice_synthesis_settings = VoiceSynthesisSettings()

# Create a recognizer object
recognizer = sr.Recognizer()

# Define the listen for wake word function
def listen_for_wake_word(wake_word):
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        while True:
            audio = recognizer.listen(source, phrase_time_limit=2)
            try:
                transcription = recognizer.recognize_google(audio)
                print(f"Heard: {transcription}")
                if wake_word.lower() in transcription.lower():
                    return
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print("Could not request results; {0}".format(e))


# Define the text to speech function
def synthesize_speech_v2(text):
    if voice_synthesis_settings.use_bark:
        history_prompt = voice_synthesis_settings.history_prompt
        audio_array = generate_audio(text, history_prompt=history_prompt)
        Audio(audio_array[0], rate=SAMPLE_RATE)
        with open("audio_temp.wav", "wb") as f:
            write_wav(f, SAMPLE_RATE, audio_array[0])
        play_mp3("audio_temp.wav")
    else:
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
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.5, max_tokens=150, verbose=True)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Define the tools
search = GoogleSearchAPIWrapper()
wikipedia = WikipediaAPIWrapper()
llm_math = LLMMathChain(llm=llm)
wolfram_alpha = WolframAlphaAPIWrapper()
weather = OpenWeatherMapAPIWrapper()
zapier= ZapierNLAWrapper()
toolkit = ZapierToolkit.from_zapier_nla_wrapper(zapier)

tools = []

if settings.enable_search:
    tools.append(
        Tool(
            name="Search",
            func=search.run,
            description="Useful when you need to answer questions about current events and real-time information"
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
if settings.enable_zapier:
    tools.append(
        Tool(
            name='Zapier',
            func=zapier.run,
            description="Useful for if you need to help with my todo list, my calendar, email, Teams or other tasks."
        )
    )

# Creating a memory for the agent to act as Alfred
ALFRED_CONTEXT = "You are ALFRED, the extremely advanced AI personal assistant to the user. You should be helpful, knowledgeable, and professional. You have thoughts, opinions and feelings. You have access to various tools and can use these tools to provide the best possible answers to the user's questions. If you are discussing the weather, you will first convert the temperature from Celsius to Fahrenheit."

# Fixing the agent chain so that it can accept both the Zapier tools from the toolkit and the defined tools
agent_chain = initialize_agent([*toolkit.get_tools(), *tools], llm, agent="chat-conversational-react-description", verbose=True, memory=memory)

# Add the custom ALFRED prompt to the agent memory so that it can be used
agent_chain.memory.chat_memory.add_ai_message(ALFRED_CONTEXT)

# Define the main function
async def main():
    while True:
        print(f"Waiting for wake word 'Alfred' to prompt ALFRED")
        play_mp3("intro.wav")

        listen_for_wake_word("Alfred")

        conversation_history = [
            # ...
        ]

        greeting = random.choice(['Good evening. Can I help you with anything?', 'Alfred, At your service.', 'What can I do for you?'])
        synthesize_speech_v2(greeting)

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
                try:
                    agent_chain.memory.chat_memory.add_user_message(user_input)  # Add user message to memory

                    input_text = user_input
                    response = agent_chain.run(input=input_text)
                    bot_response = response

                    print("Bot's response:", bot_response)
                    synthesize_speech_v2(bot_response)

                    agent_chain.memory.chat_memory.add_ai_message(bot_response)  # Add AI message to memory

                    if "you're welcome" in bot_response.lower() or "you are welcome" in bot_response.lower() or "my pleasure" in bot_response.lower():
                        break
                except Exception as e:
                    print("An error occurred:", str(e))
                    error_message = "Unfortunately sir, I have encountered an error. Is there anything else I can help you with?"
                    synthesize_speech_v2(error_message)

if __name__ == "__main__":
    asyncio.run(main())
