import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import openai
import os
import sys
from dotenv import load_dotenv, set_key
from langchain.agents import Tool
from langchain.memory import ConversationTokenBufferMemory, ReadOnlySharedMemory
from langchain.chat_models import ChatOpenAI
from langchain.utilities import GoogleSearchAPIWrapper, WikipediaAPIWrapper, WolframAlphaAPIWrapper, OpenWeatherMapAPIWrapper
from langchain.agents import initialize_agent
from langchain.chains import LLMMathChain, RetrievalQA
from langchain.utilities.zapier import ZapierNLAWrapper
from langchain.agents.agent_toolkits import ZapierToolkit
from pathlib import Path
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
import pinecone
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.summarize import load_summarize_chain
import traceback
import configparser
import tkinter
from tkinter import ttk, Toplevel, messagebox
import sv_ttk

config = configparser.ConfigParser()
config.read("settings.ini")
bot_name = config.get("settings", "bot_name")
BOT_NAME = bot_name

def restart_app():
    python = sys.executable
    os.execl(python, python, *sys.argv)

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

# Define the memory and the LLM engine
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.5, max_tokens=150, verbose=True)
memory = ConversationTokenBufferMemory(llm=llm, max_token_limit=1500, memory_key="chat_history", return_messages=True)
doc_chain = load_qa_chain(llm, chain_type="map_reduce")
readonlymemory = ReadOnlySharedMemory(memory=memory)

# Define the tools
search = GoogleSearchAPIWrapper(k=2)
wikipedia = WikipediaAPIWrapper()
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
            func=wiki_summary,
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
# Adjust pinecone tool settings in settings.ini
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

# Workaround so that the agent chain respects the Zapier settings since it uses a toolkit
if settings.enable_zapier:
    agent_chain = initialize_agent([*toolkit.get_tools(), *tools], llm, agent="chat-conversational-react-description", verbose=True, memory=memory)
else:
    agent_chain = initialize_agent(tools, llm, agent="chat-conversational-react-description", verbose=True, memory=memory)

agent_chain.memory.chat_memory.add_ai_message(CONTEXT)

