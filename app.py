
import threading
import time
import queue
from flask import Flask, render_template
from flask_socketio import SocketIO
from process import Process 

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')

class SimulationManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.processes = []
        self.message_hub_queue = queue.Queue()
        self.update_queue = queue.Queue()
        self.simulation_mode = "paused"
        self.global_time_tick = 0
        self.auto_run_thread = None

        threading.Thread(target=self.frontend_updater_loop, daemon=True).start()
        threading.Thread(target=self.message_router_loop, daemon=True).start()

    def get_state(self):
        with self.lock:
            return {
                "processes": [p.get_state() for p in self.processes],
                "mode": self.simulation_mode,
                "global_time": self.global_time_tick
            }

    def broadcast_state(self):
        socketio.emit('state_update', self.get_state())

    def start_auto_mode(self):
        with self.lock:
            if self.simulation_mode == 'running': return
            self.simulation_mode = 'running'
            if self.auto_run_thread is None or not self.auto_run_thread.is_alive():
                self.auto_run_thread = threading.Thread(target=self.auto_ticker_loop, daemon=True)
                self.auto_run_thread.start()
        self.broadcast_state()

    def pause_simulation(self):
        with self.lock:
            self.simulation_mode = 'paused'
        self.broadcast_state()

    def auto_ticker_loop(self):
        while True:
            with self.lock:
                if self.simulation_mode != 'running':
                    break
            self.advance_tick()
            time.sleep(1.0)
        
    def advance_tick(self):
        with self.lock:
            self.global_time_tick += 1
            for p in self.processes:
                p.execute_tick_action(self.global_time_tick)
        self.update_queue.put(True)

    def force_message(self, sender_id, receiver_id):
        with self.lock:
            if not (0 <= sender_id < len(self.processes) and 0 <= receiver_id < len(self.processes)):
                return
            
            sender_process = self.processes[sender_id]
            receiver_process = self.processes[receiver_id]

            self.global_time_tick += 1
            send_time_tick = self.global_time_tick
            
            message_payload = sender_process.force_send_message(receiver_id, send_time_tick)
                       
            if message_payload:
                self.global_time_tick += 1
                receive_time_tick = self.global_time_tick
                
                sent_clock, message_id = message_payload
                receiver_process.receive_message(sender_id, sent_clock, message_id, receive_time_tick)

        self.update_queue.put(True)

    def add_process(self):
        with self.lock:
            num_processes = len(self.processes)
            for p in self.processes:
                p.add_process_to_clock()
            new_proc = Process(
                process_id=num_processes, 
                num_processes_initial=num_processes + 1,
                message_hub_queue=self.message_hub_queue,
                update_queue=self.update_queue
            )
            self.processes.append(new_proc)
        self.broadcast_state()
    
    def reset(self):
        self.pause_simulation()
        with self.lock:
            self.processes.clear()
            self.global_time_tick = 0
            while not self.message_hub_queue.empty(): self.message_hub_queue.get()
            while not self.update_queue.empty(): self.update_queue.get()
        self.broadcast_state()

    def frontend_updater_loop(self):
        while True:
            self.update_queue.get() 
            self.broadcast_state()

    def message_router_loop(self):
        while True:
            try:
                sender_id, receiver_id, clock, message_id = self.message_hub_queue.get(timeout=1)
                with self.lock:
                    if 0 <= receiver_id < len(self.processes):
                        self.processes[receiver_id].message_in_queue.put((sender_id, clock, message_id))
            except queue.Empty:
                continue

manager = SimulationManager()

@app.route('/')
def index(): return render_template('index.html')

@socketio.on('connect')
def h_connect(): manager.broadcast_state()

@socketio.on('simulation:start')
def h_start(): manager.start_auto_mode()

@socketio.on('simulation:pause')
def h_pause(): manager.pause_simulation()

@socketio.on('simulation:tick')
def h_tick(): manager.advance_tick()

@socketio.on('process:add')
def h_add(): manager.add_process()

@socketio.on('simulation:reset')
def h_reset(): manager.reset()

@socketio.on('message:force_send')
def h_force(data): 
    manager.force_message(data['sender_id'], data['receiver_id'])

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)