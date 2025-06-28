
import random
import queue
import uuid

class Process:
    

    def receive_message(self, sender_id, received_clock, message_id, time_tick, trigger_update=False):       
        current_len = len(self.clock)
        received_len = len(received_clock)
        if received_len < current_len:
            
            received_clock.extend([0] * (current_len - received_len))
        
        for i in range(current_len):
            self.clock[i] = max(self.clock[i], received_clock[i])
        
        self.clock[self.process_id] += 1
        
        self._create_event("receive", self.clock.copy(), time_tick, sender_id=sender_id, message_id=message_id)
        if trigger_update:
            self.update_queue.put(True)
        
    def __init__(self, process_id, num_processes_initial, message_hub_queue, update_queue):
        self.process_id = process_id
        self.clock = [0] * num_processes_initial
        self.events = []
        self.message_in_queue = queue.Queue()
        self.message_hub_queue = message_hub_queue
        self.update_queue = update_queue

    def get_state(self):
        return {"id": self.process_id, "clock": self.clock.copy(), "events": self.events.copy()}

    def add_process_to_clock(self):
        self.clock.append(0)

    def execute_tick_action(self, time_tick):
        if not self.message_in_queue.empty():
            sender_id, received_clock, message_id = self.message_in_queue.get()
            self.receive_message(sender_id, received_clock, message_id, time_tick, trigger_update=True)
            return

        if random.random() < 0.7:
            if random.random() < 0.6 and len(self.clock) > 1:
                self._send_message_async(time_tick)
            else:
                self._local_event(time_tick)

    def force_send_message(self, receiver_id, time_tick):
        self.clock[self.process_id] += 1
        message_id = str(uuid.uuid4())
        self._create_event("send", self.clock.copy(), time_tick, receiver_id=receiver_id, message_id=message_id)
        return self.clock.copy(), message_id

    def _create_event(self, event_type, clock, time_tick, **kwargs):
        event = {"clock": clock, "type": event_type, "time_tick": time_tick, **kwargs}
        self.events.append(event)

    def _local_event(self, time_tick):
        self.clock[self.process_id] += 1
        self._create_event("local", self.clock.copy(), time_tick)
        self.update_queue.put(True)

    def _send_message_async(self, time_tick):
        num_processes = len(self.clock)
        possible_receivers = [i for i in range(num_processes) if i != self.process_id]
        receiver_id = random.choice(possible_receivers)
        
        self.clock[self.process_id] += 1
        message_id = str(uuid.uuid4())
        self._create_event("send", self.clock.copy(), time_tick, receiver_id=receiver_id, message_id=message_id)
        self.message_hub_queue.put((self.process_id, receiver_id, self.clock.copy(), message_id))
        self.update_queue.put(True)