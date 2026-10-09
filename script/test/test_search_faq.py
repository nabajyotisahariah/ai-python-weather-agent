import sys
import os
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from app.tools.crewai.faq import search_faq, search_faq_v2

def test():
    query = "Does the Weather Demo provide an SLA?"
    print(f"--- Testing search_faq ---")
    try:
        result1 = search_faq.func(query)
        print(f"Result 1:\n{result1}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    print(f"--- Testing search_faq_v2 ---")
    try:
        result2 = search_faq_v2.func(query)
        print(f"Result 2:\n{result2}\n")
    except Exception as e:
        print(f"Error: {e}\n")

if __name__ == "__main__":
    test()