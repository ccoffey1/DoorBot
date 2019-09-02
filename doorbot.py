import datetime
import random
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import cv2
import yaml
from playsound import playsound

class DoorBot(object):
    def __init__(self):
        self.__config = yaml.safe_load(open("config.yaml"))
        self.face_cascade = cv2.CascadeClassifier("classifiers/lbpcascade_frontalface.xml")
        self.webcam = cv2.VideoCapture(0)
        self._face_acknowleged = False
        self._face_dismissed = True
        self._notification_required = False
        
        # we really don't want to annoy the neighbors
        self._monologue_count = 0
        self._max_monologues = 3
        
        try:
            self.run()
        except Exception as ex:
            print('\nSomething went wrong! :( --> ' + str(ex) + '\n')
            self.__play_error()
    
    def run(self):
        while True:   
            if cv2.waitKey(1) & 0xFF == ord('q'):
                exit()
                
            # hello!
            if (self._face_dismissed):
                self.__greet()
            
            # farewell!
            if (self._face_acknowleged):
                self.__dismiss_face()
                
            # random monologue..?
            self.__play_idle()
            
            # chill
            time.sleep(0.01)

    def __greet(self):
        # check for a face, unless we already said hi
        if (not self._face_acknowleged and self.__detect_faces_and_notify()):
            # wait...
            time.sleep(1)

            # face still there? say hi and notify!
            if (self.__detect_faces_and_notify()):
                self.__play_greeting()
                self._face_acknowleged = True
                self._face_dismissed = False
                self.send_text_with_snapshot("There's someone at the door!")
                    
    def __dismiss_face(self):
        # check for a missing face, unless we already said farewell
        if (not self._face_dismissed and not self.__detect_faces_and_notify()):
            # wait for a sec...
            time.sleep(1)
                
            # face still not there? say farewell!
            if (not self.__detect_faces_and_notify()):
                self.__play_farewell()
                self._face_dismissed = True
                self._face_acknowleged = False
                
    def __play_greeting(self):
        sound = str(random.randrange(1, 19)) + '.wav'
        playsound('sounds/greetings/' + sound, False)

    def __play_farewell(self):
        sound = str(random.randrange(1, 18)) + '.wav'
        playsound('sounds/farewells/' + sound, False)
    
    def __play_idle(self):
        if (self._monologue_count < self._max_monologues):
            # "This is a dumb system to determine random
            # speech. Hur Dur." - You
            # "Yeah well you're stupid." - Me
            random_range = 500
            roll_one = random.randrange(random_range)
            roll_two = random.randrange(random_range)
            
            if (roll_one == roll_two):                
                # we're looking at someone
                if (self._face_acknowleged):
                    sound = str(random.randrange(1, 13)) + '.wav'
                    playsound('sounds/idle_someone/' + sound, False)
                    self._monologue_count += 1
                    
                # we're not looking at anyone
                if (self._face_dismissed):
                    sound = str(random.randrange(1, 15)) + '.wav'
                    playsound('sounds/idle_noone/' + sound, False)
                self._monologue_count += 1
        
    def __play_error(self):
        sound = str(random.randrange(1, 6)) + '.wav'
        playsound('sounds/errors/' + sound, True)
        
    def __detect_faces_and_notify(self, scale_factor = 1.1):
        (_, image) = self.webcam.read()
        timestamp = datetime.datetime.now()
        text = "Clear"
 
        # Post-processing for better classification
        # image = imutils.resize(image, width=500)
        gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray_img = cv2.GaussianBlur(gray_img, (21, 21), 0)
        faces = self.face_cascade.detectMultiScale(gray_img, scale_factor, minNeighbors=5)
        
        # Found a face
        face_found = False
        if len(faces):
            for x, y, w, h in faces:
                cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
            face_found = True
        
        if face_found:
            text = 'Individual at Door'
            
        # draw the text and timestamp on the frame
        ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
        cv2.putText(image, "Door Status: {}".format(text), (10, 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(image, ts, (10, image.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.35, (0, 0, 255), 1)
        
        cv2.imshow('DoorMan Output', image)
        
        return face_found

    def send_text_with_snapshot(self, message):
        addr_to = self.__config['smtp']['addr_to']
        addr_from = self.__config['smtp']['addr_from']
        subject = self.__config['smtp']['subject']
        username = self.__config['smtp']['username']
        password = self.__config['smtp']['password']

        msg = MIMEMultipart()
        msg['To'] = addr_to
        msg['From'] = addr_from
        msg['Subject'] = subject

        # attach message
        text = MIMEText(message)
        msg.attach(text)

        # attach image TODO: Use picam feed and send snap shot
        # instead of using OpenCV
        _, image = self.webcam.read()
        _, buffer = cv2.imencode('.jpg', image)
        image = MIMEImage(buffer.tobytes())
        msg.attach(image)

        s = smtplib.SMTP('smtp.gmail.com', '587')
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(username, password)
        s.sendmail(addr_from, 
                   addr_to.split(','), 
                   msg.as_string())
        s.quit()
        self._notification_required = True
