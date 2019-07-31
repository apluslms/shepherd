from flask_socketio import SocketIO
from flask import Flask
from flask_cors import CORS

import asynqp

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'secret!'
sio = SocketIO(app)


async def get_state():
    # connect to the RabbitMQ broker
    connection = await asynqp.connect('localhost', 5672, username='guest', password='guest')

    # Open a communications channel
    channel = await connection.open_channel()

    # Create a queue and an exchange on the broker
    queue = await channel.declare_queue('celery_state')
    while True:
        # Synchronously get a message from the queue
        received_message = await queue.get()
        try:
            print(received_message.json())  # get JSON from incoming messages easily
            received_message.ack()
            sio.emit('update', {
                'instance_id': received_message.json()[0][0],
                'build_number': received_message.json()[0][1],
                'current_action': received_message.json()[0][2],
                'current_state': received_message.json()[0][3]})

            sio.emit(received_message.json()[0][0], {'log': received_message.json()[0][4] + '\n'})
        except AttributeError:
            pass


if __name__ == "__main__":
    sio.start_background_task(get_state)
    sio.run(app, host='0.0.0.0', port=5001)

