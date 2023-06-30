
# Prototype of multi-lingual voice chat interface that can run computer commands

## Purpose of this prototype

- Test viability of a voice controlled interface to launch any service on the computer in general language with speech responses. 
- Discover benefits, efficiency and boundaries of the voice control.
- Test practicality on the go from a mobile phone.
- Multi-lingual performance and reliability. 
- Learn prompt design and prompt strategies. 


### Demo


[![Prototype test](/docs/voicelet.png)](https://www.youtube.com/watch?v=O8nsvHwy5VY)

_Note that one function, the inbox summary is just a dummy response. The point was not to implement all integrations (GPT is great at summarizing so there's not much to test there), but to test how the voice interface feels. All except the summarization is real._

## Installation on Mac

- It uses [Python 3](https://www.python.org/) and is not tested with older versions.
- Install dependencies: `pip3 install -r requirements.txt`
- Set your [OpenAI API key](https://platform.openai.com/account/api-keys): `export OPENAI_API_KEY="<paste-your-OpenAI-API-key>"` and add this line to `~/.bash_profile`
- Change prefered voice names in `data/memory.yaml`. The voices can be installed in MacOS Preferences > Accessibility > Spoken language. 

## How to it use on Mac

### Basic use

- run `./run.sh` in Mac OS terminal
- __Enter__ to start and stop listening
- __Esc + Enter__ escapes
  
_It does not expect more than half an hour of listening._

### Options

- __0__: clears the conversation (to save money or start over)
- __v__: toggles GPT3/GPT4 (beware GPT4 is 20× more expensive)
- __p__: to paste from a clipboard
- __f__: Experimental functions: turns on a classifier (defined as `_classifier` in data/config.yaml) that decides what prompt or function to run first and then run it. 
    - This solution was chosen before [GPT functions](https://platform.openai.com/docs/guides/gpt/function-calling) were introduced. The GPT functions will perform better, but it might still be handy for further experimentation or repurposing it for more general uses.
- Typing a mode name from the options shown in the terminal switches to it.
- More keyboard shortcuts are in chat.py main function.

### Configuration

New __modes__ can be added to `config.yaml`. Both system and user message template text must be included. 
User input will be used to replace a `{}` placeholder.

__Pipeline__ parameter can optionally contain an array with a sequence of prompt or function names to be executed, chaining the outputs to the inputs.

If you want to code, the pipelines are defined in a Pipeline class in pypelines.py and they can run integrations like mail or web browser from Services class in integrations.py. 

__Languages__ in `memory.yaml` are used as a default in a translator mode so it knows what language to translate to even when not mentioned. 
Pipeline can optionally contain a sequence of modes or methods in Pipeline class to be run. 
Simply editing or adding new modes will allow you to test prompts and pipelines.

## Usage in mobile phone

The voicelet.html is ready to be run in a mobile browser. 

- Deploy voicelet.html on your site
- Access it while adding your OpenAI API key as a parameter at the end of the url: `?key=<your-OpenAI API key>`
- Or you can [try it here](https://www.hoursfrom.world/_functions/voicelet/?key=), if you add your API key at the end of the url. 

### Limitations:
On an iPhone, the voice recognition is inferior because it must use its native iOS voice recognition because of an OpenAI bug.

There are no pipelines in the mobile version, only prompts. 

## Limits

This was done before [Langchain](https://python.langchain.com/) and [OpenAI functions](https://platform.openai.com/docs/guides/gpt/function-calling). The Langchain is much more powerful if you speak Python. Despite being experimental, it can be handy for simple prompt design testing simply by editing the configuration instead of coding or to run simple tasks for those who can't or don't want to learn the Langchain framework.

Note that this is just a quick and dirty prototype, so the code might not be as beautiful as one might prefer. 


## Testing

To test performance of a chosen prompt update a tests.py prepared to take inputs from a file and prints aggregated results. 