# terminal_runner.py
import time
import queue
import threading
import random
from process import Process

if __name__ == "__main__":
    NUM_PROCESSES = 3
    
    print(f"Iniciando simulação no terminal com {NUM_PROCESSES} processos...")

    # Filas compartilhadas
    message_hub = queue.Queue()
    update_hub = queue.Queue()

    # Cria os processos
    processes = []
    for i in range(NUM_PROCESSES):
        p = Process(i, NUM_PROCESSES, message_hub, update_hub)
        processes.append(p)

    # Roteador de mensagens simples
    def router():
        while True:
            sender_id, receiver_id, clock, message_id = message_hub.get()
            print(f"[REDE] Roteando msg de P{sender_id+1} para P{receiver_id+1}")
            processes[receiver_id].message_in_queue.put((sender_id, clock, message_id))

    threading.Thread(target=router, daemon=True).start()

    def process_simulation_loop(process):
        time_tick = 0
        while True:
            process.execute_tick_action(time_tick)
            time_tick += 1
            time.sleep(random.uniform(0.5, 1.5))

    for p in processes:
        thread = threading.Thread(target=process_simulation_loop, args=(p,), daemon=True)
        thread.start()


    # Loop para imprimir atualizações
    printed_event_counts = [0] * NUM_PROCESSES
    while True:
        update_hub.get()

        for i, p in enumerate(processes):
            state = p.get_state()
            current_events_count = len(state['events'])
            
            if current_events_count > printed_event_counts[i]:
                new_events = state['events'][printed_event_counts[i]:]
                for event in new_events:
                    print(f"[P{i+1}] Evento: {event['type']}, Relógio: {event['clock']}")
                printed_event_counts[i] = current_events_count
        
        while not update_hub.empty():
            try:
                update_hub.get_nowait()
            except queue.Empty:
                break