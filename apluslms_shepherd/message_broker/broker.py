import asyncio
import asynqp


async def get_state():
    # connect to the RabbitMQ broker
    connection = await asynqp.connect('localhost', 5672, username='guest', password='guest')

    # Open a communications channel
    channel = await connection.open_channel()

    # Create a queue and an exchange on the broker
    queue = await channel.declare_queue('celery_state')
    # Synchronously get a message from the queue
    received_message = await queue.get()
    print(received_message.json())  # get JSON from incoming messages easily

    # Acknowledge a delivered message
    received_message.ack()

    # await channel.close()
    # await connection.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(get_state())
    loop.run_forever()
