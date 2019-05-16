import asyncio

import asynqp

from aiohttp import web
import socketio

sio = socketio.AsyncServer(async_mode='aiohttp')
app = web.Application()
sio.attach(app)


async def background_task():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        await sio.sleep(10)
        count += 1
        await sio.emit('my response', {'data': 'Server generated event'}, namespace='/test')


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
            await sio.emit('update', {
                'instance_id': received_message.json()[0][0],
                'build_number': received_message.json()[0][1],
                'current_action': received_message.json()[0][2],
                'current_state': received_message.json()[0][3]})
            await sio.emit(received_message.json()[0][0], {'log': received_message.json()[0][4]+'\n'})
        except AttributeError:
            pass


if __name__ == "__main__":
    # loop = asyncio.get_event_loop()
    # loop.create_task(get_state())
    sio.start_background_task(get_state)
    web.run_app(app, port=5001)
