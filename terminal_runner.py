# terminal_runner.py
import time
import queue
import threading
from process import ProcessThread

if __name__ == "__main__":
    NUM_PROCESSES = 3
    
    print(f"Iniciando simulação no terminal com {NUM_PROCESSES} processos...")

    # Filas compartilhadas
    message_hub = queue.Queue()
    update_hub = queue.Queue()

    # Cria os processos
    processes = []
    for i in range(NUM_PROCESSES):
        p = ProcessThread(i, NUM_PROCESSES, message_hub, update_hub)
        processes.append(p)

    # Inicia as threads
    for p in processes:
        p.start()
        p.resume() # Inicia no modo automático

    # Roteador de mensagens simples
    def router():
        while True:
            sender_id, receiver_id, clock = message_hub.get()
            print(f"[REDE] Roteando msg de P{sender_id+1} para P{receiver_id+1}")
            processes[receiver_id].message_in_queue.put((sender_id, clock))

    threading.Thread(target=router, daemon=True).start()

    # Loop para imprimir atualizações
    while True:
        update = update_hub.get()
        p_id = update['process_id']
        state = processes[p_id].get_state()
        last_event = state['events'][-1]
        print(f"[P{p_id+1}] Evento: {last_event['type']}, Relógio: {last_event['clock']}")
        time.sleep(0.1)