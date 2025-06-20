
const speed = document.getElementById("speed");
const mode = document.getElementById("drop-down");
const content = document.getElementById("content");
const recordButton = document.getElementById("listen");
const clearButton = document.getElementById("clear");
const shareButton = document.getElementById("share");

var languages = "Czech, English";
var lang = navigator.language.substring(0,2) == 'cs' ? 'cs' : 'en';

var _texts = {
	'guide': {
		'en':"<ul class='guide'><li>Touch to start &amp; stop listening</li><li>Cancel by long touch</li><li>Swipe right for history </li><li>Clear conversation to save bucks</li></ul>", 
		'cs':"<ul class='guide'><li>Ťukni pro spuštění a zastavení poslechu</li><li>Zrušit podržením</li><li>Swipe doprava pro historii </li><li>Maž konverzace pro ušetření</li></ul>"},
	'iPhoneFix': {
		'en': "iPhone recognizes only 1 language as configured. Try Android or desktop for more accurate and multilingual voice recognition.",
		'cs': "<br/><br/>iPhone rozpozná jen 1 jazyk podle nastavení. Zkus Android nebo desktp pro lepší rozpoznávání hlasu a víc jazyků."
		}, 
	'iPhoneAlert':{ 
		'cs': "Povol mi tě poslouchat",
		'en': "Allow me to listen"
		}
	}

var defaults = {
	'model': 'gpt-4o-mini', 
	'system': "You are a concise factual assistant that answers in a way that is easy to understand by reading. No formalities, apologies or confirmations. Your goal is to present correct information."
	}
