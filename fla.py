from flask import Flask, render_template, redirect, Response
import sqlite3
import matplotlib.pyplot as plt
import RPi.GPIO as GPIO
import base64, io
import serial
import cv2

plt.rcParams['font.family'] ='NanumSquare'
plt.rcParams['axes.unicode_minus'] =False
plt.rcParams["figure.figsize"] = [2000, 1200]
plt.rcParams["figure.dpi"] = 300

app = Flask(__name__)

def sql(name):
    conn = sqlite3.connect("sensor.db")
    data = conn.execute(f"SELECT * FROM {name}").fetchall()
    conn.close()
    return data

def plotsql_to_base64png(data):
    id, humidities, temperatures, distances, timestamps = zip(*data[-51:])

    # plt.rcParams.update({
    # "figure.facecolor":  (1.0, 1.0, 1.0, 0.2),
    # "axes.facecolor":    (1.0, 1.0, 1.0, 0.4),
    # "savefig.facecolor": (1.0, 1.0, 1.0, 0.2),
    # })

    plt.figure(figsize=(10, 6), facecolor='white')
    plt.plot(id, humidities, label='습도')
    plt.plot(id, temperatures, label='온도')
    plt.plot(id, distances, label='거리')

    plt.title('센서값')
    plt.xlabel('#')
    plt.ylabel('값')
    plt.legend()
    plt.xticks(id[::5], rotation=45)
    plt.grid()

    

    imgfile = io.BytesIO()
    plt.savefig(imgfile, format="png")  # 이미지 파일로 저장
    url = "data:image/png;base64,"+(base64.b64encode(imgfile.getvalue())).decode('utf-8')
    return url

def dhtserial():
    ser = serial.Serial('/dev/ttyACM0', 9600)

    try:
        data1 = ser.readline()
        decoded_data1 = data1.decode('utf-8')
        data2 = ser.readline()
        decoded_data2 = data2.decode('utf-8')
        data3 = ser.readline()
        decoded_data3 = data3.decode('utf-8')

        serial_input = decoded_data1 + decoded_data2 + decoded_data3
        
        lines = serial_input.split('\n')
        parsed_values = {}

        for line in lines:
            parts = line.split(':')
            if len(parts) == 2:
                key = parts[0].strip() 
                if key == "gh": key = "ground_humi"
                if key == "h": key = "humi"
                if key == "t": key = "temp"
                value_str = parts[1].strip()

                if value_str.lower() == 'nan':
                    value = float('nan')
                else:
                    value = float(value_str)

                parsed_values[key] = value

        print(parsed_values)
        return parsed_values

    except:
        return dhtserial()

    ser.close()

def generate_frames():
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    capture.read()
    while True:
        success, frame = capture.read()  # 웹캠에서 프레임 읽기
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def root():
    data = sql("Measure1")
    b64png = plotsql_to_base64png(data)
    real = dhtserial()
    return render_template("index.html", data=data, real=real, imgurl=b64png)

@app.route('/system/led_off')
def rodot():
    GPIO.output(relay_pin, GPIO.LOW)
    return redirect("/")

@app.route('/system/led_on')
def rodt():
    GPIO.output(relay_pin, GPIO.HIGH)
    return redirect("/")

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    GPIO.setmode(GPIO.BCM)
    relay_pin = 21
    GPIO.setup(relay_pin, GPIO.OUT)
    capture = cv2.VideoCapture(0)
    app.run(debug=True, host='0.0.0.0')