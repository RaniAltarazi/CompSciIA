'''
Extensibility list:
    - Have AI summarize and get the most important parts of the encounter
    - Have user chose important vocab words they do not know and export into a CSV file for studying
    - Highlight the text that is being read outloud by the text to speech

'''

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
from PIL import Image,ImageTk

import zipfile
import wave
import os

class save():
    # Define the constructor to initialize the class variables
    def __init__(self):
        self.srcText = ""  # source text
        self.destText = ""  # destination text
        self.srcAudio = []  # source audio data
        self.destAudio = []  # destination audio data

    # Define a function to create a ZIP file and save the files in it
    def saveZIP(self, filepath, files):
        # Open the ZIP file in write mode with ZIP_DEFLATED compression
        with zipfile.ZipFile(filepath, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            # Loop through the files and save them in the ZIP file
            for file in files:
                # If the file is 0 (english transcription), then write the source text to the ZIP file
                if (file == 0):
                    # Join the English transcription and save it in a file named 'englishText.txt'
                    self.srcText = ' '.join(engTranscription)
                    with open("englishText.txt", "w") as f:
                        f.write(self.srcText)
                    f.close()
                    # Write the 'englishText.txt' file to the ZIP file
                    zf.write('englishText.txt')
                    # Remove the 'englishText.txt' file
                    os.remove("englishText.txt")
                # If the file is 1 (spanish transcription), then write the destination text to the ZIP file
                if (file == 1):
                    # Join the Spanish transcription and save it in a file named 'spanishText.txt'
                    self.destText = ' '.join(espTranscription)
                    with open("spanishText.txt", "w") as f:
                        f.write(self.destText)
                    f.close()
                    # Write the 'spanishText.txt' file to the ZIP file
                    zf.write("spanishText.txt")
                    # Remove the 'spanishText.txt' file
                    os.remove("spanishText.txt")
                
                # If the file is 2, then write the source audio to the ZIP file
                if (file == 2):
                    # Save the English audio data to a file named 'englishAudio.wav'
                    self.srcAudio = engAudio
                    with wave.open("englishAudio.wav", "wb") as wf:
                        # Set the number of audio channels to 1
                        wf.setnchannels(1)
                        # Set the sample width to 2 bytes
                        wf.setsampwidth(2)
                        # Set the frame rate to 44100 Hz
                        wf.setframerate(44100)
                        # Write the audio frames to the file
                        wf.writeframes(b''.join(self.srcAudio))
                        wf.close()
                    # Write the 'englishAudio.wav' file to the ZIP file
                    zf.write("englishAudio.wav")
                    # Remove the 'englishAudio.wav' file
                    os.remove("englishAudio.wav")
                
                # If the file is 3, then write the destination audio to the ZIP file
                if (file == 3):
                    # Save the Spanish audio data to a file named 'spanishAudio.wav'
                    self.destAudio = espAudio
                    self.sampleWidth = espSr[0]
                    self.frameRate = espFrames[0]
                    with wave.open("spanishAudio.wav", "wb") as wf:
                        # Set the number of audio channels to 1
                        wf.setnchannels(1)
                        # Set the sample width to the value in 'espSr'
                        wf.setsampwidth(self.sampleWidth)
                        # Set the frame rate
                        wf.setframerate(self.frameRate)
                        # Write the audio frames to the file
                        wf.writeframes((b''.join(self.destAudio)))
                        wf.close()
                    # Write the 'spanishAudio.wav' file to the ZIP file
                    zf.write("spanishAudio.wav")
                    # Remove the 'spanishAudio.wav' file
                    os.remove("spanishAudio.wav")
        # Close the ZIP file
        zf.close()

class recorder(Process):
    # Define the constructor to initialize the class variables
    def __init__(self,q1,q2,q1save,recordQueue,exitEvent,exitEvent2,confirm):
            #inheriting from multiprocess.Process to make this class into a process
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
    # A method that prepares the recorder, opening the audio stream if a parameter 'open' is True, and stopping and closing it if False.   
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
    # A method that saves recorded audio data for saving to a queue that will allow the user to save the data on their computer.
    def saveDataForSave (self,data):
            self.q1save.put(data)
    # A method that saves recorded audio data and sample width to a queue to allow other classes to function properly.
    def saveData(self,frames,sampleWidth):
            self.q1.put (frames)
            self.q2.put (sampleWidth)
    # The method that is executed when the process is started, which records audio and saves it to a queue.
    def run (self):
            #tells the main Process that it is recording
            self.recordQueue.put("Recording")
            if( not self.exitEvent.is_set()):
                self.p = pyaudio.PyAudio()
                self.prepareRecorder(True)
            # records for 8 seconds as long as the exitEvent is not set by the main Process
            while (not self.exitEvent.is_set()):
                frames =[]
                for _ in range (0, int(self.rate/ self.chunk * self.seconds)):
                        data = self.stream.read(self.chunk)
                        self.saveDataForSave(data = data)
                        frames.append(data)
                self.saveData(frames=frames,sampleWidth = self.p.get_sample_size(self.format))
            # once the exitEvent is set, it closes the input stream,
            # confirms that the event has exited to the main Process, 
            # and sets the exit event for another process
            self.prepareRecorder(False)
            self.confirmExit.set()
            self.exitEvent2.set()
class prepData(Process):
    # This is a constructor method that initializes the attributes of the class.
    def __init__(self,q1,q2,q3,exitEvent2,exitEvent3,confirm):
            # Inheriting from multiprocess.Process to make this class into a process
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
    # This is a method that puts the loaded audio data into the third queue.
    def saveData(self,dataPath):
         self.q3.put(whisper.load_audio(dataPath))
    # This is the main method that runs when the process starts.
    def run (self):
            # Loops until the exit event is set and the first two queues are not empty.
            while (self.exitEvent2.is_set() is False  or (self.q1.empty() is False and self.q2.empty() is False)):
                    # Opens a wave file in write mode and writes the data from the first queue into it.
                    with wave.open(self.dataFile,"wb") as wf:
                            wf.setnchannels(self.channels)
                            wf.setsampwidth (self.q2.get())
                            wf.setframerate(self.rate)
                            wf.writeframes(b''.join(self.q1.get()))
                            wf.close
                    # Calls the saveData method to put the loaded audio data into the third queue.
                    self.saveData(self.dataFile)
            # Removes the data file and sets the exit event.
            os.remove(self.dataFile)
            self.confirmExit.set()
            self.exitEvent3.set()
# Define a class named "transcribe" that inherits from the "Process" class in the "multiprocess" module.
class transcribe(Process):
    
    # Define an initialization method that is called when an instance of the class is created.
    def __init__(self, teacherL, q3, q4, q4save, exitEvent3, exitEvent4, confirm):
        # Call the initialization method of the "Process" class.
        Process.__init__(self)
        # Assign the given values to instance variables with corresponding names.
        self.lang = teacherL
        self.q3 = q3
        self.q4 = q4
        self.q4save = q4save
        self.exitEvent3 = exitEvent3
        self.exitEvent4 = exitEvent4
        self.confirmExit = confirm
        # Load the pre-trained model with the specified size.
        self.model = whisper.load_model("small")
        # Set the options for decoding.
        self.options = whisper.DecodingOptions(language=teacherL, fp16=False)
    
    # Define a method that saves the data into two queues.
    def saveData(self, data):
        # Add the data to the "q4" queue.
        self.q4.put(data)
        # Add the data to the "q4save" queue.
        self.q4save.put(data)
    
    # Define a method that is called when an instance of the class is run.
    def run(self):
        # While the "exitEvent3" flag is not set or the "q3" queue is not empty:
        while (self.exitEvent3.is_set() == False or self.q3.empty() == False):
            # Get data from the "q3" queue.
            data = self.q3.get()
            # Pad or trim the audio data.
            audio = whisper.pad_or_trim(data)
            # Compute the log-mel spectrogram and move it to the device that the model is on.
            mel = whisper.log_mel_spectrogram(audio).to(self.model.device)
            # Decode the spectrogram using the loaded model and the specified options.
            result = whisper.decode(self.model, mel, self.options)
            # Save the decoded text data into two queues.
            self.saveData(result.text)
        # Set the "confirmExit" and "exitEvent4" flags when the loop is finished.
        self.confirmExit.set()
        self.exitEvent4.set()

# This class inherits from multiprocess.Process to make it a process
class translateText(Process):
    
    def __init__(self, originalLang, finalLang, q4, q5, q5save, q6save, q7save, exitEvent4, exitEvent5, speek, confirm):
        Process.__init__(self)
        
        # Initializing variables
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
        
    # Function to save data into q5 and q5save
    def saveData(self, data):
        self.q5.put(data)
        self.q5save.put(data)
    
    # Function to save speech data into q6save and q7save
    def saveSpeechData(self, file):
        # Opening wave file and retrieving properties
        wavfile = wave.open(file, 'rb')
        num_frames = wavfile.getnframes()
        raw_data = wavfile.readframes(num_frames)
        sample_width = wavfile.getsampwidth()
        frame_rate = wavfile.getframerate()
        
        # Saving data into q6save and q7save
        self.q6save.put(raw_data)
        self.q7save.put([sample_width, frame_rate])
    
    # Function to convert translated text to speech
    def toSpeech(self):
        # While loop to keep the process running while exitEvent5 is not set or q5 is not empty
        while (not self.exitEvent5.is_set() or not self.q5.empty()):
            if (not self.q5.empty()):
                # Using Google Text-to-Speech API to generate speech from translated text
                tts = gTTS(self.q5.get(), lang="es")
                tts.save(self.filePath)
                
                # Converting mp3 file to wave file
                song = AudioSegment.from_mp3(self.filePath)
                song.export(self.filePath2, format="wav")
                
                # Saving speech data into q6save and q7save
                self.saveSpeechData(self.filePath2)
                
                # Playing speech
                play(song)
        
        # Removing mp3 file and setting done to True
        os.remove(self.filePath)
        self.done = True       
    
    def run(self):
        # Creating thread to run toSpeech function
        t1 = threading.Thread(target=self.toSpeech)
        self.translator = Translator()
        
        # While loop to keep the process running while exitEvent4 is not set or q4 is not empty
        while (self.exitEvent4.is_set() == False or self.q4.empty() == False):
            # Starting toSpeech thread if this is the first iteration and speek is 1
            if (self.first and self.speek == 1):
                t1.start()
                self.first = False
            
            # Using Google Translate API to translate text from original language to final language
            result = self.translator.translate(text=self.q4.get(), src=self.oglang, dest=self.finalL).text
            
            # Saving translated data into q5 and q5save
            self.saveData(result)
        
        # Setting exitEvent5 and waiting
        self.exitEvent5.set()
        while (not self.done and self.speek ==1):
            time.sleep(.1)
        # Set confirmExit event to True
        self.confirmExit.set()
    
class gui():
    # Define the init method that initializes the translator, user's language, teacher's language, and recording status.
    def __init__(self):
        self.translator = Translator()
        self.usersLang = "es"
        self.teacherLang = "en"
        self.recording = False
        # Create an instance of the main class.
        self.mainClass = main()

    # Define the GUI method that creates the graphical user interface. 
    def GUI(self):
        # Create the main window and set its size and title.
        self.root = Tk()
        self.root.geometry("950x500")
        self.root.title("Recorder")
        # Create a notebook widget with two tabs.
        self.tabControl =ttk.Notebook(self.root)
        self.tab1 = Frame(self.tabControl,bg="light blue")
        self.tab2 = Frame(self.tabControl,bg = "light blue")
        self.tabControl.add(self.tab1, text ='Main Tab')
        self.tabControl.add(self.tab2, text ='Record Tab')
        self.tabControl.pack(expand = 1, fill ="both")
        # Set the row and column configurations for the main tab.
        self.tab1.rowconfigure(3)
        self.tab1.columnconfigure(3)
        # Create a label and options for the user to choose from.
        self.welcome_new = Label(self.tab1, text="Welcome User! This app is ment to help you learn in school by translating and tanscribing what you teacher says into Spanish. Please select what you would like this app to do.")
        self.listOfOptions = [IntVar(value=1),IntVar(value=1),IntVar(value=1)]
        self.transcribeEN = Checkbutton(self.tab1, text= "Show English Transcription",variable=self.listOfOptions[0])
        self.transcribeES = Checkbutton(self.tab1, text= "Show Spanish Transcription",variable=self.listOfOptions[1])
        self.SpeekES = Checkbutton(self.tab1, text= "Provide audio translation (Speek in Spanish)",variable= self.listOfOptions[2])
        self.nextButton = Button(self.tab1, text="Continue to Recording TAB",command=self.gonext)
        # Set the grid positions for the label and options on the main tab.
        self.welcome_new.grid(row=0,column=0,sticky="",padx=3,pady=3,columnspan=3)
        self.transcribeEN.grid(row = 1,column=0,sticky="",padx=3,pady=3)
        self.transcribeES.grid(row=1,column=1,sticky="",padx=3,pady=3)
        self.SpeekES.grid(row=1,column=2,sticky="",padx=3,pady=3)
        self.nextButton.grid(row=2,column=0,sticky="",padx=3,pady=3,columnspan=3)
        # Create an image of a microphone and buttons to start recording and save 
        self.micIcon = Image.open("mic.png")
        self.micIcon= self.micIcon.resize((100,100),Image.Resampling.LANCZOS)
        self.micIcon = ImageTk.PhotoImage(self.micIcon)
        # creates a recording button that creates a new startRecording thread
        self.start_button = Button(self.tab2,image= self.micIcon,bd=0, command = lambda: threading.Thread(target = self.startRecording).start(), bg="green", height = 100, width =100)
        self.save_button = Button(self.tab2, text="save", command=self.openSave,height=5,width=10)
        self.start_button.place(relx=0.5,rely=0.5,anchor=S)
        self.save_button.place(relx=0.5,rely=0.5,anchor=N)
        # Provides the code with control of the closing (pressing x button) protocol so that everything can close correctly
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        # loops the GUI so it remains updated
        self.root.mainloop()
    #function to correctly close application
    def close(self):
        closeEvent1.set()
        #closes the GUI
        self.root.destroy()
        #stops all processes
        self.mainClass.stopAll()
    # function to start the recordiing and save save the data into lists
    def startRecording(self):
        self.recording= True
        # opens a new window that shows the transcription
        self.openRecordingW()
        # calls on the main class to start all the processes
        self.mainClass.startAll(self.teacherLang,self.usersLang,self.listOfOptions[2].get())
        # creates 4 threads that get the data of english audio, english transcription, spanish audio, and spanish transcription 
        engAudioThread = threading.Thread(target=self.getEngAudio)
        engAudioThread.start() 
        englishThread = threading.Thread(target= self.getEngTranscribe)
        englishThread.start()    
        espAudioThread = threading.Thread(target=self.getEspAudio)
        espAudioThread.start()
        spanishThread = threading.Thread(target= self.getEspTranscribe)
        spanishThread.start() 
        # Start a new thread that executes the setRecordingTrue function.
        t1 = threading.Thread(target=self.setRecordingTrue)
        t1.start()
        engAudio.clear()
        engTranscription.clear()
        espAudio.clear()
        espSr.clear()
        espFrames.clear()
        espTranscription.clear()
    # function that stops recording
    def stopRecording(self):
        # calls on the main class to stop the processes and sets the recording to false
        self.mainClass.stopAll()
        self.recording = False
    # creates a new window that shows the transcriptions
    def openRecordingW(self):
        self.recordingW = Toplevel(self.root)
        self.recordingW.geometry("950x500")
        self.root.iconify()
        self.loadingL = Label(self.recordingW,text="Please Wait")
        self.recordingL = Label(self.recordingW,text="Recording, Talk Now")
        # creates a stop recorind button that creates a new stopRecording thread
        self.stop_button = Button(self.recordingW, text="Stop Recording", command= lambda: threading.Thread(target = self.stopRecording).start(), bg="#3d3d3d", fg="white",height=5,width=20)
        # given the options the user has set, this code will display the transcriptions
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
        # provides the program with control over the closing of the window
        self.recordingW.protocol("WM_DELETE_WINDOW", self.closeRecording)
    # function that closes the window and ensures that all processes have completed
    def closeRecording(self):
         if (self.recording == False or confirm4.is_set()):
              self.recordingW.destroy()
         else:
              print("Please Wait")
    #thread that waits until the recording to start and notifies the user via the GUI once the recording has started
    def setRecordingTrue(self):
        while(recordQueue.empty()):
            time.sleep(.01)
            if(closeEvent1.is_set()):
                break
        if (not closeEvent1.is_set()): 
            recordQueue.get()   
            self.loadingL.forget()
            self.recordingL.grid(row=0,column=3,sticky="",padx=3,pady=3)
            self.stop_button.grid(row=9,column=6,sticky="",padx=3,pady=3)
    # opens a save window that allows the user to select what they want to save. 
    def openSave(self):
        self.top= Toplevel(self.root)
        self.top.geometry("500x500")
        self.top.title("Child Window")
        self.varsList = [IntVar(),IntVar(),IntVar(),IntVar()]
        # provides the options of what the user can save depending on their previous settings
        if (self.listOfOptions[0].get()== 1):
            engTextSave = Checkbutton(self.top, text= "Save English Text",variable=self.varsList[0])
            engTextSave.pack()
        if (self.listOfOptions[1].get()== 1):
            espTextSave = Checkbutton(self.top, text= "Save Spanish Text",variable=self.varsList[1])
            espTextSave.pack()
        engMp3Save = Checkbutton(self.top, text= "Save English MP3",variable= self.varsList[2])
        if (self.listOfOptions[2].get()== 1):
            espMp3Save = Checkbutton(self.top, text= "Save Spanish MP3",variable=self.varsList[3])
            espMp3Save.pack()
        saveZIP = Button(self.top,text="Save as ZIP", command=self.prepareSave)
        engMp3Save.pack()
        saveZIP.pack()
    # switches to next tab
    def gonext(self):
        self.tabControl.select(self.tab2)
    # thread gets and saves the enlish transcription
    def getEngTranscribe(self):
        while(not confirm3.is_set() or not q4save.empty() and self.listOfOptions[0].get()== 1 and self.recordingW.state() == "normal"):
              if (not q4save.empty()):
                data = q4save.get()
                engTranscription.append(data)
                data = ' '.join(engTranscription)
                self.originalText.configure(text=data)
    # thread gets and saves spanish transcription
    def getEspTranscribe(self):
        while((not confirm4.is_set() or not q5save.empty()) and self.listOfOptions[1].get()== 1 and self.recordingW.state() == "normal"):
              if(not q5save.empty()):
                data = q5save.get()
                espTranscription.append(data)
                data =' '.join(espTranscription)
                self.translationText.configure(text=data)
    # thread gets and saves english audio
    def getEngAudio(self):
         while((not confirm1.is_set() or not q1save.empty()) and self.recordingW.state() == "normal"):
              if(not q1save.empty()):
                data = q1save.get()
                engAudio.append(data)
    # thread gets and saves spanish audio
    def getEspAudio(self):
         while((not confirm4.is_set() or not q6save.empty()) and self.listOfOptions[2].get()== 1 and self.recordingW.state() == "normal"):
              if(not q6save.empty()):
                data = q6save.get()
                sampleWidth, frames = q7save.get()
                espSr.append (sampleWidth)
                espFrames.append(frames)
                espAudio.append(data)
    # shows a save GUI that allows the user to chose where they want to save
    def prepareSave(self):
        #destroys the openSave window
        self.top.destroy()
        using = []
        # gets the data the user wants to save on their computer
        for i,k in enumerate (self.varsList):
            if (k.get() == 1):
                using.append(i)
        # opens a GUI that allows user to save the file
        file = fd.asksaveasfilename (initialdir= str(os.path.join(os.environ["HOMEPATH"], "Desktop")),
                                defaultextension='.zip',
                                filetypes= ["zip {.zip}"])
        # calls the save class to save the data as a zip file. 
        save().saveZIP(file,using)
    # main class
class main():            
        def __init__(self):
             self.p1 = None
             self.p2 = None
             self.p3 = None
             self.p4 = None
             self.recording = False
        # starts the GUI
        def startGUI(self):
            gui().GUI()
        # stops all processes and ensures that they are stoped
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
        #starts the processes
        def startAll(self,teachL,studentL,speek):
            self.recording = True
            closeEvent1.clear()
            exitEvent1.clear()
            exitEvent2.clear()
            exitEvent3.clear()
            exitEvent4.clear()
            exitEvent5.clear()
            confirm1.clear()
            confirm2.clear()
            confirm3.clear()
            confirm4.clear()
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