var _modes = {
	'mini: Concise factual': {pipeline: function(text){ai.chat(text)}, 
		goal: "I'll reply concisely by voice by a cost effective 4o mini model.",
		messages: {
			system: defaults.system},
		model_params: {'model': defaults.model}},
	'Concise factual': {pipeline: function(text){ai.chat(text)}, 
		goal: "I'll reply concisely with the more powerful 4.1 model.\nIt is better at understanding more complex relations in the text, but it's also 30× more expensive.",
		messages: {
			system: defaults.system},
		model_params: {'model': 'gpt-4.1', 'temperature': 0.5}}, 
	'Thinking mini': {pipeline: function(text){ai.chat(text)}, 
		goal: "I'm cost-effective thinking model, yet I'm 10× more expensive.",
		messages: {
			system: defaults.system},
		model_params: {'model': 'o4-mini'}}, 
	'Thinking powerful': {pipeline: function(text){ai.chat(text)}, 
		goal: "I'm powerfull thinking model. I'm 30× more expensive.",
		messages: {
			system: defaults.system},
		model_params: {'model': 'o4-mini'}}, 
	'Translator': {pipeline: function(text){ai.chat(text)},  
		goal: "I translate sentences accurately and keep the meaning unchanged.",
		messages: {
			system: 
				`You are an accurate translator who does not change meaning of the sentences.
				You only translate into the given language. 
				No comments.
				If not specified, translate to the other language from ({}).
				`,	
			user:
				`Show just the translation of the following text without comments.

				Consider the text everything up to '---'

				Text: {}

				--- 

				Translation:`, 
			remember: 0
		},
		/*model_params: {'temperature': 0.1}}, 
	'Rusko-český překladatel': {pipeline: function(text){ai.chat(text)},  
		goal: "Překládám do ruštiny nebo z rušinty. Prostě ťukni, mluv rusky nebo česky, a ťukni znovu pro překlad.", 
		messages: {
			system: 
				`Jsi přesný překladatel mezi ruštinou a češtinou, který nic nekomentuje, nepřidává a nemění význam vět. Snažíš se překládat co nejpřesněji.
				`,	
			user:
				`Přelož následující text co nejpřesněji bez vlastních komentářů mezi ruštinou a češtinou.

				Text: 
				{}
				`, 
			remember: 0
		},*/
		model_params: {'temperature': 0.1}}, 
	'Writer': {pipeline: function(text){ai.chat(text)}, 
		goal:
			`I help you to prepare a text exactly as you say it.
			- Tell me what to write
			- Give me instructions to change it`,
		messages: {
			system: 
				`You are a writer that helps me prepare a text. 
				Add my inputs to the end of the text or do the changes I request.
				- Do not elaborate. No notes or comments.
				- Keep the meaning unchanged.
				- Keep the language of my input.
				- Maintain the text according to instructions.
				- Do not repeat instructions, show just the text.
				`,
			user: 
				`Input:
				{}

				---

				Remove the request to prepare or change the text.
				Reply with the text from my Input or do the changes to the last reply if any. 
				When no instructions were given, just reply with the text. If there is a text in the previous message, add it at the end of it.
				`, 
			remember: 3
		},
		model_params:{temperature: 0}}, 
	'Listmaker': {pipeline: function(text){ai.chat(text)},  
		goal:
			` I maintain a list of topics or tasks
			- braindump your topics
			- instruct how to change them`,
		messages: {
			system: 
				`You are my colleague that maintains a list of topics I suggest.
				- The topic can be also refered as an item, point or task.
				- Add topics I suggest or change the list according to my Inquiry.
				- Keep topics summarized into few words in my language.`,
			user: 
				`Inquiry:{}

				---

				- Identify requests to change the list of my topics in the Inquiry.
				- If there is no request, add topics in the Inquiry at the end of my list.
				- Do not add own suggestions or ideas. List only my topics.
				- Always reply only with just the list of my topics in my language. Do not translate.

				List of my topics I suggested:
				`, 
			remember: 3
		},
		model_params:{temperature: 0}},
	'Corrector': {pipeline: function(text){ai.chat(text)}, 
		goal: "I'm correcting grammar in your inputs.",
		messages: {
			system: "You are a corrector who corrects a grammar in the text if necessary.",
			user: `Text:{}
			
							---
			
							Fix the grammar if necssary.`,
			remember: 3
		},
		model_params:{temperature: 0}}, 
	'Creative': {pipeline: function(text){ai.chat(text)}, 
		goal: "I come up with creative ideas for your requests.",
		messages: {
			system: "You are a creative that comes up with ideas on the given topic.",
			remember: 6
		},
		model_params:{temperature: 1}}, 
	'Fairytaler': {pipeline: function(text){ai.chat(text)}, 
		messages: {
			goal: "I tell children fairy tales according to their wishes",
			system: "Jsi pohádkový robot. Vyprávíš pohádky dětem na jejich přání. Pokud není řečeno jinak, vymysli pohádku přibližně o sedmi odstavcích."},
		model_params: {'temperature': 0.8}},
	'Repeat what I say': {pipeline: function(text){say.say(text)}}
};



function text(id){
	if(lang in _texts[id])
		return _texts[id][lang];
	else
		try { return _texts[id]['en'];}
		catch { return id }
}

var page = 0; 			// current page

var wakelock = null; 	// prevent phone from sleeping

var touche = [0, 0];	// to detect swipe
var pressTimer;			// to detect long touche
var unlocked = false;	// iPhone speach confirmed

class AI {
	constructor(){
		this.key = new URLSearchParams(window.location.search).get('key');

		this.messages = [];
		this.tokens = 0;
		this.modes = _modes;
		this.start();
	}

			
	start(){
		try { this.messages = [this.messageFromTemplate('system', languages)];} 
		catch { this.messages = []; }
	}

	messageFromTemplate(role, text){
		try {
			let template = this.modes[mode.value]['messages'][role];
			if(text)
				text = template.replace('{}', text);
			else
				text = template;
		} 
		catch {}
		
		return {'role': role, 'content': text };
	}

	pipeline(text){
		show(text);
		page = this.messages.length-1;
		this.modes[mode.value].pipeline(text);
	}

