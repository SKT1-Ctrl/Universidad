from flask import Flask, Response  # Framework web para Python
import cv2  # OpenCV para manejo de video
import threading  # Para ejecutar la captura de video en paralelo
import socket  # Para obtener la IP local
import logging  # Para registro de errores

app = Flask(__name__)  # Crear aplicación Flask
camera = None
output_frame = None
lock = threading.Lock()  # Bloqueo para sincronización entre hilos
camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_FPS, 30)

# Función para obtener la IP local del equipo
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# Función que se ejecuta en un hilo separado para capturar continuamente frames de la cámara
def capture_frames():
    global output_frame, camera
    
    # Probar diferentes índices de cámara
    for camera_index in range(3):  # Probar índices 0, 1 y 2
        print(f"Intentando conectar con cámara en índice {camera_index}")
        camera = cv2.VideoCapture(camera_index)
        
        if camera.isOpened():
            print(f"Cámara encontrada en índice {camera_index}")
            
            # Añadir estas líneas para verificar si puede leer frames
            print("Intentando leer primer frame...")
            success, frame = camera.read()
            print(f"Lectura del primer frame: {'exitosa' if success else 'fallida'}")
            if success:
                print(f"Dimensiones del frame: {frame.shape}")
            
            break
        else:
            print(f"No se encontró cámara en índice {camera_index}")
            camera.release()
    
    if not camera.isOpened():
        logging.error("No se pudo abrir ninguna cámara")
        return
    
    # Verificar propiedades de la cámara
    width = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps = camera.get(cv2.CAP_PROP_FPS)
    print(f"Cámara abierta con resolución: {width}x{height}, FPS: {fps}")
    
    while True:
        success, frame = camera.read()
        if not success:
            print("Error al leer frame de la cámara")
            break
            
        with lock:
            output_frame = frame.copy()
    
    camera.release()

# Función generadora para streaming de video
def generate():
    global output_frame
    while True:
        with lock:
            if output_frame is None:
                continue
            
            # Codificar el frame como JPEG
            (flag, encoded_image) = cv2.imencode(".jpg", output_frame)
            if not flag:
                continue
        
        # Formato de stream MJPEG        
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encoded_image) + b'\r\n')

# Ruta principal que muestra una página HTML simple
@app.route("/")
def index():
    return """
    <html>
      <head>
        <title>Cámara USB a IP</title>
      </head>
      <body>
        <h1>Stream de Cámara USB</h1>
        <img src="/video_feed">
      </body>
    </html>
    """

# Ruta que proporciona el stream de video
@app.route("/video_feed")
def video_feed():
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

# Punto de entrada principal
if __name__ == "__main__":
    # Iniciar un hilo para la captura de frames
    t = threading.Thread(target=capture_frames)
    t.daemon = True
    t.start()
    
    # Obtener la IP del equipo
    ip = get_ip()
    print(f"Servidor iniciado en http://{ip}:5000")
    
    # Iniciar el servidor Flask en la IP local y hacerlo accesible desde el exterior
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
