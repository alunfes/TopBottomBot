import yaml
import asyncio
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext


class CommunicationData2:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.message = []
        self.message_lock = asyncio.Lock()
        self.token = self.__read_api()

    def __read_api(self):
        self.api_key = ''
        with open('./ignore/api.yaml', 'r') as f:
            api_keys = yaml.load(f, Loader=yaml.FullLoader)
            self.api_key = api_keys['telegram']['public_key']
    

    async def send_message_to_telegram(self):
        bot = Bot(self.token)

        while True:
            async with self.message_lock:
                if self.message:
                    text = self.message.pop(0)
                else:
                    text = None

            if text:
                bot.send_message(chat_id=self.chat_id, text=text)

            await asyncio.sleep(1)

    @staticmethod
    def status_command(update: Update, context: CallbackContext):
        update.message.reply_text("status")

    @staticmethod
    def start_command(update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        communication_data = CommunicationData2(chat_id)
        context.bot_data["communication_data"] = communication_data

    async def start_bot(self):
        def run_polling(updater):
            updater.start_polling()
            updater.idle()

        updater = Updater(self.token)

        # Get the dispatcher to register handlers
        dp = updater.dispatcher

        # Add the command handlers
        dp.add_handler(CommandHandler("start", self.start_command))
        dp.add_handler(CommandHandler("status", self.status_command))

        # Start the bot in a separate thread
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_polling, updater)