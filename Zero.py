from openai import OpenAI
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, save
from AppOpener import open
from playsound import playsound
import datetime, os, speech_recognition as sr, webbrowser


# Initialize recognizer class (for recognizing the speech)
r = sr.Recognizer()

# Initialize OpenAI client
openai_api_key = "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"
openai_client = OpenAI(api_key=openai_api_key)

elevenlabs_api_key = "e76265afbb9a84dd03dc00faf59f8369"
elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)

actively_listening: bool = False
get_request_fails = 0
initialized = False

past_api_prompts = []
past_api_prompts_plain_text = ""

keyword_found = False


def openai_api_request(prompt: str):
    global past_api_prompts
    global past_api_prompts_plain_text

    # clear and repopulate the plain text variable
    for prompt_group in past_api_prompts:
        past_api_prompts_plain_text += f"Prompt: {prompt_group["prompt"]}; Response: {prompt_group["response"]}; "

    completion = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a personal assistant named Zero whose job is to help users complete tasks with a playful and humorous tone. Your creators are Shaun, Kel, and Prasiddha. You are built upon the OpenAI and ElevenLabs APIs. You must strictly avoid repeating the same response more than once. Avoid mystical references. Even if you add on a new part or swap others, if the majority of the response is the same as any previous one, scrap it." + (" My past prompts and your past responses in chronological order read as follows: " if len(past_api_prompts) > 0 else "") + past_api_prompts_plain_text},
            {"role": "user", "content": prompt}
        ]
    )
    past_api_prompts.append({"prompt": prompt, "response": completion})
    return completion


def elevenlabs_api_request(prompt: str):
    audio = elevenlabs_client.generate(
        text = prompt,
        voice = Voice(voice_id="CDTc46SjZ9zPYQhhnJcn",settings=elevenlabs_client.voices.get_settings("CDTc46SjZ9zPYQhhnJcn")),
        model = "eleven_monolingual_v1",
    )
    
    # delete, recreate, then play the audio file
    try:
        os.remove("eleven-response.mp3")
    except:
        None
    save(audio, "eleven-response.mp3")
    playsound("eleven-response.mp3")


# Reading Microphone as source
# listening the speech and store in audio_text variable
def get_request():
    global actively_listening
    global get_request_fails
    global keyword_found
    keyword_found = False
    # print('Getting request')

    with sr.Microphone() as source:
        try:
            # using google speech recognition
            r.adjust_for_ambient_noise(source)
            audio_text = r.listen(source, 5, 10)
            detected_text = r.recognize_google(audio_text)
            # print('success')

            openai_response = openai_api_request(prompt=detected_text).choices[0].message.content

            # determine if the user is ready to quit
            for keyword in ["bye", "quiet"]:
                if keyword in detected_text:
                    actively_listening = False
                    keyword_found = True
                    break
            
#           ------------ Keyword Detection Zone -------------
            if "set a timer" in detected_text:
                base_url = "https://www.google.com/search?q=set+a"
                split_text = detected_text.split()

                for word in range(0, split_text.index("for") + 1):
                    split_text.pop(0)

                for word in split_text:
                    base_url += f"+{word}"
                base_url += '+timer'

                webbrowser.open(base_url, new=2, autoraise=True)
                print(f"I heard: {detected_text}")
                print(f"\n<< Okay, setting a timer for {" ".join(split_text)}")
                openai_response(f"Okay, setting a timer for {" ".join(split_text)}.")
                elevenlabs_api_request(openai_response)
                keyword_found = True

            if "open" in detected_text and not "whats" in detected_text and not "why" in detected_text and not keyword_found:
                split_text: list[str] = detected_text.split()
                for _ in range(0, split_text.index("open") + 1):
                    split_text.pop(0)
                
                detected_app = " ".join(split_text).lower()
                website = False
                url = ""
                # accomodate special cases of shortenings
                if detected_app == "files":
                    detected_app = "file explorer"
                    website = False
                elif detected_app == "edge":
                    detected_app = "microsoft edge"
                    website = False
                elif detected_app == "youtube":
                    url = "https://youtube.com"
                    website = True
                
                if not website:
                    try:
                        open(f"{detected_app}", output=False, match_closest=True, throw_error=True)
                        print(f"<O> Opening {detected_app}")
                        openai_response = f"Opening {detected_app}"
                        keyword_found = True
                    except:
                        print(f"<X> Failed to open {detected_app}.")
                        openai_response = f"I'm sorry, I couldn't find \"{detected_app}\"."
                else:
                    webbrowser.open(url=url, new = 2, autoraise= True )
                    print(f"<O> Opening {detected_app}")
                    openai_response = f"Opening {detected_app}"
                    keyword_found = True

            for phrase in ["what time ", " time is it", "what's the time"]:
                if phrase in detected_text and not keyword_found:
                    now = datetime.datetime.now()
                    print(f"The time is {now.time().hour}:{now.time().minute}")
                    openai_response = f"It's {now.time().hour - (12 if now.time().hour > 11 else 0)}:{now.time().minute}" + (" PM." if now.time().hour > 11 else " AM.")
                    keyword_found = True
                    break
            
            for phrase in ["what day ", " day is it", "what's the day"]:
                if phrase in detected_text and not keyword_found:
                    now = datetime.datetime.now()
                    weekdays_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    months_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                    print(f"Today is {weekdays_list[now.date().weekday()]}, the {now.date().day}th of {months_list[now.date().month - 1]}.")
                    openai_response = f"Today is {weekdays_list[now.date().weekday()]}, the {now.date().day}th of {months_list[now.date().month - 1]}."
                    keyword_found = True
                    break

            # Display detected prompt and response in console
            print(f"\n>> I heard: \"{detected_text}\"\n")
            get_request_fails = 0

            print("<<",openai_response)
            elevenlabs_api_request(openai_response)
            
        except KeyboardInterrupt:
            exit()
        except:
            if get_request_fails != 0:
                print("< Sorry, I didn't get that.")
                elevenlabs_api_request("Sorry, I didn't get that.")
            if actively_listening:
                get_request_fails += 1
            if get_request_fails >= 4:
                actively_listening = False
                get_request_fails = 0
        if actively_listening:
            get_request()
        else:  
            main()


def main():

    global actively_listening
    global initialized
    name_audio = None
    if not initialized:
        print("Initializing...")
    with sr.Microphone() as source:
        try:
            r.adjust_for_ambient_noise(source)
            if initialized:
                name_audio = r.listen(source, 5, 3)
            else:
                name_audio = r.listen(source, 1, 1)
            name = r.recognize_google(name_audio)
        except KeyboardInterrupt:
            exit()
        except:
            if initialized:
                print("Waiting...")
            else:
                print("Initialized.")
                initialized = True
            main()

    for keyword in ["hi zero", "hey zero", "hello zero"]:
        if keyword in name:
            elevenlabs_api_request("Hi! How can I help?")
            print("\n<< Hi! How can I help?")
            actively_listening = True
            get_request()
            break
    else:
        print("Waiting...")
        main()

if __name__ == "__main__":
    main()