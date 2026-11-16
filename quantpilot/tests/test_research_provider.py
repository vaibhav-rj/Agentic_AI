#from src.config import load_dotenv
import src.config
from src.tools.research_provider import search_research

#load_dotenv()

result = search_research("Apple revenue growth and valuation")

print(result)