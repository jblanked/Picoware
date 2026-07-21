from picoware.system.agent.agent import Agent
from picoware.system.agent.llm import DEEPSEEK, LLM
from picoware.system.view_manager import ViewManager


vm = ViewManager()

# simple
agent = Agent(vm)
topic = "What can you tell me about my device?"
response = agent.run(topic)
print("Agent response:", response)

del agent
del response

# advanced
llm = LLM(vm.storage, DEEPSEEK, "deepseek-v4-flash")
agent = Agent(vm, llm)
topic = "Make me a picoware app that says 'Hello Picoware' and changes color when I click the center button"
response = agent.run(topic)
print("Agent response:", response)