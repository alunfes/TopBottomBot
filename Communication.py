import yaml
import logging
import asyncio
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes
from CommunicationData import CommunicationData


class Communication:
    def __init__(self):
        CommunicationData.initialize()
        self.__read_api()
        # Create updater object and add handlers
        self.application = ApplicationBuilder().token(self.api_key).build()
        start_handler = CommandHandler('start', self.start)
        echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), self.echo)
        self.application.add_handler(start_handler)
        self.application.add_handler(echo_handler)
        self.application.add_handler(CommandHandler("status", self.get_status))
        self.chat_id = None
        self.__get_comm_data_thread()
        #self.application.run_polling()



    def fire_and_forget(func):
        def wrapper(*args, **kwargs):
            loop = asyncio.get_event_loop()
            func_coro = func(*args, **kwargs)
            task = loop.create_task(func_coro)
            task.add_done_callback(lambda _: None)
        return wrapper

    def __read_api(self):
        self.api_key = ''
        with open('./ignore/api.yaml', 'r') as f:
            api_keys = yaml.load(f, Loader=yaml.FullLoader)
            self.api_key = api_keys['telegram']['public_key']


    @fire_and_forget
    async def __get_comm_data_thread(self):
        while True:
            if len(CommunicationData.messages) > 0:
                if self.chat_id is not None:
                    await self.send_message(self.chat_id, CommunicationData.messages[0])
            await asyncio.sleep(1)


    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")
        print('chat id=', self.chat_id)
    
    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Res: ' + update.message.text)
    
    async def get_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text('running')

    async def send_message(self, chat_id, message: str) -> None:
        await self.application.bot.send_message(chat_id=chat_id, text=message)

    async def main_loop(self):
        while True:
            await asyncio.sleep(5)
    




if __name__ == '__main__':
    communication = Communication()
    asyncio.gather(communication.main_loop())


    