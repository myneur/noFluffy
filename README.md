 # Prototype of voice chat interface that can run computer commands

## Purpose of this prototype

- Test viability of voice controlled interface to lauch any computer service by general language and get response by speech. 
- Discover benefits, efficiency and boundaries of the voice control.
- Test practicality on the go from mobile phone.
- Multi-lingual performance and reliability. 
- Learn prompt design and prompt strategies. 

## Limits

This was done before Langchain and OpenAI functions. Langchain is much more powerful if you speak python. Despite this was done as experimental, it can be handy for simple prompt design testing simply by editing the configuration instead of coding or to run simple tasks for thosw who can't or don't want to learn the Langchain framework.

## Installation on Mac

### Install python 3

- You have the python, right?
- Install dependencies `pip3 install -r requirements.txt`
- Set OpenAI API key generated on [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys): `export OPENAI_API_KEY="<paste-your-OpenAI-API-key>"`
- Change prefered voice names in data/memory.yaml. The voices must be installed in your Mac. 

## How to it use on Mac

### Basic use

- run `./run.sh` in Mac OS terminal app in the dir you installed it to
- __Enter__ to start and stop listening
    - It does not expect more than half an hour of listening. 
- __Esc + Enter__ escapes

### Options

Typing a mode name from the options shown in the terminal switches to it
– __0__ clears conversation (to save money or start over)
– __v__ toggles GPT3/GPT4 (GPT4 is 20xx  more expensive)
– __p__ to paste from clipboard
– __f__ Experimental: turns on a classifier (defined as `_classifier` in data/config.yaml) that decides what function to run and then run it. 
    – This solution was chosen before GPT functions were introduced. The GPT functions will perform better, but might be still handy for experimentation reporpused for more general uses when you speak python.

– More keyboard shortcuts are in chat.py main function.

### Configuration

New __modes__ can be added to config.yaml in the YAML format under modes node. Both system and user message template text mus be present. 
{} will be replaced with user input and must be included
__Languages__ are used as default by a translator mode. They get updated if you ask the translator to translate into a different language in the prompt.
Pipeline can optionally contain a sequence of modes or methods in Pipeline class to be run. 
Simply editing or ading new modes will allow you to test prompts and pipelines.

## Usage in mobile phone

The voicelet.html is ready to run in your browser. 

- Deploy voicelet.html on your site
- Access site on while adding your OpenAI API key as a parameter into the url: ?key=<your-OpenAI API key>

Limitations: on iPhone, the voice recognition is inferior because it must use its native iOS voice recognition because of an OpenAI bug.


## Testing

To test prompt aggregated performance, a tests.py can be used. 