#Define the Settings GUI
def open_settings():
    settings_window = Toplevel()
    settings_window.title("Settings")
    settings_window.iconbitmap(default="icon.ico")

    def save_settings():
        config.set("settings", "bot_name", bot_name_var.get())
        config.set("settings", "bot_context", bot_context_var.get())
        config.set("settings", "hotkey", hotkey_var.get())
        for key, var in settings_vars.items():
            config.set("tools", key, str(var.get()))
        
        config.set("pinecone", "tool_name", pinecone_tool_name_var.get())
        config.set("pinecone", "tool_description", pinecone_tool_description_var.get())
        config.set("pinecone", "pinecone_index", pinecone_index_var.get())
        config.set("pinecone", "pinecone_env", pinecone_env_var.get())

        config.set("voice", "use_bark", str(use_bark_var.get()))
        config.set("voice", "history_prompt", history_prompt_var.get())

        with open("settings.ini", "w") as configfile:
            config.write(configfile)

        restart = messagebox.askyesno("Settings Saved", "Settings have been saved successfully. Would you like to restart the application?")
        if restart:
            restart_app()
        else:
            settings_window.destroy()

    settings_frame = ttk.Frame(settings_window, padding="10")
    settings_frame.grid(row=0, column=0, sticky="nsew")

    bot_name_var = tk.StringVar()
    bot_context_var = tk.StringVar()
    hotkey_var = tk.StringVar()
    bot_name_var.set(config.get("settings", "bot_name"))
    bot_context_var.set(config.get("settings", "bot_context"))
    hotkey_var.set(config.get("settings", "hotkey"))

    settings_vars = {}
    for key in config.options("tools"):
        settings_vars[key] = tk.BooleanVar()
        settings_vars[key].set(config.getboolean("tools", key))

    ttk.Label(settings_frame, text="General Settings").grid(row=0, column=0, sticky="w", pady=5)
    ttk.Separator(settings_frame, orient="horizontal").grid(row=1, column=0, sticky="ew")

    ttk.Label(settings_frame, text="Bot Name:").grid(row=2, column=0, sticky="w")
    ttk.Entry(settings_frame, textvariable=bot_name_var).grid(row=3, column=0, sticky="nsew")

    ttk.Label(settings_frame, text="Bot Context:").grid(row=4, column=0, sticky="w")
    ttk.Entry(settings_frame, textvariable=bot_context_var).grid(row=5, column=0, sticky="nsew")

    ttk.Label(settings_frame, text="Hotkey:").grid(row=6, column=0, sticky="w")
    ttk.Entry(settings_frame, textvariable=hotkey_var).grid(row=7, column=0, sticky="nsew")

    ttk.Label(settings_frame, text="Tools Selection").grid(row=8, column=0, sticky="w", pady=5)
    ttk.Separator(settings_frame, orient="horizontal").grid(row=9, column=0, sticky="ew")

    row = 10
    for key, var in settings_vars.items():
        ttk.Checkbutton(settings_frame, text=key, variable=var).grid(row=row, column=0, sticky="w")
        row += 1
    ttk.Label(settings_frame, text="Pinecone Settings").grid(row=row, column=0, sticky="w", pady=5)
    row += 1
    ttk.Separator(settings_frame, orient="horizontal").grid(row=row, column=0, sticky="ew")
    row += 1
    pinecone_tool_name_var = tk.StringVar()
    pinecone_tool_description_var = tk.StringVar()
    pinecone_index_var = tk.StringVar()
    pinecone_env_var = tk.StringVar()
    pinecone_tool_name_var.set(config.get("pinecone", "tool_name"))
    pinecone_tool_description_var.set(config.get("pinecone", "tool_description"))
    pinecone_index_var.set(config.get("pinecone", "pinecone_index"))
    pinecone_env_var.set(config.get("pinecone", "pinecone_env"))
    ttk.Label(settings_frame, text="Tool Name:").grid(row=row, column=0, sticky="w")
    row += 1
    ttk.Entry(settings_frame, textvariable=pinecone_tool_name_var).grid(row=row, column=0, sticky="nsew")
    row += 1
    ttk.Label(settings_frame, text="Tool Description:").grid(row=row, column=0, sticky="w")
    row += 1
    ttk.Entry(settings_frame, textvariable=pinecone_tool_description_var).grid(row=row, column=0, sticky="nsew")
    row += 1
    ttk.Label(settings_frame, text="Pinecone Index:").grid(row=row, column=0, sticky="w")
    row += 1
    ttk.Entry(settings_frame, textvariable=pinecone_index_var).grid(row=row, column=0, sticky="nsew")
    row += 1
    ttk.Label(settings_frame, text="Pinecone Environment:").grid(row=row, column=0, sticky="w")
    row += 1
    ttk.Entry(settings_frame, textvariable=pinecone_env_var).grid(row=row, column=0, sticky="nsew")
    row += 1
    ttk.Label(settings_frame, text="Voice Settings").grid(row=row, column=0, sticky="w", pady=5)
    row += 1
    ttk.Separator(settings_frame, orient="horizontal").grid(row=row, column=0, sticky="ew")
    row += 1
    use_bark_var = tk.BooleanVar()
    history_prompt_var = tk.StringVar()
    use_bark_var.set(config.getboolean("voice", "use_bark"))
    history_prompt_var.set(config.get("voice", "history_prompt"))
    ttk.Checkbutton(settings_frame, text="Use Bark", variable=use_bark_var).grid(row=row, column=0, sticky="w")
    row += 1
    ttk.Label(settings_frame, text="Bark Voice:").grid(row=row, column=0, sticky="w")
    row += 1
    ttk.Entry(settings_frame, textvariable=history_prompt_var).grid(row=row, column=0, sticky="nsew")
    row += 1
    ttk.Button(settings_frame, text="Edit API Keys", command=edit_api_keys).grid(row=row, column=0, pady=(10, 0))
    row += 1
    ttk.Button(settings_frame, text="Save Settings", command=save_settings).grid(row=row, column=0, pady=(10, 0))
    settings_window.columnconfigure(0, weight=1)
    settings_window.rowconfigure(0, weight=1)