	async transcribe(file){
		var formData = new FormData();
		formData.append('file', file);
		formData.append('model', 'whisper-1')

		try {
			const transcription = await fetch("https://api.openai.com/v1/audio/transcriptions", {
				method: 'POST',
				headers: {
					'Authorization': "Bearer "+this.key //,"Content-Type": "multipart/form-data"
				},
				body: formData //,model: "whisper-1"
			});
			const query = await transcription.json();
			// error on iPhone: https://community.openai.com/t/whisper-api-cannot-read-files-correctly/93420
			return (query);
			} 
		catch(e){
			log("Can't transcribe the recording<br/>");
			log(`${e.name} <br/>`);
			//log(`${e.message}<br/>${e.lineNumber}<br/><br/><br/>${e.stack}`);
			return {'error': {'message':"Error in voice recognition"}}
		}
	}

	keepLastMessages() {
		try {
			let keep = this.modes[mode.value]['messages']['remember'];
			if (keep < this.messages.length){
				this.messages = this.messages.splice(this.messages.length - keep);
				if('system' in this.modes[mode.value]['messages'])
					if(this.messages.len == 0 || this.messages[0]['role'] != 'system')
						this.messages.unshift(this.messageFromTemplate('system', languages));
			}
		} 
		catch {}
	}

	clearMessages(keep){
		try {
			if(Keep)
				ai.messages = messages.splice(page, 1) 
			else 
				this.start()
		}
		catch {}
	}

	async chat(question){
		this.messages.push(this.messageFromTemplate('user', question));
		recordButton.textContent = "…thinking";

		let params = this.modes[mode.value].model_params
		if(!('model' in params))
			params.model = default_model
		params.messages = this.messages

		try {

			const response = await fetch("https://api.openai.com/v1/chat/completions", {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Authorization': 'Bearer '+this.key
				},
				body: JSON.stringify(params)
			});

			const reply = await response.json();

			if(typeof(reply) === 'undefined'){
				let err = "Error: AI did not reply:(";
				log(err);
				say.say(err);
			}
			let message = reply['choices'][0]['message'];

			this.messages.push(message);
			this.keepLastMessages();
			this.tokens = reply['usage']['total_tokens'];

			clearButton.textContent = "Clear " + this.tokens + " words";
			show(message['content']);
			page = this.messages.length-1;
			say.say(message['content']);
		} 
		catch (e) {
			console.log(l);
			log(l);
			//log(`${e.name} <br/>`);log(`${e.message}`);
			
			try{
				if('error' in reply){
					let error = reply['error'];
					show(error)
					say.say(error)
				} else { 
					log(`${e.name} <br/>${e.message}`);
				}
			}	 
			catch (f) {
				log(`${f.name} <br/>${f.message}`);
			}
		}
	}
}

class Recorder {
	constructor(){
		this.format = 'mp3';
		this.type = "audio/mpeg"; //audio/mpeg, audio/mp4, audio/x-m4a, not audio/webm
		this.isRecording = false;
		this.mediaRecorder;

		this.process = this.stop;
		this.label = "Shh!"
	}

	async rec() {
		this.isRecording = true;
		window.speechSynthesis.cancel();
		try {
			wakelock = await navigator.wakeLock.request('screen');
			} 
		catch (e) {
			wakelock = true; // iPhones are woke
			}

		// add recording in subclasses
	}

	stop() {
		this.isRecording = false;
		if(this.mediaRecorder)
			this.mediaRecorder.stop();
		return this.label
	}

	toggleRec(){
		if(this.isRecording){
			this.process();
			return this.label;
		} 
		else if(wakelock){
			window.speechSynthesis.cancel();
			try { wakelock.release()} catch {}
			wakelock = null;
			return 'Listen';
			}
		else 
			this.rec();
			return 'STOP rec & Answer!'	// TODO should resove in rec()
	}
}

