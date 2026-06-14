from picoware.system.agent.agent import Agent, MODE_APP_CREATOR
from picoware.system.agent.llm import DEEPSEEK
from picoware.system.view_manager import ViewManager


vm = ViewManager()
agent = Agent(vm, mode=MODE_APP_CREATOR, llm_id=DEEPSEEK)
#topic = "Make me a picoware app that says 'Hello Picoware' and changes color when I click the center button"
topic = "What can you tell me about my device?"
response = agent.run(topic)
print("Agent response:", response)