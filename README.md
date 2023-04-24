![Alfred](docs/alfred.png)
# A.L.F.R.E.D. - Artificial Lifeform Rendered for Expedient Discourse
Alfred is a LangChain and GPT-3.5-turbo powered personal assistant for you computer!<br>
<sub>Image generated with Blue Willow AI on Discord</sub>

## Latest update
* Added ability to switch between pyttsx3 and Bark for voice synthesis
* Removed hotkey for now
* Added intro.wav so that you know when it's done loading and is waiting for wake word (it was generated with Bark, that should give you an idea of the voice quality)
* Made Barks history_prompt (also known as the voice) changable in one spot
* Exceptions now loop back to wake word detection instead of crashing

## Features
* Natural language integration with Zapier, enabling Alfred to access, use and manage over 5000 applications
* Speech recognition using the speech_recognition and whisper libraries
* Speech synthesis using pyttsx3 or Bark (https://github.com/suno-ai/bark)
* Uses LangChain to use tools to answer questions with more current data
* Activate with a spoken wake word "Alfred" - user editable
* Terminates the conversation when the bot says "You're welcome" or a similar phrase
* Configurable tools for LangChain, so if you don't have an API for a tool or don't want the tool, you can disable it

## Setup

1. Clone the repo, cd into the root, create an environment based on Python 3.10 and activate it:
```
git clone https://github.com/masrad/ALFRED.git
cd ALFRED
C:\PATHTOYOUR\Python310\python.exe -m venv venv
.\venv\Scripts\activate
```

2. Next, install the required packages:
```
pip install -r requirements.txt
```

2.1 Install ffmpeg, as whisper requires this to work:
```bash
# on Ubuntu or Debian
sudo apt update && sudo apt install ffmpeg

# on Arch Linux
sudo pacman -S ffmpeg

# on MacOS using Homebrew (https://brew.sh/)
brew install ffmpeg

# on Windows using Chocolatey (https://chocolatey.org/)
choco install ffmpeg

# on Windows using Scoop (https://scoop.sh/)
scoop install ffmpeg

# on Windows using the less good way
https://www.geeksforgeeks.org/how-to-install-ffmpeg-on-windows/
```

3. Create a .env file or rename the example in the root and update the information:
```
OPENAI_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here
GOOGLE_CSE_ID=your-key-here
WOLFRAM_ALPHA_APPID=your-key-here
OPENWEATHERMAP_API_KEY=your-key-here
```

4. If you'd like, you can update the Wake Word to whatever you'd like in the main.py file

## Usage
1. Run the main scrript:
```
python main.py
```

2. Speak the Wake Word "Alfred"

3. Once you hear a chime, Speak your query or command.

4. The assistant will respond with synthesized speech.

5. To end the conversation, say "Thank you" or a similar phrase.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Tools
If you would like to use any of the tools I have included, you will need to follow a few instructions
### Zapier
1. Create a Zapier Dev account
* Go to https://zapier.com/l/natural-language-actions and request API access (it's pretty instant)
* Begin making Actions in Zapier, choose "Let AI Guess" for most fields, and the AI will determine what should go in that field
* Copy your key into the .env file at ZAPIER_NLA_API_KEY
* You're done. You can use complex chains such as "Summarize the last email I got about the TPS reports and add it to my todo list so that I will remember to review them tomorrow. Also ask Greg in Teams what he thinks about the TPS reports and add a funny gif to the message too."
### Google Search
1. Get Google API key
* Go to https://console.cloud.google.com/apis/dashboard while signed in
* Create a New Project
* Name the project and assign a location (if applicable)
* Select "Credentials" on the side bar, and click CREATE CREDENTIALS at the top of the page
* Click Create an API Key and copy the key that it creates to your .env file under GOOGLE_API_KEY
* Click on "Enabled APIs & Services" on the sidebar, and click ENABLE APIS AND SERVICES at the top of the page
* Search for, and click "Custom Search API", click ENABLE
2. Create a custom search engine
* From the Google Custom Search homepage ( http://www.google.com/cse/ ), click Create a Custom Search Engine.
* Type a name and description for your search engine.
* Under Define your search engine, in the Sites to Search box, enter at least one valid URL (For now, just put www.anyurl.com to get past this screen. More on this later ).
* Select the CSE edition you want and accept the Terms of Service, then click Next. Select the layout option you want, and then click Next.
* Click any of the links under the Next steps section to navigate to your Control panel.
* In the left-hand menu, under Control Panel, click Basics.
* In the Search Preferences section, select Search the entire web but emphasize included sites.
* Click Save Changes.
* In the left-hand menu, under Control Panel, click Sites.
* Delete the site you entered during the initial setup process.
* Enter the Search engine ID you get from the Basics page into the .env file at GOOGLE_CSE_ID

### Wolfram Alpha
* Create a developer account and get your APP ID from here: https://developer.wolframalpha.com/
* Enter the Application ID from Wolfram Alpha into the .env file at WOLFRAM_ALPHA_APPID

### Open Weather Map
* Create a developer account and sign up for an API key here: https://openweathermap.org/api/
* Follow the prompts to make an API, as long as you aren't asking too often a free acount is fine
* Enter the API into the .env at OPENWEATHERMAP_API_KEY

## Important
Remember, if you want to use a service and have an API key setup, you must enable the tool by updating the bool in the Settings class:
```
enable_search: bool = True
enable_wikipedia: bool = True
enable_calculator: bool = True
enable_wolfram_alpha: bool = True
enable_weather: bool = False
```

## Important
Remember, if you want to use a service and have an API key setup, you must enable the tool by updating the bool in the Settings class:
```
enable_search: bool = True
enable_wikipedia: bool = True
enable_calculator: bool = True
enable_wolfram_alpha: bool = True
enable_weather: bool = True
enable_zapier: bool = True
```
If you want to enable Bark:
```
use_bark: bool = True
```
If you want to change Barks voice:
```
history_prompt: str = "en_speaker_1"
```
The available "voices" that you can use should be located in the venv folder, likely somewhere like \venv\Lib\site-packages\bark\assets\prompts
## License
This project is licensed with GNU General Public License Version 3, see LICENSE.md for more information