# Define the keys GUI
def edit_api_keys():
    load_dotenv()
    
    def save_api_keys():
        def update_env_key(env_file, key, value):
            with open(env_file, 'r') as file:
                lines = file.readlines()
            with open(env_file, 'w') as file:
                for line in lines:
                    if line.startswith(key + '='):
                        line = f"{key}={value}\n"
                    file.write(line)
        env_vars = {
            'OPENAI_API_KEY': openai_api_key_var.get(),
            'GOOGLE_API_KEY': google_api_key_var.get(),
            'GOOGLE_CSE_ID': google_cse_id_var.get(),
            'WOLFRAM_ALPHA_APPID': wolfram_alpha_appid_var.get(),
            'OPENWEATHERMAP_API_KEY': openweathermap_api_key_var.get(),
            'ZAPIER_NLA_API_KEY': zapier_nla_api_key_var.get(),
            'PINE_API_KEY': pine_api_key_var.get()
        }
        for key, value in env_vars.items():
            update_env_key('.env', key, value)
        restart = messagebox.askyesno("API Keys Saved", "API keys have been saved successfully. Would you like to restart the application?")
        if restart:
            restart_app()
        else:
            api_keys_window.destroy()

    api_keys_window = Toplevel()
    api_keys_window.title("API Keys")
    api_keys_window.iconbitmap(default="icon.ico")
    api_keys_frame = ttk.Frame(api_keys_window, padding="10")
    api_keys_frame.grid(row=0, column=0, sticky="nsew")
    openai_api_key_var = tk.StringVar(value=os.getenv('OPENAI_API_KEY'))
    google_api_key_var = tk.StringVar(value=os.getenv('GOOGLE_API_KEY'))
    google_cse_id_var = tk.StringVar(value=os.getenv('GOOGLE_CSE_ID'))
    wolfram_alpha_appid_var = tk.StringVar(value=os.getenv('WOLFRAM_ALPHA_APPID'))
    openweathermap_api_key_var = tk.StringVar(value=os.getenv('OPENWEATHERMAP_API_KEY'))
    zapier_nla_api_key_var = tk.StringVar(value=os.getenv('ZAPIER_NLA_API_KEY'))
    pine_api_key_var = tk.StringVar(value=os.getenv('PINE_API_KEY'))
    vars = {
        'OPENAI_API_KEY': openai_api_key_var,
        'GOOGLE_API_KEY': google_api_key_var,
        'GOOGLE_CSE_ID': google_cse_id_var,
        'WOLFRAM_ALPHA_APPID': wolfram_alpha_appid_var,
        'OPENWEATHERMAP_API_KEY': openweathermap_api_key_var,
        'ZAPIER_NLA_API_KEY': zapier_nla_api_key_var,
        'PINE_API_KEY': pine_api_key_var
    }
    display_names = {
        'OPENAI_API_KEY': 'OpenAI API Key',
        'GOOGLE_API_KEY': 'Google API Key',
        'GOOGLE_CSE_ID': 'Google CSE ID',
        'WOLFRAM_ALPHA_APPID': 'Wolfram Alpha App ID',
        'OPENWEATHERMAP_API_KEY': 'OpenWeatherMap API Key',
        'ZAPIER_NLA_API_KEY': 'Zapier NLA API Key',
        'PINE_API_KEY': 'Pine API Key'
    }
    row = 0
    for key, var in vars.items():
        display_key = display_names.get(key, key)
        ttk.Label(api_keys_frame, text=display_key + ":").grid(row=row, column=0, sticky="w")
        ttk.Entry(api_keys_frame, textvariable=var).grid(row=row, column=1, sticky="nsew")
        row += 1
    ttk.Button(api_keys_frame, text="Save API Keys", command=save_api_keys).grid(row=row, column=0, pady=(10, 0), columnspan=2)
    api_keys_window.columnconfigure(0, weight=1)
    api_keys_window.rowconfigure(0, weight=1)
    api_keys_frame.columnconfigure(1, weight=1)

# Define the main function
def main():
    def on_submit():
        user_input = user_entry.get()
        user_entry.delete(0, tk.END)

        if user_input:
            chat_history.config(state="normal")
            chat_history.insert(tk.END, f"User: {user_input}\n")
            chat_history.config(state="disabled")
            chat_history.yview(tk.END)

            root.update_idletasks()

            agent_chain.memory.chat_memory.add_user_message(user_input)

            try:
                response = agent_chain.run(input=user_input)
                bot_response = response
            except Exception as e:
                tb_string = traceback.format_exc()

                if "This model's maximum context length is" in tb_string:
                    agent_chain.memory.chat_memory.clear()
                    bot_response = (
                        "Apologies, the last request went over the maximum context length so I have to clear my memory. Is there anything else I can help you with?"
                    )
                else:
                    traceback.print_exc()

                    bot_response = f"Apologies, An error occurred while processing your request: {str(e)}."

        chat_history.config(state="normal")
        chat_history.insert(tk.END, f"{BOT_NAME}: {bot_response}\n")
        chat_history.config(state="disabled")
        chat_history.yview(tk.END)

        agent_chain.memory.chat_memory.add_ai_message(bot_response)

    root = tkinter.Tk()
    root.title(f"{BOT_NAME} Chatbot")
    root.iconbitmap(default="icon.ico")

    chat_frame = ttk.Frame(root, padding="5")
    chat_frame.grid(row=0, column=0, sticky="nsew")

    user_frame = ttk.Frame(root, padding="5")
    user_frame.grid(row=1, column=0, sticky="nsew")

    chat_history = ScrolledText(chat_frame, wrap="word", width=80, height=20, state="disabled")
    chat_history.grid(row=0, column=0, sticky="nsew")

    user_entry = ttk.Entry(user_frame, width=70)
    user_entry.grid(row=0, column=0, sticky="nsew")
    user_entry.focus()
    user_entry.bind("<Return>", lambda event: on_submit())

    settings_button = ttk.Button(user_frame, text="Settings", command=open_settings)
    settings_button.grid(row=0, column=2, padx=(5, 0))
    submit_button = ttk.Button(user_frame, text="Submit", command=on_submit)
    submit_button.grid(row=0, column=1, padx=(5, 0))

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    chat_frame.columnconfigure(0, weight=1)
    chat_frame.rowconfigure(0, weight=1)
    user_frame.columnconfigure(0, weight=5)
    user_frame.rowconfigure(0, weight=1)

    sv_ttk.set_theme("dark")

    root.mainloop()

if __name__ == "__main__":
    main()