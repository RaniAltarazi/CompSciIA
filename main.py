import whisper
import pyaudio
from tkinter import *
from tkinter import ttk
from tkinter import filedialog as fd
import wave
from multiprocessing import Process, Queue, Event
import threading
import openai
from googletrans import Translator
import os 
import zipfile
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play

openai.api_key = "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"
exitEvent = Event()
q1 = Queue()
q1save = Queue()
q2 = Queue()
q3 = Queue()
q4 = Queue()
q4save = Queue()
q5 = Queue()
q5save = Queue()
q6save = Queue()

class save():
    def __init__(self):
        self.srcText =""
        self.destText = ""
        self.srcAudio = []
        self.destAudio = []
        qlist = [q1save,q4save,q5save,q6save]

        for i,eachq in enumerate(qlist):
            while(eachq.empty()==False):
                if (i ==1):
                    self.srcText = self.srcText+ " "+ eachq.get()
                if (i ==2):
                    self.destText = self.destText+ " "+ eachq.get()
                if (i ==0):
                    self.srcAudio.append(eachq.get())
                if (i == 3):
                    self.destAudio.append(eachq.get())
    def saveZIP(self,filepath,files):
         print(filepath)
         with zipfile.ZipFile(filepath, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                if (file ==0):
                    with open("englishText.txt","w")as f:
                        f.write(self.srcText)
                    f.close()
                    zf.write('englishText.txt')
                    os.remove("englishText.txt") 
                if (file ==1):
                    with open("spanishText.txt","w")as f:
                        f.write(self.destText)
                    f.close()
                    zf.write("spanishText.txt")
                    os.remove("spanishText.txt")
                if (file ==2):
                    with wave.open("englishAudio.wav","wb") as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth (2)
                            wf.setframerate(44100)
                            wf.writeframes(b''.join(self.srcAudio))
                            wf.close
                    zf.write("englishAudio.wav")
                    os.remove("englishAudio.wav")
                if (file ==3):
                    with wave.open("spanishAudio.wav","wb") as wf:
                         wf.setnchannels(1)
                         wf.setsampwidth(2)
                         wf.setframerate(44100)
                         wf.writeframes(b''.join(self.destAudio))
                         wf.close
                    zf.write("spanishAudio.wav")
                    os.remove("spanishAudio.wav")
            zf.close()
class recorder(Process):
    def __init__(self,q1,q2,q1save,exitEvent):
            Process.__init__(self)
            self.q1=q1
            self.q2 = q2
            self.q1save = q1save
            self.exitEvent = exitEvent
            self.chunk = 1024
            self.format = pyaudio.paInt16
            self.channels = 1
            self.rate = 44100
            self.seconds = 15   
    def prepareRecorder(self,open):
            if (open):
                self.stream = self.p.open(
                    rate=self.rate,
                    format=self.format,
                    channels=self.channels,
                    input=True,
                    frames_per_buffer=self.chunk
                )
            if not open:
                self.stream.stop_stream()     
                self.stream.close()
                self.p.terminate()
    def saveDataForSave (self,data):
            self.q1save.put(data)
    def saveData(self,frames,sampleWidth):
            self.q1.put (frames)
            self.q2.put (sampleWidth)
    def run (self):
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(
                    rate=self.rate,
                    format=self.format,
                    channels=self.channels,
                    input=True,
                    frames_per_buffer=self.chunk)
            while (self.exitEvent.is_set() is False):
                print("running")
                frames =[]
                for _ in range (0, int(self.rate/ self.chunk * self.seconds)):
                        data = self.stream.read(self.chunk)
                        self.saveDataForSave(data = data)
                        frames.append(data)
                self.saveData(frames=frames,sampleWidth = self.p.get_sample_size(self.format))
            self.stream.stop_stream()     
            self.stream.close()
            self.p.terminate()
class prepData(Process):
    def __init__(self,q1,q2,q3,exitEvent):
            Process.__init__(self)
            self.q1=q1
            self.q2 = q2
            self.q3 = q3
            self.exitEvent = exitEvent
            self.channels = 1
            self.rate = 44100
            self.dataFile= "outputwave.wav"

    def saveData(self,dataPath):
         self.q3.put(whisper.load_audio(dataPath))
    def run (self):
            while (self.exitEvent.is_set() is False  or (self.q1.empty() is False and self.q2.empty() is False)):
                    with wave.open(self.dataFile,"wb") as wf:
                            wf.setnchannels(self.channels)
                            wf.setsampwidth (self.q2.get())
                            wf.setframerate(self.rate)
                            wf.writeframes(b''.join(self.q1.get()))
                            wf.close
                    self.saveData(self.dataFile)
            os.remove(self.dataFile)
class transcribe(Process):
    def __init__(self,teacherL,q3,q4,q4save,exitEvent):
            Process.__init__(self)
            self.lang = teacherL
            self.q3=q3
            self.q4 = q4
            self.q4save = q4save
            self.exitEvent = exitEvent
            self.model = whisper.load_model("small")
            self.options = whisper.DecodingOptions(language=teacherL, fp16=False)
    def saveData(self,data):
         self.q4.put(data)
         self.q4save.put(data)
    def run(self):  
            while (self.exitEvent.is_set()==False or self.q3.empty()==False):
                    data = self.q3.get()
                    audio = whisper.pad_or_trim(data)
                    mel = whisper.log_mel_spectrogram(audio).to(self.model.device) 
                    result = whisper.decode(self.model, mel, self.options)
                    self.saveData(result.text)
class translateText(Process):
    def __init__(self,originalLang,finalLang,q4,q5,q5save,q6save,exitEvent):
            Process.__init__(self)
            self.oglang = originalLang
            self.finalL = finalLang
            self.q4 = q4
            self.q5 = q5
            self.q5save = q5save
            self.q6save = q6save
            self.exitEvent = exitEvent
            self.filePath = "espOut.mp3"
            self.first = True
    def saveData(self,data):
             self.q5.put(data)
             self.q5save.put(data)
    def saveSpeechData(self,data):
             self.q6save.put(data)

    def toSpeech (self):
            data = []
            while (not self.exitEvent.is_set() or not self.q5.empty()):
                if (not self.q5.empty()):
                    print("speek")
                    tts = gTTS(self.q5.get(),lang= "es")
                    for idx, decoded in enumerate (tts.stream()):
                        data.append(decoded)
                    self.saveSpeechData(data)
                    self.saveSpeechData(tts)
                    tts.save(self.filePath)                   
                    song = AudioSegment.from_mp3(self.filePath)
                    play(song)
            os.remove(self.filePath)       
    def run(self):
            t1 = threading.Thread(target=self.toSpeech)
            self.translator = Translator()
            while (self.exitEvent.is_set() == False or self.q4.empty()==False):
                    if (self.first):
                        t1.start()
                        self.first = False
                    result = self.translator.translate(text = self.q4.get(),src = self.oglang, dest = self.finalL).text
                    self.saveData(result)
class main():            
        def __init__(self, running,teachL, studentL):
            if (running ==True):
                exitEvent.clear()
                p1 = recorder(q1,q2,q1save,exitEvent)
                p1.start()
                p2 = prepData(q1,q2,q3,exitEvent)
                p2.start()
                p3 = transcribe(teachL,q3,q4,q4save,exitEvent)
                p3.start()
                p4 = translateText(teachL,studentL,q4,q5,q5save,q6save,exitEvent)
                p4.start()
                
            if (running == False):
                exitEvent.set()             
class gui():
    def __init__(self):
        self.translator = Translator()
        self.usersLang = "es"
        self.teacherLang = "en"
        self.root = Tk()
        self.root.state("zoomed")
        self.root.geometry("500x500")
        self.root.title("Recorder")
        self.tabControl =ttk.Notebook(self.root)
        self.tab1 = Frame(self.tabControl,bg="light blue")
        self.tab2 = Frame(self.tabControl,bg = "light blue")
        self.tabControl.add(self.tab1, text ='Main Tab')
        self.tabControl.add(self.tab2, text ='Record Tab')
        self.tabControl.pack(expand = 1, fill ="both")
        self.variablesUser = StringVar(self.tab1)
        self.variablesTeach = StringVar(self.tab1)
        self.welcome_new = Label(self.tab1, text="Welcome User!")
        #self.languageOptions = ["english","spanish","french","chinese (simplified)","arabic","german","russian","vietnamese","greek","italian"]
        #self.UserLang = Label(self.tab1,text="Your Language: ")
        #self.TeacherLang = Label(self.tab1,text="Teacher Language: ")
        #self.variablesUser.set(self.languageOptions[0])
        #self.variablesTeach.set(self.languageOptions[0])
        #self.selectLangUser = OptionMenu(self.tab1, self.variablesUser, *self.languageOptions)
        #self.sleectLangTeacher = OptionMenu(self.tab1, self.variablesTeach, *self.languageOptions)
        self.nextButton = Button(self.tab1, text="next",command=self.gonext)
        self.welcome_new.grid(row=0,column=0,sticky="",padx=3,pady=3)
        #self.UserLang.grid(row=1,column=0,sticky="",padx=3,pady=3)
        #self.selectLangUser.grid(row=1,column=1,sticky="",padx=3,pady=3)
        #self.TeacherLang.grid(row=2,column=0,sticky="",padx=3,pady=3)
        #self.sleectLangTeacher.grid(row=2,column=1,sticky="",padx=3,pady=3)
        self.nextButton.grid(row=3,column=2,sticky="",padx=3,pady=3)
        self.buttonvars = [StringVar(),StringVar(),StringVar()]
        self.buttonvars[0].set("Start Recording")
        self.buttonvars[1].set("Stop Recording")
        self.buttonvars[2].set("Save")
        self.start_button = Button(self.tab2, textvariable=self.buttonvars[0], command = self.startRecording, bg="#3d3d3d", fg="white",height=5,width=20)
        self.stop_button = Button(self.tab2, textvariable=self.buttonvars[1], command=self.stopRecording, bg="#3d3d3d", fg="white",height=5,width=20)
        self.save_button = Button(self.tab2, textvariable = self.buttonvars[2], command=self.openSave,height=5,width=20)
        self.originalTextLabel = Label(self.tab2,text=(self.translator.translate(text = "English Transcription",src = "en", dest = "es").text))
        self.originalText = Text(self.tab2,height=20,width=100, bg="white",state=DISABLED)
        self.translationTextLabel =  Label(self.tab2,text= (self.translator.translate(text = "Spanish Transcription",src = "en", dest = "es").text))
        self.translationText = Text(self.tab2,height=20,width=100, bg="white",state=DISABLED)
        self.start_button.grid(row=0,column=0,sticky="",padx=3, pady=3,columnspan=3)
        self.stop_button.grid(row=1,column=0,sticky="",padx=3, pady=3,columnspan=3)
        self.save_button.grid(row=2,column=0,sticky="",padx=3, pady=3,columnspan=3)
        self.originalTextLabel.grid(row=0,column=3,sticky="",padx=3,pady=3,columnspan=1)
        self.originalText.grid(row=0,column=4, sticky="",padx=3,pady=3,columnspan=5)
        self.translationTextLabel.grid(row=1,column=3,sticky="",padx=3,pady=3,columnspan=1)
        self.translationText.grid(row=1,column=4, sticky="",padx=3,pady=3,columnspan=5)
        self.root.mainloop()
    def startRecording(self):
        self.recording = True
        main(True,self.teacherLang,self.usersLang)
    def stopRecording(self):
        self.recording = False
        main(False,self.teacherLang,self.usersLang)
    def openSave(self):
        self.top= Toplevel(self.root)
        self.top.geometry("500x500")
        self.top.title("Child Window")
        self.varsList = [IntVar(),IntVar(),IntVar(),IntVar()]
        engTextSave = Checkbutton(self.top, text= "Save English Text",variable=self.varsList[0])
        espTextSave = Checkbutton(self.top, text= "Save Spanish Text",variable=self.varsList[1])
        engMp3Save = Checkbutton(self.top, text= "Save English MP3",variable= self.varsList[2])
        espMp3Save = Checkbutton(self.top, text= "Save Spanish MP3",variable=self.varsList[3])
        saveZIP = Button(self.top,text="Save as ZIP", command=self.prepareSave)
        engTextSave.pack()
        espTextSave.pack()
        engMp3Save.pack()
        espMp3Save.pack()
        saveZIP.pack()
    def gonext(self):
        self.buttonvars[0].set("Start Recording")
        self.buttonvars[1].set("Stop Recording")
        self.buttonvars[2].set("Save")
        for i, string in enumerate (self.buttonvars):
            self.buttonvars[i].set(self.translator.translate(text = string.get(),src = "en", dest = self.usersLang).text)
        self.tabControl.select(self.tab2)
    def getTeachData(self):
         while(self.recording):
            self.originalText["text"] = q4[0]
         
    def prepareSave(self):
        using = []
        for i,k in enumerate (self.varsList):
            if (k.get() == 1):
                using.append(i)
       
        file = fd.asksaveasfilename (initialdir= str(os.path.join(os.environ["HOMEPATH"], "Desktop")),
                                defaultextension='.zip',
                                filetypes= ["zip {.zip}"])
        save().saveZIP(file,using)
    def main(self):
        t1 =threading.Thread(target=self.getTeachData)
        t1.start()
    
if __name__ == "__main__":
  gui()


