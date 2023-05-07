import yaml
import asyncio
import time
import re
import requests
import discord

from CommunicationData import CommunicationData
from Flags import Flags


class Communication:
    def __init__(self):
        CommunicationData.initialize()
        self.__read_api()
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = MyClient(intents=intents)
        #self.client.run(self.bot_token)

    
    def __read_api(self):
        self.api_key = ''
        with open('./ignore/api.yaml', 'r') as f:
            api_keys = yaml.load(f, Loader=yaml.FullLoader)
            self.bot_token = api_keys['discord']['bot_token']

    def fire_and_forget(func):
        def wrapper(*args, **kwargs):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_in_executor(None, func, *args, *kwargs)
        return wrapper

    

    async def main_loop(self):
        await self.client.start(self.bot_token)
        


class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self) -> None:
        self.tg_task = self.loop.create_task(self.post_communication_data())

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        self.channel = discord.Client.get_channel(1103166554138484826)
        


    async def post_communication_data(self):
        await self.wait_until_ready()
        channel = self.get_channel(1103166554138484826)
        while not self.is_closed():
            if len(CommunicationData.messages) > 0:
                await channel.send(CommunicationData.get_message())
            await asyncio.sleep(1)
        
        
    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')
        if message.content.startswith('bs'):
            await message.reply('AccountData.get_bs()', mention_author=True)



if __name__ == '__main__':
    Flags.initialize()
    communication = Communication()
    #communication.get_message()
    asyncio.run(communication.main_loop())
    