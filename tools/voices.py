# You can use this to see what voices are available in Windows
# It won't sound good, but it's faster than Bark and freer than ElevenLabs so it is what it is for now

import pyttsx3

engine = pyttsx3.init()

# Get the system's available voices
voices = engine.getProperty('voices')

for voice in voices:
    # Activate the voices one by one
    engine.setProperty('voice', voice.id)
    
    # Text-to-speech the message to test the voice
    engine.say('This is a test of the Windows voices')
    
    # Print the active's voice id
    # https://pyttsx3.readthedocs.io/en/latest/engine.html#pyttsx3.voice.Voice
    print (f'id: "{voice.id}".' )

# Wait while the text-to-speech engine is working
engine.runAndWait()