class iPhoneRecorder extends Recorder {
	
	rec(){				 
		super.rec();
		this.mediaRecorder = new webkitSpeechRecognition();
		this.mediaRecorder.start();
		this.mediaRecorder.onresult = function(e) {
			let result = e.results[0][0].transcript;
			ai.pipeline(result);
		}
		return 'STOP & Answer!'
	}
}

class OpenAIRecorder extends Recorder {
	constructor(){
		super();

		this.recordedAudio = null;	
		this.recordedChunks = [];

		this.process = this.processAudio;
		this.label = "…recognizing";
	}

	async rec() {
		super.rec();
		
		try {
			this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
			this.mediaRecorder = new MediaRecorder(this.mediaStream);
			this.mediaRecorder.addEventListener('dataavailable', event => {
				if (event.data.size > 0)
					this.recordedChunks.push(event.data);
			});

			this.recordedChunks = [];
			this.mediaRecorder.start();

			return 'STOP & Answer!'
		} 
		catch (e) {
			log(e);
			say.say(`Error while recording: ${e.name})`);
			return `Error while recording: ${e.name})`
		}
	}


	stop() {
		super.stop();
		this.mediaStream.getTracks().forEach(track => track.stop()); // free resources
		return this.label
	}

	
	async processAudio() {
		this.stop();
		try {  
			this.mediaRecorder.addEventListener("stop", async () => {
				const audioBlob = new Blob(this.recordedChunks, {type: this.type}); 
				//const audioUrl = URL.createObjectURL(audioBlob);
				this.recordedAudio = new File([audioBlob], "recordedAudio."+this.format, {type: this.type});

				let query = await ai.transcribe(this.recordedAudio);
				
				if(query.hasOwnProperty('text'))
					ai.pipeline(query.text);

				if(query.hasOwnProperty('error')){
					log("Error: "+query['error']['message']);
					say.say(query['error']['message']);}});
		} 
		catch (e) {
			log("Can't save the recording");
			log(e);}
	}
}

class Synthesizer {
	constructor(){
		this.czechChars = /[ěščřžýáíéúůďťňĚŠČŘŽÝÁÍÉÚŮĎŤŇ]/i; 
		this.cyrillic = /[джзийлпнтфцчшщъыьэюяДЖЗИЙЛПНТФЦЧШЩЪЫЬЭЮЯ]/i; //[инп]/i; 

		this.voices = this.getBestVoices();
		}

	getBestVoices(){
		try{
			this.voices = {};
			let ranks = ["enhanced", "premium"]; // from worst to best
			//set best ranked voice per lang
			window.speechSynthesis.getVoices().forEach(voice => {
				let lang = voice.lang.substring(0,2);
				//content.innerHTML += "<br/>"+ lang + ":"+ voice.name;
				if(! (lang in this.voices)){
					this.voices[lang] = voice;
				} else {
					//if(voice.name.toLowerCase().includes('premium')) this.voices[lang] = voice;
					let candidateRank = ranks.findIndex(rank => voice.name.toLowerCase().includes(rank));
					let currentRank = ranks.findIndex(rank => this.voices[lang].name.toLowerCase().includes(rank));
					if(candidateRank>currentRank){
						this.voices[lang] = voice;
					}
				}
			});
		}
		catch (e){
			log(`${e.name} <br/>`);
			log(`${e.message}<br/>${e.lineNumber}<br/><br/><br/>${e.stack}`);
			}
		}

