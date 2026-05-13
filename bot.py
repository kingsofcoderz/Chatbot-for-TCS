import traceback

print("STARTED")

try:
    import os
    import time
    import requests
    import xml.etree.ElementTree as ET
    import json
    from openai import OpenAI

    print("IMPORTS OK")

    NS_NATION = os.getenv("NS_NATION")
    NS_PASSWORD = os.getenv("NS_PASSWORD")
    NS_REGION = os.getenv("NS_REGION")
    NS_CLIENT = os.getenv("NS_CLIENT")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    print("ENV OK")

    client = OpenAI(api_key=OPENAI_API_KEY)

    print("OPENAI INIT OK")

    raise Exception("FORCED STOP TO TEST")

except Exception as e:
    print("CRASH REVEALED:")
    print(traceback.format_exc())
    raise
