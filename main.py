import whisper
import pyaudio
from tkinter import *
from tkinter import ttk
from tkinter import filedialog as fd
import wave
from multiprocessing import Process, Queue, Event
import threading
from googletrans import Translator
import os 
import zipfile
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import time
import librosa
from PIL import Image,ImageTk

class save():
    def __init__(self):
        self.srcText =""
        self.destText = ""
        self.srcAudio = []
        self.destAudio = []
    def saveZIP(self,filepath,files):
         with zipfile.ZipFile(filepath, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                if (file ==0):
                    self.srcText = ' '.join(engTranscription)
                    with open("englishText.txt","w")as f:
                        f.write(self.srcText)
                    f.close()
                    zf.write('englishText.txt')
                    os.remove("englishText.txt") 
                if (file ==1):
                    self.destText = ' '.join(espTranscription)
                    with open("spanishText.txt","w")as f:
                        f.write(self.destText)
                    f.close()
                    zf.write("spanishText.txt")
                    os.remove("spanishText.txt")
                if (file ==2):
                    self.srcAudio = engAudio
                    with wave.open("englishAudio.wav","wb") as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth (2)
                            wf.setframerate(44100)
                            wf.writeframes(b''.join(self.srcAudio))
                            wf.close
                    zf.write("englishAudio.wav")
                    os.remove("englishAudio.wav")
                if (file ==3):
                    self.destAudio = espAudio
                    self.sampleWidth = espSr[0]
                    self.frameRate = espFrames[0]
                    with wave.open("spanishAudio.wav","wb") as wf:
                         wf.setnchannels(1)
                         wf.setsampwidth(self.sampleWidth)
                         wf.setframerate(self.frameRate)
                         wf.writeframes((b''.join(self.destAudio)))
                         wf.close
                    zf.write("spanishAudio.wav")
                    os.remove("spanishAudio.wav")
            zf.close()
class recorder(Process):
    def __init__(self,q1,q2,q1save,recordQueue,exitEvent,exitEvent2,confirm):
            Process.__init__(self)
            self.q1=q1
            self.q2 = q2
            self.q1save = q1save
            self.exitEvent = exitEvent
            self.exitEvent2 = exitEvent2
            self.confirmExit = confirm
            self.recordQueue = recordQueue
            self.chunk = 1024
            self.format = pyaudio.paInt16
            self.channels = 1
            self.rate = 44100
            self.seconds = 8   
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
            self.recordQueue.put("Recording")
            if( not self.exitEvent.is_set()):
                self.p = pyaudio.PyAudio()
                self.prepareRecorder(True)
        
            while (not self.exitEvent.is_set()):
                frames =[]
                for _ in range (0, int(self.rate/ self.chunk * self.seconds)):
                        data = self.stream.read(self.chunk)
                        self.saveDataForSave(data = data)
                        frames.append(data)
                self.saveData(frames=frames,sampleWidth = self.p.get_sample_size(self.format))
            self.prepareRecorder(False)
            self.confirmExit.set()
            self.exitEvent2.set()
class prepData(Process):
    def __init__(self,q1,q2,q3,exitEvent2,exitEvent3,confirm):
            Process.__init__(self)
            self.q1=q1
            self.q2 = q2
            self.q3 = q3
            self.exitEvent2 = exitEvent2
            self.exitEvent3 = exitEvent3
            self.confirmExit = confirm
            self.channels = 1
            self.rate = 44100
            self.dataFile= "outputwave.wav"

    def saveData(self,dataPath):
         self.q3.put(whisper.load_audio(dataPath))
    def run (self):
            while (self.exitEvent2.is_set() is False  or (self.q1.empty() is False and self.q2.empty() is False)):
                    with wave.open(self.dataFile,"wb") as wf:
                            wf.setnchannels(self.channels)
                            wf.setsampwidth (self.q2.get())
                            wf.setframerate(self.rate)
                            wf.writeframes(b''.join(self.q1.get()))
                            wf.close
                    self.saveData(self.dataFile)
            os.remove(self.dataFile)
            self.confirmExit.set()
            self.exitEvent3.set()
class transcribe(Process):
    def __init__(self,teacherL,q3,q4,q4save,exitEvent3,exitEvent4,confirm):
            Process.__init__(self)
            self.lang = teacherL
            self.q3=q3
            self.q4 = q4
            self.q4save = q4save
            self.q4save.cancel_join_thread()
            self.exitEvent3 = exitEvent3
            self.exitEvent4 = exitEvent4
            self.confirmExit = confirm
            self.model = whisper.load_model("small")
            self.options = whisper.DecodingOptions(language=teacherL, fp16=False)
    def saveData(self,data):
         self.q4.put(data)
         self.q4save.put(data)
    def run(self):  
            while (self.exitEvent3.is_set()==False or self.q3.empty()==False):
                    data = self.q3.get()
                    audio = whisper.pad_or_trim(data)
                    mel = whisper.log_mel_spectrogram(audio).to(self.model.device) 
                    result = whisper.decode(self.model, mel, self.options)
                    self.saveData(result.text)
            self.confirmExit.set()
            self.exitEvent4.set()
class translateText(Process):
    def __init__(self,originalLang,finalLang,q4,q5,q5save,q6save,q7save,exitEvent4,exitEvent5,speek,confirm):
            Process.__init__(self)
            self.oglang = originalLang
            self.finalL = finalLang
            self.q4 = q4
            self.q5 = q5
            self.q5save = q5save
            self.q6save = q6save
            self.q7save = q7save
            self.exitEvent4 = exitEvent4
            self.exitEvent5 = exitEvent5
            self.confirmExit = confirm
            self.speek = speek
            self.filePath = "espOut.mp3"
            self.filePath2 = "espOut.wav"
            self.first = True
            self.done = False
    def saveData(self,data):
             self.q5.put(data)
             self.q5save.put(data)
    def saveSpeechData(self,file):
            wavfile = wave.open(file,'rb')
            num_frames = wavfile.getnframes()
            raw_data = wavfile.readframes(num_frames)
            sample_width = wavfile.getsampwidth()
            frame_rate= wavfile.getframerate()
            self.q6save.put(raw_data)
            self.q7save.put([sample_width,frame_rate])


    def toSpeech (self):
            while (not self.exitEvent5.is_set() or not self.q5.empty()):
                if (not self.q5.empty()):
                    tts = gTTS(self.q5.get(),lang= "es")
                    tts.save(self.filePath)
                    song = AudioSegment.from_mp3(self.filePath)
                    song.export(self.filePath2, format="wav")
                    

                    self.saveSpeechData(self.filePath2)
                    play(song)
            os.remove(self.filePath)
            self.done = True       
    def run(self):
            t1 = threading.Thread(target=self.toSpeech)
            self.translator = Translator()
            while (self.exitEvent4.is_set() == False or self.q4.empty()==False):
                    if (self.first and self.speek == 1):
                        t1.start()
                        self.first = False
                    result = self.translator.translate(text = self.q4.get(),src = self.oglang, dest = self.finalL).text
                    self.saveData(result)
            self.exitEvent5.set()
            while (not self.done):
                time.sleep(.1)
            self.confirmExit.set()
      
class gui():
    def __init__(self):
        self.translator = Translator()
        self.usersLang = "es"
        self.teacherLang = "en"
        self.recording = False
        t1 = threading.Thread(target=self.setRecordingTrue)
        t1.start()
        self.mainClass = main()
        
    def GUI(self):
        self.root = Tk()
        self.root.geometry("950x500")
        self.root.title("Recorder")
        self.tabControl =ttk.Notebook(self.root)
        self.tab1 = Frame(self.tabControl,bg="light blue")
        self.tab2 = Frame(self.tabControl,bg = "light blue")
        self.tabControl.add(self.tab1, text ='Main Tab')
        self.tabControl.add(self.tab2, text ='Record Tab')
        self.tabControl.pack(expand = 1, fill ="both")
        self.variablesUser = StringVar(self.tab1)
        self.variablesTeach = StringVar(self.tab1)
        self.tab1.rowconfigure(3)
        self.tab1.columnconfigure(3)
        self.welcome_new = Label(self.tab1, text="Welcome User! This app is ment to help you learn in school by translating and tanscribing what you teacher says into Spanish. Please select what you would like this app to do.")
        self.listOfOptions = [IntVar(value=1),IntVar(value=1),IntVar(value=1)]
        self.transcribeEN = Checkbutton(self.tab1, text= "Show English Transcription",variable=self.listOfOptions[0])
        self.transcribeES = Checkbutton(self.tab1, text= "Show Spanish Transcription",variable=self.listOfOptions[1])
        self.SpeekES = Checkbutton(self.tab1, text= "Provide audio translation (Speek in Spanish)",variable= self.listOfOptions[2])
        self.nextButton = Button(self.tab1, text="Continue to Recording TAB",command=self.gonext)
        self.welcome_new.grid(row=0,column=0,sticky="",padx=3,pady=3,columnspan=3)
        self.transcribeEN.grid(row = 1,column=0,sticky="",padx=3,pady=3)
        self.transcribeES.grid(row=1,column=1,sticky="",padx=3,pady=3)
        self.SpeekES.grid(row=1,column=2,sticky="",padx=3,pady=3)
        self.nextButton.grid(row=2,column=0,sticky="",padx=3,pady=3,columnspan=3)
        self.micIcon = Image.open("mic.png")
        self.micIcon= self.micIcon.resize((100,100),Image.Resampling.LANCZOS)
        self.micIcon = ImageTk.PhotoImage(self.micIcon)
        self.start_button = Button(self.tab2,image= self.micIcon,bd=0, command = lambda: threading.Thread(target = self.startRecording).start(), bg="green", height = 100, width =100)
        self.save_button = Button(self.tab2, text="save", command=self.openSave,height=5,width=10)
        self.start_button.place(relx=0.5,rely=0.5,anchor=S)
        self.save_button.place(relx=0.5,rely=0.5,anchor=N)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.mainloop()
    def close(self):
        closeEvent1.set()
        self.root.destroy()
        self.mainClass.stopAll()
    def startRecording(self):
        self.recording= True
        self.openRecordingW()
        self.mainClass.startAll(self.teacherLang,self.usersLang,self.listOfOptions[2].get())
        engAudioThread = threading.Thread(target=self.getEngAudio)
        engAudioThread.start() 
        englishThread = threading.Thread(target= self.getEngTranscribe)
        englishThread.start()    
        espAudioThread = threading.Thread(target=self.getEspAudio)
        espAudioThread.start()
        spanishThread = threading.Thread(target= self.getEspTranscribe)
        spanishThread.start() 
    def stopRecording(self):
        self.mainClass.stopAll()
        self.recording = False
    def openRecordingW(self):
        self.recordingW = Toplevel(self.root)
        self.recordingW.geometry("950x500")
        self.root.iconify()
        self.loadingL = Label(self.recordingW,text="Please Wait")
        self.recordingL = Label(self.recordingW,text="Recording, Talk Now")
        self.stop_button = Button(self.recordingW, text="Stop Recording", command= lambda: threading.Thread(target = self.stopRecording).start(), bg="#3d3d3d", fg="white",height=5,width=20)
        if (self.listOfOptions[0].get() == 1):
            self.originalTextLabel = Label(self.recordingW,text= "English Transcription")
            self.originalText = Message(self.recordingW, bg="white")
            self.originalTextLabel.grid(row=3,column=0,sticky="",padx=3,pady=3)
            self.originalText.grid(row=3,column=3, sticky="",padx=3,pady=3)
        if (self.listOfOptions[1].get()== 1):
            self.translationTextLabel =  Label(self.recordingW,text= (self.translator.translate(text = "Spanish Transcription",src = "en", dest = "es").text))
            self.translationText = Message(self.recordingW, bg="white")
            self.translationTextLabel.grid(row=6,column=0,sticky="",padx=3,pady=3)
            self.translationText.grid(row=6,column=3, sticky="",padx=3,pady=3)
        self.loadingL.grid(row=0,column=3,sticky="",padx=3,pady=3)
        self.recordingW.protocol("WM_DELETE_WINDOW", self.closeRecording)
    def closeRecording(self):
         if (self.recording == False or confirm4.is_set()):
              self.recordingW.destroy()
         else:
              print("Please Wait")

    def setRecordingTrue(self):
        while(recordQueue.empty()):
            time.sleep(.01)
            if(closeEvent1.is_set()):
                break
        if (not closeEvent1.is_set()):    
            self.loadingL.forget()
            self.recordingL.grid(row=0,column=3,sticky="",padx=3,pady=3)
            self.stop_button.grid(row=9,column=6,sticky="",padx=3,pady=3)
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
        self.tabControl.select(self.tab2)
    def getEngTranscribe(self):
        while(not confirm3.is_set() or not q4save.empty() and self.listOfOptions[0].get()== 1 and self.recordingW.state() == "normal"):
              if (not q4save.empty()):
                data = q4save.get()
                engTranscription.append(data)
                data = ' '.join(engTranscription)
                self.originalText.configure(text=data)
    def getEspTranscribe(self):
        while((not confirm4.is_set() or not q5save.empty()) and self.listOfOptions[1].get()== 1 and self.recordingW.state() == "normal"):
              if(not q5save.empty()):
                data = q5save.get()
                espTranscription.append(data)
                data =' '.join(espTranscription)
                self.translationText.configure(text=data)
    def getEngAudio(self):
         while((not confirm1.is_set() or not q1save.empty()) and self.recordingW.state() == "normal"):
              if(not q1save.empty()):
                data = q1save.get()
                engAudio.append(data)
    def getEspAudio(self):
         while((not confirm4.is_set() or not q6save.empty()) and self.listOfOptions[2].get()== 1 and self.recordingW.state() == "normal"):
              if(not q6save.empty()):
                data = q6save.get()
                sampleWidth, frames = q7save.get()
                espSr.append (sampleWidth)
                espFrames.append(frames)
                espAudio.append(data)
    def prepareSave(self):
        
        self.top.destroy()
        using = []
        for i,k in enumerate (self.varsList):
            if (k.get() == 1):
                using.append(i)
       
        file = fd.asksaveasfilename (initialdir= str(os.path.join(os.environ["HOMEPATH"], "Desktop")),
                                defaultextension='.zip',
                                filetypes= ["zip {.zip}"])
        save().saveZIP(file,using)
class main():            
        def __init__(self):
             self.p1 = None
             self.p2 = None
             self.p3 = None
             self.p4 = None
             self.recording = False
        def startGUI(self):
            gui().GUI()
        def stopAll(self):
            if (not exitEvent1.is_set() and self.recording):
                exitEvent1.set()
                while(not confirm1.is_set() or not confirm2.is_set() or not confirm3.is_set() or not confirm4.is_set()):
                     time.sleep(0.1)
                self.p1.terminate()
                self.p2.terminate()
                self.p3.terminate()
                self.p4.terminate()   
            self.recording = False
        def startAll(self,teachL,studentL,speek):
            self.recording = True
            exitEvent1.clear()
            exitEvent2.clear()
            exitEvent3.clear()
            exitEvent4.clear()
            self.p1 = recorder(q1,q2,q1save,recordQueue,exitEvent1,exitEvent2,confirm1)
            self.p2 = prepData(q1,q2,q3,exitEvent2,exitEvent3,confirm2)
            self.p3 = transcribe(teachL,q3,q4,q4save,exitEvent3,exitEvent4,confirm3)
            self.p4 = translateText(teachL,studentL,q4,q5,q5save,q6save,q7save,exitEvent4,exitEvent5,speek,confirm4)
            self.p1.start()
            self.p2.start()
            self.p3.start()
            self.p4.start() 
if __name__ == "__main__":
    recordingData = []
    translationData = []
    engAudio=[]
    engTranscription = []
    espAudio=[]
    espSr = []
    espFrames = []
    espTranscription = []
    closeEvent1 = Event()
    exitEvent1 = Event()
    exitEvent2 = Event()
    exitEvent3 = Event()
    exitEvent4 = Event()
    exitEvent5 = Event()
    confirm1 = Event()
    confirm2 = Event()
    confirm3 = Event()
    confirm4 = Event()
    q1 = Queue()
    q1save = Queue()
    q2 = Queue()
    q3 = Queue()
    q4 = Queue()
    q4save = Queue()
    q5 = Queue()
    q5save = Queue()
    q6save = Queue()
    q7save = Queue()
    recordQueue = Queue()
    main().startGUI()
