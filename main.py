import os
import random
import keyboard
import asyncio
import traceback
import configparser
from pathlib import Path
from dotenv import load_dotenv

import pygame.mixer
import whisper
import pyttsx3
import speech_recognition as sr
from bark import SAMPLE_RATE, generate_audio, preload_models
from IPython.display import Audio
import torchaudio
from scipy.io.wavfile import write as write_wav

import openai
import pinecone
from pydantic import BaseSettings
from langchain.agents import Tool
from langchain.memory import ConversationTokenBufferMemory, ReadOnlySharedMemory
from langchain.chat_models import ChatOpenAI
from langchain.utilities import GoogleSearchAPIWrapper, WikipediaAPIWrapper, WolframAlphaAPIWrapper, OpenWeatherMapAPIWrapper
from langchain.agents import initialize_agent
from langchain.chains import LLMMathChain, RetrievalQA
from langchain.utilities.zapier import ZapierNLAWrapper
from langchain.agents.agent_toolkits import ZapierToolkit
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.summarize import load_summarize_chain

# Set audio backend to soundfile
torchaudio.set_audio_backend("soundfile")

# Load settings.ini and get bot name
config = configparser.ConfigParser()
config.read("settings.ini")
bot_name = config.get("settings", "bot_name")
BOT_NAME = bot_name

class SearchSettings:
    def __init__(self, file_path="settings.ini"):
        config = configparser.ConfigParser()
        config.read(file_path)

        self.enable_search = config.getboolean("tools", "enable_search")
        self.enable_wikipedia = config.getboolean("tools", "enable_wikipedia")
        self.enable_calculator = config.getboolean("tools", "enable_calculator")
        self.enable_wolfram_alpha = config.getboolean("tools", "enable_wolfram_alpha")
        self.enable_weather = config.getboolean("tools", "enable_weather")
        self.enable_zapier = config.getboolean("tools", "enable_zapier")
        self.enable_pinecone = config.getboolean("tools", "enable_pinecone")

# You can change the history_prompt for Bark in the settings GUI or settings.ini, see Bark documentation for more details
class VoiceSynthesisSettings(BaseSettings):
    use_bark = config.getboolean("voice", "use_bark")
    history_prompt = config.get("voice", "history_prompt")

    use_bark: bool = use_bark
    history_prompt: str = history_prompt

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
PINE_API_KEY = os.getenv("PINE_API_KEY")
PINE_ENV = os.getenv("PINE_ENV")

# Initialize Pinecone
embeddings = OpenAIEmbeddings()
pinecone_env = config.get("pinecone", "pinecone_env")

pinecone.init(
    api_key=PINE_API_KEY,
    environment=pinecone_env
)

index_name = config.get("pinecone", "pinecone_index")
docsearch = Pinecone.from_existing_index(index_name, embeddings)

settings = SearchSettings("settings.ini")
pygame.mixer.init()
voice_synthesis_settings = VoiceSynthesisSettings()
recognizer = sr.Recognizer()

def start_chat():
    chat_script_path = Path(__file__).parent / "chat.py"
    os.system(f"python {chat_script_path}")

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
        engine.setProperty('rate', 150)
        engine.say(text)
        engine.runAndWait()

def play_mp3(file_path):
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

# Define the memory and the LLM engine
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.5, max_tokens=150, verbose=True)
memory = ConversationTokenBufferMemory(llm=llm, max_token_limit=1000, memory_key="chat_history", return_messages=True)
doc_chain = load_qa_chain(llm, chain_type="map_reduce")
readonlymemory = ReadOnlySharedMemory(memory=memory)

# Tool definitions and wikipedia hack
search = GoogleSearchAPIWrapper(k=2)
wikipedia = WikipediaAPIWrapper(lang='en', top_k_results=1)
llm_math = LLMMathChain(llm=llm)
wolfram_alpha = WolframAlphaAPIWrapper()
weather = OpenWeatherMapAPIWrapper()
zapier= ZapierNLAWrapper()
toolkit = ZapierToolkit.from_zapier_nla_wrapper(zapier)
retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k":2})
pinecone_tool = RetrievalQA.from_chain_type(llm=llm, chain_type="map_rerank", retriever=docsearch.as_retriever())
wikisummarize = load_summarize_chain(llm, chain_type="stuff")

class WikiPage:
    def __init__(self, title, summary):
        self.title = title
        self.page_content = summary
        self.metadata = {}

def wiki_summary(search_query: str) -> str:
    wikipedia_wrapper = wikipedia
    wiki_result = wikipedia_wrapper.run(search_query)

    if not wiki_result:
        return "No good Wikipedia Search Result was found"

    wiki_pages = []
    for section in wiki_result.split("\n\n"):
        title, summary = section.split("\nSummary: ", 1)
        title = title.replace("Page: ", "")
        wiki_pages.append(WikiPage(title=title, summary=summary))

    summary_result = wikisummarize.run(wiki_pages)
    return summary_result

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
if settings.enable_pinecone:
    pinecone_name = config.get("pinecone", "tool_name")
    pinecone_description = config.get("pinecone", "tool_description")

    tools.append(
        Tool(
            name=pinecone_name,
            func=pinecone_tool.run,
            description=pinecone_description
        )
    )

bot_context = config.get("settings", "bot_context")
CONTEXT = bot_context

# Probably hacky workaround so that the agent chain respects the Zapier settings since it uses a toolkit
if settings.enable_zapier:
    agent_chain = initialize_agent([*toolkit.get_tools(), *tools], llm, agent="chat-conversational-react-description", verbose=True, memory=memory)
else:
    agent_chain = initialize_agent(tools, llm, agent="chat-conversational-react-description", verbose=True, memory=memory)

agent_chain.memory.chat_memory.add_ai_message(CONTEXT)

async def main():
    config = configparser.ConfigParser()
    config.read("settings.ini")
    hotkey = config.get("settings", "hotkey")

    keyboard.add_hotkey(hotkey, start_chat, suppress=True)
    print(f"Press {hotkey} to launch chat window")
    while True:
        print(f"Waiting for wake word {BOT_NAME} to prompt")
        play_mp3("intro.wav")

        listen_for_wake_word(BOT_NAME)

        greeting = random.choice(['Yes?', 'At your service.', 'What can I do for you?'])
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
                    agent_chain.memory.chat_memory.add_user_message(user_input)

                    input_text = user_input
                    response = agent_chain.run(input=input_text)
                    bot_response = response

                    print("Bot's response:", bot_response)
                    synthesize_speech_v2(bot_response)

                    agent_chain.memory.chat_memory.add_ai_message(bot_response)

                    if "you're welcome" in bot_response.lower() or "you are welcome" in bot_response.lower() or "my pleasure" in bot_response.lower():
                        break
                except Exception as e:
                    tb_string = traceback.format_exc()

                    if "This model's maximum context length is" in tb_string:
                        agent_chain.memory.chat_memory.clear()
                        traceback.print_exc()
                        error_message = "Apologies, the last request went over the maximum context length so I have to clear my memory. Is there anything else I can help you with?"
                        synthesize_speech_v2(error_message)
                    else:
                        traceback.print_exc()
                        error_message = "Unfortunately, I have encountered an error. Is there anything else I can help you with?"
                        synthesize_speech_v2(error_message)

if __name__ == "__main__":
    asyncio.run(main())
