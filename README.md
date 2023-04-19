![Alfred](docs/alfred.png)
# A.L.F.R.E.D. - Artificial Lifeform Rendered for Expedient Discourse
Alfred is a personal voice assistant inspired by the popular butler, you know the one. It is designed to answer queries and perform tasks using the OpenAI GPT-3.5-turbo API. The assistant uses speech recognition and synthesis to provide a natural language interface. Alfred is a helpful assistant who has some concerns about local crime and certainly does not know who that masked vigilante is.

## Features
* Speech recognition using the speech_recognition and whisper libraries
* Speech synthesis using Amazon Polly
* Uses OpenAI GPT-3.5-turbo for AI-powered conversation
* Activates with a hotkey: ctrl+shift+1
* Terminates the conversation when the user says "Thank you" or a similar phrase

## Setup

1. After cloning the repo locally and unziping, in the root of the project, create an environment based on Python 3.10 and activate it (Pytorch and Whisper aren't compatible with later versions):
```
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

3. Create a .env file in the root and add your OpenAI API Key like this:
```
OPENAI_API_KEY=your_openai_api_key
```

4. Set up an AWS account and configure the AWS CLI with your credentials. This is necessary for using Amazon Polly for speech synthesis.

5. If you'd like, you can update the hotkey (currently CTRL+Shift+1) to whatever you'd like in the main.py file

## Usage
1. Run the main script:
```
python main.py
```

2. Press the hotkey (default is CTRL+Shift+1)

3. Speak your query or command.

4. Alfred will respond with synthesized speech.

5. To end the conversation, say "Thank you" or a similar phrase.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Roadmap
* Use a library such as pyttsx3 to handle text to speech locally, as AWS incurs cost
* Implement custom wake word recognition to prompt
* Release as a Windows service
* Implement support for llama.cpp api to run entirely locally using GPT4All, Vicuna and Koala among others

## License
This project is licensed with GNU General Public License Version 3, see LICENSE.md for more information