	simplify2read(text){		
		let processed = text.replace(/(```.*?```)/gs, "Example code.\n"); // remove code blocks
		processed = processed.replace(/`/g, "'"); // it reads it as 'back quote'

		processed = processed.replace(/\*+(.*?)\*+/g, '$1') // it pronounces markdown formatting

		// unwoke by removing unreadable gender fluff
		processed = processed.replace(/(\p{L}{3,})(\/á)|(\/a)|\(a\)(?=\s|$)/ug, '$1');

		return processed
		}

	getVoiceByLang(str) {
		const substring = str.substring(0, 100);
		if (this.czechChars.test(substring))
			return this.voices['cs'];
		else if (this.cyrillic.test(substring))
			return this.voices['ru'];
		else
			return this.voices['en'];
		}

	async say(text, callback){
		if ('speechSynthesis' in window) {
			recordButton.textContent = "Shh!";
			let rate = speed.value;
			const utterance = new SpeechSynthesisUtterance();
			utterance.voice = this.getVoiceByLang(text);
			utterance.text = this.simplify2read(text);;
			utterance.rate = rate;

			//content.innerHTML += utterance.voice.lang + ":" + utterance.voice.name;
			utterance.onend = function(event) {
				if(wakelock)
					try { wakelock.release()} catch {}
				wakelock = null;
				recordButton.textContent = "Listen";
				if(callback){
					callback()
					}
				};
			window.speechSynthesis.speak(utterance);

			return 'Shh!'
			} 
		else 
			log("Your phone can't speak");
			return('Listen')
			}
		}

function detectiPhone(){
	return /iPhone/.test(navigator.userAgent) && /Safari/.test(navigator.userAgent);
}

var recorder = detectiPhone() ? new iPhoneRecorder() : new OpenAIRecorder();
var say = new Synthesizer();
var ai = new AI();

function setupUI() {
	try {
		// setup modes from conf
		for(role in ai.modes){
			let option = document.createElement('option');
			option.textContent = role;
			option.value = role;
			mode.appendChild(option);
		}

		// read cookies
		Array.from(document.getElementsByTagName('select')).forEach(dropDown => {
			let id = dropDown.getAttribute('id');
			if (localStorage.getItem(id)){
				dropDown.value = localStorage.getItem(id);
			}
		});
		clear();

		// setup voice synthesizer
		say.getBestVoices();
		try { window.speechSynthesis.addEventListener('voiceschanged', function(){ say.getBestVoices()}) } 
		catch (e) {
			//log("Your phone can not speak:(")
		}
		if(ai.key == null || ai.key.length == 0)
			content.innerHTML = "The ?key is not provided. It must be in address as ?key=<paste your key>\nIf you don't have it, get it on <a href='https://platform.openai.com/account/api-keys'>platform.openai.com/account/api-keys</a>"
		else {
			content.innerHTML  += text('guide');

			
			if(detectiPhone())
				content.innerHTML += text('iPhoneFix');
		}

		document.addEventListener('touchstart', handleTouchStart, false);        
		document.addEventListener('touchend', handleTouchEnd, false);

		longTouch(shareButton, longShare);
		longTouch(recordButton, longListen);
		longTouch(clearButton, clearOne);

		recordButton.addEventListener("click", function(){ 
			if(!unlocked && detectiPhone()){
				say.say(text('iPhoneAlert'), function(){ recordButton.textContent = recorder.toggleRec()});
				unlocked = true;
				return
			}
			unlocked = true;
			recordButton.textContent = recorder.toggleRec();
			});
		clearButton.addEventListener("click", clear);
		mode.addEventListener("change", clear);
		shareButton.addEventListener("click", share);
		speed.addEventListener("change", testSpeed);

		document.addEventListener("visibilitychange", function() {
			if (document.hidden) {	// lost focus
				//window.speechSynthesis.pause();
				window.speechSynthesis.resume();
			} 
		});

	} catch (e) { }
}

setupUI();



function handleTouchStart(evt) {                                         
	touche = [evt.touches[0].clientX, evt.touches[0].clientY];
}

function handleTouchEnd(evt) {
	var diff = [evt.changedTouches[0].clientX - touche[0], evt.changedTouches[0].clientY - touche[1]];

	if(diff[0]>100)
		flip(-1);
	else if(diff[0]<-100)
		flip(1);
}

function share(){
	if(page){
		let text = ai.messages[page]['content'];
		if (navigator.share)
			navigator.share({text: text})
				.then(() => console.log('Successful share'))
				.catch((error) => console.log('Error sharing:', error));
		else navigator.clipboard.writeText(text);}
}

function flip(p) {
	let systemMessages =( ai.messages.length>0 && 'role' in ai.messages[0] && ai.messages[0]['role'] == 'system') ? 1 : 0;
	if(!page)
		page = ai.messages.length-1;
	page += p;
	if(page < systemMessages)
		page = systemMessages; 
	if(page > ai.messages.length)
		page = ai.messages.length-1;
	if(page < ai.messages.length && page >= systemMessages)
		show(ai.messages[page]['content']);
}


function longTouch(element, action){
	element.addEventListener('touchstart', function(event){ 
			pressTimer = performance.now(); 
			event.preventDefault()
		}, 
		{passive: false});
	element.addEventListener('touchend', action, {passive: false});
}

function longShare(event){
	if(performance.now() - pressTimer > 1000){
		try { (new Audio(URL.createObjectURL(recorder.recordedAudio)).play()) } catch {}
		event.preventDefault();}  
	else 
		event.target.click()
}

function longListen(event){
	if(performance.now() - pressTimer > 1000){
		if(recorder.isRecording){
			recorder.stop();
			recordButton.textContent = "Listen"; 
			try { wakelock.release()} catch {}
			wakelock = null;}
		else 
			try { 
				if(content.innerText)
					ai.modes[mode.value].pipeline(content.innerText);
				else if (navigator.clipboard){
					navigator.clipboard.readText().then(clipText => {
						content.innerHTML = clipText;
						ai.modes[mode.value].pipeline(clipText);
						});}} 
			catch (e) {
				log(e)}
		event.preventDefault();}
	else 
		event.target.click()
}

function clearOne(){
	if(performance.now() - pressTimer > 1000){
		ai.clearMessages(1);
		event.preventDefault();}  
	else 
		event.target.click()
}

function log(text){
	content.innerHTML += text + " ";
}
function show(text){
	content.innerHTML = enhance4screen(text);
	shareButton.textContent = navigator.share ? 'Share' : 'Copy';
}

function enhance4screen(text){
	text = text.replaceAll("<", "&lt;").replaceAll(">", "&gt;");
	let pattern = /^(?:\s*)```([\s\S]*?)```\s*$/gm;
	text = text.replace(pattern, '\n<pre><code>' + '$1' + '</code></pre>\n');
	
	text = text.replace(/\n/g, "<br/>\n");

	// convert markdown to html

	// WARNING! This will replace elements with ** whatever ** at the same line on the code too and I don't care for this prototype. 

	//text = text.replace(/(?:\s*)\*\*([\s\S]*?)\*\*\s*/gm, '<strong>$1</strong>\n');
	text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
	//text = text.replace(/\*(.*?)\*/g, '<em>$1</em>')
	text = text.replace(/^###+ (.+)$/gm, '<h3>$1</h3>\n')
	text = text.replace(/^## (.+)$/gm, '<h2>$1</h2>\n')
	text = text.replace(/^# (.+)$/gm, '<h1>$1</h1>\n')
	
	return text
}

function testSpeed(){
	localStorage.setItem('speed', this.value);
	let sel = speed.options[speed.selectedIndex].innerHTML;

	say.say("The speed of speaking set to " + sel, function(){ say.say("Rychlost řeči nastavena na " + sel);});
	
}

function clear(){
	ai.start()
	if('goal' in ai.modes[mode.value])
		content.innerHTML = ai.modes[mode.value].goal.replaceAll("\n","<br/>");
	else
		content.innerHTML = ""
	
	clearButton.textContent = "";
	shareButton.textContent = ""
	tokens = 0;
}