import asynqp
import socketio
from aiohttp import web

sio = socketio.AsyncServer(async_mode='aiohttp')
app = web.Application()
sio.attach(app)


async def get_state():
    # connect to the RabbitMQ broker
    connection = await asynqp.connect('172.17.0.2', 5672, username='guest', password='guest')

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
            await sio.emit('update', {
                'instance_id': received_message.json()[0][0],
                'build_number': received_message.json()[0][1],
                'current_action': received_message.json()[0][2],
                'current_state': received_message.json()[0][3]})

            await sio.emit(received_message.json()[0][0], {'log': received_message.json()[0][4]+'\n'})
        except AttributeError:
            pass


if __name__ == "__main__":
    sio.start_background_task(get_state)
    web.run_app(app, host='0.0.0.0', port=5001)
