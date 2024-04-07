from openai import OpenAI
from elevenlabs.client import ElevenLabs
import tkinter, datetime, speech_recognition as sr
from math import sin, cos, radians, pi


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

now = datetime.datetime.now()
keyword_found = False


class ZeroAIUI:
    def __init__(self, master: tkinter.Tk) -> None:
        # define window and parameters
        self.master = master
        self.master.title("ZeroAI")
        self.master.geometry("800x800")
        self.master.resizable(False,False)

        self.canvas = tkinter.Canvas(self.master, width=800, height=800)
        self.canvas.pack()

        # other necessary parameters
        self.is_listening = False
        self.is_muted = False

        # define locations of animated objects
        self.slash_top_point = [460,330] # DO NOT CHANGE
        self.slash_bottom_point = [340,470] # DO NOT CHANGE
        self.zero_height_from_center = 50
        self.CENTER = [400,400]
        self.zero_bob_direction = "up"
        self.text_box_showing = False

        # define timers
        self.slash_rotation_timer = 0
        self.slash_rotation_timer_speed = 0.025
        self.zero_bob_timer = 0
        self.bob_aligned = True
        self.text_box_sliding_timer: float = 0

        self.set_keybinds()
        self.initialize_ui_elements()
        self.draw_screen()


    def decrement_timers(self):
        # slash rotation
        if self.slash_rotation_timer < 0:
            self.slash_rotation_timer += self.slash_rotation_timer_speed
        elif self.slash_rotation_timer > 0:
            self.slash_rotation_timer -= self.slash_rotation_timer_speed
        if self.slash_rotation_timer < 0.05 and self.slash_rotation_timer > -0.05:
            self.slash_rotation_timer = 0
        
        # bobbing
        self.bob_max = 75
        self.bob_min = 50
        self.bob_middle = (self.bob_max + self.bob_min) / 2
        self.bob_speed = 0.05
        self.zero_height_from_center += self.zero_bob_timer
        if self.is_listening:
            if self.bob_aligned:
                if self.zero_bob_direction == "up":
                    if self.zero_height_from_center < self.bob_middle:
                        self.zero_bob_timer += self.bob_speed
                    elif self.zero_height_from_center >= self.bob_middle:
                        self.zero_bob_timer -= self.bob_speed
                    
                    if round(self.zero_height_from_center) == self.bob_max:
                        self.zero_bob_direction = "down"
                
                elif self.zero_bob_direction == "down":
                    if self.zero_height_from_center <= self.bob_middle:
                        self.zero_bob_timer -= self.bob_speed
                    elif self.zero_height_from_center > self.bob_middle:
                        self.zero_bob_timer += self.bob_speed

                    if round(self.zero_height_from_center) == self.bob_min:
                        self.zero_bob_direction = "up"
                
                if self.zero_height_from_center < self.bob_min:
                    self.zero_height_from_center = self.bob_min
                if self.zero_height_from_center > self.bob_max:
                    self.zero_height_from_center = self.bob_max
            else:
                if self.zero_height_from_center > 50:
                    self.zero_height_from_center -= 0.50
                if self.zero_height_from_center < 50:
                    self.zero_height_from_center = 50
                    self.bob_aligned = True
        else:
            self.zero_bob_timer = 0

        # text box
        self.text_box_sliding_timer -= 1
        if self.text_box_sliding_timer < 0:
            self.text_box_sliding_timer = 0
        if self.text_box_showing:
            self.canvas.moveto(self.text_box,"", self.sine_between(800,600,self.text_box_sliding_timer/100))
            self.canvas.moveto(self.text_box_contents, "", self.sine_between(810,610,self.text_box_sliding_timer/100))
        else:
            self.canvas.moveto(self.text_box,"", self.sine_between(600,800,self.text_box_sliding_timer/100))
            self.canvas.moveto(self.text_box_contents, "", self.sine_between(610,810,self.text_box_sliding_timer/100))


    def show_hide_text_box(self):
        if self.text_box_showing and self.text_box_sliding_timer == 0:
            self.text_box_showing = False
            self.text_box_sliding_timer = 100
        elif self.text_box_showing == 0:
            self.text_box_showing = True
            self.text_box_sliding_timer = 100
    

    def toggle_mute(self):
        if self.is_muted:
            self.is_muted = False
            self.canvas.create_rectangle(5,5,150,100,fill="#00CC00",activefill="#20FF20",width=5,activewidth=7,tags="MuteButton")
            self.canvas.create_text(77,50,anchor="center",font=("",25),text="Mute?",tags="MuteButtonText",fill="black",activefill="#555555")
        else:
            self.is_muted = True
            self.canvas.create_rectangle(5,5,150,100,fill="#CC0000",activefill="#FF2020",width=5,activewidth=7,tags="MuteButton")
            self.canvas.create_text(77,50,anchor="center",font=("",25),text="Muted",tags="MuteButtonText",fill="white",activefill="#AAAAAA")


    def listening_toggle(self):
        if self.slash_rotation_timer == 0:
            if self.is_listening:
                self.is_listening = False
                self.slash_rotation_timer += 2
            else:
                self.is_listening = True
                self.slash_rotation_timer += -2
            if not self.zero_height_from_center == 50:
                self.bob_aligned=False

    def set_keybinds(self):
        self.master.bind("<a>", lambda event: self.listening_toggle())
        self.master.bind("<s>", lambda event: self.show_hide_text_box())
        self.canvas.tag_bind("MuteButton", "<Button-1>", lambda event: self.toggle_mute())
        self.canvas.tag_bind("MuteButtonText", "<Button-1>", lambda event: self.toggle_mute())

    def initialize_ui_elements(self):
        self.text_box = self.canvas.create_rectangle(5,600,795,795,width=5,fill="#B0B0B0",outline="black")
        self.text_box_contents = self.canvas.create_text(15,610,anchor="nw",width=760,text="this is a sample piece of text to show what is possible in the future of iterations of Zero.", font=("",20))
        self.canvas.create_rectangle(5,5,150,100,fill="#00CC00",activefill="#20FF20",width=5,activewidth=7,tags="MuteButton")
        self.canvas.create_text(77,50,anchor="center",font=("",25),text="Mute?",tags="MuteButtonText",fill="black",activefill="#555555")

    def draw_screen(self):
        self.canvas.delete("ZeroBody", "ZeroSlash")
        self.decrement_timers()

        self.canvas.create_oval(325,300-self.zero_height_from_center,475,500-self.zero_height_from_center,width=25,fill="white",tags="ZeroBody")
        self.canvas.create_line(self.slash_top_point[0],self.slash_top_point[1]-self.zero_height_from_center,self.slash_bottom_point[0],self.slash_bottom_point[1]-self.zero_height_from_center,width=15,tags="ZeroSlash")
        self.slash_top_point = self.rotate([self.slash_top_point],self.slash_rotation_timer,self.CENTER)[0]
        self.slash_bottom_point = self.rotate([self.slash_bottom_point],self.slash_rotation_timer,self.CENTER)[0]
        self.master.after(10, self.draw_screen)


    def sine_between(self, min: float, max: float, percent: float):
        return (max + 0.5 * (1-cos(percent*pi)) * (min - max))


    def rotate(self, points: list[list[float]], angle: float, center: list[float]) -> list[list[float]]:
            angle = radians(angle)
            cos_val = cos(angle)
            sin_val = sin(angle)
            cx, cy = center
            new_points = []
            for x_old, y_old in points:
                x_old -= cx
                y_old -= cx
                x_new = x_old * cos_val - y_old * sin_val
                y_new = x_old * sin_val + y_old * cos_val
                new_points.append([x_new + cx, y_new + cy])
            return new_points

if __name__ == "__main__":
    root = tkinter.Tk()
    ai_window = ZeroAIUI(root)
    root.mainloop()