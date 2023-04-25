import yaml
import asyncio
import time
from CommunicationData import CommunicationData
from Flags import Flags
from slack_sdk.web import WebClient
from slack_sdk.webhook import WebhookClient
from slack_sdk.errors import SlackApiError


class Communication:
    def __init__(self):
        CommunicationData.initialize()
        self.token = self.__read_api()
        self.client = WebClient(token=self.token)
    
    def __read_api(self):
        self.api_key = ''
        with open('./ignore/api.yaml', 'r') as f:
            api_keys = yaml.load(f, Loader=yaml.FullLoader)
            return api_keys['slack']['bot_token']


    async def main_loop(self):
        while Flags.get_system_flag():
            await asyncio.sleep(1)
            if len(CommunicationData.messages) > 0:
                self.__send_message_to_slack(CommunicationData.get_message())

    def __send_message_to_slack(self, message):
        try:
            # Call the chat.postMessage method using the WebClient
            response = self.client.chat_postMessage(text=message, channel="#topbottom")
        except SlackApiError as e:
            print(f"Error posting message: {e}")


if __name__ == '__main__':
    Flags.initialize()
    communication = Communication()
    asyncio.run(communication.main_loop())