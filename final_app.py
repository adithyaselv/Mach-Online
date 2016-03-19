#basic webapp

from threading import Thread
import time
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug import secure_filename
from ABE_ExpanderPi import ADC
import RPi.GPIO as GPIO
import serial
import sqlite3


red_led=24
green_led=23
switch=25
relay=12
pps = 2
btemp="NA"
etemp="NA"
etargettemp="NA"
btargettemp="NA"
progress = -1
prevprogress= -1
counter=0
access = ""
out = ""
startup=0
printfile = None
mainflag=1
print_ser = serial.Serial()
rfid_ser = serial.Serial(port='/dev/ttyAMA0',baudrate=9600)
content=""
line_no=0

def ser_flush(ser):
    while ser.inWaiting() > 0:
        ser.read()

def led_blink(led):
    GPIO.output(led,1)
    time.sleep(1)
    GPIO.output(led,0)


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.cleanup()
GPIO.setup(relay,GPIO.OUT)
GPIO.setup(red_led,GPIO.OUT)
GPIO.setup(green_led,GPIO.OUT)
GPIO.setup(switch,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.output(relay,0)
GPIO.output(red_led,0)
GPIO.output(green_led,0)

upload_folder='./uploads'
allowed_ext=set(['txt','gcode'])

adc=ADC()
app= Flask(__name__)
app.config['UPLOAD_FOLDER']=upload_folder

curr_error=adc.read_adc_voltage(2)-2.4;


def allow_file(filename):
    return '.' in filename and \
            filename.rsplit('.',1)[1] in allowed_ext


@app.route('/',methods=['GET','POST'])
def index():
    if request.method =='POST':
        global pps
        file = request.files['file']
        if file and allow_file(file.filename):
            filename="job.gcode"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
            pps=4
	    try:
                os.remove('test.db')
	    except:
		pass
            conn = sqlite3.connect('test.db')
            try:
                conn.execute('''CREATE TABLE mperform
                        (percent INT PRIMARY KEY    NOT NULL,
                        volt           FLOAT    NOT NULL,
                        current         FLOAT   NOT NULL,
                        btemp           FLOAT   NOT NULL,
                        etemp           FLOAT   NOT NULL,
                        power         FLOAT NOT NULL);''')
            except :
                pass
            conn.close()

            return render_template('test.html')

    return render_template('test.html')

@app.route('/files',methods=['GET','POST'])
def upload_files():
    if request.method =='POST':
        file = request.files['file']
        if file and allow_file(file.filename):
            filename=secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
            return "Your file is successfully uploaded"
    return render_template('fileup.html')

@app.route('/json')
def jsongive():
    li={"server":"rasp","ports":"4000"}
    return jsonify(li)

@app.route('/vgraph')
def vgraph():
    return render_template("vgraph.html")

@app.route('/pgraph')
def pgraph():
    return render_template("pgraph.html")

@app.route('/cgraph')
def cgraph():
    return render_template("cgraph.html")

@app.route('/btempgraph')
def btempgraph():
    return render_template("btempgraph.html")

@app.route('/pfgraph')
def pfgraph():
    return render_template("pfgraph.html")

@app.route('/etempgraph')
def etempgraph():
    return render_template("etempgraph.html")

@app.route('/report')
def report():
    return render_template("report.html")

def fetchbase(x):
   conn = sqlite3.connect('test.db')
   print "Opened database successfully";
   print "SELECT "+x+" from mperform"
   try:
       cursor = conn.execute("SELECT "+x+" from mperform")
   except Exception as inst:
       print inst
   A=[]
   for row in cursor:
       A.append(row[0])
   print "Operation done successfully";
   conn.close()
   return A

@app.route('/chartdata')
def chartdata():
    global btargettemp
    global etargettemp
    pprac=fetchbase("power")
    pth=98*[60]
    pth.insert(0,100)
    pth.insert(1,80)
    pfprac=[1]*100
    pfth=[1]*100
    vprac=fetchbase("volt")
    cprac=fetchbase("current")
    btempprac=fetchbase("btemp")
    etempprac=fetchbase("etemp")
    vth=100*[10]
    cth=98*[6]
    cth.insert(0,10)
    cth.insert(1,8)
    btempth=99*[btargettemp]
    btempth.insert(0,0)
    etempth=99*[etargettemp]
    etempth.insert(0,0)
    percent=fetchbase("percent")
    dataout={"pprac":pprac,"vprac":vprac,"cprac":cprac,"pfprac":pfprac,"btempprac":btempprac,"etempprac":etempprac,"vth":vth,"pth":pth,"pfth":pfth,"cth":cth,"btempth":btempth,"etempth":etempth,"percent":percent}
    return jsonify(dataout)


@app.route('/getdata')
def givedata():
    global progress
    if progress<0:
	tempprogress=0
    else:
	tempprogress=progress
    vol=round(adc.read_adc_voltage(4)*12.0/4.1,3)
    cur=round((adc.read_adc_voltage(2)-curr_error-2.4)*(20/2.4),3)
    if cur<0:
        cur=0
    powe=round(vol*cur,3)
    pf=1
    global pps
    global btemp
    global etemp
    global etargettemp
    global btargettemp
    if pps==0 or pps==3:
        print_status="Printing"
    elif pps==1:
        print_status="Paused"
    else:
        print_status="Stop"
    rstate=int(GPIO.input(relay))
    File="top.code"
    lstate=1
    jsoval={"progress":round(tempprogress,1),"status1":print_status,"voltage":str(vol)+" V","file1":"top.gcode","current":str(cur)+" A","btemp":str(btemp),"etemp":str(etemp),"pc":str(powe)+" W","pf":str(pf),"power_stat":rstate,"lstat":lstate,"etarget":etargettemp+" C" ,"btarget":btargettemp+" C","pps":pps}

    send_data=jsoval
    return jsonify(send_data)

@app.route('/jsontest')
def jsout():
    return render_template('jsontest.html')

@app.route('/powercontrol')
def powercontrol():
    global startup

    GPIO.output(relay,not GPIO.input(relay))
    if not GPIO.input(relay):
        startup=0

    return ""
    
@app.route('/lightcon')
def lightcon():
    return ""

@app.route('/pps',methods=['GET','POST'])
def ppschange():
    global pps
    if request.method=='POST':
        newpps=int(request.form['pps'])
        pps=newpps
        return ""


@app.route('/capture')
def capture():
    t=str(time.time())[0:10]
    os.system("rm ./static/images/*")
    os.system("fswebcam -r 640x480  --crop 480x480 --no-banner ./static/images/"+t+".jpeg -S 20")
    return t

def lolol():
    app.run(debug=False,use_reloader=False,host='0.0.0.0')

def dbupdate():
    while 1:
    	global progress
    	global prevprogress
    	global btemp
    	global etemp
	if btemp!="NA" and etemp!="NA":
    	    if int(progress) > prevprogress:
                prevprogress = int(progress)
            	vol=round(adc.read_adc_voltage(4)*12.0/4.1,3)
            	cur=round((adc.read_adc_voltage(2)-2.4)*(20/2.4),3)
            	powe=round(vol*cur,3)
            	if cur<0:
                    cur=0
            	conn = sqlite3.connect('test.db')
            	conn.execute("INSERT INTO mperform (percent,volt,current,btemp,etemp,power) VALUES ("+str(int(progress))+","+str(vol)+","+str(cur)+","+str(btemp)+","+str(etemp)+","+str(powe)+" )");
            	print "INSERT INTO mperform (percent,volt,current,btemp,etemp,power) VALUES ("+str(int(progress))+","+str(vol)+","+str(cur)+","+str(btemp)+","+str(etemp)+","+str(powe)+" )"
	    	conn.commit()
            	conn.close()


if __name__=='__main__':
    t2=Thread(target=lolol)
    t2.setDaemon(True)
    t2.start()

    t3=Thread(target=dbupdate)
    t3.setDaemon(True)
    t3.start()

    while 1:
        access = ""
        if rfid_ser.inWaiting() > 0 :
            while rfid_ser.inWaiting() > 0 :
                access = access+rfid_ser.read()
                time.sleep(0.1)
            if access != "" :
                print (access)
                print GPIO.input(relay)
                if GPIO.input(relay):
                    led_blink(red_led)
                else :
                    if access == "6D00346B5062":
                        GPIO.output(relay,1)
                        led_blink(green_led)
                    else:
                        led_blink(red_led)
                        
        if not GPIO.input(switch):
            if GPIO.input(relay):
                #if pps == 0 or pps == 1:
                print_ser.close()
                GPIO.output(relay,0)
                startup = 0
                led_blink(green_led)    
        if GPIO.input(relay) and startup == 0 :
            try :
                time.sleep(40)
                print "locked"
                print_ser.port = "/dev/ttyUSB0"
                print_ser.baudrate = 115200
                print_ser.open()
                while 1:
                    out = print_ser.readline()
                    print(out)
                    if out == "wait\r\n":
                        break
                    startup=1
            except :
                print "cannot connect to printer" 
                GPIO.output(relay,0)
                led_blink(red_led)
        if pps == 4 and startup == 1 :
            print("sending command...")
            printfile = open("./uploads/job.gcode","r")
            content = printfile.read()
            printfile.close()
            content=content.split("\n")
            pps = 0
            line_no = 0
            out = "ok 0"
            ser_flush(print_ser)
        if GPIO.input(relay) and startup == 1 :
            if pps == 0:
                if line_no < len(content) :
                    if "ok 0" in out or "wait" in out:
                        if counter > 10 :
                            print_ser.write("M105\r")
                            counter = 0;
                        else:
                            while 1:
                                line = content[line_no].strip()
                                if line.find(";") != -1 :
                                    line = line[:line.find(";")].strip()
                                if line != "" :
                                    line_no += 1
                                    break
                                line_no += 1
                                if line_no > len(content):
                                    pps=2
                                    break
                            if pps == 0:
                                print_ser.write(line+'\r')
                                print line
                        progress = (line_no/float(len(content)))*100
                        counter += 1
	    if pps == 1:
            	counter += 0.25
            if pps == 2:
            	counter += 0.25
            if counter > 10 and pps != 0 and startup == 1:
            	print_ser.write("M105\r")
            	counter = 0
            if out.find("T:") != -1:
                etemp = out[out.find("T:")+2:].strip()
                etemp = etemp[:etemp.find(" ")].strip()
                if line_no > 5 :
                    counter += 0.5
            if out.find("B:") != -1:
                btemp=out[out.find("B:")+2:].strip()
                btemp=btemp[:btemp.find(" ")].strip()
                if line_no > 5 :
                    counter += 0.5
            if out.find("TargetBed:") == 0:
                btargettemp = out[out.find("TargetBed:")+10:].strip()
            if out.find("TargetExtr0:") == 0:
                etargettemp = out[out.find("TargetExtr0:")+12:].strip()
        out=""
        if startup == 1 and print_ser.inWaiting() > 0:
            #while print_ser.inWaiting() > 0:
            out = print_ser.readline()
            out.strip()
            print out
    rfid_ser.close()



