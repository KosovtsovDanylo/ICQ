from client import MessengerClient
from multiprocessing import Process
import subprocess
import time

def run_server():
    subprocess.run(['python', 'server.py'])

def run_client():
    app = MessengerClient()
    app.mainloop()

if __name__ == "__main__":
    # Start the server process
    server_process = Process(target=run_server)
    server_process.start()
    time.sleep(1)  # Small delay to allow the server to start

    # Start client processes
    p1 = Process(target=run_client)
    p2 = Process(target=run_client)
    p3 = Process(target=run_client)

    p1.start()
    p2.start()
    p3.start()

    p1.join()
    p2.join()
    p3.join()

    # Stop the server process
    server_process.terminate()
    server_process.join()
